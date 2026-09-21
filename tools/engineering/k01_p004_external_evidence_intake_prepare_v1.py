#!/usr/bin/env python3
import argparse, json, shutil
from datetime import datetime, timezone
from pathlib import Path


def load_json(p: Path):
    with p.open('r', encoding='utf-8') as f:
        return json.load(f)


def dump_json(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('w', encoding='utf-8', newline='\n') as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write('\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo-root', required=True)
    args = ap.parse_args()
    root = Path(args.repo_root).resolve()

    active = root / 'control' / 'project' / 'K01_ACTIVE_STEP_GATE.json'
    nextp = root / 'control' / 'project' / 'K01_NEXT_ACTIONS_CURRENT.json'
    if not active.exists() or not nextp.exists():
        raise SystemExit('HOLD: canonical navigation state missing; run lifecycle reducer/guards first')

    a = load_json(active)
    n = load_json(nextp)
    blob = json.dumps([a, n], ensure_ascii=False)
    if 'P004-EXTERNAL-EVIDENCE-ACQUISITION' not in blob:
        raise SystemExit('HOLD: frontier is not P004-EXTERNAL-EVIDENCE-ACQUISITION; refusing to prepare the wrong intake')

    plan_src = root / 'reports' / 'test' / 'K01_P004_PHYSICAL_EVIDENCE_PLAN_CURRENT.json'
    template_src = root / 'evidence' / 'templates' / 'K01_P004_GUIDE_REPEATABILITY_CHARACTERIZATION_TEMPLATE.csv'
    if not plan_src.exists():
        raise SystemExit(f'HOLD: missing evidence plan: {plan_src}')
    if not template_src.exists():
        raise SystemExit(f'HOLD: missing repeatability template: {template_src}')

    intake = root / 'evidence' / 'intake' / 'K01-P-004_EXTERNAL_EVIDENCE'
    intake.mkdir(parents=True, exist_ok=True)

    tests = {
        'T-P004-01_DIMENSIONAL_FAI_AS_BUILT': [
            'Record actual P004 OD, bore and OAL; P001 guide diameter; P003 seat; effective P003/P014 retention space.',
            'Record part temperature, instrument ID, method, calibration/traceability, measurement uncertainty if known, material lot and process route.',
            'Do not convert prototype measurements into released production tolerances.'
        ],
        'T-P004-02_GUIDE_REPEATABILITY': [
            'Characterize OUT=0 mm, MID=5 mm, IN=10 mm over 10 complete OUT→MID→IN→MID→OUT cycles.',
            'Approach positions from both directions where possible. Record raw mechanical target/lateral error and optical/reference signal if available.',
            'This is characterization only: no pass/fail threshold is authorized yet.'
        ],
        'T-P004-03_SEAT_AXIAL_FLOAT_20C_SCREEN': [
            'Record prototype seat clearance and axial float at approximately 20 °C.',
            'Engineering screen windows are 0.040…0.080 mm for seat clearance and 0.040…0.080 mm for axial float.',
            'These are not released production acceptance limits for P003/P014 until capability and authority are closed.'
        ],
        'T-P004-04_GUIDE_SURFACE_BEFORE_AFTER': [
            'Photograph/inspect guide surfaces before and after cycling.',
            'Record debris, shaving, scoring, stick-slip, binding and any visible damage.',
            'Use photos with scale/reference when practical.'
        ]
    }

    for name, lines in tests.items():
        d = intake / name
        d.mkdir(parents=True, exist_ok=True)
        readme = d / 'README.txt'
        readme.write_text(
            'K01 / P004 EXTERNAL EVIDENCE INTAKE\n'
            f'TEST: {name}\n\n' + '\n'.join('- ' + x for x in lines) +
            '\n\nPlace raw files here. Preserve original filenames and dates. Do not overwrite raw evidence.\n',
            encoding='utf-8'
        )

    shutil.copy2(template_src, intake / 'T-P004-02_GUIDE_REPEATABILITY' / template_src.name)

    templates = {
        'K01_P004_DIMENSIONAL_FAI_TEMPLATE.csv':
            'test_id,part_id,serial_or_fai_id,feature,nominal_mm,location,ambient_C,part_C,measured_mm,instrument_id,calibration_status,method,contact_force,uncertainty_mm,material_lot,coc_ref,process_revision,stabilization_or_anneal,operator,notes\n'
            'T-P004-01,K01-P-004,,OD,6.540,,,,,,,,,,,,,,,\n'
            'T-P004-01,K01-P-004,,BORE,5.055,,,,,,,,,,,,,,,\n'
            'T-P004-01,K01-P-004,,OAL,8.000,,,,,,,,,,,,,,,\n'
            'T-P004-01,K01-P-001,,GUIDE_DIAMETER,5.000,,,,,,,,,,,,,,,\n'
            'T-P004-01,K01-P-003,,P004_SEAT_ID,6.600,,,,,,,,,,,,,,,\n'
            'T-P004-01,K01-P-003/P014,,EFFECTIVE_RETENTION_SPACE_H,8.060,,,,,,,,,,,,,,,\n',
        'K01_P004_SEAT_AXIAL_SCREEN_TEMPLATE.csv':
            'test_id,assembly_id,ambient_C,part_C,P003_seat_ID_mm,P004_OD_mm,derived_seat_clearance_mm,effective_retention_H_mm,P004_OAL_mm,derived_axial_float_mm,direct_axial_float_mm,instrument_ids,uncertainty_notes,screen_only,operator_notes\n'
            'T-P004-03,,,,,,,,,,,,,YES,\n',
        'K01_P004_GUIDE_SURFACE_OBSERVATION_TEMPLATE.csv':
            'test_id,assembly_id,stage,ambient_C,part_C,cycles_completed,binding,stick_slip,polymer_debris,shaving,scoring,photo_or_file_ref,inspection_method,operator_notes\n'
            'T-P004-04,,BEFORE,,,,,,,,,,,,\n'
            'T-P004-04,,AFTER,,,,,,,,,,,,\n'
    }
    template_dest = {
        'K01_P004_DIMENSIONAL_FAI_TEMPLATE.csv': intake / 'T-P004-01_DIMENSIONAL_FAI_AS_BUILT',
        'K01_P004_SEAT_AXIAL_SCREEN_TEMPLATE.csv': intake / 'T-P004-03_SEAT_AXIAL_FLOAT_20C_SCREEN',
        'K01_P004_GUIDE_SURFACE_OBSERVATION_TEMPLATE.csv': intake / 'T-P004-04_GUIDE_SURFACE_BEFORE_AFTER'
    }
    for name, text in templates.items():
        tp = root / 'evidence' / 'templates' / name
        tp.parent.mkdir(parents=True, exist_ok=True)
        tp.write_text(text, encoding='utf-8', newline='\n')
        shutil.copy2(tp, template_dest[name] / name)

    shutil.copy2(plan_src, intake / 'K01_P004_PHYSICAL_EVIDENCE_PLAN_SNAPSHOT.json')

    top = intake / 'README_START_HERE.txt'
    top.write_text(
        'K01 / P004 — EXTERNAL EVIDENCE DROP ZONE\n\n'
        'Current engineering blocker remains P004-EXTERNAL-EVIDENCE-ACQUISITION.\n'
        'This folder is an intake workpack only; creating it does NOT close the blocker or change lifecycle state.\n\n'
        'Minimum useful return package:\n'
        '1) dimensional/as-built measurements at ~20 °C,\n'
        '2) guide repeatability raw data over OUT/MID/IN positions,\n'
        '3) seat + axial-float prototype screen,\n'
        '4) guide-surface before/after evidence,\n'
        '5) available material/process/instrument traceability.\n\n'
        'Do not invent missing pass/fail limits. Keep raw evidence unchanged.\n',
        encoding='utf-8'
    )

    now = datetime.now(timezone.utc).isoformat()
    report = {
        'record_type': 'K01_P004_EXTERNAL_EVIDENCE_INTAKE_WORKPACK',
        'generated_utc': now,
        'status': 'READY_FOR_EXTERNAL_EVIDENCE_DROP',
        'lifecycle': 'L5',
        'active_object': 'K01-P-004',
        'current_blocker': 'P004-EXTERNAL-EVIDENCE-ACQUISITION',
        'state_transition': 'NONE',
        'engineering_authority_change': 'NONE',
        'native_mutation': 'NONE',
        'intake_root': str(intake.relative_to(root)).replace('\\', '/'),
        'required_tracks': list(tests.keys()),
        'source_plan': str(plan_src.relative_to(root)).replace('\\', '/'),
        'notes': [
            'Preparation of the intake workpack does not satisfy the physical-evidence blocker.',
            'Raw measurements and setup/equipment details remain external inputs.',
            'Guide numeric acceptance remains open until requirement/characterization evidence is reviewed.'
        ]
    }
    report_path = root / 'reports' / 'test' / 'K01_P004_EXTERNAL_EVIDENCE_INTAKE_CURRENT.json'
    dump_json(report_path, report)

    print('PASS_P004_EXTERNAL_EVIDENCE_INTAKE_WORKPACK_READY__BLOCKER_UNCHANGED')
    print('INTAKE:', intake)
    print('REPORT:', report_path)
    print('BLOCKER: P004-EXTERNAL-EVIDENCE-ACQUISITION')
    print('STATE_TRANSITION: NONE')
    print('NATIVE_MUTATION: NONE')

if __name__ == '__main__':
    main()
