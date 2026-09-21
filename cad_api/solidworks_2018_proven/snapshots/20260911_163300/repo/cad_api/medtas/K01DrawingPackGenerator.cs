using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Web.Script.Serialization;
using SolidWorks.Interop.sldworks;
using SolidWorks.Interop.swconst;

public class K01DrawingPackGenerator
{
    static Dictionary<string,object> ReadJson(string p){var js=new JavaScriptSerializer();js.MaxJsonLength=Int32.MaxValue;return js.Deserialize<Dictionary<string,object>>(File.ReadAllText(p,Encoding.UTF8));}
    static void WriteJson(string p,object o){Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(p)));var js=new JavaScriptSerializer();js.MaxJsonLength=Int32.MaxValue;File.WriteAllText(p,js.Serialize(o),new UTF8Encoding(false));}
    static string S(Dictionary<string,object> d,string k){object v;return d!=null&&d.TryGetValue(k,out v)&&v!=null?Convert.ToString(v):"";}
    static IEnumerable Items(object o){if(o==null)yield break;Array a=o as Array;if(a!=null){foreach(object x in a)yield return x;yield break;}IEnumerable e=o as IEnumerable;if(e!=null)foreach(object x in e)yield return x;}
    static bool Save(ModelDoc2 m,string path,out int er,out int wr){er=0;wr=0;Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(path)));return m.Extension.SaveAs(path,(int)swSaveAsVersion_e.swSaveAsCurrentVersion,(int)swSaveAsOptions_e.swSaveAsOptions_Silent,null,out er,out wr);}
    static Dictionary<string,object> BuildOne(SldWorks sw,string template,Dictionary<string,object> item){
        string model=S(item,"model_path"), native=S(item,"slddrw_path"), pdf=S(item,"pdf_path"), drawingNo=S(item,"drawing_no");
        var row=new Dictionary<string,object>();row["drawing_no"]=drawingNo;row["model_path"]=model;row["slddrw_path"]=native;row["pdf_path"]=pdf;
        if(!File.Exists(model))throw new FileNotFoundException("Model not found",model);if(!File.Exists(template))throw new FileNotFoundException("Drawing template not found",template);
        ModelDoc2 dm=sw.NewDocument(template,0,0.0,0.0) as ModelDoc2;if(dm==null)throw new Exception("NewDocument returned null for "+drawingNo);DrawingDoc dd=dm as DrawingDoc;if(dd==null)throw new Exception("New document is not DrawingDoc");
        bool views=dd.Create3rdAngleViews2(model);row["orthographic_views_created"]=views;
        // Isometric view is supplementary; failure is recorded but does not erase orthographic evidence.
        try{View iv=dd.CreateDrawViewFromModelView3(model,"*Isometric",0.245,0.175,0.0) as View;row["isometric_view_created"]=iv!=null;}catch(Exception ex){row["isometric_warning"]=ex.Message;}
        // v1.9: intentionally do NOT place dimensions/PMI automatically.
        // The adapter creates only the controlled drawing skeleton (template + standard views).
        // Release characteristics are placed intentionally by the engineer from native model PMI/MBD.
        // AutoDimension and blanket InsertModelAnnotations are prohibited.
        row["annotation_placement"]="MANUAL_FROM_NATIVE_MBD";
        row["inserted_annotation_count"]=0;
        int er=0,wr=0;bool okNative=Save(dm,native,out er,out wr);row["native_save_ok"]=okNative;row["native_save_errors"]=er;row["native_save_warnings"]=wr;
        int per=0,pwr=0;bool okPdf=Save(dm,pdf,out per,out pwr);row["pdf_save_ok"]=okPdf;row["pdf_save_errors"]=per;row["pdf_save_warnings"]=pwr;
        row["status"]=(views&&okNative&&okPdf)?"PASS":"HOLD";
        try{sw.CloseDoc(dm.GetTitle());}catch{}
        return row;
    }
    [STAThread]
    public static int Main(string[] args){
        string job=null,outp=null;for(int i=0;i<args.Length-1;i++){if(args[i]=="--job")job=args[i+1];if(args[i]=="--out")outp=args[i+1];}
        if(String.IsNullOrEmpty(job)||String.IsNullOrEmpty(outp)){Console.Error.WriteLine("--job and --out required");return 2;}
        var results=new List<object>();var errors=new List<string>();
        try{
            var j=ReadJson(job);string template=S(j,"template_path");object itemsObj=null;j.TryGetValue("items",out itemsObj);SldWorks sw=(SldWorks)Marshal.GetActiveObject("SldWorks.Application");
            foreach(object io in Items(itemsObj)){
                var item=io as Dictionary<string,object>;if(item==null)continue;
                try{var r=BuildOne(sw,template,item);results.Add(r);if(Convert.ToString(r["status"])!="PASS")errors.Add(S(item,"drawing_no")+":generation HOLD");}
                catch(Exception ex){errors.Add(S(item,"drawing_no")+":"+ex.Message);results.Add(new Dictionary<string,object>{{"drawing_no",S(item,"drawing_no")},{"status","HOLD"},{"error",ex.ToString()}});}
            }
            var payload=new Dictionary<string,object>{{"schema","k01.native_drawing_pack.raw.v1_9"},{"status",errors.Count==0?"PASS":"HOLD"},{"items",results},{"errors",errors},{"policy","Create controlled template/views skeleton only. Dimension/PMI placement is manual from native model MBD; AutoDimension and blanket model-item import are not used."}};WriteJson(outp,payload);Console.WriteLine((errors.Count==0?"PASS":"HOLD")+" native drawing pack items="+results.Count);return errors.Count==0?0:1;
        }catch(Exception ex){try{WriteJson(outp,new Dictionary<string,object>{{"schema","k01.native_drawing_pack.raw.v1_9"},{"status","ERROR"},{"error",ex.ToString()}});}catch{}Console.Error.WriteLine(ex);return 3;}
    }
}
