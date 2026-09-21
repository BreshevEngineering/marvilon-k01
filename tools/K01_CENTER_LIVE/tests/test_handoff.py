import json,sys,tempfile,unittest,zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
import build_ai_handoff as handoff
class Handoff(unittest.TestCase):
 def setup_tree(self,d):
  root=Path(d)/'repo';app=Path(d)/'center';app.mkdir()
  p=root/'tools/medtas/ai_handoff_v2_0.py';p.parent.mkdir(parents=True);p.write_text('# fixture')
  (app/'settings.json').write_text(json.dumps({'repo_root':str(root)}))
  return root,app
 def test_success_contains_inventory(self):
  with tempfile.TemporaryDirectory() as d:
   root,app=self.setup_tree(d)
   def run(*args,**kwargs):
    p=root/'reports/control/K01_AI_HANDOFF_CURRENT.zip';p.parent.mkdir(parents=True)
    with zipfile.ZipFile(p,'w') as z:z.writestr('state.json','{}')
    return SimpleNamespace(returncode=0)
   with patch.object(handoff,'APP',app),patch.object(handoff.subprocess,'run',side_effect=run):self.assertEqual(handoff.main(),0)
   with zipfile.ZipFile(app/'runtime/handoff/K01_AI_HANDOFF_WITH_REQUIREMENTS.zip') as z:self.assertIn('K01_REQUIREMENTS_INVENTORY.json',z.namelist())
 def test_failure_no_success_package(self):
  with tempfile.TemporaryDirectory() as d:
   root,app=self.setup_tree(d)
   with patch.object(handoff,'APP',app),patch.object(handoff.subprocess,'run',return_value=SimpleNamespace(returncode=7)):
    self.assertEqual(handoff.main(),7)
   self.assertFalse((app/'runtime/handoff/K01_AI_HANDOFF_WITH_REQUIREMENTS.zip').exists())
