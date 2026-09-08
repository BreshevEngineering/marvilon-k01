using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Runtime.InteropServices;
using System.Web.Script.Serialization;
using SolidWorks.Interop.sldworks;
using SolidWorks.Interop.swconst;

namespace Marvilon.K01.Gate04D_C2.Verify
{
    public sealed class Rpt
    {
        public string schema="k01_gate04d_c2_verify_v1";
        public string created_utc=DateTime.UtcNow.ToString("o");
        public string status="RUNNING";
        public string solidworks_revision="";
        public bool p003_candidate=false;
        public bool p007_candidate=false;
        public bool old_concentric5_suppressed=false;
        public bool old_coincident5_suppressed=false;
        public bool j2_pilot_concentric=false;
        public bool j2_axial_face=false;
        public bool j2_clocking_m2p5=false;
        public int active_mate_errors=-1;
        public List<string> notes=new List<string>();
        public string error="";
    }

    public sealed class PlaneHit
    {
        public Face2 face;
        public double x;
        public double area;
    }

    public static class Program
    {
        const double MM=0.001;
        const double PI=Math.PI;

        const string A001=@"D:\Marvilon\K01\cad\assemblies\K01-A-001_Calibration_Module.SLDASM";
        const string P003S=@"D:\Marvilon\K01\cad\parts\K01-P-003_Cartridge_Body.SLDPRT";
        const string P007S=@"D:\Marvilon\K01\cad\parts\K01-P-007_Hermetic_Magnetic_Can.SLDPRT";
        const string P003C=@"D:\Marvilon\K01\cad\candidates\gate04d_c2\K01-P-003_Cartridge_Body_GATE04D_C2_CANDIDATE.SLDPRT";
        const string P007C=@"D:\Marvilon\K01\cad\candidates\gate04d_c2\K01-P-007_Hermetic_Magnetic_Can_GATE04D_C2_CANDIDATE.SLDPRT";
        const string VDIR=@"D:\Marvilon\K01\cad\candidates\gate04d_c2\verification";
        const string VASM=@"D:\Marvilon\K01\cad\candidates\gate04d_c2\verification\K01-A-001_GATE04D_C2_VERIFY.SLDASM";
        const string RDIR=@"D:\BreshevEngineering\marvilon-k01\reports\cad\current";

        static SldWorks sw;
        static Rpt R=new Rpt();
        static string logPath;
        static string jsonPath;

        public static int Main(string[] args)
        {
            try
            {
                Directory.CreateDirectory(VDIR);
                Directory.CreateDirectory(Path.Combine(VDIR,"history"));
                Directory.CreateDirectory(RDIR);
                string stamp=DateTime.Now.ToString("yyyyMMdd_HHmmss");
                logPath=Path.Combine(RDIR,"K01_GATE04D_C2_VERIFY_"+stamp+".log");
                jsonPath=Path.Combine(RDIR,"K01_GATE04D_C2_VERIFY.json");
                File.WriteAllText(logPath,"K01 Gate04D-C2 Verify\r\n");

                Connect();
                Verify();
                R.status="PASS";
                SaveReport();
                Log("STATUS=PASS");
                return 0;
            }
            catch(Exception ex)
            {
                R.status="FAIL";
                R.error=ex.ToString();
                try{SaveReport();}catch{}
                try{Log("STATUS=FAIL\r\n"+ex);}catch{}
                return 1;
            }
        }

        static void Connect()
        {
            object a=null;
            try{a=Marshal.GetActiveObject("SldWorks.Application");}catch{}
            if(a!=null) sw=(SldWorks)a;
            else sw=(SldWorks)Activator.CreateInstance(Type.GetTypeFromProgID("SldWorks.Application",true));
            sw.Visible=true;
            R.solidworks_revision=sw.RevisionNumber();
            Log("Connected SW "+R.solidworks_revision);
        }

        static void Verify()
        {
            Need(A001); Need(P003S); Need(P007S); Need(P003C); Need(P007C);
            CopyFresh(A001,VASM);

            int e=0,w=0;
            ModelDoc2 doc=sw.OpenDoc6(VASM,(int)swDocumentTypes_e.swDocASSEMBLY,
                (int)swOpenDocOptions_e.swOpenDocOptions_Silent,"",ref e,ref w) as ModelDoc2;
            if(doc==null) throw new Exception("Open verification failed errors="+e);
            string title=doc.GetTitle();

            try
            {
                AssemblyDoc asm=doc as AssemblyDoc;
                if(asm==null) throw new Exception("Not AssemblyDoc");

                Feature c5=FindMate(doc,"Concentric5");
                Feature k5=FindMate(doc,"Coincident5");
                GuardPair(c5,"K01-P-003_Cartridge_Body","K01-P-007_Hermetic_Magnetic_Can");
                GuardPair(k5,"K01-P-006_Retaining_Plug","K01-P-007_Hermetic_Magnetic_Can");

                R.old_concentric5_suppressed=Suppress(c5);
                R.old_coincident5_suppressed=Suppress(k5);
                if(!R.old_concentric5_suppressed || !R.old_coincident5_suppressed)
                    throw new Exception("Legacy J2 mate suppression failed");
                Save(doc,"A legacy J2 mates suppressed");

                Component2 s3=FindComp(asm,P003S), s7=FindComp(asm,P007S);
                if(s3==null || s7==null) throw new Exception("Stable P003/P007 component not found");
                Replace(asm,doc,s3,P003C,"P003");
                Replace(asm,doc,s7,P007C,"P007");
                doc.ForceRebuild3(false);
                Save(doc,"B candidates replaced");

                Component2 c3=FindComp(asm,P003C), c7=FindComp(asm,P007C);
                R.p003_candidate=c3!=null; R.p007_candidate=c7!=null;
                if(c3==null || c7==null) throw new Exception("Candidate links missing");

                int pre=ActiveMateErrors(doc);
                if(pre!=0) throw new Exception("Mate errors before new J2 mates="+pre);

                ModelDoc2 d3=c3.GetModelDoc2() as ModelDoc2;
                ModelDoc2 d7=c7.GetModelDoc2() as ModelDoc2;
                if(d3==null || d7==null) throw new Exception("Candidate ModelDoc2 unavailable");

                Face2 pilot3=FindCyl(d3,14.10,0.08,null);
                Face2 bore7=FindCyl(d7,14.10,0.08,null);
                if(pilot3==null || bore7==null) throw new Exception("D14.10 J2 cylinder missing");

                double[] bb3=BoxMm(d3), bb7=BoxMm(d7);
                PlaneHit face3=FindPlaneX(d3,(bb3[3]-1.50)*MM,0.04);
                PlaneHit face7=FindPlaneX(d7,bb7[0]*MM,0.04);

                double ey=14.0*Math.Cos(30.0*PI/180.0);
                double ez=14.0*Math.Sin(30.0*PI/180.0);
                Face2 hole3=FindCyl(d3,2.05,0.10,new double[]{ey,ez});
                Face2 hole7=FindCyl(d7,2.90,0.10,new double[]{ey,ez});
                if(hole3==null || hole7==null) throw new Exception("Clocking hole cylinder missing");

                R.j2_pilot_concentric=AddMate(asm,doc,c3,pilot3,c7,bore7,
                    (int)swMateType_e.swMateCONCENTRIC,(int)swMateAlign_e.swMateAlignCLOSEST,
                    "K01_J2_C2_PILOT_CONCENTRIC");
                if(!R.j2_pilot_concentric) throw new Exception("Pilot mate failed");

                R.j2_axial_face=AddMate(asm,doc,c3,face3.face,c7,face7.face,
                    (int)swMateType_e.swMateCOINCIDENT,(int)swMateAlign_e.swMateAlignANTI_ALIGNED,
                    "K01_J2_C2_AXIAL_FACE");
                if(!R.j2_axial_face) throw new Exception("Axial face mate failed");

                R.j2_clocking_m2p5=AddMate(asm,doc,c3,hole3,c7,hole7,
                    (int)swMateType_e.swMateCONCENTRIC,(int)swMateAlign_e.swMateAlignCLOSEST,
                    "K01_J2_C2_CLOCKING_M2P5");
                if(!R.j2_clocking_m2p5) throw new Exception("Clocking mate failed");

                doc.ForceRebuild3(false);
                Save(doc,"C controlled J2 mates");

                R.active_mate_errors=ActiveMateErrors(doc);
                if(R.active_mate_errors!=0) throw new Exception("Final active mate errors="+R.active_mate_errors);

                SetProp(doc,"K01_GATE","Gate04D_C2_VERIFY");
                SetProp(doc,"J2_MateArchitecture",
                    "P003/P007 face + D14.10 pilot + one M3 hole axis");
                Save(doc,"FINAL Gate04D-C2 Verify");

                R.notes.Add("Legacy Concentric5 and Coincident5 suppressed, not deleted; C2 controlled mates created.");
                R.notes.Add("No Transform2 clocking hack used.");
                R.notes.Add("SW2018 AddMate5 success is ErrorStatus=1.");
                Log("GATE04D-C2 VERIFY PASS");
            }
            catch
            {
                try{Save(doc,"HOLD persisted");}catch{}
                throw;
            }
            finally
            {
                try{sw.CloseDoc(title);}catch{}
            }
        }

        static bool AddMate(AssemblyDoc asm,ModelDoc2 doc,Component2 c1,object p1,Component2 c2,object p2,
            int type,int align,string name)
        {
            Entity e1=c1.GetCorrespondingEntity(p1) as Entity;
            Entity e2=c2.GetCorrespondingEntity(p2) as Entity;
            if(e1==null || e2==null) throw new Exception(name+": corresponding entity null");

            HashSet<string> before=MateNames(doc);
            doc.ClearSelection2(true);
            SelectionMgr sm=doc.SelectionManager as SelectionMgr;
            SelectData d1=sm.CreateSelectData() as SelectData;
            SelectData d2=sm.CreateSelectData() as SelectData;
            d1.Mark=1; d2.Mark=1;
            if(!e1.Select4(false,d1) || !e2.Select4(true,d2))
                throw new Exception(name+": entity selection failed");

            int err=0;
            Mate2 m=asm.AddMate5(type,align,false,0,0,0,1,1,0,0,0,false,false,0,out err);
            doc.ClearSelection2(true);
            Log(name+" AddMate5 ErrorStatus="+err+" result="+(m==null?"null":"Mate2"));
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
            while(f!=null){h.Add(f.Name??""); f=f.GetNextSubFeature() as Feature;}
            return h;
        }

        static Feature MateGroup(ModelDoc2 doc)
        {
            Feature f=doc.FirstFeature() as Feature;
            while(f!=null){if(String.Equals(f.GetTypeName2(),"MateGroup",StringComparison.OrdinalIgnoreCase))return f; f=f.GetNextFeature() as Feature;}
            return null;
        }

        static Feature FindMate(ModelDoc2 doc,string name)
        {
            Feature g=MateGroup(doc); if(g==null) return null;
            Feature f=g.GetFirstSubFeature() as Feature;
            while(f!=null){if(String.Equals(f.Name,name,StringComparison.OrdinalIgnoreCase))return f; f=f.GetNextSubFeature() as Feature;}
            return null;
        }

        static void GuardPair(Feature f,string a,string b)
        {
            if(f==null) throw new Exception("Mate guard: feature missing");
            Mate2 m=f.GetSpecificFeature2() as Mate2;
            if(m==null) throw new Exception(f.Name+" not Mate2");
            string s="";
            for(int i=0;i<m.GetMateEntityCount();i++)
            {
                MateEntity2 me=m.MateEntity(i);
                Component2 c=me==null?null:me.ReferenceComponent;
                if(c!=null) s+="|"+(c.Name2??"");
            }
            if(s.IndexOf(a,StringComparison.OrdinalIgnoreCase)<0 || s.IndexOf(b,StringComparison.OrdinalIgnoreCase)<0)
                throw new Exception(f.Name+" pair guard failed: "+s);
            Log(f.Name+" pair guard PASS "+s);
        }

        static bool Suppress(Feature f)
        {
            return f.SetSuppression2((int)swFeatureSuppressionAction_e.swSuppressFeature,
                (int)swInConfigurationOpts_e.swThisConfiguration,null);
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

        static int ActiveMateErrors(ModelDoc2 doc)
        {
            int n=0; Feature g=MateGroup(doc); if(g==null)return 0;
            Feature f=g.GetFirstSubFeature() as Feature;
            while(f!=null)
            {
                if(!IsSuppressed(f))
                {
                    bool warn=false; int code=f.GetErrorCode2(out warn);
                    if(code!=0 && !warn){n++; Log("ACTIVE MATE ERROR "+f.Name+" code="+code);}
                }
                f=f.GetNextSubFeature() as Feature;
            }
            Log("Active mate errors="+n); return n;
        }

        static Component2 FindComp(AssemblyDoc asm,string path)
        {
            foreach(object o in ToObjects(asm.GetComponents(false)))
            {
                Component2 c=o as Component2; if(c==null)continue;
                if(String.Equals(Norm(c.GetPathName()),Norm(path),StringComparison.OrdinalIgnoreCase))return c;
            }
            return null;
        }

        static void Replace(AssemblyDoc asm,ModelDoc2 doc,Component2 c,string path,string tag)
        {
            doc.ClearSelection2(true);
            if(!c.Select4(false,null,false)) throw new Exception(tag+" component selection failed");
            bool ok=asm.ReplaceComponents2(path,"",false,
                (int)swReplaceComponentsConfiguration_e.swReplaceComponentsConfiguration_MatchName,true);
            if(!ok) throw new Exception(tag+" ReplaceComponents2 false");
            Log(tag+" replaced");
        }

        static object[] Bodies(ModelDoc2 doc)
        {
            PartDoc p=doc as PartDoc; if(p==null)throw new Exception("Not PartDoc "+doc.GetTitle());
            return ToObjects(p.GetBodies2((int)swBodyType_e.swSolidBody,false));
        }

        static IEnumerable<Face2> Faces(ModelDoc2 doc)
        {
            foreach(object bo in Bodies(doc))
            {
                Body2 b=bo as Body2;
                foreach(object fo in ToObjects(b.GetFaces())){Face2 f=fo as Face2;if(f!=null)yield return f;}
            }
        }

        static double[] BoxMm(ModelDoc2 doc)
        {
            object[] bs=Bodies(doc); if(bs.Length!=1)throw new Exception("Expected 1 body "+doc.GetTitle());
            double[] x=ToD((bs[0] as Body2).GetBodyBox());
            for(int i=0;i<x.Length;i++)x[i]*=1000.0;
            return x;
        }

        static PlaneHit FindPlaneX(ModelDoc2 doc,double target,double tolMm)
        {
            PlaneHit best=null; double tol=tolMm*MM;
            foreach(Face2 f in Faces(doc))
            {
                Surface s=f.GetSurface() as Surface; if(s==null || !s.IsPlane())continue;
                double[] p=ToD(s.PlaneParams); if(p.Length<6)continue;
                if(Math.Abs(Math.Abs(p[0])-1)>1e-5 || Math.Abs(p[1])>1e-5 || Math.Abs(p[2])>1e-5)continue;
                if(Math.Abs(p[3]-target)<=tol)
                {
                    double area=f.GetArea();
                    if(best==null || area>best.area)best=new PlaneHit{face=f,x=p[3],area=area};
                }
            }
            if(best==null)throw new Exception("Axial face missing at X="+(target/MM).ToString("0.######",CultureInfo.InvariantCulture));
            return best;
        }

        static Face2 FindCyl(ModelDoc2 doc,double dmm,double tol,double[] yz)
        {
            Face2 best=null; double score=1e99;
            foreach(Face2 f in Faces(doc))
            {
                Surface s=f.GetSurface() as Surface; if(s==null || !s.IsCylinder())continue;
                double[] p=ToD(s.CylinderParams); if(p.Length<7)continue;
                if(Math.Abs(Math.Abs(p[3])-1)>1e-5 || Math.Abs(p[4])>1e-5 || Math.Abs(p[5])>1e-5)continue;
                double d=2*Math.Abs(p[6])/MM; if(Math.Abs(d-dmm)>tol)continue;
                double q=0;
                if(yz!=null){double dy=p[1]/MM-yz[0],dz=p[2]/MM-yz[1];q=Math.Sqrt(dy*dy+dz*dz);}
                if(best==null || q<score){best=f;score=q;}
            }
            Log(doc.GetTitle()+" find cylinder D"+dmm+" score="+score.ToString("0.######",CultureInfo.InvariantCulture));
            return best;
        }

        static void CopyFresh(string src,string dst)
        {
            Need(src); Close(dst);
            if(File.Exists(dst))
            {
                string hd=Path.Combine(Path.GetDirectoryName(dst),"history"); Directory.CreateDirectory(hd);
                string h=Path.Combine(hd,Path.GetFileNameWithoutExtension(dst)+"_"+DateTime.Now.ToString("yyyyMMdd_HHmmss")+Path.GetExtension(dst));
                File.Copy(dst,h,true); File.Delete(dst);
            }
            File.Copy(src,dst,true);
        }

        static void Save(ModelDoc2 doc,string label)
        {
            int e=0,w=0;
            bool ok=doc.Save3((int)swSaveAsOptions_e.swSaveAsOptions_Silent,ref e,ref w);
            if(!ok || e!=0)throw new Exception(label+" Save3 errors="+e+" warnings="+w);
            Log(label+" saved");
        }

        static void SetProp(ModelDoc2 doc,string k,string v)
        {
            CustomPropertyManager c=doc.Extension.get_CustomPropertyManager("");
            try{c.Delete2(k);}catch{}
            int r=c.Add(k,"Text",v); if(r==0)try{c.Set2(k,v);}catch{}
        }

        static void Need(string p){if(!File.Exists(p))throw new Exception("Missing "+p);}
        static void Close(string p){try{ModelDoc2 d=sw.GetOpenDocumentByName(p) as ModelDoc2;if(d!=null)sw.CloseDoc(d.GetTitle());}catch{}}
        static string Norm(string p){try{return Path.GetFullPath(p).TrimEnd('\\').ToLowerInvariant();}catch{return (p??"").ToLowerInvariant();}}

        static object[] ToObjects(object x)
        {
            if(x==null)return new object[0]; object[] o=x as object[]; if(o!=null)return o;
            Array a=x as Array; if(a==null)return new object[]{x}; object[] r=new object[a.Length];
            for(int i=0;i<a.Length;i++)r[i]=a.GetValue(i); return r;
        }

        static double[] ToD(object x)
        {
            if(x==null)return new double[0]; double[] d=x as double[]; if(d!=null)return d;
            Array a=x as Array; if(a==null)return new double[0]; double[] r=new double[a.Length];
            for(int i=0;i<a.Length;i++)r[i]=Convert.ToDouble(a.GetValue(i),CultureInfo.InvariantCulture); return r;
        }

        static void Log(string s)
        {
            string l="["+DateTime.Now.ToString("s")+"] "+s; Console.WriteLine(l);
            File.AppendAllText(logPath,l+global::System.Environment.NewLine);
        }

        static void SaveReport()
        {
            File.WriteAllText(jsonPath,new JavaScriptSerializer().Serialize(R));
        }
    }
}
