"""Saved-file observation only; never computes engineering acceptance."""
import os
import threading
from datetime import datetime, timezone
from pathlib import Path


class Monitor:
    def __init__(self, roots, interval=3):
        self.roots = {name: Path(path).resolve() for name, path in roots.items() if path}
        self.interval = interval
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self.previous = {}
        self.initialized = set()
        self.events = []
        self.checked = None
        self.errors = []
        self.sequence = 0

    def scan(self):
        now = datetime.now(timezone.utc).isoformat()
        errors = []
        with self.lock:
            for name, root in self.roots.items():
                current = {}
                failures = []
                if not root.is_dir():
                    failures.append('Directory unavailable: ' + str(root))
                else:
                    for folder, dirs, files in os.walk(root, onerror=lambda e: failures.append(str(e)), followlinks=False):
                        dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', 'node_modules', '.venv', 'runtime'} and not (Path(folder)/d).is_symlink()]
                        for filename in files:
                            p = Path(folder)/filename
                            if p.is_symlink() or filename.startswith('~$'):
                                continue
                            try:
                                stat = p.stat()
                                current[p.relative_to(root).as_posix()] = (stat.st_mtime_ns, stat.st_size)
                            except OSError as exc:
                                failures.append(str(exc))
                errors.extend(failures)
                # A partial scan cannot prove deletion; retain the previous baseline.
                if failures:
                    continue
                old = self.previous.get(name, {})
                if name in self.initialized:
                    for path in sorted(old.keys() | current.keys()):
                        kind = 'DELETED' if path not in current else 'CREATED' if path not in old else 'MODIFIED' if current[path] != old[path] else None
                        if kind:
                            self.sequence += 1
                            self.events.insert(0, dict(id=self.sequence, observed_utc=now, root=name, path=path, event=kind))
                self.previous[name] = current
                self.initialized.add(name)
            self.events = self.events[:200]
            self.errors = errors
            self.checked = now

    def state(self):
        with self.lock:
            return dict(state='PARTIAL' if self.errors else 'OBSERVING' if self.checked else 'STARTING', checked_utc=self.checked,
                        interval_seconds=self.interval, sequence=self.sequence, events=list(self.events), errors=list(self.errors),
                        roots={k: str(v) for k,v in self.roots.items()}, files=sum(len(v) for v in self.previous.values()))

    def run(self):
        while not self.stop.is_set():
            self.scan()
            self.stop.wait(self.interval)
