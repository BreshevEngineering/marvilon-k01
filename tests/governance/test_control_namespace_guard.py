import json, shutil, sys, tempfile, unittest
from pathlib import Path
REPO=Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path: sys.path.insert(0,str(REPO))
from tools.repo.control_namespace_guard import audit

class TestControlNamespaceGuard(unittest.TestCase):
    def test_current_repository_has_no_namespace_violation(self):
        rep=audit(REPO)
        self.assertTrue(str(rep.get('status','')).startswith('PASS'),rep.get('violations'))
    def test_new_graph_sibling_is_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td)
            for rel in ['control/repo/K01_CONTROL_NAMESPACE_BASELINE.json','control/project/K01_AUTHORITY_MAP_CURRENT.json']:
                p=r/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(REPO/rel,p)
            amap=json.loads((r/'control/project/K01_AUTHORITY_MAP_CURRENT.json').read_text(encoding='utf-8'))
            fam=amap['control_families']['engineering_build_graph']
            for rel in [fam['authority'],*fam['legacy']]:
                src=REPO/rel
                if src.is_file():
                    dst=r/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
            extra=r/'control/medtas/v1/graph/K01_engineering_build_graph_v999_999.json';extra.parent.mkdir(parents=True,exist_ok=True);extra.write_text('{}',encoding='utf-8')
            rep=audit(r)
            self.assertEqual(rep['status'],'HOLD')
            self.assertTrue(any(x.get('rule') in ('NEW_VERSION_SIBLING','UNDECLARED_CRITICAL_SIBLING') for x in rep['violations']))
if __name__=='__main__':unittest.main()
