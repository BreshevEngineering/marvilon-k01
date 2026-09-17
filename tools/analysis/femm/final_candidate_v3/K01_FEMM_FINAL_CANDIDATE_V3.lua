
setcompatibilitymode(0)

OUTDIR = "D:/BreshevEngineering/marvilon-k01/reports/femm/final_candidate_20260916_v3/"
CSV = OUTDIR .. "K01_FEMM_FINAL_CANDIDATE_SWEEP_V3.csv"
LOG = OUTDIR .. "K01_FEMM_FINAL_CANDIDATE_V3.log"
MU0 = 1.2566370614359173e-6

-- Final P007 geometry from current K01 Product Definition.
-- Coordinate system follows the proven fixed-coil FEMM benchmark.
P007_FRONT_Z = -19.8
P007_LOCATOR_BACK_Z = -17.8  -- 2.00 mm locator depth
P007_CAN_FRONT_Z = -16.8     -- OD33 flange total thickness = 3.00 mm
P007_BLIND_INNER_Z = 14.2
P007_REAR_Z = 15.2           -- 1.00 mm integral blind end
P007_LOCATOR_R = 7.05        -- D14.10 H7 nominal
P007_CAN_RI = 4.7            -- ID9.40 nominal
P007_CAN_RO = 5.0            -- OD10.00 nominal
P007_FLANGE_RO = 16.5        -- OD33.00 nominal

COIL_RI = 5.7
COIL_RO = 9.2
COIL_A_Z0 = -11.75
COIL_A_Z1 = -5.75
COIL_B_Z0 = 5.75
COIL_B_Z1 = 11.75

function logline(s)
  ff=openfile(LOG,"a")
  write(ff,s.."\n")
  closefile(ff)
end

function rect(r0,z0,r1,z1)
  mi_addnode(r0,z0)
  mi_addnode(r1,z0)
  mi_addnode(r1,z1)
  mi_addnode(r0,z1)
  mi_addsegment(r0,z0,r1,z0)
  mi_addsegment(r1,z0,r1,z1)
  mi_addsegment(r1,z1,r0,z1)
  mi_addsegment(r0,z1,r0,z0)
end

function addlabel(r,z,mat,mesh,circuit,magdir,group,turns)
  mi_addblocklabel(r,z)
  mi_selectlabel(r,z)
  mi_setblockprop(mat,0,mesh,circuit,magdir,group,turns)
  mi_clearselected()
end

function add_p007_connected_polygon()
  -- One continuous monolithic 316L region.
  -- Front 2 mm: D14.10 locator bore.
  -- Rear 1 mm of flange + can: ID9.40.
  -- Thin can continues to integral blind end.
  mi_addnode(P007_LOCATOR_R,P007_FRONT_Z)
  mi_addnode(P007_FLANGE_RO,P007_FRONT_Z)
  mi_addnode(P007_FLANGE_RO,P007_CAN_FRONT_Z)
  mi_addnode(P007_CAN_RO,P007_CAN_FRONT_Z)
  mi_addnode(P007_CAN_RO,P007_REAR_Z)
  mi_addnode(0,P007_REAR_Z)
  mi_addnode(0,P007_BLIND_INNER_Z)
  mi_addnode(P007_CAN_RI,P007_BLIND_INNER_Z)
  mi_addnode(P007_CAN_RI,P007_LOCATOR_BACK_Z)
  mi_addnode(P007_LOCATOR_R,P007_LOCATOR_BACK_Z)

  mi_addsegment(P007_LOCATOR_R,P007_FRONT_Z,P007_FLANGE_RO,P007_FRONT_Z)
  mi_addsegment(P007_FLANGE_RO,P007_FRONT_Z,P007_FLANGE_RO,P007_CAN_FRONT_Z)
  mi_addsegment(P007_FLANGE_RO,P007_CAN_FRONT_Z,P007_CAN_RO,P007_CAN_FRONT_Z)
  mi_addsegment(P007_CAN_RO,P007_CAN_FRONT_Z,P007_CAN_RO,P007_REAR_Z)
  mi_addsegment(P007_CAN_RO,P007_REAR_Z,0,P007_REAR_Z)
  mi_addsegment(0,P007_REAR_Z,0,P007_BLIND_INNER_Z)
  mi_addsegment(0,P007_BLIND_INNER_Z,P007_CAN_RI,P007_BLIND_INNER_Z)
  mi_addsegment(P007_CAN_RI,P007_BLIND_INNER_Z,P007_CAN_RI,P007_LOCATOR_BACK_Z)
  mi_addsegment(P007_CAN_RI,P007_LOCATOR_BACK_Z,P007_LOCATOR_R,P007_LOCATOR_BACK_Z)
  mi_addsegment(P007_LOCATOR_R,P007_LOCATOR_BACK_Z,P007_LOCATOR_R,P007_FRONT_Z)

  -- Label is placed in the thin-wall zone; the complete polygon is connected,
  -- so the same material applies to flange + can + blind end.
  addlabel(4.85,0,"K01_316L_SCREEN",0.15,"<None>",0,20,0)
end

function build_and_solve(tag,zmag,turns,br,magmur,p007mur,ia,ib)
  logline("START "..tag)
  newdocument(0)
  mi_probdef(0,"millimeters","axi",1.e-8,0,30)

  mi_addmaterial("K01_AIR",1,1,0,0,0,0,0,1,0,0,0,0,0)
  mi_addmaterial("K01_316L_SCREEN",p007mur,p007mur,0,0,0,0,0,1,0,0,0,0,0)
  hc = br/(MU0*magmur)
  mi_addmaterial("K01_MAG",magmur,magmur,hc,0,0,0,0,1,0,0,0,1,0)
  mi_addmaterial("K01_COIL_REGION",1,1,0,0,0,0,0,1,0,0,0,0,0)

  mi_addcircprop("CoilA",ia,1)
  mi_addcircprop("CoilB",ib,1)
  mi_addboundprop("A0",0,0,0,0,0,0,0,0,0)

  -- Proven benchmark outer domain.
  mi_addnode(0,-60)
  mi_addnode(50,-60)
  mi_addnode(50,60)
  mi_addnode(0,60)
  mi_addsegment(0,-60,50,-60)
  mi_addsegment(50,-60,50,60)
  mi_addsegment(50,60,0,60)
  mi_addsegment(0,60,0,-60)

  mi_selectsegment(25,-60)
  mi_setsegmentprop("A0",0,1,0,0)
  mi_clearselected()
  mi_selectsegment(50,30)
  mi_setsegmentprop("A0",0,1,0,0)
  mi_clearselected()
  mi_selectsegment(25,60)
  mi_setsegmentprop("A0",0,1,0,0)
  mi_clearselected()
  mi_selectsegment(0,0)
  mi_setsegmentprop("A0",0,1,0,0)
  mi_clearselected()

  -- Moving B001 magnet D8 x 8.
  rect(0,zmag-4,4,zmag+4)
  addlabel(2,zmag,"K01_MAG",0.15,"<None>",90,10,0)

  -- Monolithic final P007. No overlapping wall/blind/flange regions.
  add_p007_connected_polygon()

  -- Coil A.
  rect(COIL_RI,COIL_A_Z0,COIL_RO,COIL_A_Z1)
  addlabel(7.45,-8.75,"K01_COIL_REGION",0.20,"CoilA",0,21,turns)

  -- Coil B.
  rect(COIL_RI,COIL_B_Z0,COIL_RO,COIL_B_Z1)
  addlabel(7.45,8.75,"K01_COIL_REGION",0.20,"CoilB",0,22,turns)

  -- All remaining void is one connected air region through the open J2 end.
  addlabel(20,0,"K01_AIR",1.0,"<None>",0,0,0)

  -- Keep a single diagnostic FEM model on disk if a later solve fails.
  mi_saveas(OUTDIR .. "K01_FEMM_DIAGNOSTIC_CURRENT.fem")
  mi_analyze()
  mi_loadsolution()

  mo_groupselectblock(10)
  fz = mo_blockintegral(19)
  vol = mo_blockintegral(10)
  mo_clearblock()

  iA,vA,fluxA = mo_getcircuitproperties("CoilA")
  iB,vB,fluxB = mo_getcircuitproperties("CoilB")

  mo_close()
  mi_close()
  logline("PASS "..tag.." Fz="..format("%.17g",fz))
  return fz,vol,fluxA,fluxB
end

function run_scenario(name,turns,br,magmur,p007mur,current)
  logline("SCENARIO "..name)
  for z=-5,5,1 do
    f0,v0,fa0,fb0 = build_and_solve(name.."_Z"..z.."_ZERO",z,turns,br,magmur,p007mur,0,0)

    -- Positive useful direction: A negative, B positive.
    fp,vp,fap,fbp = build_and_solve(name.."_Z"..z.."_PLUS",z,turns,br,magmur,p007mur,-current,current)

    -- Reverse useful direction.
    fm,vm,fam,fbm = build_and_solve(name.."_Z"..z.."_MINUS",z,turns,br,magmur,p007mur,current,-current)

    kp = abs(fp-f0)/current
    km = abs(fm-f0)/current
    kmin = kp
    if km < kmin then kmin=km end

    ff=openfile(CSV,"a")
    write(ff,name..","..z..","..turns..","..br..","..magmur..","..p007mur..","..current..","..
      format("%.17g",f0)..","..format("%.17g",fp)..","..format("%.17g",fm)..","..
      format("%.17g",kp)..","..format("%.17g",km)..","..format("%.17g",kmin).."\n")
    closefile(ff)
  end
end

ff=openfile(LOG,"w")
write(ff,"K01 FEMM V3 FINAL CANDIDATE SWEEP\n")
closefile(ff)

ff=openfile(CSV,"w")
write(ff,"scenario,z_mm,turns_per_coil,Br_T,mag_mu_r,p007_mu_r,current_A,F0_N,Fplus_N,Fminus_N,Kplus_N_per_A,Kminus_N_per_A,Kmin_N_per_A\n")
closefile(ff)

-- Proposed final design candidate:
-- 350 turns/coil, Br >= 1.00 T at 55 C, conservative magnetic permeability sensitivity.
run_scenario("CANDIDATE_350_BR1_BOUND",350,1.00,1.05,1.050,1.0)

-- Sensitivity only: 5% lower Br than proposed procurement bound.
-- This is not the released design condition.
run_scenario("SENSITIVITY_350_BR095",350,0.95,1.05,1.050,1.0)

ff=openfile(OUTDIR .. "K01_FEMM_SWEEP_V3_PASS.txt","w")
write(ff,"PASS\n")
closefile(ff)

quit()
