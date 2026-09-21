using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using SolidWorks.Interop.sldworks;
using SolidWorks.Interop.swconst;
using SolidWorks.Interop.swdimxpert;

public class K01D006VerifyImportedPmi
{
    static void Need(bool ok,string msg){if(!ok)throw new Exception(msg);}
    static string Arg(string[] a,string k){for(int i=0;i<a.Length-1;i++)if(a[i]==k)return a[i+1];return null;}
    static IEnumerable Items(object o){
        if(o==null)yield break;
        Array a=o as Array;if(a!=null){foreach(object x in a)yield return x;yield break;}
        IEnumerable e=o as IEnumerable;if(e!=null)foreach(object x in e)yield return x;
    }
    static string Sha(string p){
        using(FileStream fs=new FileStream(p,FileMode.Open,FileAccess.Read,FileShare.ReadWrite|FileShare.Delete))
        using(SHA256 h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(fs)).Replace("-","").ToLowerInvariant();
    }
    static string DxFeatureName(Annotation a){
        try{
            object f=a.GetDimXpertFeature();
            if(f==null)return "";
            DimXpertFeature dx=f as DimXpertFeature;
            return dx==null?"":dx.Name;
        }catch{return "";}
    }
    static string DxName(Annotation a){try{return a.GetDimXpertName();}catch{return "";}}
    static string RefModel(View v){try{return v.GetReferencedModelName();}catch{return "";}}
    static bool Eq(string a,string b){return String.Equals(a??"",b??"",StringComparison.OrdinalIgnoreCase);}

    static int Main(string[] args){
        string drawing=Arg(args,"--drawing"),part=Arg(args,"--part"),report=Arg(args,"--report");
        if(String.IsNullOrWhiteSpace(drawing)||String.IsNullOrWhiteSpace(part)||String.IsNullOrWhiteSpace(report)){
            Console.Error.WriteLine("missing args");return 2;
        }
        SldWorks sw=null;bool created=false;ModelDoc2 doc=null;
        try{
            Need(File.Exists(drawing),"drawing missing");
            Need(File.Exists(part),"part missing");
            string drawingSha=Sha(drawing);
            try{sw=Marshal.GetActiveObject("SldWorks.Application") as SldWorks;}catch{}
            if(sw==null){
                Type t=Type.GetTypeFromProgID("SldWorks.Application");Need(t!=null,"SW ProgID missing");
                sw=Activator.CreateInstance(t) as SldWorks;Need(sw!=null,"SW activate failed");created=true;sw.Visible=false;
            }
            Need(typeof(SldWorks).Assembly.GetName().Version.Major==26,"requires SW2018 interop major 26");
            int er=0,wr=0;
            doc=sw.OpenDoc6(drawing,(int)swDocumentTypes_e.swDocDRAWING,
                (int)swOpenDocOptions_e.swOpenDocOptions_Silent | (int)swOpenDocOptions_e.swOpenDocOptions_ReadOnly,
                "",ref er,ref wr) as ModelDoc2;
            Need(doc!=null,"open drawing failed e="+er+" w="+wr);
            DrawingDoc dr=doc as DrawingDoc;Need(dr!=null,"not drawing");

            string partBase=Path.GetFileName(part);
            int modelRefCount=0,dxCount=0;bool c02=false,c05=false;
            var records=new List<string>();
            View v=dr.GetFirstView() as View;
            while(v!=null){
                string rm=RefModel(v);
                if(!String.IsNullOrWhiteSpace(rm)&&Eq(Path.GetFileName(rm),partBase))modelRefCount++;
                foreach(object ao in Items(v.GetAnnotations())){
                    Annotation a=ao as Annotation;if(a==null)continue;
                    string f=DxFeatureName(a),n=DxName(a);
                    if(String.IsNullOrWhiteSpace(f)&&String.IsNullOrWhiteSpace(n))continue;
                    dxCount++;
                    records.Add("VIEW="+(v.GetName2()??"")+";F="+f+";N="+n);
                    if(Eq(f,"Cylinder1")&&Eq(n,"Diameter2"))c02=true;
                    if(Eq(f,"Cylinder2")&&Eq(n,"Diameter4"))c05=true;
                }
                v=v.GetNextView() as View;
            }
            Need(modelRefCount>0,"drawing has no P007 view referencing proven PMI part: "+partBase);

            string pdf=Path.ChangeExtension(drawing,"PDF"),bmp=Path.ChangeExtension(drawing,"BMP");
            int pe=0,pw=0;
            bool pdfOk=doc.Extension.SaveAs(pdf,(int)swSaveAsVersion_e.swSaveAsCurrentVersion,
                (int)swSaveAsOptions_e.swSaveAsOptions_Silent,null,ref pe,ref pw);
            doc.ViewZoomtofit2();
            bool bmpOk=doc.SaveBMP(bmp,1800,1273);

            sw.CloseDoc(doc.GetTitle());doc=null;
            Need(Sha(drawing)==drawingSha,"drawing changed during read-only verification/export");
            string status=(c02&&c05)?"PASS_D006_NATIVE_DIMXPERT_C02_C05_VERIFIED":"HOLD_D006_NATIVE_DIMXPERT_C02_C05_MISSING";
            var sb=new StringBuilder();
            sb.AppendLine("STATUS="+status);
            sb.AppendLine("DRAWING="+drawing);
            sb.AppendLine("DRAWING_SHA256="+drawingSha);
            sb.AppendLine("SOURCE_PART="+part);
            sb.AppendLine("P007_VIEW_REFERENCE_COUNT="+modelRefCount);
            sb.AppendLine("DIMXPERT_ANNOTATION_COUNT="+dxCount);
            sb.AppendLine("C02="+c02);
            sb.AppendLine("C05="+c05);
            sb.AppendLine("PDF="+pdf);
            sb.AppendLine("PDF_EXPORT_OK="+pdfOk);
            sb.AppendLine("BMP="+bmp);
            sb.AppendLine("BMP_EXPORT_OK="+bmpOk);
            for(int i=0;i<records.Count;i++)sb.AppendLine("DX_"+(i+1)+"="+records[i]);
            File.WriteAllText(report,sb.ToString(),Encoding.UTF8);

            Console.WriteLine("STATUS: "+status);
            Console.WriteLine("DIMXPERT COUNT: "+dxCount);
            Console.WriteLine("C02: "+c02+" C05: "+c05);
            Console.WriteLine("P007 VIEW REFS: "+modelRefCount);
            Console.WriteLine("PDF: "+pdf+" refreshed="+pdfOk);
            Console.WriteLine("BMP: "+bmp+" refreshed="+bmpOk);
            return (c02&&c05)?0:3;
        }catch(Exception ex){
            try{File.WriteAllText(report,"STATUS=HOLD_D006_NATIVE_DIMXPERT_VERIFY_ERROR\nERROR="+ex.ToString()+"\n",Encoding.UTF8);}catch{}
            Console.Error.WriteLine(ex.ToString());return 2;
        }finally{
            try{if(doc!=null&&sw!=null)sw.CloseDoc(doc.GetTitle());}catch{}
            try{if(created&&sw!=null)sw.ExitApp();}catch{}
        }
    }
}
