import importlib.util, json, pathlib, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
MOD = ROOT / "tools" / "medtas" / "drawing_candidate_lifecycle_v1.py"
spec = importlib.util.spec_from_file_location("drawing_candidate_lifecycle_v1", MOD)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


def test_artifact_record_and_manifest_roundtrip():
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td) / "a.txt"; p.write_text("abc", encoding="utf-8")
        r = m.artifact(p)
        assert r["exists"] is True
        assert r["sha256"] == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        mp = pathlib.Path(td) / "candidate_manifest.json"
        data = {"schema":"k01.drawing_candidate.v1","state":"GENERATED"}
        m.save_manifest(mp, data)
        out = json.loads(mp.read_text(encoding="utf-8"))
        assert out["schema"] == "k01.drawing_candidate.v1"
        assert "updated_utc" in out
