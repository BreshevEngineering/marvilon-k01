using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Web.Script.Serialization;
using SolidWorks.Interop.sldworks;
using SolidWorks.Interop.swconst;

public class K01P007PersistentRefRebind
{
    static string PartPath, OutPath, LogPath;
    static string Stage="BOOT";
    static readonly List<string> Notes=new List<string>();
    static SldWorks sw=null;
    static bool createdSw=false;
    static ModelDoc2 model=null;

    static void Log(string s){
        string line=DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss.fff")+" | "+Stage+" | "+s;
        try{Console.WriteLine(line);}catch{}
        if(!String.IsNullOrEmpty(LogPath)){
            try{Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(LogPath)));File.AppendAllText(LogPath,line+System.Environment.NewLine,new UTF8Encoding(false));}catch{}
        }
    }
    static string Arg(string[] a,string n){for(int i=0;i<a.Length-1;i++)if(a[i].Equals(n,StringComparison.OrdinalIgnoreCase))return a[i+1];return null;}
    static IEnumerable Items(object o){if(o==null)yield break;Array a=o as Array;if(a!=null){foreach(object x in a)yield return x;yield break;}IEnumerable e=o as IEnumerable;if(e!=null)foreach(object x in e)yield return x;}
    static void WriteJson(string p,object o){Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(p)));var js=new JavaScriptSerializer();js.MaxJsonLength=Int32.MaxValue;File.WriteAllText(p,js.Serialize(o),new UTF8Encoding(false));}
    static double[] Dbl(object o){var x=new List<double>();foreach(object q in Items(o)){try{x.Add(Convert.ToDouble(q));}catch{}}return x.ToArray();}
    static bool Near(double a,double b,double tol){return Math.Abs(a-b)<=tol;}
    static double Mm(double m){return Math.Round(m*1000.0,6);}
    static string Sha256(string p){using(var h=SHA256.Create())using(var f=File.OpenRead(p)){var b=h.ComputeHash(f);return BitConverter.ToString(b).Replace("-","").ToLowerInvariant();}}

    static SldWorks GetSw(){
        try{
            object o=Marshal.GetActiveObject("SldWorks.Application");
            SldWorks a=o as SldWorks;
            if(a!=null){createdSw=false;return a;}
        }catch{}
        Type t=Type.GetTypeFromProgID("SldWorks.Application");
        if(t==null)throw new Exception("SldWorks.Application ProgID not found");
        object n=Activator.CreateInstance(t);
        SldWorks s=n as SldWorks;
        if(s==null)throw new Exception("Cannot create SolidWorks instance");
        createdSw=true;
        try{s.Visible=false;}catch{}
        return s;
    }

    static ModelDoc2 OpenPart(SldWorks s,string p,out int er,out int wr){
        er=0;wr=0;
        ModelDoc2 m=null;
        try{m=s.IGetOpenDocumentByName2(p);}catch{}
        if(m!=null)return m;
        int opts=(int)swOpenDocOptions_e.swOpenDocOptions_Silent | (int)swOpenDocOptions_e.swOpenDocOptions_ReadOnly;
        return s.OpenDoc6(p,(int)swDocumentTypes_e.swDocPART,opts,"",ref er,ref wr);
    }

    class FRec{
        public Face2 face;
        public string surface;
        public double area;
        public double[] box;
        public double[] normal;
        public double[] cyl;
        public double[] plane;
        public int runtimeIndex;
    }

    static List<FRec> Faces(ModelDoc2 m){
        var outp=new List<FRec>();
        PartDoc part=m as PartDoc;if(part==null)throw new Exception("P007 is not PartDoc");
        object bodies=part.GetBodies2((int)swBodyType_e.swSolidBody,true);
        foreach(object bo in Items(bodies)){
            Body2 body=bo as Body2;if(body==null)continue;
            object raw=body.GetFaces();int idx=0;
            foreach(object fo in Items(raw)){
                idx++;Face2 f=fo as Face2;if(f==null)continue;
                var r=new FRec();r.face=f;r.runtimeIndex=idx;
                try{r.area=Convert.ToDouble(f.GetArea());}catch{r.area=0;}
                try{r.box=Dbl(f.GetBox());}catch{r.box=new double[0];}
                try{r.normal=Dbl(f.Normal);}catch{r.normal=new double[0];}
                try{
                    Surface su=f.IGetSurface();
                    if(su.IsPlane()){r.surface="plane";r.plane=Dbl(su.PlaneParams);}
                    else if(su.IsCylinder()){r.surface="cylinder";r.cyl=Dbl(su.CylinderParams);}
                    else r.surface="other";
                }catch{r.surface="unknown";}
                outp.Add(r);
            }
        }
        return outp;
    }

    static double SpanX(FRec f){return f.box!=null&&f.box.Length>=6?Math.Abs(f.box[3]-f.box[0]):0;}
    static double MinX(FRec f){return f.box!=null&&f.box.Length>=6?Math.Min(f.box[0],f.box[3]):Double.NaN;}
    static double MaxX(FRec f){return f.box!=null&&f.box.Length>=6?Math.Max(f.box[0],f.box[3]):Double.NaN;}
    static double Radius(FRec f){return f.cyl!=null&&f.cyl.Length>=7?Math.Abs(f.cyl[f.cyl.Length-1]):Double.NaN;}
    static double CenterRadiusYZ(FRec f){
        if(f.cyl==null||f.cyl.Length<3)return Double.NaN;
        return Math.Sqrt(f.cyl[1]*f.cyl[1]+f.cyl[2]*f.cyl[2]);
    }
    static double AxisX(FRec f){
        if(f.cyl==null||f.cyl.Length<7)return Double.NaN;
        return Math.Abs(f.cyl[3]);
    }
    static double PlaneX(FRec f){
        // ISurface::PlaneParams = normal.xyz + rootPoint.xyz.
        // Use the analytic plane definition for planes normal to X.
        if(f.plane!=null&&f.plane.Length>=6&&Math.Abs(f.plane[0])>0.999999)
            return f.plane[3];
        return Double.NaN;
    }

    static byte[] Persist(Face2 f){
        object raw=model.Extension.GetPersistReference3(f);
        if(raw==null)throw new Exception("GetPersistReference3 returned null");
        byte[] b=raw as byte[];
        if(b!=null)return b;
        Array a=raw as Array;
        if(a==null)throw new Exception("Persistent reference is not an array: "+raw.GetType().FullName);
        byte[] z=new byte[a.Length];
        for(int i=0;i<a.Length;i++)z[i]=Convert.ToByte(a.GetValue(i));
        return z;
    }

    static Dictionary<string,object> FaceJson(FRec f,byte[] p){
        var d=new Dictionary<string,object>();
        d["runtime_face_index"]=f.runtimeIndex;
        d["surface_type"]=f.surface;
        d["area_m2"]=f.area;
        d["box_m"]=f.box;
        d["normal"]=f.normal;
        d["radius_mm"]=Double.IsNaN(Radius(f))?(object)null:Mm(Radius(f));
        d["span_x_mm_diagnostic_only"]=Mm(SpanX(f));
        d["axis_x_abs"]=Double.IsNaN(AxisX(f))?(object)null:AxisX(f);
        d["center_radius_yz_mm"]=Double.IsNaN(CenterRadiusYZ(f))?(object)null:Mm(CenterRadiusYZ(f));
        d["plane_x_mm"]=Double.IsNaN(PlaneX(f))?(object)null:Mm(PlaneX(f));
        d["persist_ref_b64"]=Convert.ToBase64String(p);
        return d;
    }

    static List<FRec> Select(List<FRec> all,Func<FRec,bool> pred){var x=new List<FRec>();foreach(var f in all)if(pred(f))x.Add(f);return x;}
    static void Need(bool x,string m){if(!x)throw new Exception(m);}

    static List<Dictionary<string,object>> BindFaces(List<FRec> fs,Dictionary<string,byte[]> refs,string prefix){
        var rows=new List<Dictionary<string,object>>();int i=0;
        foreach(var f in fs){i++;byte[] p=Persist(f.face);refs[prefix+"_"+i]=p;rows.Add(FaceJson(f,p));}
        return rows;
    }

    static Dictionary<string,object> Binding(string type,List<Dictionary<string,object>> entities){
        return new Dictionary<string,object>{{"binding_type",type},{"entities",entities},{"binding_status","PASS_CANONICAL_PERSISTENT_REF"}};
    }

    static void Run(string[] args){
        PartPath=Arg(args,"--part");OutPath=Arg(args,"--out");LogPath=Arg(args,"--log");
        if(String.IsNullOrEmpty(PartPath)||String.IsNullOrEmpty(OutPath))throw new Exception("Usage: --part <P007.SLDPRT> --out <json> [--log <log>]");
        if(!File.Exists(PartPath))throw new FileNotFoundException("P007 not found",PartPath);
        string before=Sha256(PartPath);

        Stage="START_SW";sw=GetSw();Log("SolidWorks revision="+sw.RevisionNumber());
        Stage="OPEN_PART";int er=0,wr=0;model=OpenPart(sw,PartPath,out er,out wr);if(model==null)throw new Exception("OpenDoc6 failed er="+er+" wr="+wr);
        if(model.GetType()!=(int)swDocumentTypes_e.swDocPART)throw new Exception("Document is not a part");
        Log("Opened P007 read-only; errors="+er+" warnings="+wr);

        Stage="FACE_CLASSIFICATION";
        var all=Faces(model);
        Need(all.Count>0,"No solid faces");

        // Establish the axial envelope from analytic X-normal plane roots.
        // IFace2::GetBox is deliberately NOT used for engineering selection:
        // SOLIDWORKS documents it as approximate.
        var xPlanes=Select(all,f=>f.surface=="plane"&&!Double.IsNaN(PlaneX(f)));
        Need(xPlanes.Count>=2,"Cannot establish analytic X envelope from planar faces");
        double xmin=Double.MaxValue,xmax=Double.MinValue;
        foreach(var f in xPlanes){
            double x=PlaneX(f);
            xmin=Math.Min(xmin,x);
            xmax=Math.Max(xmax,x);
        }
        Need(xmin<Double.MaxValue&&xmax>Double.MinValue,"Cannot establish X envelope");
        Need(Near(xmax-xmin,0.035,0.00001),"P007 analytic X envelope is not 35.00 mm");

        var datumA=Select(all,f=>f.surface=="plane"&&!Double.IsNaN(PlaneX(f))&&Math.Abs(PlaneX(f)-xmin)<=0.0000005);
        var c02=Select(all,f=>f.surface=="cylinder"&&AxisX(f)>0.999999&&Near(Radius(f),0.00705,0.000002)&&Near(CenterRadiusYZ(f),0.0,0.00001));
        var c04=Select(all,f=>f.surface=="cylinder"&&AxisX(f)>0.999999&&Near(Radius(f),0.00145,0.000002)&&Near(CenterRadiusYZ(f),0.01325,0.00001));
        var flangeOD=Select(all,f=>f.surface=="cylinder"&&AxisX(f)>0.999999&&Near(Radius(f),0.0165,0.000002)&&Near(CenterRadiusYZ(f),0.0,0.00001));
        var flangeBack=Select(all,f=>f.surface=="plane"&&!Double.IsNaN(PlaneX(f))&&Math.Abs(PlaneX(f)-(xmin+0.003))<=0.000001);
        var rearEnd=Select(all,f=>f.surface=="plane"&&!Double.IsNaN(PlaneX(f))&&Math.Abs(PlaneX(f)-xmax)<=0.000001);

        Need(datumA.Count==2,"C01/Datum-A expected 2 coplanar front faces; got "+datumA.Count);
        Need(c02.Count==1,"C02 expected 1 Ø14.10 x 2.00 cylinder; got "+c02.Count);
        Need(c04.Count==3,"C04 expected 3 Ø2.90 x 3.00 cylinders on R13.25; got "+c04.Count);
        Need(flangeOD.Count==1,"C05 flange OD Ø33 x 3 expected one cylinder; got "+flangeOD.Count);
        Need(flangeBack.Count>=1,"C05 flange-back plane at A+3.00 missing");
        Need(rearEnd.Count==1,"C06 rear end plane expected one; got "+rearEnd.Count);

        var refs=new Dictionary<string,byte[]>();
        var bA=BindFaces(datumA,refs,"C01");
        var b02=BindFaces(c02,refs,"C02");
        var b04=BindFaces(c04,refs,"C04");
        var b05od=BindFaces(flangeOD,refs,"C05OD");
        var b05back=BindFaces(flangeBack,refs,"C05BACK");
        var b06rear=BindFaces(rearEnd,refs,"C06REAR");

        var bindings=new Dictionary<string,object>();
        bindings["C01"]=Binding("COMPOSITE_COPLANAR_FACE_SET",bA);
        bindings["C02"]=Binding("CYLINDRICAL_FACE",b02);
        bindings["C04"]=Binding("CYLINDRICAL_PATTERN_FACES",b04);
        var c05ents=new List<Dictionary<string,object>>();c05ents.AddRange(b05od);c05ents.AddRange(bA);c05ents.AddRange(b05back);
        bindings["C05"]=Binding("FLANGE_OD_PLUS_AXIAL_FACE_SET",c05ents);
        var c06ents=new List<Dictionary<string,object>>();c06ents.AddRange(bA);c06ents.AddRange(b06rear);
        bindings["C06"]=Binding("OVERALL_LENGTH_AXIAL_FACE_SET",c06ents);

        Stage="CLOSE_REOPEN";
        string title=model.GetTitle();
        sw.CloseDoc(title);model=null;
        int er2=0,wr2=0;model=OpenPart(sw,PartPath,out er2,out wr2);if(model==null)throw new Exception("Reopen failed er="+er2+" wr="+wr2);
        var resolution=new List<object>();
        foreach(var kv in refs){
            int state=-999;object resolved=model.Extension.GetObjectByPersistReference3(kv.Value,out state);
            var r=new Dictionary<string,object>();r["id"]=kv.Key;r["state"]=state;r["resolved"]=resolved!=null;r["runtime_type"]=resolved==null?"":resolved.GetType().FullName;resolution.Add(r);
            Need(state==0&&resolved!=null,"Persistent-reference reopen resolution failed for "+kv.Key+" state="+state);
        }

        string after=Sha256(PartPath);
        Need(String.Equals(before,after,StringComparison.OrdinalIgnoreCase),"Native P007 binary hash changed during read-only rebind");

        var root=new Dictionary<string,object>();
        root["schema"]="k01.p007.canonical_persistent_rebind.raw.v1";
        root["status"]="PASS";
        root["native_CAD_mutated"]=false;
        root["part"]=PartPath;
        root["sha256_before"]=before;
        root["sha256_after"]=after;
        root["x_envelope_mm"]=new double[]{Mm(xmin),Mm(xmax),Mm(xmax-xmin)};
        root["bindings"]=bindings;
        root["resolution_after_close_reopen"]=resolution;
        root["counts"]=new Dictionary<string,object>{{"C01",datumA.Count},{"C02",c02.Count},{"C04",c04.Count},{"C05_flange_od",flangeOD.Count},{"C05_back_planes",flangeBack.Count},{"C06_rear",rearEnd.Count}};
        root["notes"]=Notes;
        Stage="WRITE_JSON";WriteJson(OutPath,root);Log("PASS canonical persistent-reference rebind");
    }

    [STAThread]
    public static int Main(string[] args){
        try{Console.OutputEncoding=Encoding.UTF8;Run(args);return 0;}
        catch(Exception ex){
            try{Log("ERROR "+ex);}catch{}
            try{WriteJson(OutPath,new Dictionary<string,object>{{"schema","k01.p007.canonical_persistent_rebind.error.v1"},{"status","ERROR"},{"stage",Stage},{"error",ex.Message},{"stack_trace",ex.ToString()}});}catch{}
            Console.Error.WriteLine(ex);return 1;
        }
        finally{
            try{if(model!=null&&sw!=null)sw.CloseDoc(model.GetTitle());}catch{}
            model=null;
            try{if(createdSw&&sw!=null)sw.ExitApp();}catch{}
            try{if(sw!=null&&Marshal.IsComObject(sw))Marshal.FinalReleaseComObject(sw);}catch{}
            sw=null;
            try{GC.Collect();GC.WaitForPendingFinalizers();GC.Collect();GC.WaitForPendingFinalizers();}catch{}
        }
    }
}
