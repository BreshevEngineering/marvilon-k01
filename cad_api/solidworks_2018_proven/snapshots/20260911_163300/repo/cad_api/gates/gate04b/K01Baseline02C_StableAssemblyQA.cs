using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text.RegularExpressions;
using System.Web.Script.Serialization;
using SolidWorks.Interop.sldworks;
using SolidWorks.Interop.swconst;

namespace Marvilon.K01.Baseline02C.StableAssemblyQA
{
    public sealed class GateReport
    {
        public string status="";
        public string release_status="";
        public Candidate P003;
        public Candidate P016;
        public P017Candidate P017;
    }
    public sealed class Candidate
    {
        public string native="";
        public string step="";
        public CandidateResult result;
    }
    public sealed class CandidateResult
    {
        public double C_angle_deg=0;
        public double C_radius_mm=0;
        public double[] C_center_local_m;
        public double D_mm=0;
    }
    public sealed class P017Candidate
    {
        public string native="";
        public string source_step="";
        public P017Result result;
    }
    public sealed class P017Result
    {
        public double[] size_mm;
        public double radial_minor_nominal_mm=0;
        public double tangential_major_nominal_mm=0;
        public double overall_length_nominal_mm=0;
        public double protrusion_nominal_mm=0;
        public string press_shank_nominal="";
        public string material_baseline="";
        public string material_card_status="";
    }

    public sealed class InterferenceRow
    {
        public string state="";
        public List<string> components=new List<string>();
        public List<string> part_ids=new List<string>();
        public double volume_mm3=0;
        public string classification="";
    }
    public sealed class MotionRow
    {
        public string part_id="";
        public double[] delta_mid_mm;
        public double[] delta_out_mm;
        public double max_vector_error_mid_mm=0;
        public double max_vector_error_out_mm=0;
        public string status="";
    }
    public sealed class QaReport
    {
        public string schema="k01_gate04b_datum_c_assembly_qa_v1";
        public string created_utc=DateTime.UtcNow.ToString("o");
        public string status="RUNNING";
        public string release_status="HOLD";
        public string solidworks_revision="";
        public string canonical_assembly="";
        public string canonical_sha256="";
        public string verification_assembly="";
        public string verification_sha256="";
        public string p003_candidate="";
        public string p016_candidate="";
        public string p017_candidate="";
        public int open_errors=0;
        public int open_warnings=0;
        public int component_count=0;
        public int active_mate_errors=-1;
        public string p003_constrained="";
        public string p016_constrained="";
        public string p017_constrained="";
        public bool datum_c_nominal_surrogate_mate=false;
        public bool datum_c_clocking_angle_mate=false;
        public string datum_c_clocking_method="";
        public string datum_c_clocking_plane_p003="";
        public string datum_c_clocking_plane_p016="";
        public double datum_c_clocking_angle_deg=999;
        public double datum_c_alignment_rotation_deg=999;
        public int rejected_peripheral_concentric_error=5;
        public bool p017_press_concentric_locked=false;
        public bool p017_press_depth_mate=false;
        public double c_axis_center_error_mm=999;
        public double p017_orientation_error_deg=999;
        public string p017_press_concentric_alignment="";
        public double p017_axis_alignment_deg=999;
        public double p017_bottom_offset_along_p016_z_mm=999;
        public double p017_press_depth_mm=999;
        public double p017_protrusion_mm=999;
        public bool moving_group_pass=false;
        public List<MotionRow> moving_group=new List<MotionRow>();
        public int unexpected_interference_total=0;
        public List<InterferenceRow> interferences=new List<InterferenceRow>();
        public double original_limit_distance_mm=0;
        public bool original_limit_restored=false;
        public string installation_status="PASS_SCREEN_QUALIFICATION_OPEN";
        public string bom_delta="+ K01-P-017 x1; modeled occurrence count 13 -> 14";
        public string p017_material_status="";
        public List<string> checks=new List<string>();
        public List<string> notes=new List<string>();
        public string error="";
    }

    public sealed class PlaneHit { public Face2 face; public double station; public double area; }
    public sealed class CylHit
    {
        public Face2 face;
        public double[] origin;
        public double[] axis;
        public double dmm;
        public double score;
    }

    public static class Program
    {
        const double MM=0.001;
        const string REPO=@"D:\BreshevEngineering\marvilon-k01";
        const string P003S=@"D:\Marvilon\K01\cad\parts\K01-P-003_Cartridge_Body.SLDPRT";
        const string P016S=@"D:\Marvilon\K01\cad\parts\K01-P-016_Long_Run_Interface_Boss.SLDPRT";
        const string P017S=@"D:\Marvilon\K01\cad\parts\K01-P-017_Datum_C_Relieved_Locator.SLDPRT";
        const string GATE_REPORT=@"D:\BreshevEngineering\marvilon-k01\reports\cad\current\K01_GATE04B_DATUM_C_BUILD.json";
        const string DEFAULT_RDIR=@"D:\BreshevEngineering\marvilon-k01\reports\cad\current";

        static SldWorks sw;
        static QaReport R=new QaReport();
        static string logPath="";
        static GateReport G;
        static string targetAssembly="";
        static string outJson="";
        static bool createdSw=false;


        public static int Main(string[] args)
        {
            try
            {
                targetAssembly="";
                outJson="";
                for(int i=0;i<args.Length;i++)
                {
                    string a=args[i]??"";
                    if(String.Equals(a,"--assembly",StringComparison.OrdinalIgnoreCase) && i+1<args.Length)
                        targetAssembly=args[++i];
                    else if(String.Equals(a,"--report",StringComparison.OrdinalIgnoreCase) && i+1<args.Length)
                        outJson=args[++i];
                }
                if(String.IsNullOrWhiteSpace(targetAssembly))
                    throw new Exception("--assembly is required");
                if(String.IsNullOrWhiteSpace(outJson))
                    throw new Exception("--report is required");
                Need(targetAssembly);
                Directory.CreateDirectory(Path.GetDirectoryName(outJson));
                string stamp=DateTime.Now.ToString("yyyyMMdd_HHmmss");
                logPath=Path.Combine(Path.GetDirectoryName(outJson),
                    Path.GetFileNameWithoutExtension(outJson)+"_"+stamp+".log");
                File.WriteAllText(logPath,"K01 Baseline-02C stable assembly QA\r\n");

                LoadGateReport();
                GuardInputs();
                Connect();
                Run();
                SaveReport();

                Log("STATUS="+R.status);
                return R.status=="PASS_STABLE_ASSEMBLY_QA" ? 0 : 2;
            }
            catch(Exception ex)
            {
                R.status="FAIL";
                R.release_status="HOLD";
                R.error=ex.ToString();
                try{SaveReport();}catch{}
                try{Log("STATUS=FAIL\r\n"+ex);}catch{}
                return 1;
            }
            finally
            {
                try
                {
                    if(createdSw && sw!=null) sw.ExitApp();
                }
                catch{}
                try
                {
                    if(sw!=null && Marshal.IsComObject(sw))
                        Marshal.FinalReleaseComObject(sw);
                }
                catch{}
                sw=null;
                try
                {
                    GC.Collect();
                    GC.WaitForPendingFinalizers();
                    GC.Collect();
                    GC.WaitForPendingFinalizers();
                }
                catch{}
            }
        }

        static void LoadGateReport()
        {
            if(!File.Exists(GATE_REPORT)) throw new Exception("Gate04B report missing: "+GATE_REPORT);
            JavaScriptSerializer js=new JavaScriptSerializer();
            js.MaxJsonLength=Int32.MaxValue;
            G=js.Deserialize<GateReport>(File.ReadAllText(GATE_REPORT));
            if(G==null || G.P003==null || G.P016==null || G.P017==null)
                throw new Exception("Gate04B report missing P003/P016/P017 objects");
        }

        static void GuardInputs()
        {
            Need(targetAssembly); Need(P003S); Need(P016S); Need(P017S);
            if(!String.Equals(G.status,"PASS",StringComparison.OrdinalIgnoreCase))
                throw new Exception("Gate04B build is not PASS");
            Need(G.P003.native); Need(G.P016.native); Need(G.P017.native);

            if(!String.Equals(Sha256(P003S),Sha256(G.P003.native),StringComparison.OrdinalIgnoreCase))
                throw new Exception("Stable P003 binary differs from verified Gate04B candidate");
            if(!String.Equals(Sha256(P016S),Sha256(G.P016.native),StringComparison.OrdinalIgnoreCase))
                throw new Exception("Stable P016 binary differs from verified Gate04B candidate");
            if(!String.Equals(Sha256(P017S),Sha256(G.P017.native),StringComparison.OrdinalIgnoreCase))
                throw new Exception("Stable P017 binary differs from verified Gate04B candidate");

            R.schema="k01_baseline_02c_stable_assembly_qa_v1";
            R.canonical_assembly=targetAssembly;
            R.canonical_sha256=Sha256(targetAssembly);
            R.p003_candidate=G.P003.native;
            R.p016_candidate=G.P016.native;
            R.p017_candidate=G.P017.native;
            R.p017_material_status=(G.P017.result==null)?"OPEN":(G.P017.result.material_card_status??"OPEN");
        }

        static void Connect()
        {
            object a=null;
            try{a=Marshal.GetActiveObject("SldWorks.Application");}catch{}
            createdSw=(a==null);
            sw=a!=null?(SldWorks)a:(SldWorks)Activator.CreateInstance(Type.GetTypeFromProgID("SldWorks.Application",true));
            sw.Visible=true;
            R.solidworks_revision=sw.RevisionNumber();
            if(!R.solidworks_revision.StartsWith("26."))
                throw new Exception("Expected SOLIDWORKS 2018 / revision 26; got "+R.solidworks_revision);
            Log("Connected SW "+R.solidworks_revision+" created="+createdSw);
        }

        static void Run()
        {
            int e=0,w=0;
            ModelDoc2 doc=sw.OpenDoc6(targetAssembly,(int)swDocumentTypes_e.swDocASSEMBLY,
                (int)swOpenDocOptions_e.swOpenDocOptions_Silent,"",ref e,ref w) as ModelDoc2;
            R.open_errors=e; R.open_warnings=w;
            if(doc==null) throw new Exception("Open stable/staging A001 failed errors="+e+" warnings="+w);
            string title=doc.GetTitle();
            R.verification_assembly=targetAssembly;
            R.verification_sha256=Sha256(targetAssembly);

            try
            {
                AssemblyDoc asm=doc as AssemblyDoc;
                if(asm==null) throw new Exception("Target document is not AssemblyDoc");

                int rc=asm.ResolveAllLightWeightComponents(false);
                Log("ResolveAllLightWeightComponents rc="+rc);

                List<string> candidateLinks=new List<string>();
                foreach(object o in ToObjects(asm.GetComponents(false)))
                {
                    Component2 c=o as Component2;
                    if(c==null) continue;
                    string p=SafePath(c);
                    if(p.IndexOf(@"\candidates\",StringComparison.OrdinalIgnoreCase)>=0)
                        candidateLinks.Add((c.Name2??"")+" -> "+p);
                }
                if(candidateLinks.Count!=0)
                    throw new Exception("Stable/staging assembly still links candidate paths: "+String.Join(" | ",candidateLinks.ToArray()));

                Component2 c3=FindCompByPath(asm,P003S);
                Component2 c16=FindCompByPath(asm,P016S);
                Component2 c17=FindCompByPath(asm,P017S);
                if(c3==null || c16==null || c17==null)
                    throw new Exception("Stable P003/P016/P017 occurrence missing");

                R.component_count=CountModeled(asm);
                if(R.component_count!=14)
                    throw new Exception("Expected 14 modeled occurrences; got "+R.component_count);

                R.active_mate_errors=ActiveMateErrors(doc);
                if(R.active_mate_errors!=0)
                    throw new Exception("Active mate errors="+R.active_mate_errors);

                R.p003_constrained=ConstrainedName(c3);
                R.p016_constrained=ConstrainedName(c16);
                R.p017_constrained=ConstrainedName(c17);
                if(!IsFully(R.p003_constrained) || !IsFully(R.p016_constrained) || !IsFully(R.p017_constrained))
                    throw new Exception("P003/P016/P017 not fully constrained: "+R.p003_constrained+" | "+R.p016_constrained+" | "+R.p017_constrained);

                R.datum_c_clocking_angle_mate=FindFeatureRecursive(doc,"K01_J1_DATUM_C_CLOCKING_ANGLE")!=null;
                R.p017_press_concentric_locked=FindFeatureRecursive(doc,"K01_J1_P017_PRESS_CONCENTRIC_LOCKED")!=null;
                R.p017_press_depth_mate=FindFeatureRecursive(doc,"K01_J1_P017_PRESS_DEPTH_4MM")!=null;
                if(!R.datum_c_clocking_angle_mate || !R.p017_press_concentric_locked || !R.p017_press_depth_mate)
                    throw new Exception("Datum-C/P017 controlled mate features missing");

                double[] c3loc=Need3(G.P003.result==null?null:G.P003.result.C_center_local_m,"P003 C center");
                double[] c16loc=Need3(G.P016.result==null?null:G.P016.result.C_center_local_m,"P016 C center");

                double[] t3=Transform(c3);
                double[] t16=Transform(c16);
                double[] c3w=TransformPoint(t3,c3loc);
                double[] c16w=TransformPoint(t16,c16loc);
                R.c_axis_center_error_mm=1000.0*Norm(Sub(c3w,c16w));
                if(R.c_axis_center_error_mm>0.002)
                    throw new Exception("Datum-C C-center error "+R.c_axis_center_error_mm.ToString("0.######",CultureInfo.InvariantCulture)+" mm > 0.002 mm");

                double theta=G.P016.result.C_angle_deg*Math.PI/180.0;
                double[] t17=Transform(c17);
                double[] radialLocal=new double[]{Math.Cos(theta),Math.Sin(theta),0};
                double[] radialWorld=TransformVector(t16,radialLocal);
                double[] p17X=Unit(new double[]{t17[0],t17[1],t17[2]});
                double dot=Math.Max(-1.0,Math.Min(1.0,Dot(Unit(radialWorld),p17X)));
                R.p017_orientation_error_deg=Math.Acos(dot)*180.0/Math.PI;
                if(R.p017_orientation_error_deg>0.01)
                    throw new Exception("P017 relief orientation error="+R.p017_orientation_error_deg.ToString("0.######",CultureInfo.InvariantCulture)+" deg");

                double[] z16w=Unit(TransformVector(t16,new double[]{0,0,1}));
                double[] z17w=Unit(TransformVector(t17,new double[]{0,0,1}));
                double zDot=Math.Max(-1.0,Math.Min(1.0,Dot(z16w,z17w)));
                R.p017_axis_alignment_deg=Math.Acos(zDot)*180.0/Math.PI;
                if(R.p017_axis_alignment_deg>0.01)
                    throw new Exception("P017 axial alignment error="+R.p017_axis_alignment_deg.ToString("0.######",CultureInfo.InvariantCulture)+" deg");

                double[] topWorld=TransformPoint(t16,c16loc);
                double[] bottomWorld=TransformPoint(t17,new double[]{0,0,0});
                double[] p17TopWorld=TransformPoint(t17,new double[]{0,0,0.006});
                R.p017_bottom_offset_along_p016_z_mm=1000.0*Dot(Sub(bottomWorld,topWorld),z16w);
                R.p017_press_depth_mm=-R.p017_bottom_offset_along_p016_z_mm;
                R.p017_protrusion_mm=1000.0*Dot(Sub(p17TopWorld,topWorld),z16w);

                Log("P017 signed readback: axis_deg="+R.p017_axis_alignment_deg.ToString("0.######",CultureInfo.InvariantCulture)+
                    " depth_mm="+R.p017_press_depth_mm.ToString("0.######",CultureInfo.InvariantCulture)+
                    " protrusion_mm="+R.p017_protrusion_mm.ToString("0.######",CultureInfo.InvariantCulture));

                if(Math.Abs(R.p017_press_depth_mm-4.0)>0.02)
                    throw new Exception("P017 signed press depth="+R.p017_press_depth_mm+" mm");
                if(Math.Abs(R.p017_protrusion_mm-2.0)>0.02)
                    throw new Exception("P017 signed protrusion="+R.p017_protrusion_mm+" mm");

                RunStrokeQa(doc,asm);
                if(!R.original_limit_restored)
                    throw new Exception("Original LimitDistance1 position was not restored");

                R.checks.Add("PASS: assembly links only stable P003/P016/P017 identities; no candidate paths.");
                R.checks.Add("PASS: 14 modeled occurrences; P003/P016/P017 fully constrained; active mate errors=0.");
                R.checks.Add("PASS: controlled Datum-C/P017 mate features exist.");
                R.checks.Add("PASS: Datum-C C-center, P017 orientation, signed 4-mm press depth and +2-mm protrusion verified.");
                R.checks.Add("PASS: IN/MID/OUT unexpected interference count=0.");
                R.checks.Add("PASS: P001/P008/B001/P013 moving-group propagation preserved.");

                R.status="PASS_STABLE_ASSEMBLY_QA";
                R.release_status="HOLD_PRODUCT_RELEASE";
                R.notes.Add("This is engineering-baseline integration QA only; it does not close release-only requirements.");
                R.notes.Add("P017 material baseline is 316L / EN 1.4404; native material-card assignment remains OPEN.");
            }
            finally
            {
                try{sw.CloseDoc(title);}catch{}
            }
        }

        static void RunStrokeQa(ModelDoc2 doc,AssemblyDoc asm)
        {
            Feature lf=FindFeatureRecursive(doc,"LimitDistance1");
            if(lf==null) throw new Exception("LimitDistance1 feature missing");
            Dimension q=lf.Parameter("D1") as Dimension;
            if(q==null) throw new Exception("D1@LimitDistance1 missing");
            double original=q.SystemValue;
            R.original_limit_distance_mm=original*1000.0;

            Dictionary<string,double[]> atIn=null, atMid=null, atOut=null;

            string[] states=new string[]{"IN","MID","OUT"};
            double[] vals=new double[]{0.0,0.005,0.010};
            for(int i=0;i<states.Length;i++)
            {
                q.SystemValue=vals[i];
                bool rb=doc.ForceRebuild3(false);
                if(!rb) throw new Exception("ForceRebuild3 returned false at "+states[i]);
                Dictionary<string,double[]> p=CaptureMovingTranslations(asm);
                if(states[i]=="IN") atIn=p;
                if(states[i]=="MID") atMid=p;
                if(states[i]=="OUT") atOut=p;
                RunInterference(asm,states[i]);
            }

            q.SystemValue=original;
            doc.ForceRebuild3(false);
            R.original_limit_restored=Math.Abs(q.SystemValue-original)<1e-10;

            string[] ids=new string[]{"K01-P-001","K01-P-008","K01-B-001","K01-P-013"};
            double[] p1m=Sub(atMid["K01-P-001"],atIn["K01-P-001"]);
            double[] p1o=Sub(atOut["K01-P-001"],atIn["K01-P-001"]);
            bool all=true;
            foreach(string id in ids)
            {
                double[] dm=Sub(atMid[id],atIn[id]);
                double[] dout=Sub(atOut[id],atIn[id]);
                double em=1000.0*MaxAbs(Sub(dm,p1m));
                double eo=1000.0*MaxAbs(Sub(dout,p1o));
                bool ok=em<=1e-5 && eo<=1e-5;
                all=all&&ok;
                R.moving_group.Add(new MotionRow{
                    part_id=id,
                    delta_mid_mm=Scale(dm,1000.0),
                    delta_out_mm=Scale(dout,1000.0),
                    max_vector_error_mid_mm=em,
                    max_vector_error_out_mm=eo,
                    status=ok?"PASS":"HOLD"
                });
            }
            R.moving_group_pass=all;
            if(!all) throw new Exception("Moving-group propagation changed after Datum-C candidate integration");
            if(R.unexpected_interference_total!=0)
                throw new Exception("Unexpected interference(s) found in IN/MID/OUT sweep: "+R.unexpected_interference_total);
        }

        static void RunInterference(AssemblyDoc asm,string state)
        {
            InterferenceDetectionMgr mgr=asm.InterferenceDetectionManager;
            mgr.TreatCoincidenceAsInterference=false;
            mgr.TreatSubAssembliesAsComponents=false;
            mgr.IncludeMultibodyPartInterferences=true;
            mgr.MakeInterferingPartsTransparent=false;
            mgr.CreateFastenersFolder=false;
            mgr.IgnoreHiddenBodies=false;
            mgr.ShowIgnoredInterferences=false;
            mgr.UseTransform=false;
            object raw=mgr.GetInterferences();
            object[] rows=ToObjects(raw);
            foreach(object o in rows)
            {
                IInterference it=o as IInterference;
                if(it==null) continue;
                InterferenceRow r=new InterferenceRow();
                r.state=state;
                r.volume_mm3=it.Volume*1e9;
                object[] cc=ToObjects(it.Components);
                foreach(object co in cc)
                {
                    Component2 c=co as Component2;
                    if(c==null) continue;
                    string n=c.Name2??"";
                    r.components.Add(n);
                    r.part_ids.Add(PartId(n+"|"+SafePath(c)));
                }
                r.classification=ClassifyInterference(r.part_ids);
                if(r.classification=="NEW_OR_UNCLASSIFIED") R.unexpected_interference_total++;
                R.interferences.Add(r);
            }
            try{mgr.Done();}catch{}
        }

        static string ClassifyInterference(List<string> ids)
        {
            string s=String.Join("|",ids.ToArray()).ToUpperInvariant();
            if((s.Contains("K01-P-001")&&s.Contains("K01-P-008")) ||
               (s.Contains("K01-P-003")&&s.Contains("K01-P-009")))
                return "KNOWN_INTENTIONAL_OR_LEGACY";
            return "NEW_OR_UNCLASSIFIED";
        }

        static Dictionary<string,double[]> CaptureMovingTranslations(AssemblyDoc asm)
        {
            string[] ids=new string[]{"K01-P-001","K01-P-008","K01-B-001","K01-P-013"};
            Dictionary<string,double[]> d=new Dictionary<string,double[]>(StringComparer.OrdinalIgnoreCase);
            foreach(string id in ids)
            {
                Component2 c=FindCompByIdentity(asm,id);
                if(c==null) throw new Exception("Moving-group component missing: "+id);
                double[] t=Transform(c);
                d[id]=new double[]{t[9],t[10],t[11]};
            }
            return d;
        }

        static double AlignP016Clocking(ModelDoc2 doc,Component2 c3,Component2 c16,double[] c3loc,double[] c16loc)
        {
            double[] t3=Transform(c3);
            double[] t16=Transform(c16);

            // P003 Datum-B axis is local X; P016 Datum-B axis is local Z.
            double[] b3loc=new double[]{c3loc[0],0,0};
            double[] b16loc=new double[]{0,0,c16loc[2]};
            double[] r3=Unit(Sub(TransformPoint(t3,c3loc),TransformPoint(t3,b3loc)));
            double[] r16=Unit(Sub(TransformPoint(t16,c16loc),TransformPoint(t16,b16loc)));
            double[] axis=Unit(TransformVector(t16,new double[]{0,0,1}));

            double delta=SignedAngle(r16,r3,axis);
            double[] rz=RotationZ(delta);
            SetTransform(c16,Compose(t16,rz));
            bool rb=doc.ForceRebuild3(false);
            if(!rb) throw new Exception("ForceRebuild3 false after P016 clocking alignment");

            double[] t16a=Transform(c16);
            double[] c3w=TransformPoint(Transform(c3),c3loc);
            double[] c16w=TransformPoint(t16a,c16loc);
            double err=1000.0*Norm(Sub(c3w,c16w));
            Log("P016 geometric clocking delta_deg="+(delta*180.0/Math.PI).ToString("0.######",CultureInfo.InvariantCulture)+
                " C-center error_mm="+err.ToString("0.######",CultureInfo.InvariantCulture));
            return delta*180.0/Math.PI;
        }

        static bool AddClockingAngleMate(AssemblyDoc asm,ModelDoc2 doc,Component2 c3,Component2 c16,
            out string p3PlaneName,out string p16PlaneName,out double angleRad)
        {
            p3PlaneName=""; p16PlaneName=""; angleRad=0.0;

            ModelDoc2 d3=c3.GetModelDoc2() as ModelDoc2;
            ModelDoc2 d16=c16.GetModelDoc2() as ModelDoc2;
            if(d3==null || d16==null) throw new Exception("Part docs unavailable for clocking-plane mate");

            double[] t3=Transform(c3);
            double[] t16=Transform(c16);
            double[] bAxis=Unit(TransformVector(t16,new double[]{0,0,1}));

            List<Feature> p3=RefPlanes(d3);
            List<Feature> p16=RefPlanes(d16);
            if(p3.Count<2 || p16.Count<2) throw new Exception("Reference-plane inventory incomplete");

            Feature best3=null,best16=null;
            double[] bestN3=null,bestN16=null;
            double bestScore=-1.0;

            foreach(Feature f3 in p3)
            {
                double[] n3=RefPlaneNormalWorld(f3,t3);
                double tr3=Norm(Sub(n3,Scale(bAxis,Dot(n3,bAxis))));
                if(tr3<0.5) continue; // plane normal must be sensitive to rotation about B

                foreach(Feature f16 in p16)
                {
                    double[] n16=RefPlaneNormalWorld(f16,t16);
                    double tr16=Norm(Sub(n16,Scale(bAxis,Dot(n16,bAxis))));
                    if(tr16<0.5) continue;

                    // Prefer strongly transverse normals and a well-conditioned angle
                    // (avoid almost parallel/anti-parallel where angle direction is ambiguous).
                    double c=Math.Abs(Dot(Unit(n3),Unit(n16)));
                    double conditioning=1.0-Math.Abs(c-0.5); // broad preference around 60 deg
                    double score=tr3*tr16+0.05*conditioning;
                    if(score>bestScore)
                    {
                        bestScore=score; best3=f3; best16=f16; bestN3=n3; bestN16=n16;
                    }
                }
            }
            if(best3==null || best16==null) throw new Exception("No suitable transverse reference-plane pair for Datum C");

            double dot=Math.Max(-1.0,Math.Min(1.0,Dot(Unit(bestN3),Unit(bestN16))));
            angleRad=Math.Acos(dot);
            p3PlaneName=best3.Name??"";
            p16PlaneName=best16.Name??"";

            object o3=c3.GetCorresponding(best3);
            object o16=c16.GetCorresponding(best16);
            Feature a3=o3 as Feature;
            Feature a16=o16 as Feature;
            if(a3==null || a16==null)
                throw new Exception("GetCorresponding failed for Datum-C reference planes");

            HashSet<string> before=MateNames(doc);
            doc.ClearSelection2(true);
            if(!a3.Select2(false,1) || !a16.Select2(true,1))
                throw new Exception("Datum-C reference-plane selection failed");

            int err=0;
            Mate2 m=asm.AddMate5(
                (int)swMateType_e.swMateANGLE,(int)swMateAlign_e.swMateAlignCLOSEST,false,
                0,0,0,1,1,
                angleRad,angleRad,angleRad,
                false,false,0,out err);
            doc.ClearSelection2(true);

            Log("K01_J1_DATUM_C_CLOCKING_ANGLE AddMate5 ErrorStatus="+err+
                " result="+(m==null?"null":"Mate2")+
                " P003_plane="+p3PlaneName+" P016_plane="+p16PlaneName+
                " angle_deg="+(angleRad*180.0/Math.PI).ToString("0.######",CultureInfo.InvariantCulture));

            if(m==null || err!=(int)swAddMateError_e.swAddMateError_NoError) return false;
            Feature nf=FindNewMate(doc,before);
            if(nf==null) throw new Exception("Datum-C angle mate feature not found");
            nf.Name="K01_J1_DATUM_C_CLOCKING_ANGLE";
            return true;
        }

        static List<Feature> RefPlanes(ModelDoc2 doc)
        {
            List<Feature> r=new List<Feature>();
            Feature f=doc.FirstFeature() as Feature;
            while(f!=null)
            {
                if(String.Equals(f.GetTypeName2(),"RefPlane",StringComparison.OrdinalIgnoreCase))
                    r.Add(f);
                f=f.GetNextFeature() as Feature;
            }
            return r;
        }

        static double[] RefPlaneNormalWorld(Feature f,double[] componentTransform)
        {
            RefPlane rp=f.GetSpecificFeature2() as RefPlane;
            if(rp==null) throw new Exception("RefPlane specific feature unavailable: "+f.Name);
            MathTransform mt=rp.Transform as MathTransform;
            if(mt==null) throw new Exception("RefPlane transform unavailable: "+f.Name);
            double[] pt=ToD(mt.ArrayData);
            double[] localNormal=Unit(TransformVector(pt,new double[]{0,0,1}));
            return Unit(TransformVector(componentTransform,localNormal));
        }

        static int PressConcentricAlignmentForSameLocalZ(CylHit p17,CylHit p16)
        {
            if(p17==null || p16==null) throw new Exception("P017/P016 cylinder hit missing for press alignment");

            double s17=Dot(Unit(p17.axis),new double[]{0,0,1});
            double s16=Dot(Unit(p16.axis),new double[]{0,0,1});
            if(Math.Abs(Math.Abs(s17)-1.0)>1e-5 || Math.Abs(Math.Abs(s16)-1.0)>1e-5)
                throw new Exception("P017/P016 press cylinders are not local-Z axes");

            // If the signed cylinder parameter axes have the same local-Z sign, ALIGNED
            // preserves equal component +Z directions. If their signs differ, ANTI_ALIGNED
            // is required to preserve equal component +Z directions.
            return (s17*s16>=0.0)
                ? (int)swMateAlign_e.swMateAlignALIGNED
                : (int)swMateAlign_e.swMateAlignANTI_ALIGNED;
        }

        static double SignedAngle(double[] from,double[] to,double[] axis)
        {
            double[] a=Unit(from),b=Unit(to),n=Unit(axis);
            double c=Math.Max(-1.0,Math.Min(1.0,Dot(a,b)));
            double s=Dot(n,Cross(a,b));
            return Math.Atan2(s,c);
        }

        static double[] RotationZ(double a)
        {
            double c=Math.Cos(a),s=Math.Sin(a);
            return new double[]{
                c,s,0,
                -s,c,0,
                0,0,1,
                0,0,0,
                1,0,0,0
            };
        }

        static double[] Cross(double[] a,double[] b)
        {
            return new double[]{
                a[1]*b[2]-a[2]*b[1],
                a[2]*b[0]-a[0]*b[2],
                a[0]*b[1]-a[1]*b[0]
            };
        }

        static Component2 AddPart(AssemblyDoc asm,string path)
        {
            int e=0,w=0;
            ModelDoc2 preload=sw.OpenDoc6(path,(int)swDocumentTypes_e.swDocPART,
                (int)swOpenDocOptions_e.swOpenDocOptions_Silent,"",ref e,ref w) as ModelDoc2;
            if(preload==null) throw new Exception("P017 preload failed e="+e+" w="+w);
            Component2 c=asm.AddComponent5(path,0,"",false,"",0.0,0.0,0.0) as Component2;
            if(c==null) throw new Exception("AddComponent5 P017 returned null");
            int rrc=asm.ResolveAllLightWeightComponents(false);
            Log("P017 added via AddComponent5; ResolveAllLightWeightComponents rc="+rrc);
            return c;
        }

        static Entity ResolveMateEntity(Component2 c,object source,string tag)
        {
            Entity e=null;

            try
            {
                e=c.GetCorrespondingEntity(source) as Entity;
                if(e!=null)
                {
                    Log(tag+" corresponding entity via GetCorrespondingEntity");
                    return e;
                }
            }
            catch(Exception ex)
            {
                Log(tag+" GetCorrespondingEntity note: "+ex.GetType().Name+": "+ex.Message);
            }

            Entity se=source as Entity;
            if(se!=null)
            {
                try
                {
                    e=c.IGetCorrespondingEntity(se);
                    if(e!=null)
                    {
                        Log(tag+" corresponding entity via IGetCorrespondingEntity");
                        return e;
                    }
                }
                catch(Exception ex)
                {
                    Log(tag+" IGetCorrespondingEntity note: "+ex.GetType().Name+": "+ex.Message);
                }
            }

            Face2 sf=source as Face2;
            if(sf!=null)
            {
                e=ResolveFaceFromOccurrenceBody(c,sf,tag);
                if(e!=null)
                {
                    Log(tag+" corresponding entity via occurrence-body fallback");
                    return e;
                }
            }

            Log(tag+" corresponding entity unresolved");
            return null;
        }

        static Entity ResolveFaceFromOccurrenceBody(Component2 c,Face2 source,string tag)
        {
            Body2 b=null;
            try{b=c.GetBody() as Body2;}
            catch(Exception ex){Log(tag+" GetBody note: "+ex.GetType().Name+": "+ex.Message);}
            if(b==null) return null;

            Surface ss=null;
            try{ss=source.GetSurface() as Surface;}
            catch(Exception ex)
            {
                Log(tag+" source Face2 unavailable for occurrence fallback: "+ex.GetType().Name+": "+ex.Message);
                return null;
            }
            if(ss==null) return null;

            bool srcCyl=false,srcPlane=false;
            try{srcCyl=ss.IsCylinder();}catch{}
            try{srcPlane=ss.IsPlane();}catch{}

            double srcArea=0;
            try{srcArea=source.GetArea();}catch{}

            double srcRadius=-1;
            if(srcCyl)
            {
                try
                {
                    double[] cp=ToD(ss.CylinderParams);
                    if(cp.Length>=7) srcRadius=Math.Abs(cp[6]);
                }
                catch{}
            }

            Face2 best=null;
            double bestScore=Double.MaxValue;
            foreach(object fo in ToObjects(b.GetFaces()))
            {
                Face2 f=fo as Face2;
                if(f==null) continue;
                Surface s=f.GetSurface() as Surface;
                if(s==null) continue;

                bool isCyl=false,isPlane=false;
                try{isCyl=s.IsCylinder();}catch{}
                try{isPlane=s.IsPlane();}catch{}
                if(srcCyl!=isCyl || srcPlane!=isPlane) continue;

                double area=0;
                try{area=f.GetArea();}catch{}
                double score=Math.Abs(area-srcArea)*1.0e6;

                if(srcCyl)
                {
                    double[] cp=ToD(s.CylinderParams);
                    if(cp.Length<7) continue;
                    double r=Math.Abs(cp[6]);
                    double rErr=Math.Abs(r-srcRadius);
                    if(rErr>0.00002) continue;
                    score+=rErr*1.0e9;
                }

                if(score<bestScore)
                {
                    bestScore=score;
                    best=f;
                }
            }

            if(best==null) return null;
            Log(tag+" occurrence-body face score="+bestScore.ToString("0.######",CultureInfo.InvariantCulture));
            return best as Entity;
        }

        static bool AddMate(AssemblyDoc asm,ModelDoc2 doc,Component2 c1,object p1,Component2 c2,object p2,
            int type,int align,bool flip,double distance,bool lockRotation,string name)
        {
            Entity e1=ResolveMateEntity(c1,p1,name+"[1]");
            Entity e2=ResolveMateEntity(c2,p2,name+"[2]");
            if(e1==null || e2==null)
                throw new Exception(name+": corresponding entity null e1="+(e1==null?"NULL":"OK")+" e2="+(e2==null?"NULL":"OK"));

            HashSet<string> before=MateNames(doc);
            doc.ClearSelection2(true);
            SelectionMgr sm=doc.SelectionManager as SelectionMgr;
            SelectData d1=sm.CreateSelectData() as SelectData;
            SelectData d2=sm.CreateSelectData() as SelectData;
            d1.Mark=1; d2.Mark=1;
            if(!e1.Select4(false,d1) || !e2.Select4(true,d2))
                throw new Exception(name+": entity selection failed");

            int err=0;
            Mate2 m=asm.AddMate5(type,align,flip,
                distance,distance,distance,
                1,1,0,0,0,
                false,lockRotation,0,out err);
            doc.ClearSelection2(true);
            Log(name+" AddMate5 ErrorStatus="+err+" lockRotation="+lockRotation+" result="+(m==null?"null":"Mate2"));
            if(m==null || err!=(int)swAddMateError_e.swAddMateError_NoError) return false;

            Feature nf=FindNewMate(doc,before);
            if(nf==null) throw new Exception(name+": new mate feature not found");
            nf.Name=name;
            return true;
        }

        static Feature FindNewMate(ModelDoc2 doc,HashSet<string> before)
        {
            Feature g=MateGroup(doc); if(g==null) return null;
            Feature f=g.GetFirstSubFeature() as Feature, found=null;
            while(f!=null){ if(!before.Contains(f.Name??"")) found=f; f=f.GetNextSubFeature() as Feature; }
            return found;
        }

        static HashSet<string> MateNames(ModelDoc2 doc)
        {
            HashSet<string> h=new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            Feature g=MateGroup(doc); if(g==null) return h;
            Feature f=g.GetFirstSubFeature() as Feature;
            while(f!=null){h.Add(f.Name??"");f=f.GetNextSubFeature() as Feature;}
            return h;
        }

        static Feature MateGroup(ModelDoc2 doc)
        {
            Feature f=doc.FirstFeature() as Feature;
            while(f!=null)
            {
                if(String.Equals(f.GetTypeName2(),"MateGroup",StringComparison.OrdinalIgnoreCase)) return f;
                f=f.GetNextFeature() as Feature;
            }
            return null;
        }

        static int ActiveMateErrors(ModelDoc2 doc)
        {
            int n=0; Feature g=MateGroup(doc); if(g==null) return 0;
            Feature f=g.GetFirstSubFeature() as Feature;
            while(f!=null)
            {
                if(!IsSuppressed(f))
                {
                    bool warn=false; int code=f.GetErrorCode2(out warn);
                    if(code!=0 && !warn){n++;Log("ACTIVE MATE ERROR "+f.Name+" code="+code);}
                }
                f=f.GetNextSubFeature() as Feature;
            }
            Log("Active mate errors="+n); return n;
        }

        static bool IsSuppressed(Feature f)
        {
            try
            {
                object o=f.IsSuppressed2((int)swInConfigurationOpts_e.swThisConfiguration,null);
                if(o is bool) return (bool)o;
                Array a=o as Array; if(a!=null && a.Length>0) return Convert.ToBoolean(a.GetValue(0));
            }catch{}
            return false;
        }

        static Feature FindFeatureRecursive(ModelDoc2 doc,string name)
        {
            Feature top=doc.FirstFeature() as Feature;
            while(top!=null)
            {
                Feature hit=FindFeatureSub(top,name);
                if(hit!=null) return hit;
                top=top.GetNextFeature() as Feature;
            }
            return null;
        }

        static Feature FindFeatureSub(Feature f,string name)
        {
            Feature cur=f;
            while(cur!=null)
            {
                if(String.Equals(cur.Name,name,StringComparison.OrdinalIgnoreCase)) return cur;
                Feature sub=cur.GetFirstSubFeature() as Feature;
                Feature hit=FindFeatureSub(sub,name);
                if(hit!=null) return hit;
                cur=cur.GetNextSubFeature() as Feature;
            }
            return null;
        }

        static CylHit FindCyl(ModelDoc2 doc,double dmm,double tolMm,double[] axisExpected,double[] center2)
        {
            CylHit best=null;
            foreach(Face2 f in Faces(doc))
            {
                Surface s=f.GetSurface() as Surface;
                if(s==null || !s.IsCylinder()) continue;
                double[] p=ToD(s.CylinderParams);
                if(p.Length<7) continue;
                double d=2.0*Math.Abs(p[6])/MM;
                if(Math.Abs(d-dmm)>tolMm) continue;
                double[] ax=Unit(new double[]{p[3],p[4],p[5]});
                if(Math.Abs(Math.Abs(Dot(ax,axisExpected))-1.0)>1e-5) continue;

                double score=0;
                if(center2!=null)
                {
                    if(Math.Abs(axisExpected[0])>0.9)
                        score=Math.Sqrt(Math.Pow(p[1]-center2[0],2)+Math.Pow(p[2]-center2[1],2));
                    else if(Math.Abs(axisExpected[2])>0.9)
                        score=Math.Sqrt(Math.Pow(p[0]-center2[0],2)+Math.Pow(p[1]-center2[1],2));
                }
                if(best==null || score<best.score)
                    best=new CylHit{face=f,origin=new double[]{p[0],p[1],p[2]},axis=ax,dmm=d,score=score};
            }
            return best;
        }

        static PlaneHit FindPlane(ModelDoc2 doc,int axisIndex,double target,double tolMm,double minAreaMm2)
        {
            PlaneHit best=null;
            foreach(Face2 f in Faces(doc))
            {
                Surface s=f.GetSurface() as Surface;
                if(s==null || !s.IsPlane()) continue;
                double[] p=ToD(s.PlaneParams);
                if(p.Length<6) continue;
                double[] n=Unit(new double[]{p[0],p[1],p[2]});
                if(Math.Abs(Math.Abs(n[axisIndex])-1.0)>1e-5) continue;
                double station=p[3+axisIndex];
                if(Math.Abs(station-target)>tolMm*MM) continue;
                double area=f.GetArea()*1e6;
                if(area<minAreaMm2) continue;
                if(best==null || area>best.area) best=new PlaneHit{face=f,station=station,area=area};
            }
            return best;
        }

        static IEnumerable<Face2> Faces(ModelDoc2 doc)
        {
            PartDoc p=doc as PartDoc;
            if(p==null) throw new Exception("Not PartDoc "+doc.GetTitle());
            foreach(object bo in ToObjects(p.GetBodies2((int)swBodyType_e.swSolidBody,false)))
            {
                Body2 b=bo as Body2; if(b==null) continue;
                foreach(object fo in ToObjects(b.GetFaces()))
                {
                    Face2 f=fo as Face2; if(f!=null) yield return f;
                }
            }
        }

        static double[] Transform(Component2 c)
        {
            MathTransform mt=c.Transform2 as MathTransform;
            if(mt==null) throw new Exception("Transform2 unavailable for "+(c.Name2??""));
            return ToD(mt.ArrayData);
        }

        static void SetTransform(Component2 c,double[] t)
        {
            MathUtility mu=sw.GetMathUtility() as MathUtility;
            if(mu==null) throw new Exception("MathUtility unavailable");
            MathTransform mt=mu.CreateTransform((object)t) as MathTransform;
            if(mt==null) throw new Exception("CreateTransform returned null");
            c.Transform2=mt;
        }

        static double[] LocalP017Transform(double[] c,double theta)
        {
            double ct=Math.Cos(theta),st=Math.Sin(theta);
            return new double[]{
                ct,st,0,
                -st,ct,0,
                0,0,1,
                c[0],c[1],c[2]-0.004,
                1,0,0,0
            };
        }

        static double[] Compose(double[] a,double[] b)
        {
            double[] ex=TransformVector(a,new double[]{b[0],b[1],b[2]});
            double[] ey=TransformVector(a,new double[]{b[3],b[4],b[5]});
            double[] ez=TransformVector(a,new double[]{b[6],b[7],b[8]});
            double[] bt=new double[]{b[9],b[10],b[11]};
            double[] t=Add(new double[]{a[9],a[10],a[11]},TransformVector(a,bt));
            return new double[]{
                ex[0],ex[1],ex[2],
                ey[0],ey[1],ey[2],
                ez[0],ez[1],ez[2],
                t[0],t[1],t[2],
                1,0,0,0
            };
        }

        static double[] TransformPoint(double[] t,double[] p)
        {
            return Add(new double[]{t[9],t[10],t[11]},TransformVector(t,p));
        }

        static double[] TransformVector(double[] t,double[] v)
        {
            return new double[]{
                t[0]*v[0]+t[3]*v[1]+t[6]*v[2],
                t[1]*v[0]+t[4]*v[1]+t[7]*v[2],
                t[2]*v[0]+t[5]*v[1]+t[8]*v[2]
            };
        }

        static Component2 FindCompByPath(AssemblyDoc asm,string path)
        {
            foreach(object o in ToObjects(asm.GetComponents(false)))
            {
                Component2 c=o as Component2;
                if(c!=null && String.Equals(Norm(SafePath(c)),Norm(path),StringComparison.OrdinalIgnoreCase)) return c;
            }
            return null;
        }

        static Component2 FindCompByIdentity(AssemblyDoc asm,string id)
        {
            foreach(object o in ToObjects(asm.GetComponents(false)))
            {
                Component2 c=o as Component2; if(c==null) continue;
                string s=(c.Name2??"")+"|"+SafePath(c);
                if(s.IndexOf(id,StringComparison.OrdinalIgnoreCase)>=0) return c;
            }
            return null;
        }

        static int CountModeled(AssemblyDoc asm)
        {
            int n=0;
            foreach(object o in ToObjects(asm.GetComponents(false)))
            {
                Component2 c=o as Component2; if(c==null) continue;
                if(c.GetSuppression()==(int)swComponentSuppressionState_e.swComponentSuppressed) continue;
                if(!String.IsNullOrWhiteSpace(SafePath(c))) n++;
            }
            return n;
        }

        static string ConstrainedName(Component2 c)
        {
            int x=c.GetConstrainedStatus();
            string n=Enum.GetName(typeof(swConstrainedStatus_e),x);
            return String.IsNullOrWhiteSpace(n)?x.ToString(CultureInfo.InvariantCulture):n;
        }

        static bool IsFully(string s)
        {
            return (s??"").IndexOf("Fully",StringComparison.OrdinalIgnoreCase)>=0;
        }

        static void Replace(AssemblyDoc asm,ModelDoc2 doc,Component2 c,string path,string tag)
        {
            doc.ClearSelection2(true);
            if(!c.Select4(false,null,false)) throw new Exception(tag+" component selection failed");
            bool ok=asm.ReplaceComponents2(path,"",false,
                (int)swReplaceComponentsConfiguration_e.swReplaceComponentsConfiguration_MatchName,true);
            if(!ok) throw new Exception(tag+" ReplaceComponents2 false");
            Log(tag+" replaced -> "+path);
        }

        static void CopyFresh(string src,string dst)
        {
            Need(src); Close(dst);
            Directory.CreateDirectory(Path.GetDirectoryName(dst));
            if(File.Exists(dst))
            {
                string hd=Path.Combine(Path.GetDirectoryName(dst),"history");
                Directory.CreateDirectory(hd);
                string h=Path.Combine(hd,Path.GetFileNameWithoutExtension(dst)+"_"+DateTime.Now.ToString("yyyyMMdd_HHmmss")+Path.GetExtension(dst));
                File.Copy(dst,h,true); File.Delete(dst);
            }
            File.Copy(src,dst,true);
        }

        static void Save(ModelDoc2 doc,string label)
        {
            int e=0,w=0;
            bool ok=doc.Save3((int)swSaveAsOptions_e.swSaveAsOptions_Silent,ref e,ref w);
            if(!ok || e!=0) throw new Exception(label+" Save3 errors="+e+" warnings="+w);
            Log(label+" saved warnings="+w);
        }

        static void SetProp(ModelDoc2 doc,string k,string v)
        {
            CustomPropertyManager c=doc.Extension.get_CustomPropertyManager("");
            try{c.Delete2(k);}catch{}
            int r=c.Add(k,"Text",v);
            if(r==0) try{c.Set2(k,v);}catch{}
        }

        static string PartId(string s)
        {
            Match m=Regex.Match(s??"",@"K01-(?:P|B)-\d{3}",RegexOptions.IgnoreCase);
            return m.Success?m.Value.ToUpperInvariant():"";
        }

        static string SafePath(Component2 c)
        {
            try{return c.GetPathName()??"";}catch{return "";}
        }

        static void Need(string p){if(String.IsNullOrWhiteSpace(p)||!File.Exists(p))throw new Exception("Missing "+p);}
        static void Close(string p){try{ModelDoc2 d=sw==null?null:sw.GetOpenDocumentByName(p) as ModelDoc2;if(d!=null)sw.CloseDoc(d.GetTitle());}catch{}}
        static string Norm(string p){try{return Path.GetFullPath(p).TrimEnd('\\').ToLowerInvariant();}catch{return (p??"").ToLowerInvariant();}}

        static double[] Need3(double[] a,string label)
        {
            if(a==null || a.Length<3) throw new Exception(label+" missing");
            return new double[]{a[0],a[1],a[2]};
        }

        static object[] ToObjects(object x)
        {
            if(x==null)return new object[0];
            object[] o=x as object[]; if(o!=null)return o;
            Array a=x as Array; if(a==null)return new object[]{x};
            object[] r=new object[a.Length];
            for(int i=0;i<a.Length;i++)r[i]=a.GetValue(i);
            return r;
        }

        static double[] ToD(object x)
        {
            if(x==null)return new double[0];
            double[] d=x as double[]; if(d!=null)return d;
            Array a=x as Array; if(a==null)return new double[0];
            double[] r=new double[a.Length];
            for(int i=0;i<a.Length;i++)r[i]=Convert.ToDouble(a.GetValue(i),CultureInfo.InvariantCulture);
            return r;
        }

        static double[] Add(double[] a,double[] b){return new double[]{a[0]+b[0],a[1]+b[1],a[2]+b[2]};}
        static double[] Sub(double[] a,double[] b){return new double[]{a[0]-b[0],a[1]-b[1],a[2]-b[2]};}
        static double[] Scale(double[] a,double s){return new double[]{a[0]*s,a[1]*s,a[2]*s};}
        static double Dot(double[] a,double[] b){return a[0]*b[0]+a[1]*b[1]+a[2]*b[2];}
        static double Norm(double[] a){return Math.Sqrt(Dot(a,a));}
        static double[] Unit(double[] a){double n=Norm(a);if(n<=0)throw new Exception("zero vector");return Scale(a,1.0/n);}
        static double MaxAbs(double[] a){return Math.Max(Math.Abs(a[0]),Math.Max(Math.Abs(a[1]),Math.Abs(a[2])));}

        static string Sha256(string p)
        {
            using(FileStream fs=new FileStream(p,FileMode.Open,FileAccess.Read,FileShare.ReadWrite|FileShare.Delete))
            using(SHA256 h=SHA256.Create())
                return BitConverter.ToString(h.ComputeHash(fs)).Replace("-","").ToLowerInvariant();
        }

        static void Log(string s)
        {
            string l="["+DateTime.Now.ToString("s")+"] "+s;
            Console.WriteLine(l);
            if(!String.IsNullOrWhiteSpace(logPath)) File.AppendAllText(logPath,l+System.Environment.NewLine);
        }

        static void SaveReport()
        {
            if(String.IsNullOrWhiteSpace(outJson)) return;
            JavaScriptSerializer js=new JavaScriptSerializer();
            js.MaxJsonLength=Int32.MaxValue;
            File.WriteAllText(outJson,js.Serialize(R));
        }
    }
}
