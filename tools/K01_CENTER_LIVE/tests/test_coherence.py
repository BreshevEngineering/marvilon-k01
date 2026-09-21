import json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from model import Model

class Coherence(unittest.TestCase):
 def put(self,root,rel,obj):
  p=root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj),encoding='utf-8');return p
 def test_hold_locks_mutation_lane(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);m=Model(root)
   m.cfg['sources']['assurance_coherence']='reports/control/K01_ASSURANCE_COHERENCE_CURRENT.json'
   self.put(root,'reports/control/K01_ASSURANCE_COHERENCE_CURRENT.json',{'schema':'k01.assurance_coherence.current.v1','status':'HOLD_ASSURANCE_COHERENCE','checks':[{'id':'ACI-001','pass':False}]})
   state=m.state();self.assertEqual(state['action_lock']['state'],'LOCKED');self.assertEqual(state['action_lock']['blocking_checks'],['ACI-001'])
 def test_missing_coherence_is_fail_closed(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);m=Model(root);m.cfg['sources']['assurance_coherence']='reports/control/K01_ASSURANCE_COHERENCE_CURRENT.json'
   self.assertEqual(m.state()['action_lock']['state'],'UNKNOWN')
 def test_pass_does_not_claim_engineering_release(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);m=Model(root);m.cfg['sources']['assurance_coherence']='reports/control/K01_ASSURANCE_COHERENCE_CURRENT.json'
   self.put(root,'reports/control/K01_ASSURANCE_COHERENCE_CURRENT.json',{'schema':'k01.assurance_coherence.current.v1','status':'PASS_ASSURANCE_COHERENCE','checks':[]})
   state=m.state();self.assertEqual(state['action_lock']['state'],'UNLOCKED');self.assertIn('Engineering gates still control',state['action_lock']['reason'])

if __name__=='__main__': unittest.main()
