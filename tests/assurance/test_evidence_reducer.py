import sys,tempfile,unittest,json
from pathlib import Path
REPO=Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:sys.path.insert(0,str(REPO))
from tools.assurance.evidence_reducer import reduce_evidence,build
class TestEvidenceReducer(unittest.TestCase):
    def test_missing_is_hold(self):
        v=reduce_evidence({"records":[{"source":"x","state":"MISSING","payload":None}],"release_history":[]})
        self.assertEqual(v["verdict"],"HOLD")
    def test_pass_with_blockers_is_contradiction(self):
        ev={"records":[
            {"source":"control/project/K01_PROJECT_CLOSURE_MATRIX.json","state":"PRESENT","payload":{"overall_status":"PASS","domains":[]}},
            {"source":"control/drawings/K01_D006_RELEASE_DEFINITION.json","state":"PRESENT","payload":{"release_blockers":["C10"]}}
        ],"release_history":[]}
        v=reduce_evidence(ev)
        self.assertTrue(any(x["id"]=="RELEASE_PASS_WITH_BLOCKERS" for x in v["contradictions"]))
    def test_three_screens_only(self):
        self.assertEqual(reduce_evidence({"records":[],"release_history":[]})["screens"],["BLOCKERS","GRAPH","RELEASE_HISTORY"])
    def test_center_directory_not_required(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            # No center/ directory at all. Missing controlled evidence must yield HOLD, not import/runtime failure.
            ep,vp,view=build(root)
            self.assertTrue(ep.exists())
            self.assertTrue(vp.exists())
            self.assertEqual(view["verdict"],"HOLD")
            self.assertFalse((root/"center").exists())
if __name__=="__main__":unittest.main()
