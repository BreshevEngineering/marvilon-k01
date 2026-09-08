from canonical_hash_v1_4 import canonical_json_hash, canonicalize_step_text
import hashlib

def main():
    a={'schema':'x','generated':'2026-09-06T10:00:00','native_path':'D:/one/a.SLDPRT','solidworks_revision':'34.0','b':1.00000000000001,'a':{'z':2,'y':3.0}}
    b={'a':{'y':3.0000000000000004,'z':2},'b':1.0,'schema':'x','generated':'2099-01-01','native_path':'C:/different/a.SLDPRT','solidworks_revision':'99.9'}
    ha=canonical_json_hash(a); hb=canonical_json_hash(b)
    if ha!=hb:
        print('HOLD JSON canonical invariance',ha,hb); return 1
    s1="""ISO-10303-21;\nHEADER;\nFILE_DESCRIPTION(('x'),'2;1');\nFILE_NAME('a.step','2026-09-06T10:00:00',('A'),('B'),'SW','SW','');\nFILE_SCHEMA(('CONFIG_CONTROL_DESIGN'));\nENDSEC;\nDATA;\n#1=PRODUCT('X','X','',());\nENDSEC;\nEND-ISO-10303-21;\n"""
    s2=s1.replace("'a.step','2026-09-06T10:00:00',('A'),('B')","'b.step','2099-01-01T00:00:00',('Q'),('Z')")
    hs1=hashlib.sha256(canonicalize_step_text(s1).encode()).hexdigest(); hs2=hashlib.sha256(canonicalize_step_text(s2).encode()).hexdigest()
    if hs1!=hs2:
        print('HOLD STEP header invariance',hs1,hs2); return 2
    print('PASS canonical hash self-test')
    print('JSON canonical hash =',ha)
    print('STEP normalized hash=',hs1)
    return 0
if __name__=='__main__': raise SystemExit(main())
