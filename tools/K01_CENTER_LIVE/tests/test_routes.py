import hashlib,importlib.util,json,sys,tempfile,unittest
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE/'integration'))
from connect import install
from k01_center_routes import main,capabilities
class Routes(unittest.TestCase):
 def test_exit_code_and_capabilities(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);p=root/'tools/pds/k01_pds.py';p.parent.mkdir(parents=True);p.write_text('raise SystemExit(7)')
   self.assertEqual(main(['pds-status'],root),7)
   self.assertTrue(capabilities(root)['commands'][0]['center_enabled'])
   self.assertFalse(capabilities(root)['commands'][2]['center_enabled'])
 def test_guard_and_backup(self):
  with tempfile.TemporaryDirectory() as d:
   import shutil
   root=Path(d)/'project';root.mkdir();original=b'@echo off\r\nexit /b 9\r\n';(root/'run.cmd').write_bytes(original)
   app=Path(d)/'app';(app/'integration').mkdir(parents=True)
   shutil.copyfile(BASE/'integration/k01_center_routes.py',app/'integration/k01_center_routes.py')
   with self.assertRaises(ValueError):install(root,'wrong',app)
   self.assertEqual((root/'run.cmd').read_bytes(),original)
   install(root,hashlib.sha256(original).hexdigest(),app)
   self.assertEqual((app/'runtime/dispatcher_backup/run.cmd.original').read_bytes(),original)
   self.assertTrue((root/'run.cmd').read_bytes().endswith(original))
   before=(root/'run.cmd').read_bytes();install(root,'unused',app);self.assertEqual(before,(root/'run.cmd').read_bytes())
