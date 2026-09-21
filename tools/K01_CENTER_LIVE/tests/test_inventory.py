import json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from requirements_inventory import inventory
from p007 import work_item
class Inventory(unittest.TestCase):
 def test_duplicate_and_history(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)
   for rel,val in [('control/requirements/a.json',1),('control/requirements/b.json',2),('control/requirements/history/c.json',3)]:
    p=root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps({'requirements':[{'id':'R1','value':val}]}))
   result=inventory(root)
   self.assertEqual(len(result['files']),3)
   self.assertEqual(len(result['duplicate_ids']),1)
   self.assertEqual(len(result['duplicate_ids'][0]['sources']),2)
 def test_exact_action(self):
  actions={'C12':{'next_action':'Source instruction','expected_evidence':'Source evidence'}}
  self.assertEqual(work_item({'id':'C12'},actions)['suggested_action'],'Source instruction')
  self.assertIn('NOT_DECLARED',work_item({'id':'C12-renamed'},actions)['suggested_action'])
 def test_no_arbitrary_status(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'control/requirements/tool.json';p.parent.mkdir(parents=True);p.write_text('{"nested":{"id":"R1","status":"PASS"}}')
   self.assertEqual(inventory(d)['occurrences'],[])
