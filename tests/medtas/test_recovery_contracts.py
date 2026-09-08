import unittest,tempfile,sys,json,subprocess
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools/medtas'))
import build_bom_v2_2 as bom
import final_assembly_promotion_v2_2 as promo
import final_assembly_semantic_verify_v2_2 as sem
from v22_common import save,sha256_file

class RecoveryTests(unittest.TestCase):
 def test_actual_snapshot_contract(self):
  raw=json.loads((ROOT/'reports/cad/current/K01_A001_SEMANTIC_RAW_API_v1_4.json').read_text(encoding='utf-8-sig'))
  reg=json.loads((ROOT/'control/product/parts.json').read_text(encoding='utf-8-sig'))
  out=bom.build(raw,reg)
  self.assertEqual(out['source_component_count'],13);self.assertEqual(len(out['rows']),15)
  self.assertEqual(next(x for x in out['rows'] if x['PartNo']=='K01-P-007')['Material'],'AISI 316L / EN 1.4404')
  self.assertEqual(out['status'],'HOLD')
 def test_missing_raw_cannot_pass(self): self.assertIn('CAD_OCCURRENCES_MISSING',bom.build({}, {})['issues'])
 def test_duplicate_occurrences_counted(self):
  raw={'status':'OK','assembly':{'component_count':2},'instances':[{'path':'K01-P-001.SLDPRT','suppressed':False}]*2}
  self.assertEqual(bom.build(raw,{'items':{}})['rows'][0]['Qty'],2)
 def test_unidentified_occurrence_blocks(self):
  out=bom.build({'instances':[{'name':'unknown','suppressed':False}]},{})
  self.assertTrue(any(x.startswith('UNIDENTIFIED') for x in out['issues']))
 def test_suppressed_not_counted(self):
  out=bom.build({'instances':[{'path':'K01-P-001.SLDPRT','suppressed':True}]},{})
  self.assertEqual(out['source_component_count'],0);self.assertTrue(out['suppressed'])
 def test_verify_never_launches_adapter(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);save(r/promo.BASE,{'source':'cad/missing.SLDASM','target':'cad/final_candidate/R01/A.SLDASM'})
   with patch.object(sys,'argv',['prog','--repo-root',d,'--mode','verify']),patch.object(promo.subprocess,'run',side_effect=AssertionError('MUTATION')):
    self.assertEqual(promo.main(),2)
   self.assertFalse((r/'cad').exists())
 def test_target_escape_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(ValueError):promo.paths(Path(d),{'source':'cad/A.SLDASM','target':'../escape.SLDASM'})
 def test_external_cad_root(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);s,t=promo.paths(r,{'source':'cad/A.SLDASM','target':'cad/final_candidate/R01/A.SLDASM'},r/'external')
   self.assertEqual(s,r/'external/cad/A.SLDASM')
 def test_changed_candidate_detected(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);b={'source':'cad/A.SLDASM','target':'cad/final_candidate/R01/A.SLDASM'};save(r/promo.BASE,b)
   target=r/b['target'];target.parent.mkdir(parents=True);target.write_bytes(b'one')
   save(target.parent/promo.MANIFEST,{'baseline_sha256':sha256_file(r/promo.BASE),'files':[{'name':target.name,'sha256':sha256_file(target)}]})
   self.assertEqual(promo.verify_target(r,b,target),[])
   target.write_bytes(b'two');self.assertIn('FILE_MISSING_OR_CHANGED:A.SLDASM',promo.verify_target(r,b,target))
 def test_unbound_old_snapshot_cannot_pass(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);b={'source':'cad/A.SLDASM','target':'cad/final_candidate/R01/A.SLDASM','expected_component_count':0,'expected_mate_count':0};save(r/promo.BASE,b)
   self.assertEqual(sem.evaluate(r,b,{'status':'OK','assembly':{'native_path':'old.SLDASM'}})['status'],'HOLD')
 def test_release_blocks_legacy_green_reports(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d)
   for rel in ['reports/control/K01_FINAL_ASSEMBLY_PROMOTION_CURRENT.json','reports/control/K01_NODE_TECHNICAL_FILTER_CURRENT.json','reports/bom/current/K01_EBOM_A001_CURRENT.json','reports/control/K01_PROJECT_STRUCTURE_AUDIT_CURRENT.json','reports/control/K01_GIT_AUDIT_CURRENT.json','reports/drawing/current/K01_DRAWING_RELEASE_PLAN_CURRENT.json','reports/control/K01_REQUIREMENTS_COVERAGE_CURRENT.json']:save(r/rel,{'status':'PASS'})
   cp=subprocess.run([sys.executable,str(ROOT/'tools/medtas/build_r01_release_candidate_v2_2.py'),'--repo-root',d],capture_output=True)
   self.assertNotEqual(cp.returncode,0);self.assertFalse((r/'release/R01').exists())
if __name__=='__main__':unittest.main(verbosity=2)
