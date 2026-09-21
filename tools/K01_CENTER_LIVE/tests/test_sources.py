import sys,json,tempfile,unittest,threading,urllib.request,zipfile,io
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from model import Model
from server import Server
class Sources(unittest.TestCase):
 def setUp(self):self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
 def tearDown(self):self.temp.cleanup()
 def put(self,name,d):
  p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d));return p
 def test_alternative_is_not_used(self):
  self.put('control/state/K01_STATE_CURRENT_v8.json',{'production_release':'PASS'})
  d=Model(self.root).state();self.assertEqual(d['overall'],'MISSING');self.assertTrue(d['source_candidates'])
 def test_explicit_source(self):
  self.put('evidence/current/K01_CENTER_VIEW.json',{'schema':'k01.center.view.v3','verdict':'HOLD','blockers':[{'id':'FEMM','severity':'HOLD'}]})
  d=Model(self.root).state();self.assertEqual(d['overall'],'HOLD');self.assertEqual(d['blockers'][0]['status'],'HOLD')
 def test_nested_tool_status_is_not_engineering(self):
  self.put('evidence/current/K01_CENTER_VIEW.json',{'schema':'k01.center.view.v3','verdict':'HOLD','tool':{'status':'ok'}})
  d=Model(self.root).state();self.assertEqual(d['groups']['nodes'],[]);self.assertEqual(d['blockers'],[])
 def test_unknown_schema(self):
  self.put('evidence/current/K01_CENTER_VIEW.json',{'schema':'unknown','verdict':'PASS'})
  self.assertEqual(Model(self.root).state()['overall'],'UNSUPPORTED_SCHEMA')
 def test_missing_does_not_fabricate_data(self):
  d=Model(self.root).state();self.assertEqual(d['overall'],'MISSING');self.assertEqual(d['commands'],[])
 def test_bom_issues_visible_without_verdict(self):
  self.put('reports/bom/current/K01_EBOM_A001_CURRENT.json',{'status':'HOLD','issues':['Supplier missing'],'rows':[]})
  self.assertEqual(Model(self.root).state()['blockers'][0]['reasons'],['Supplier missing'])
 def test_corrupt_current_does_not_fall_back_to_pass(self):
  self.put('evidence/current/K01_CENTER_VIEW.json',{}).write_text('{')
  self.put('control/state/K01_STATE_CURRENT_v8.json',{'production_release':'PASS'})
  self.assertEqual(Model(self.root).state()['overall'],'ERROR')
 def test_paths_remain_contained(self):
  with self.assertRaises(ValueError):Model(self.root).resolve('../private.json')
 def test_http_and_diagnostics(self):
  before=list(self.root.rglob('*'));s=Server(self.root,0);threading.Thread(target=s.serve_forever,daemon=True).start()
  try:
   d=json.load(urllib.request.urlopen(s.origin+'/api/state'));self.assertEqual(d['overall'],'MISSING')
   raw=urllib.request.urlopen(s.origin+'/diagnostics').read()
   with zipfile.ZipFile(io.BytesIO(raw)) as z:self.assertIn('center_diagnostics.json',z.namelist())
   self.assertEqual(urllib.request.urlopen(s.origin+'/').status,200)
  finally:s.shutdown();s.server_close()
  self.assertEqual(list(self.root.rglob('*')),before)
 def test_capability_contract(self):
  from unittest.mock import patch
  from types import SimpleNamespace
  m=Model(self.root);m.cfg['capability_query_enabled']=True
  data={'schema':'k01.commands.v1','commands':[{'id':'audit','argv':['audit'],'center_enabled':True}]}
  with patch('model.subprocess.run',return_value=SimpleNamespace(returncode=0,stdout=json.dumps(data),stderr='')):
   self.assertEqual(m.available_commands(),{'audit':['audit']})
 def test_capability_error_is_visible(self):
  from unittest.mock import patch
  from types import SimpleNamespace
  m=Model(self.root);m.cfg['capability_query_enabled']=True
  with patch('model.subprocess.run',return_value=SimpleNamespace(returncode=0,stdout='not json',stderr='')):
   self.assertEqual(m.available_commands(),{});self.assertEqual(m.capabilities['state'],'ERROR')
 def test_existing_requirement_documents_are_connected(self):
  self.put('control/requirements/K01_RELEASE_REQUIREMENTS_CURRENT.json',{'schema':'existing.project.schema','load':300})
  self.put('control/requirements/K01_FIXED_COIL_ACTUATOR_REQUIREMENTS.json',{'schema':'existing.actuator.schema','acceptance':'OPEN'})
  d=Model(self.root).state()
  self.assertEqual(d['sources']['requirements']['state'],'AVAILABLE')
  self.assertEqual(d['sources']['requirements']['adapter_state'],'DOCUMENT_ONLY')
  self.assertEqual(d['groups']['requirements'],[])
  self.assertEqual(d['requirement_documents']['actuator_requirements']['acceptance'],'OPEN')
 def test_ui_english(self):
  import re
  for name in ['index.html','app.js']:
   text=(Path(__file__).resolve().parents[1]/'app'/name).read_text();self.assertIsNone(re.search('[\u0400-\u04ff]',text))
if __name__=='__main__':unittest.main()
