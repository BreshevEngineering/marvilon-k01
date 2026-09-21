import importlib.util,json,sys,tempfile,unittest,urllib.request,urllib.error,threading
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'center/panel'))
from model import Model
from server import Server
class PanelTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
 def tearDown(self):self.tmp.cleanup()
 def put(self,p,d):
  q=self.root/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(json.dumps(d),encoding='utf-8')
 def test_missing_is_not_pass(self):self.assertEqual(Model(self.root).state()['overall'],'MISSING')
 def test_broken_json_is_visible(self):
  self.put('evidence/verdict.json',{});(self.root/'evidence/verdict.json').write_text('{');self.assertEqual(Model(self.root).state()['overall'],'ERROR')
 def test_reasons_and_semantic_hash_retained(self):
  self.put('evidence/verdict.json',{'overall':'HOLD','nodes':{'FEMM':{'status':'HOLD','reasons':['No physical qualification'],'semantic_sha256':'abc'}}})
  d=Model(self.root).state();self.assertEqual(d['blockers'][0]['reasons'],['No physical qualification']);self.assertEqual(d['groups']['nodes'][0]['semantic_sha256'],'abc')
 def test_changed_input_does_not_overwrite_engine_verdict(self):
  self.put('control/input.json',{});self.put('evidence/verdict.json',{'overall':'PASS','inputs':[{'path':'control/input.json','sha256':'wrong'}]})
  d=Model(self.root).state();self.assertEqual(d['overall'],'PASS');self.assertEqual(d['input_checks'][0]['state'],'CHANGED')
 def test_path_escape(self):
  with self.assertRaises(ValueError):Model(self.root).resolve('../outside.txt')
 def test_malformed_ledger_visible(self):
  self.put('evidence/ledger.jsonl',{'command':'audit'});p=self.root/'evidence/ledger.jsonl';p.write_text(p.read_text()+'\ninvalid');d=Model(self.root).state();self.assertEqual(len(d['history_errors']),1)
 def test_bom_quantity_zero_preserved(self):
  self.put('reports/bom/current/K01_EBOM_A001_CURRENT.json',{'status':'HOLD','rows':[{'PartNo':'retired','Qty':0}]});self.assertEqual(Model(self.root).state()['boms']['ebom']['rows'][0]['Qty'],0)
 def test_transport_blocks_cross_origin_and_unknown_command(self):
  s=Server(self.root,0);t=threading.Thread(target=s.serve_forever,daemon=True);t.start()
  try:
   d=json.load(urllib.request.urlopen(s.origin+'/api/state'));self.assertEqual(d['overall'],'MISSING')
   for headers,command,code in [({},'verdict',403),({'Origin':s.origin,'X-K01-Token':s.token},'release',400)]:
    req=urllib.request.Request(s.origin+'/api/run',data=json.dumps({'command':command}).encode(),headers=headers)
    with self.assertRaises(urllib.error.HTTPError) as c:urllib.request.urlopen(req)
    self.assertEqual(c.exception.code,code)
   self.assertEqual(urllib.request.urlopen(s.origin+'/').status,200)
  finally:s.shutdown();s.server_close()
 def test_install_preserves_unknown_dispatcher(self):
  spec=importlib.util.spec_from_file_location('installer',Path(__file__).resolve().parents[1]/'install.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  p=self.root/'run.cmd';p.write_text('existing dispatcher');m.install(self.root);self.assertEqual(p.read_text(),'existing dispatcher')
if __name__=='__main__':unittest.main()
