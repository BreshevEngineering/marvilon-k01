"""
K01 — диспетчер подкоманд.

Единственная точка входа в проект. Новые .cmd файлы не создаются никогда;
добавляется запись в таблицу COMMANDS ниже.

    run                          список подкоманд
    run <команда> --help         справка по команде
    run verdict                  что блокирует прямо сейчас
    run impact params/k01_params.py
    run build-all

Соглашения:
  * код возврата 0 = PASS, 1 = HOLD (найдены проблемы), 2 = ошибка запуска;
  * каждый вызов пишется в evidence/ledger.jsonl только дописыванием;
  * команды, требующие CAD, помечены needs_cad и отказываются работать
    там, где CAD недоступен, вместо того чтобы падать невнятно;
  * изменяющие команды не запускаются, если repo_guard не проходит.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(os.environ.get("K01_ROOT") or Path(__file__).resolve().parents[1])
LEDGER = ROOT / "evidence" / "ledger.jsonl"
GRAPH = ROOT / "control" / "graph.json"
RUN_VERSION = "1.0.0"


# ------------------------------------------------------------- описание
@dataclass
class Cmd:
    name: str
    help: str
    script: str | None = None          # относительный путь к скрипту
    args: list[str] = field(default_factory=list)
    fn: str | None = None              # имя внутренней функции
    needs_cad: bool = False
    mutates: bool = False               # правит рабочее дерево
    blocking: bool = True               # в build-all останавливает конвейер


COMMANDS: list[Cmd] = [
    Cmd("center", "Open evidence-based local dashboard", script="center/panel/server.py"),
    Cmd("snapshot", "Снять канонические слепки деталей из CAD",
        script="backends/solidworks/k01_backend_solidworks.py",
        args=["--parts", "cad", "--out", "evidence/snapshots"],
        needs_cad=True, mutates=True),

    Cmd("bom", "Сгенерировать EBOM и MBOM из слепков и реестра деталей",
        script="tools/build_bom.py",
        args=["--snapshots", "evidence/snapshots",
              "--registry", "requirements/parts.json",
              "--out", "evidence/bom"],
        mutates=True),

    Cmd("board", "Пересобрать доску прогресса из доказательств",
        script="tools/build_board.py",
        args=["--evidence", "evidence", "--out", "evidence/board/K01_BOARD.html"],
        mutates=True),

    Cmd("compare", "Сравнить слепки разных CAD-бэкендов с допуском",
        script="tools/k01_compare.py",
        args=["--dir-a", "evidence/snapshots",
              "--dir-b", "evidence/snapshots_freecad",
              "--evidence", "evidence/backend_equivalence.json"],
        blocking=False),

    Cmd("audit", "Проверить структуру репозитория и схемы",
        script="tools/repo_guard.py"),

    Cmd("selftest", "Проверить целостность самого управляющего контура",
        script="tools/center_selftest.py"),

    Cmd("verdict", "Вычислить статусы узлов, требований и гейтов", fn="cmd_verdict"),
    Cmd("impact", "Что обесценится, если изменится указанный файл", fn="cmd_impact"),
    Cmd("build-all", "Прогнать весь конвейер по порядку", fn="cmd_build_all"),
]

BY_NAME = {c.name: c for c in COMMANDS}

# Порядок конвейера. Тяжёлые расчёты сюда не входят — они ночные.
PIPELINE = ["audit", "selftest", "snapshot", "bom", "verdict", "board"]


# ------------------------------------------------------------ инструменты
def sha256(path: Path) -> str | None:
    try:
        h = hashlib.sha256()
        with path.open("rb") as fh:
            for c in iter(lambda: fh.read(1 << 16), b""):
                h.update(c)
        return h.hexdigest()
    except OSError:
        return None


def cad_available() -> bool:
    if platform.system() != "Windows":
        return False
    try:
        import win32com.client  # noqa: F401
        return True
    except ImportError:
        return False


def log(entry: dict):
    """Только дописывание. Каждая запись несёт хеш предыдущей."""
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    prev = ""
    if LEDGER.exists():
        with LEDGER.open("rb") as fh:
            lines = fh.read().splitlines()
        if lines:
            prev = hashlib.sha256(lines[-1]).hexdigest()
    entry["prev"] = prev
    entry["run_version"] = RUN_VERSION
    with LEDGER.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")


def run_script(cmd: Cmd, extra: list[str]) -> int:
    script = ROOT / cmd.script
    if not script.exists():
        print(f"[ОШИБ] нет скрипта: {script}")
        return 2
    argv = [sys.executable, str(script)] + cmd.args + extra
    return subprocess.run(argv, cwd=ROOT).returncode


# ---------------------------------------------------------- граф и статусы
def load_graph() -> dict:
    if not GRAPH.exists():
        return {"nodes": [], "gates": []}
    return json.loads(GRAPH.read_text(encoding="utf-8"))


def load_json_dir(rel: str, key: str | None = None) -> list[dict]:
    d = ROOT / rel
    out = []
    if not d.exists():
        return out
    for p in sorted(d.rglob("*.json")):
        try:
            doc = json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"[ДЕФЕ] {p.relative_to(ROOT)}: {exc}")
            continue
        items = doc.get(key) if key and isinstance(doc, dict) else doc
        out.extend(items if isinstance(items, list) else [items])
    return out


def current_hashes(paths) -> dict[str, str]:
    return {p: sha256(ROOT / p) or "" for p in paths}


def build_state() -> dict:
    graph = load_graph()
    requirements = load_json_dir("requirements/definitions")
    evidence = [e for e in load_json_dir("evidence")
                if isinstance(e, dict) and e.get("inputs") is not None]
    tracked = {i["path"] for e in evidence for i in e.get("inputs", [])}
    return {
        "nodes": graph.get("nodes", []),
        "gates": graph.get("gates", []),
        "requirements": requirements,
        "evidence": evidence,
        "current_hashes": current_hashes(tracked),
    }


def cmd_verdict(extra) -> int:
    sys.path.insert(0, str(ROOT / "tools"))
    try:
        import k01_verdict
    except ImportError:
        print("[ОШИБ] tools/k01_verdict.py не найден")
        return 2

    state = build_state()
    if not state["nodes"] and not state["requirements"]:
        print("[НЕТ ] ни узлов графа, ни требований — вычислять нечего")
        return 1

    res = k01_verdict.evaluate(state)
    blocking = [(k, v) for k, v in
                {**res["requirements"], **res["nodes"]}.items()
                if v["status"] != "PASS"]
    blocking.sort(key=lambda kv: k01_verdict.RANK[kv[1]["status"]])

    print(f"итог: {res['overall']}    "
          f"узлов {len(res['nodes'])}, требований {len(res['requirements'])}\n")
    if not blocking:
        print("ничто не блокирует")
    else:
        print("ЧТО БЛОКИРУЕТ:")
        for name, f in blocking:
            print(f"  [{f['status']:8s}] {name}")
            for r in f["reasons"]:
                print(f"             {r}")

    out = ROOT / "evidence" / "verdict.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    return 0 if res["overall"] == "PASS" else 1


def cmd_impact(extra) -> int:
    """Вызывается ДО правки. Отвечает, что обесценится."""
    if not extra:
        print("укажите файл: run impact params/k01_params.py")
        return 2
    target = extra[0].replace("\\", "/")

    evidence = [e for e in load_json_dir("evidence")
                if isinstance(e, dict) and e.get("inputs")]
    direct = [e for e in evidence
              if any(i["path"].replace("\\", "/") == target
                     for i in e["inputs"])]

    graph = load_graph()
    downstream, frontier = set(), {e.get("node") for e in direct if e.get("node")}
    while frontier:
        nxt = set()
        for node in graph.get("nodes", []):
            if node["id"] in downstream:
                continue
            if set(node.get("depends_on", [])) & frontier:
                nxt.add(node["id"])
        downstream |= frontier
        frontier = nxt - downstream

    print(f"изменение: {target}\n")
    if not direct:
        print("прямых доказательств на этом входе нет")
    else:
        print(f"обесценится напрямую ({len(direct)}):")
        for e in direct:
            print(f"  {e.get('id', '?'):18s} {e.get('node', '?')}"
                  f"  ({e.get('schema', '?')})")
    below = downstream - {e.get("node") for e in direct}
    if below:
        print(f"\nпо цепочке ниже ({len(below)}):")
        for n in sorted(below):
            print(f"  {n}")
    gates = [g["id"] for g in graph.get("gates", [])
             if set(g.get("nodes", [])) & downstream]
    if gates:
        print(f"\nзатронутые гейты: {', '.join(gates)}")
    print("\nЭто прогноз. Правку делайте после того, как посмотрели список.")
    return 0


def cmd_build_all(extra) -> int:
    print(f"конвейер: {' -> '.join(PIPELINE)}\n")
    results, failed = [], None
    for name in PIPELINE:
        cmd = BY_NAME[name]
        if cmd.needs_cad and not cad_available():
            print(f"[ПРОП] {name}: CAD недоступен на этой машине")
            results.append((name, "SKIPPED"))
            continue
        print(f"--- {name} " + "-" * (56 - len(name)))
        rc = dispatch(name, [], nested=True)
        results.append((name, "PASS" if rc == 0 else f"HOLD({rc})"))
        if rc != 0 and cmd.blocking:
            failed = name
            break

    print("\n" + "=" * 62)
    for name, status in results:
        print(f"  {name:12s} {status}")
    if failed:
        print(f"\nконвейер остановлен на: {failed}")
        return 1
    print("\nконвейер пройден")
    return 0


# ------------------------------------------------------------- диспетчер
def dispatch(name: str, extra: list[str], nested: bool = False) -> int:
    cmd = BY_NAME[name]
    started = time.time()

    if cmd.needs_cad and not cad_available():
        print(f"[ОШИБ] {name} требует SolidWorks и pywin32 на Windows")
        return 2

    if cmd.mutates and name != "audit" and not nested:
        guard = ROOT / "tools" / "repo_guard.py"
        if guard.exists():
            rc = subprocess.run([sys.executable, str(guard)],
                                cwd=ROOT, capture_output=True).returncode
            if rc != 0 and "--force" not in extra:
                print("[СТОП] repo_guard не проходит. Запустите 'run audit', "
                      "исправьте, либо повторите с --force (будет записано).")
                return 1
            if rc != 0:
                print("[!] выполнено с --force при непройденном repo_guard")

    extra = [a for a in extra if a != "--force"]
    rc = (globals()[cmd.fn](extra) if cmd.fn else run_script(cmd, extra))

    log({"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
         "command": name, "args": extra, "returncode": rc,
         "seconds": round(time.time() - started, 2),
         "host": platform.node(), "cad": cad_available()})
    return rc


def usage() -> int:
    print(f"K01 run {RUN_VERSION}   корень: {ROOT}")
    print(f"CAD доступен: {'да' if cad_available() else 'нет'}\n")
    print("подкоманды:")
    for c in COMMANDS:
        flags = []
        if c.needs_cad:
            flags.append("CAD")
        if c.mutates:
            flags.append("пишет")
        mark = f" [{', '.join(flags)}]" if flags else ""
        print(f"  {c.name:12s} {c.help}{mark}")
    print("\nновые .cmd не создаются — добавьте запись в COMMANDS")
    return 0


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help", "help"):
        return usage()
    name = argv[0]
    if name not in BY_NAME:
        print(f"неизвестная подкоманда: {name}\n")
        return usage() or 2
    return dispatch(name, argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
