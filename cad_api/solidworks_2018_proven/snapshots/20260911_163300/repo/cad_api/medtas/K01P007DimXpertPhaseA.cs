using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Web.Script.Serialization;
using SolidWorks.Interop.sldworks;
using SolidWorks.Interop.swconst;
using SolidWorks.Interop.swdimxpert;

public class K01P007DimXpertPhaseA
{
    static string PartPath, OutPath, LogPath;
    static string Stage="BOOT";
    static SldWorks sw=null;
    static bool createdSw=false;
    static ModelDoc2 model=null;
    static readonly List<string> Warnings=new List<string>();

    static void Log(string s){
        string line=DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss.fff")+" | "+Stage+" | "+s;
        try{Console.WriteLine(line);}catch{}
        if(!String.IsNullOrEmpty(LogPath)){
            try{
                Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(LogPath)));
                File.AppendAllText(LogPath,line+System.Environment.NewLine,new UTF8Encoding(false));
            }catch{}
        }
    }
    static string Arg(string[] a,string n){for(int i=0;i<a.Length-1;i++)if(a[i].Equals(n,StringComparison.OrdinalIgnoreCase))return a[i+1];return null;}
    static IEnumerable Items(object o){if(o==null)yield break;Array a=o as Array;if(a!=null){foreach(object x in a)yield return x;yield break;}IEnumerable e=o as IEnumerable;if(e!=null)foreach(object x in e)yield return x;}
    static void WriteJson(string p,object o){Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(p)));var js=new JavaScriptSerializer();js.MaxJsonLength=Int32.MaxValue;File.WriteAllText(p,js.Serialize(o),new UTF8Encoding(false));}
    static void Need(bool ok,string msg){if(!ok)throw new Exception(msg);}
    static bool Near(double a,double b,double t){return Math.Abs(a-b)<=t;}
    static double Mm(double m){return Math.Round(m*1000.0,6);}
    static string Sha256(string p){using(var h=SHA256.Create())using(var f=File.OpenRead(p)){byte[] b=h.ComputeHash(f);return BitConverter.ToString(b).Replace("-","").ToLowerInvariant();}}
    static double[] Dbl(object o){var x=new List<double>();foreach(object q in Items(o)){try{x.Add(Convert.ToDouble(q,CultureInfo.InvariantCulture));}catch{}}return x.ToArray();}

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

    static ModelDoc2 OpenPart(SldWorks s,string p,bool readOnly,out int er,out int wr){
        er=0;wr=0;
        int opts=(int)swOpenDocOptions_e.swOpenDocOptions_Silent;
        if(readOnly)opts|=(int)swOpenDocOptions_e.swOpenDocOptions_ReadOnly;
        return s.OpenDoc6(p,(int)swDocumentTypes_e.swDocPART,opts,"",ref er,ref wr);
    }

    static void ActivateCandidate(){
        Need(sw!=null&&model!=null,"ActivateCandidate requires open model");
        int er=0;
        ModelDoc2 active=sw.IActivateDoc3(model.GetTitle(),true,ref er);
        Need(active!=null&&er==0,"IActivateDoc3 failed error="+er);
        model=active;
        ModelDoc2 check=sw.IActiveDoc2;
        Need(check!=null,"IActiveDoc2 is null after activation");
        string activePath="";
        try{activePath=check.GetPathName();}catch{}
        Need(String.Equals(Path.GetFullPath(activePath),Path.GetFullPath(PartPath),StringComparison.OrdinalIgnoreCase),
             "Active document mismatch after activation: "+activePath);
        Log("active_document="+activePath);
    }

    class FRec{
        public Face2 face;
        public string surface;
        public double area;
        public double[] cyl;
        public double[] plane;
    }

    static List<FRec> Faces(ModelDoc2 m){
        var rows=new List<FRec>();
        PartDoc p=m as PartDoc;if(p==null)throw new Exception("Not PartDoc");
        foreach(object bo in Items(p.GetBodies2((int)swBodyType_e.swSolidBody,true))){
            Body2 b=bo as Body2;if(b==null)continue;
            foreach(object fo in Items(b.GetFaces())){
                Face2 f=fo as Face2;if(f==null)continue;
                var r=new FRec();r.face=f;
                try{r.area=Convert.ToDouble(f.GetArea(),CultureInfo.InvariantCulture);}catch{r.area=0;}
                try{
                    Surface su=f.IGetSurface();
                    if(su.IsPlane()){r.surface="plane";r.plane=Dbl(su.PlaneParams);}
                    else if(su.IsCylinder()){r.surface="cylinder";r.cyl=Dbl(su.CylinderParams);}
                    else if(su.IsCone())r.surface="cone";
                    else if(su.IsSphere())r.surface="sphere";
                    else r.surface="other";
                }catch{r.surface="unknown";}
                rows.Add(r);
            }
        }
        return rows;
    }

    static double Radius(FRec f){return f.cyl!=null&&f.cyl.Length>=7?Math.Abs(f.cyl[6]):Double.NaN;}
    static double AxisX(FRec f){return f.cyl!=null&&f.cyl.Length>=6?Math.Abs(f.cyl[3]):Double.NaN;}
    static double CenterRadiusYZ(FRec f){return f.cyl!=null&&f.cyl.Length>=3?Math.Sqrt(f.cyl[1]*f.cyl[1]+f.cyl[2]*f.cyl[2]):Double.NaN;}
    static double PlaneX(FRec f){return f.plane!=null&&f.plane.Length>=6&&Math.Abs(f.plane[0])>0.999999?f.plane[3]:Double.NaN;}
    static List<FRec> Select(List<FRec> all,Func<FRec,bool> pred){var x=new List<FRec>();foreach(var f in all)if(pred(f))x.Add(f);return x;}

    static string GeometryFingerprint(ModelDoc2 m){
        var sig=new List<string>();
        foreach(var f in Faces(m)){
            string s=f.surface+"|A="+f.area.ToString("G17",CultureInfo.InvariantCulture);
            if(f.surface=="plane"&&f.plane!=null){
                s+="|P="+String.Join(",",Array.ConvertAll(f.plane,x=>x.ToString("G17",CultureInfo.InvariantCulture)));
            }else if(f.surface=="cylinder"&&f.cyl!=null){
                s+="|C="+String.Join(",",Array.ConvertAll(f.cyl,x=>x.ToString("G17",CultureInfo.InvariantCulture)));
            }
            sig.Add(s);
        }
        sig.Sort(StringComparer.Ordinal);
        byte[] raw=Encoding.UTF8.GetBytes(String.Join("\n",sig.ToArray()));
        using(var h=SHA256.Create()){return BitConverter.ToString(h.ComputeHash(raw)).Replace("-","").ToLowerInvariant();}
    }

    static DimXpertPart Dx(ModelDoc2 m,out string cfg){
        cfg=m.ConfigurationManager.ActiveConfiguration.Name;
        DimXpertManager mgr=m.Extension.get_DimXpertManager(cfg,true);
        if(mgr==null)throw new Exception("DimXpertManager is null");
        DimXpertPart dx=mgr.DimXpertPart as DimXpertPart;
        if(dx==null)throw new Exception("DimXpertPart is null");
        return dx;
    }

    static List<Dictionary<string,object>> Annotations(DimXpertPart dx){
        var rows=new List<Dictionary<string,object>>();
        foreach(object ao in Items(dx.GetAnnotations())){
            DimXpertAnnotation a=ao as DimXpertAnnotation;if(a==null)continue;
            var d=new Dictionary<string,object>();
            try{d["name"]=a.Name;}catch{d["name"]="";}
            try{d["annotation_type"]=a.Type.ToString();}catch{d["annotation_type"]="";}
            DimXpertDimensionTolerance dt=a as DimXpertDimensionTolerance;
            if(dt!=null){
                try{d["nominal_SI"]=dt.GetNominalValue();}catch{}
                // Phase A deliberately avoids tolerance-limit introspection.
            // Acceptance is based on native annotation persistence, nominal semantic readback,
            // persistent-reference reopen resolution, and invariant solid geometry.
            }
            rows.Add(d);
        }
        return rows;
    }

    static int NominalCount(List<Dictionary<string,object>> rows,double nominal,double tol){
        int n=0;
        foreach(var d in rows){
            object o=null;if(!d.TryGetValue("nominal_SI",out o)||o==null)continue;
            try{if(Math.Abs(Convert.ToDouble(o,CultureInfo.InvariantCulture)-nominal)<=tol)n++;}catch{}
        }
        return n;
    }

    static DimXpertAnnotation UniqueNominalAnnotation(DimXpertPart dx,double nominal,double tol){
        DimXpertAnnotation hit=null;int n=0;
        foreach(object ao in Items(dx.GetAnnotations())){
            DimXpertAnnotation a=ao as DimXpertAnnotation;if(a==null)continue;
            DimXpertDimensionTolerance dt=a as DimXpertDimensionTolerance;if(dt==null)continue;
            try{
                if(Math.Abs(dt.GetNominalValue()-nominal)<=tol){hit=a;n++;}
            }catch{}
        }
        if(n==1)return hit;
        return null;
    }

    static byte[] Persist(object obj){
        object raw=model.Extension.GetPersistReference3(obj);
        if(raw==null)return null;
        byte[] b=raw as byte[];if(b!=null)return b;
        Array a=raw as Array;if(a==null)return null;
        byte[] z=new byte[a.Length];for(int i=0;i<a.Length;i++)z[i]=Convert.ToByte(a.GetValue(i));return z;
    }

    static bool SelectFace(Face2 f,bool append,string tag){
        Need(f!=null,tag+" face is null");
        Entity ent=f as Entity;
        Need(ent!=null,tag+" Face2 -> Entity cast failed");
        bool ok=ent.Select4(append,null);
        Need(ok,tag+" IEntity.Select4 failed");

        SelectionMgr sm=model.SelectionManager as SelectionMgr;
        Need(sm!=null,tag+" SelectionMgr is null");
        int count=sm.GetSelectedObjectCount2(-1);
        int type=count>0?sm.GetSelectedObjectType3(count,-1):-1;
        Log(tag+" select=True selection_count="+count+" selection_type="+type);
        if(!append){
            Need(count==1,tag+" expected exactly one selected entity; got "+count);
            Need(type==(int)swSelectType_e.swSelFACES,tag+" expected selected type swSelFACES; got "+type);
        }
        return ok;
    }

    static bool InsertSize(DimXpertPart dx,Face2 f,double[] pos,string tag){
        // SOLIDWORKS API documented sequence:
        // GetDimOption -> set TextPosition/FeatureSelectorOptions -> select face -> InsertSizeDimension.
        DimXpertDimensionOption opt=dx.GetDimOption();
        Need(opt!=null,tag+" GetDimOption returned null");
        object posvar=pos;
        opt.TextPosition=posvar;

        // Force a cylinder feature. This mirrors the successful historical Step13 result
        // (Cylinder1/Cylinder2) instead of relying on the context-sensitive default selector.
        int[] selector=new int[]{(int)swDimXpertFeatureSelectorOption_e.swDimXpertFeatureSelectorOption_Cylinder};
        object selectorVar=selector;
        opt.FeatureSelectorOptions=selectorVar;

        model.ClearSelection2(true);
        SelectFace(f,false,tag);
        bool ret=dx.InsertSizeDimension(opt);

        SelectionMgr sm=model.SelectionManager as SelectionMgr;
        int count=sm==null?-1:sm.GetSelectedObjectCount2(-1);
        int type=(sm==null||count<1)?-1:sm.GetSelectedObjectType3(1,-1);
        Log(tag+" InsertSizeDimension return="+ret+" post_call_selection_count="+count+" selection_type="+type);
        model.ClearSelection2(true);
        return ret;
    }

    static bool InsertLocation(DimXpertPart dx,Face2 origin,Face2 locating,double[] pos,string tag){
        DimXpertDimensionOption opt=dx.GetDimOption();
        Need(opt!=null,tag+" GetDimOption returned null");
        object posvar=pos;
        opt.TextPosition=posvar;

        model.ClearSelection2(true);
        SelectFace(origin,false,tag+"_ORIGIN");
        SelectFace(locating,true,tag+"_LOCATING");

        SelectionMgr sm=model.SelectionManager as SelectionMgr;
        Need(sm!=null,tag+" SelectionMgr is null");
        int count=sm.GetSelectedObjectCount2(-1);
        Need(count==2,tag+" expected two selected faces; got "+count);
        Need(sm.GetSelectedObjectType3(1,-1)==(int)swSelectType_e.swSelFACES,tag+" origin selection is not a face");
        Need(sm.GetSelectedObjectType3(2,-1)==(int)swSelectType_e.swSelFACES,tag+" locating selection is not a face");

        bool ret=dx.InsertLocationDimension(opt);
        model.ClearSelection2(true);
        Log(tag+" InsertLocationDimension return="+ret);
        return ret;
    }

    static void Save(ModelDoc2 m){
        int e=0,w=0;bool ok=m.Save3((int)swSaveAsOptions_e.swSaveAsOptions_Silent,ref e,ref w);
        if(!ok||e!=0)throw new Exception("Save3 failed errors="+e+" warnings="+w);
    }

    static Dictionary<string,object> ResolvePersist(byte[] id){
        var d=new Dictionary<string,object>();
        if(id==null){d["captured"]=false;d["resolved"]=false;d["state"]=-999;return d;}
        int state=-999;object o=model.Extension.GetObjectByPersistReference3(id,out state);
        d["captured"]=true;d["state"]=state;d["resolved"]=o!=null;d["runtime_type"]=o==null?"":o.GetType().FullName;
        return d;
    }

    static void Run(string[] args){
        PartPath=Arg(args,"--part");OutPath=Arg(args,"--out");LogPath=Arg(args,"--log");
        if(String.IsNullOrEmpty(PartPath)||String.IsNullOrEmpty(OutPath))throw new Exception("Usage: --part <candidate.SLDPRT> --out <json> [--log <log>]");
        Need(File.Exists(PartPath),"Candidate missing: "+PartPath);
        string shaBefore=Sha256(PartPath);

        Stage="START_SW";sw=GetSw();Log("SolidWorks revision="+sw.RevisionNumber());
        Stage="OPEN";int er=0,wr=0;model=OpenPart(sw,PartPath,false,out er,out wr);Need(model!=null,"OpenDoc6 failed er="+er+" wr="+wr);
        Log("Opened writable candidate errors="+er+" warnings="+wr);
        Stage="ACTIVATE";ActivateCandidate();

        string geomBefore=GeometryFingerprint(model);
        string cfg="";DimXpertPart dx=Dx(model,out cfg);
        var before=Annotations(dx);
        int beforeCount=before.Count;

        var faces=Faces(model);
        var xplanes=Select(faces,f=>f.surface=="plane"&&!Double.IsNaN(PlaneX(f)));
        Need(xplanes.Count>=2,"Cannot establish axial planes");
        double xmin=Double.MaxValue,xmax=Double.MinValue;
        foreach(var f in xplanes){double x=PlaneX(f);xmin=Math.Min(xmin,x);xmax=Math.Max(xmax,x);}
        Need(Near(xmax-xmin,0.035,0.00001),"P007 OAL analytic envelope is not 35 mm");

        var front=Select(faces,f=>f.surface=="plane"&&!Double.IsNaN(PlaneX(f))&&Math.Abs(PlaneX(f)-xmin)<=0.0000005);
        var back=Select(faces,f=>f.surface=="plane"&&!Double.IsNaN(PlaneX(f))&&Math.Abs(PlaneX(f)-(xmin+0.003))<=0.000001);
        var rear=Select(faces,f=>f.surface=="plane"&&!Double.IsNaN(PlaneX(f))&&Math.Abs(PlaneX(f)-xmax)<=0.000001);
        var c02=Select(faces,f=>f.surface=="cylinder"&&AxisX(f)>0.999999&&Near(Radius(f),0.00705,0.000002)&&Near(CenterRadiusYZ(f),0.0,0.00001));
        var c05=Select(faces,f=>f.surface=="cylinder"&&AxisX(f)>0.999999&&Near(Radius(f),0.0165,0.000002)&&Near(CenterRadiusYZ(f),0.0,0.00001));
        var c04=Select(faces,f=>f.surface=="cylinder"&&AxisX(f)>0.999999&&Near(Radius(f),0.00145,0.000002)&&Near(CenterRadiusYZ(f),0.01325,0.00001));
        Need(front.Count==2,"Datum-A front face set count !=2");
        Need(back.Count>=1,"Flange back plane missing");
        Need(rear.Count==1,"Rear end plane count !=1");
        Need(c02.Count==1,"C02 cylinder count !=1");
        Need(c05.Count==1,"C05 cylinder count !=1");
        Need(c04.Count==3,"C04 hole cylinder count !=3");

        var api=new Dictionary<string,object>();
        Stage="AUTHOR_REQUIRED";
        if(NominalCount(before,0.01410,0.000002)==0)api["C02_insert_return"]=InsertSize(dx,c02[0].face,new double[]{xmin+0.001,0.018,0.0},"C02");
        else api["C02_reused_existing"]=true;
        if(NominalCount(before,0.03300,0.000003)==0)api["C05_OD_insert_return"]=InsertSize(dx,c05[0].face,new double[]{xmin+0.001,-0.022,0.0},"C05_OD");
        else api["C05_OD_reused_existing"]=true;

        Stage="AUTHOR_OPTIONAL";
        try{
            var now=Annotations(dx);
            if(NominalCount(now,0.00290,0.000002)==0)
                api["C04_hole_diameter_insert_return"]=InsertSize(dx,c04[0].face,new double[]{xmin+0.001,0.021,0.021},"C04_HOLE_D");
            else api["C04_hole_diameter_reused_existing"]=true;
        }catch(Exception ex){Warnings.Add("C04 optional authoring: "+ex.Message);api["C04_optional_error"]=ex.Message;}

        try{
            var now=Annotations(dx);
            if(NominalCount(now,0.03500,0.000005)==0)
                api["C06_OAL_insert_return"]=InsertLocation(dx,front[0].face,rear[0].face,new double[]{xmin+0.0175,-0.026,0.0},"C06_OAL");
            else api["C06_OAL_reused_existing"]=true;
        }catch(Exception ex){Warnings.Add("C06 optional authoring: "+ex.Message);api["C06_optional_error"]=ex.Message;}

        try{
            var now=Annotations(dx);
            if(NominalCount(now,0.00300,0.000003)==0)
                api["C05_THK_insert_return"]=InsertLocation(dx,front[0].face,back[0].face,new double[]{xmin+0.001,-0.017,0.0},"C05_THK");
            else api["C05_THK_reused_existing"]=true;
        }catch(Exception ex){Warnings.Add("C05 thickness optional authoring: "+ex.Message);api["C05_THK_optional_error"]=ex.Message;}

        // API boolean is diagnostic only. Semantic readback is the acceptance authority.
        var authored=Annotations(dx);
        Need(NominalCount(authored,0.01410,0.000002)==1,"C02 nominal Ø14.10 not uniquely present after authoring");
        Need(NominalCount(authored,0.03300,0.000003)==1,"C05 nominal Ø33.00 not uniquely present after authoring");

        var persist=new Dictionary<string,byte[]>();
        DimXpertAnnotation a02=UniqueNominalAnnotation(dx,0.01410,0.000002);
        DimXpertAnnotation a05=UniqueNominalAnnotation(dx,0.03300,0.000003);
        Need(a02!=null,"C02 unique annotation not found");Need(a05!=null,"C05 unique annotation not found");
        persist["C02"]=Persist(a02);persist["C05"]=Persist(a05);
        DimXpertAnnotation a04=UniqueNominalAnnotation(dx,0.00290,0.000002);if(a04!=null)persist["C04_D"]=Persist(a04);
        DimXpertAnnotation a06=UniqueNominalAnnotation(dx,0.03500,0.000005);if(a06!=null)persist["C06"]=Persist(a06);
        DimXpertAnnotation a05t=UniqueNominalAnnotation(dx,0.00300,0.000003);if(a05t!=null)persist["C05_THK"]=Persist(a05t);

        Stage="SAVE";Save(model);string title=model.GetTitle();sw.CloseDoc(title);model=null;
        string shaAfterSave=Sha256(PartPath);

        Stage="REOPEN";int er2=0,wr2=0;model=OpenPart(sw,PartPath,true,out er2,out wr2);Need(model!=null,"Reopen failed er="+er2+" wr="+wr2);
        Stage="REOPEN_ACTIVATE";ActivateCandidate();
        string geomAfter=GeometryFingerprint(model);
        Need(geomBefore==geomAfter,"Geometry fingerprint changed during PMI-only authoring");
        string cfg2="";DimXpertPart dx2=Dx(model,out cfg2);var after=Annotations(dx2);

        int c02n=NominalCount(after,0.01410,0.000002);
        int c05n=NominalCount(after,0.03300,0.000003);
        int c04n=NominalCount(after,0.00290,0.000002);
        int c06n=NominalCount(after,0.03500,0.000005);
        int c05tn=NominalCount(after,0.00300,0.000003);
        Need(c02n==1,"C02 reopen nominal count !=1");
        Need(c05n==1,"C05 OD reopen nominal count !=1");

        var resolution=new Dictionary<string,object>();
        foreach(var kv in persist){
            var rr=ResolvePersist(kv.Value);
            resolution[kv.Key]=rr;
            Need(Convert.ToBoolean(rr["resolved"])&&Convert.ToInt32(rr["state"])==0,"Persistent reference failed after reopen for "+kv.Key);
        }

        var root=new Dictionary<string,object>();
        root["schema"]="k01.p007.dimxpert.phase_a.raw.v1";
        root["status"]=(c04n>=1&&c06n>=1)?"PASS_PHASE_A_EXTENDED":"PASS_PHASE_A_REQUIRED_C02_C05";
        root["candidate"]=PartPath;root["configuration"]=cfg2;
        root["sha256_before"]=shaBefore;root["sha256_after_save"]=shaAfterSave;
        root["geometry_fingerprint_before"]=geomBefore;root["geometry_fingerprint_after_reopen"]=geomAfter;root["geometry_invariant"]=geomBefore==geomAfter;
        root["annotation_count_before"]=beforeCount;root["annotation_count_after"]=after.Count;
        root["nominal_counts"]=new Dictionary<string,object>{{"C02_14p10",c02n},{"C05_OD_33",c05n},{"C04_hole_2p90",c04n},{"C06_OAL_35",c06n},{"C05_thickness_3",c05tn}};
        root["api_returns"]=api;root["persistent_resolution_after_reopen"]=resolution;root["annotations_after_reopen"]=after;root["warnings"]=Warnings;root["selection_method"]="Face2 cast to IEntity -> IEntity.Select4";root["phase_a_interop_policy"]="minimal SW2018 surface: GetAnnotations/GetNominalValue/GetDimOption/InsertSizeDimension/InsertLocationDimension + persistent-reference APIs";root["step13_regression_target"]="active candidate + one selected face(type=swSelFACES) + forced Cylinder selector + semantic readback; historical Step13 created Cylinder1/Cylinder2 despite api_return=false";
        root["release_boundary"]=new string[]{
          "C01 composite Datum-A native representation not authored in Phase A",
          "C02 H7 fit code not released by this Phase A write",
          "C03 perpendicularity remains candidate/open until authority is closed",
          "C04 position/PCD basic semantics remain candidate/open even if hole diameter PMI exists",
          "C05 released tolerance semantics remain separately controlled",
          "C07/C08/C10/C11/C12 and blind-end release definition remain OPEN"
        };
        Stage="WRITE_JSON";WriteJson(OutPath,root);Log("PASS "+root["status"]+" annotations="+after.Count);
    }

    [STAThread]
    public static int Main(string[] args){
        try{Console.OutputEncoding=Encoding.UTF8;Run(args);return 0;}
        catch(Exception ex){
            try{Log("ERROR "+ex);}catch{}
            try{WriteJson(OutPath,new Dictionary<string,object>{{"schema","k01.p007.dimxpert.phase_a.error.v1"},{"status","ERROR"},{"stage",Stage},{"error",ex.Message},{"stack_trace",ex.ToString()}});}catch{}
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
