import sys,unittest
from pathlib import Path
REPO=Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:sys.path.insert(0,str(REPO))
from tools.governance.change_control import classify_path,max_class,DEFAULT_RULES
class TestChangeControl(unittest.TestCase):
    def test_requirement_is_A(self):self.assertEqual(classify_path("control/requirements/x.json",DEFAULT_RULES)["class"],"A")
    def test_candidate_drawing_is_B(self):self.assertEqual(classify_path("control/drawings/K01_D006.json",DEFAULT_RULES)["class"],"B")
    def test_tool_is_C(self):self.assertEqual(classify_path("tools/governance/x.py",DEFAULT_RULES)["class"],"C")
    def test_max_class(self):self.assertEqual(max_class(["C","B","A"]),"A")
if __name__=="__main__":unittest.main()
