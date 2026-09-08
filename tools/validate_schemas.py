from pathlib import Path
import json, sys
from jsonschema import Draft202012Validator

ROOT=Path(__file__).resolve().parents[1]
pairs=[
    ("control/requirements/requirements.json","control/schemas/requirements.schema.json"),
    ("control/technical_filter/K01_J2_C2R1_TECHNICAL_FILTER_v1.json","control/schemas/technical_filter.schema.json"),
    ("control/configuration/revision_policy.json","control/schemas/revision_policy.schema.json"),
    ("control/drawings/definitions/K01-D-003.drawing.json","control/schemas/drawing_definition.schema.json"),
    ("control/drawings/definitions/K01-D-006.drawing.json","control/schemas/drawing_definition.schema.json"),
]
failed=False
for data_rel,schema_rel in pairs:
    data_path=ROOT/data_rel; schema_path=ROOT/schema_rel
    data=json.loads(data_path.read_text(encoding="utf-8-sig"))
    schema=json.loads(schema_path.read_text(encoding="utf-8-sig"))
    errors=sorted(Draft202012Validator(schema).iter_errors(data),key=lambda e:list(e.path))
    if errors:
        failed=True
        print(f"FAIL {data_rel}")
        for e in errors:
            print("  ",list(e.path),e.message)
    else:
        print(f"PASS {data_rel}")
sys.exit(2 if failed else 0)
