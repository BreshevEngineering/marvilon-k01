from pathlib import Path
import tempfile,json,sys
from medtas_v16_common import load
with tempfile.TemporaryDirectory() as td:
    p=Path(td)/'x.json';p.write_text('{"a":1}',encoding='utf-8')
    assert load(p,{})=={'a':1}
    assert load(Path(td)/'missing.json',{'fallback':1})=={'fallback':1}
print('PASS medtas_v16_common.load default regression')
