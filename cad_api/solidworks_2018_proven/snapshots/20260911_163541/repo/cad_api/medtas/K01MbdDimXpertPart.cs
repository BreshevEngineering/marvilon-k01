using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Web.Script.Serialization;
using SolidWorks.Interop.sldworks;
using SolidWorks.Interop.swconst;
using SolidWorks.Interop.swdimxpert;

public class K01MbdDimXpertPart
{
    static string OutPath, LogPath, PartPath, ConfigName;
    static string Stage="BOOT";
    static readonly List<string> Warnings=new List<string>();

    static void Log(string s){
        string line=DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss.fff")+" | "+Stage+" | "+s;
        Console.WriteLine(line);
        if(!String.IsNullOrEmpty(LogPath)){
            try{Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(LogPath)));File.AppendAllText(LogPath,line+System.Environment.NewLine,new UTF8Encoding(false));}catch{}
        }
    }
    static string Arg(string[] a,string n){for(int i=0;i<a.Length-1;i++)if(a[i].Equals(n,StringComparison.OrdinalIgnoreCase))return a[i+1];return null;}
    static IEnumerable Items(object o){if(o==null)yield break;Array a=o as Array;if(a!=null){foreach(object x in a)yield return x;yield break;}IEnumerable e=o as IEnumerable;if(e!=null)foreach(object x in e)yield return x;}
    static void WriteJson(string p,object o){Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(p)));var js=new JavaScriptSerializer();js.MaxJsonLength=Int32.MaxValue;File.WriteAllText(p,js.Serialize(o),new UTF8Encoding(false));}

    static SldWorks Attach(){
        object o=Marshal.GetActiveObject("SldWorks.Application");
        SldWorks sw=o as SldWorks;
        if(sw==null)throw new Exception("Active SolidWorks instance cannot be cast to SldWorks");
        return sw;
    }
    static ModelDoc2 OpenPart(SldWorks sw,string path,out int er,out int wr,out bool already){
        er=0;wr=0;already=false;
        ModelDoc2 m=null;
        try{m=sw.IGetOpenDocumentByName2(path);if(m!=null){already=true;return m;}}catch(Exception ex){Warnings.Add("IGetOpenDocumentByName2:"+ex.Message);}
        m=sw.OpenDoc6(path,(int)swDocumentTypes_e.swDocPART,(int)swOpenDocOptions_e.swOpenDocOptions_Silent,"",ref er,ref wr);
        return m;
    }

    static Dictionary<string,object> AnnotationData(DimXpertAnnotation a){
        var d=new Dictionary<string,object>();
        try{d["name"]=a.Name;}catch{d["name"]="";}
        try{d["annotation_type"]=a.Type.ToString();}catch{d["annotation_type"]="";}
        try{d["suppressed"]=a.IsSuppressed();}catch{d["suppressed"]=false;}
        try{d["to_be_inspected"]=a.IsToBeInspected();}catch{d["to_be_inspected"]=false;}
        try{d["statistical"]=a.IsStatistical();}catch{d["statistical"]=false;}
        try{d["free_state"]=a.IsFreeState();}catch{d["free_state"]=false;}
        try{
            Feature mf=a.GetModelFeature() as Feature;
            if(mf!=null){d["model_feature_name"]=mf.Name;d["model_feature_type"]=mf.GetTypeName2();}
        }catch(Exception ex){Warnings.Add("annotation_model_feature:"+ex.Message);}

        DimXpertDimensionTolerance dt=a as DimXpertDimensionTolerance;
        if(dt!=null){
            try{d["dimension_type"]=dt.DimensionType.ToString();}catch{}
            try{d["nominal_SI"]=dt.GetNominalValue();}catch(Exception ex){Warnings.Add("dim_nominal:"+ex.Message);}
            try{double up=0,lo=0;bool ok=dt.GetUpperAndLowerLimit(ref up,ref lo);d["limit_available"]=ok;if(ok){d["upper_limit_SI"]=up;d["lower_limit_SI"]=lo;}}catch(Exception ex){Warnings.Add("dim_limits:"+ex.Message);}
        }
        DimXpertDatum datum=a as DimXpertDatum;
        if(datum!=null){try{d["datum_identifier"]=datum.Identifier;}catch(Exception ex){Warnings.Add("datum_identifier:"+ex.Message);}}
        return d;
    }

    static Dictionary<string,object> FeatureData(DimXpertFeature f){
        var d=new Dictionary<string,object>();
        try{d["name"]=f.Name;}catch{d["name"]="";}
        try{d["feature_type"]=f.Type.ToString();}catch{d["feature_type"]="";}
        try{d["suppressed"]=f.IsSuppressed();}catch{d["suppressed"]=false;}
        try{d["face_count"]=f.GetFaceCount();}catch{d["face_count"]=null;}
        try{Feature mf=f.GetModelFeature() as Feature;if(mf!=null){d["model_feature_name"]=mf.Name;d["model_feature_type"]=mf.GetTypeName2();}}catch(Exception ex){Warnings.Add("dimxpert_feature_model:"+ex.Message);}
        return d;
    }

    static void Run(string[] args){
        PartPath=Arg(args,"--part");ConfigName=Arg(args,"--config")??"";OutPath=Arg(args,"--out");LogPath=Arg(args,"--log");
        if(String.IsNullOrEmpty(PartPath)||String.IsNullOrEmpty(OutPath))throw new Exception("Usage: --part <SLDPRT> [--config <name>] --out <json> [--log <log>]");
        if(!File.Exists(PartPath))throw new FileNotFoundException("Part not found",PartPath);
        Stage="ATTACH";SldWorks sw=Attach();Log("Attached to SolidWorks");
        Stage="OPEN_PART";int er,wr;bool already;ModelDoc2 model=OpenPart(sw,PartPath,out er,out wr,out already);if(model==null)throw new Exception("OpenDoc6 failed errors="+er+" warnings="+wr);
        if(model.GetType()!=(int)swDocumentTypes_e.swDocPART)throw new Exception("Document is not a part");
        if(String.IsNullOrEmpty(ConfigName)){try{ConfigName=model.ConfigurationManager.ActiveConfiguration.Name;}catch{ConfigName="";}}
        Log((already?"Using open":"Opened")+" part; config="+ConfigName);

        Stage="DIMXPERT_MANAGER";
        DimXpertManager mgr=model.Extension.get_DimXpertManager(ConfigName,true);
        if(mgr==null)throw new Exception("DimXpertManager is null");
        DimXpertPart dx=mgr.DimXpertPart as DimXpertPart;
        if(dx==null)throw new Exception("DimXpertPart is null");

        var anns=new List<object>();var feats=new List<object>();
        Stage="ANNOTATIONS";
        try{foreach(object ao in Items(dx.GetAnnotations())){DimXpertAnnotation a=ao as DimXpertAnnotation;if(a!=null)anns.Add(AnnotationData(a));}}catch(Exception ex){Warnings.Add("annotations:"+ex.Message);Log("WARNING "+ex.Message);}
        Stage="FEATURES";
        try{foreach(object fo in Items(dx.GetFeatures())){DimXpertFeature f=fo as DimXpertFeature;if(f!=null)feats.Add(FeatureData(f));}}catch(Exception ex){Warnings.Add("features:"+ex.Message);Log("WARNING "+ex.Message);}

        var root=new Dictionary<string,object>();
        root["schema"]="k01.mbd.dimxpert.part.raw.v1_6";root["status"]="OK";root["document_title"]=model.GetTitle();root["configuration"]=ConfigName;
        root["annotation_count"]=anns.Count;root["feature_count"]=feats.Count;root["annotations"]=anns;root["features"]=feats;root["warnings"]=Warnings;
        Stage="WRITE";WriteJson(OutPath,root);Log("PASS annotations="+anns.Count+" features="+feats.Count);
    }

    [STAThread]
    public static int Main(string[] args){try{Console.OutputEncoding=Encoding.UTF8;Run(args);return 0;}catch(Exception ex){try{Log("ERROR: "+ex);}catch{}try{WriteJson(OutPath,new Dictionary<string,object>{{"schema","k01.mbd.dimxpert.part.error.v1_6"},{"status","ERROR"},{"stage",Stage},{"error",ex.Message},{"stack_trace",ex.ToString()}});}catch{}Console.Error.WriteLine(ex);return 1;}}
}
