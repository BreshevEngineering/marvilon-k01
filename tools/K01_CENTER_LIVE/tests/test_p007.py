import io,json,sys,tempfile,unittest,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from model import Model
from p007 import build_case
from integration_package import collect
class P007(unittest.TestCase):
 def test_scope_and_guidance(self):
  with tempfile.TemporaryDirectory() as d:
   m=Model(d)
   c=build_case(m,[{'id':'K01-D-006:C12 leak','severity':'HOLD'},{'id':'FEMM','severity':'HOLD'}],[],{'ebom':{'rows':[]}})
   self.assertEqual(len(c['issues']),1)
   self.assertIn('NOT_DECLARED',c['issues'][0]['suggested_action'])
   self.assertEqual(c['issues'][0]['severity'],'HOLD')
 def test_export_read_only(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'run.cmd').write_text('@echo off')
   before=list(root.rglob('*'))
   with zipfile.ZipFile(io.BytesIO(collect(Model(root)))) as z:
    self.assertEqual(z.read('project/run.cmd'),b'@echo off')
    manifest=json.loads(z.read('manifest.json'))
    self.assertTrue(any(x['path']=='tools/run.py' and x['state']=='MISSING' for x in manifest))
   self.assertEqual(before,list(root.rglob('*')))
