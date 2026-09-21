import json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from model import Model
class Diagnostics(unittest.TestCase):
 def test_v3_connections(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)
   def write(p,v):
    f=root/p;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(json.dumps(v))
   write('evidence/current/K01_CENTER_VIEW.json',{'schema':'k01.center.view.v3','verdict':'HOLD','blockers':[{'id':'BOM','severity':'HOLD','reason':'Open seal'}]})
   write('evidence/current/K01_EVIDENCE_INDEX.json',{'files':{'drawing':{'report':'reports/drawings/current/D006.json'}}})
   write('reports/drawings/current/D006.json',{'status':'HOLD'})
   write('reports/bom/current/K01_EBOM_A001_CURRENT.json',{'rows':[{'part_number':'K01-P-007','release_state':'HOLD'}]})
   s=Model(root).state()
   self.assertEqual(s['blockers'][0]['status'],'HOLD')
   self.assertTrue(any(a['file_id'] and a['path'].endswith('D006.json') for a in s['artifacts']))
   self.assertEqual(s['boms']['ebom']['rows'][0]['part_number'],'K01-P-007')
