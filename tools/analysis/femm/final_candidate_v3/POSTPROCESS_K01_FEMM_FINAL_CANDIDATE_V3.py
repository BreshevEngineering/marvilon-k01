from pathlib import Path
import csv, json

ROOT = Path(r"D:\BreshevEngineering\marvilon-k01")
DIR = ROOT / "reports" / "femm" / "final_candidate_20260916_v3"
IN = DIR / "K01_FEMM_FINAL_CANDIDATE_SWEEP_V3.csv"
OUT = DIR / "K01_FEMM_FINAL_CANDIDATE_SUMMARY_V3.json"
MD = DIR / "K01_FEMM_FINAL_CANDIDATE_SUMMARY_V3.md"
CRIT = 0.930894486

if not IN.exists():
    raise SystemExit(f"Missing FEMM CSV: {IN}")

rows=[]
with IN.open(newline="",encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        for k in ("z_mm","turns_per_coil","Br_T","mag_mu_r","p007_mu_r","current_A",
                  "F0_N","Fplus_N","Fminus_N","Kplus_N_per_A","Kminus_N_per_A","Kmin_N_per_A"):
            r[k]=float(r[k])
        rows.append(r)

scenarios={}
for name in sorted({r["scenario"] for r in rows}):
    rs=[r for r in rows if r["scenario"]==name]
    worst=min(rs,key=lambda x:x["Kmin_N_per_A"])
    scenarios[name]={
        "K_F_min_N_per_A":worst["Kmin_N_per_A"],
        "worst_z_mm":worst["z_mm"],
        "criterion_N_per_A":CRIT,
        "margin_pct":(worst["Kmin_N_per_A"]/CRIT-1)*100,
        "positions":len(rs),
        "verdict":"PASS_NUMERICAL_SCREEN" if worst["Kmin_N_per_A"] >= CRIT else "FAIL_NUMERICAL_SCREEN",
    }

cand=scenarios.get("CANDIDATE_350_BR1_BOUND")
overall = "PASS_DESIGN_CANDIDATE" if cand and cand["verdict"]=="PASS_NUMERICAL_SCREEN" else "HOLD_DESIGN_CANDIDATE"

obj={
    "schema":"k01.femm_final_candidate_summary.v3",
    "criterion_N_per_A":CRIT,
    "candidate_definition":{
        "turns_per_coil":350,
        "Br_eff_min_T_at_55C":1.00,
        "magnet_mu_r_screen":1.05,
        "P007_mu_r_screen":1.05,
        "nominal_current_A":1.0,
        "boost_current_A":1.25,
    },
    "overall":overall,
    "scenarios":scenarios,
    "release_boundary":"Numerical design candidate only. Wire-pack/thermal definition and physical B001/bench qualification remain separate gates."
}
OUT.write_text(json.dumps(obj,indent=2),encoding="utf-8")

lines=[
    "# K01 FEMM FINAL CANDIDATE V3","",
    f"Criterion: **K_F,min >= {CRIT:.9f} N/A at nominal 1 A**","",
    "Proposed candidate: **350 turns per coil; B001 Br_eff,min >= 1.00 T at 55 °C**.","",
    "| Scenario | K_F,min N/A | worst z mm | margin | verdict |",
    "|---|---:|---:|---:|---|"
]
for name,v in scenarios.items():
    lines.append(f"| {name} | {v['K_F_min_N_per_A']:.6f} | {v['worst_z_mm']:.1f} | {v['margin_pct']:+.2f}% | {v['verdict']} |")
lines += [
    "",
    f"Overall candidate state: **{overall}**.",
    "",
    "Do not convert this to production release until P015 wire-pack/thermal definition and later B001/bench qualification are closed."
]
MD.write_text("\n".join(lines)+"\n",encoding="utf-8")

print(MD)
print(OUT)
for name,v in scenarios.items():
    print(name, v["verdict"], f"KFmin={v['K_F_min_N_per_A']:.6f}", f"margin={v['margin_pct']:+.2f}%")
