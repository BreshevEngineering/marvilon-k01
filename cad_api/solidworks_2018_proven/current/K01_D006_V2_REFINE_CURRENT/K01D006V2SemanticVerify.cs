using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using SolidWorks.Interop.sldworks;
using SolidWorks.Interop.swconst;

public class K01D006V2SemanticVerify
{
    static void Need(bool ok,string msg){if(!ok)throw new Exception(msg);}
    static string Arg(string[] a,string k){for(int i=0;i<a.Length-1;i++)if(a[i]==k)return a[i+1];return null;}
    static bool Visible(Annotation a){try{return a!=null&&a.Visible!=(int)swAnnotationVisibilityState_e.swAnnotationHidden;}catch{return true;}}
    static string Ref(View v){try{return v.GetReferencedModelName()??"";}catch{return "";}}
    static string Name(View v){try{return v.GetName2()??"";}catch{return "";}}
    static int CountMarker(DrawingDoc dr,string marker,bool visibleOnly){
        int c=0;View v=dr.GetFirstView() as View;
        while(v!=null){
            Note n=null;try{n=v.GetFirstNote() as Note;}catch{}
            while(n!=null){
                Note nx=null;try{nx=n.GetNext() as Note;}catch{}
                string t="";try{t=n.GetText()??"";}catch{}
                Annotation a=null;try{a=n.GetAnnotation() as Annotation;}catch{}
                if(t.IndexOf(marker,StringComparison.OrdinalIgnoreCase)>=0&&(!visibleOnly||Visible(a)))c++;
                n=nx;
            } v=v.GetNextView() as View;
        } return c;
    }
    static int ModelViews(DrawingDoc dr,string modelBase,out int sections){
        int c=0;sections=0;View v=dr.GetFirstView() as View;if(v!=null)v=v.GetNextView() as View;
        while(v!=null){
            string r=Ref(v);
            if(!String.IsNullOrWhiteSpace(r)&&String.Equals(Path.GetFileName(r),modelBase,StringComparison.OrdinalIgnoreCase)){
                c++;string n=Name(v).ToUpperInvariant();if(n.Contains("SECTION")||n.Contains("A-A")||n.Contains("B-B"))sections++;
            }v=v.GetNextView() as View;
        }return c;
    }
    public static int Main(string[] args){
        string drawing=Arg(args,"--drawing"),model=Arg(args,"--model"),report=Arg(args,"--report");
        if(String.IsNullOrWhiteSpace(drawing)||String.IsNullOrWhiteSpace(model)||String.IsNullOrWhiteSpace(report)){Console.Error.WriteLine("missing args");return 2;}
        SldWorks sw=null;ModelDoc2 doc=null;
        try{
            Need(File.Exists(drawing),"candidate missing");Need(File.Exists(model),"model missing");
            Type t=Type.GetTypeFromProgID("SldWorks.Application");Need(t!=null,"SW ProgID missing");sw=Activator.CreateInstance(t) as SldWorks;Need(sw!=null,"SW activation failed");sw.Visible=false;
            int e=0,w=0;int opts=(int)swOpenDocOptions_e.swOpenDocOptions_Silent | (int)swOpenDocOptions_e.swOpenDocOptions_ReadOnly;
            doc=sw.OpenDoc6(drawing,(int)swDocumentTypes_e.swDocDRAWING,opts,"",ref e,ref w) as ModelDoc2;Need(doc!=null,"open candidate read-only failed e="+e+" w="+w);
            DrawingDoc dr=doc as DrawingDoc;Need(dr!=null,"not drawing");
            int sec=0,mv=ModelViews(dr,Path.GetFileName(model),out sec);
            int srf=CountMarker(dr,"[D006-SURFACE-J2-RELEASE]",true);
            int c12=CountMarker(dr,"[D006-C12-J2-LEAK]",true);
            int insp=CountMarker(dr,"[D006-INSPECTION-REF]",true);
            int obsolete=CountMarker(dr,"ENGINEERING-REVIEW CANDIDATE",true);
            Need(mv>=2,"model view count <2");Need(sec>=1,"section view missing");Need(srf==1,"surface release note missing/duplicate");Need(c12==1,"C12 note missing/duplicate");Need(insp==1,"inspection note missing/duplicate");Need(obsolete==0,"obsolete visible surface review note remains");
            var sb=new StringBuilder();sb.AppendLine("STATUS=PASS_D006_V2_NATIVE_DELTA_QA");sb.AppendLine("MODEL_VIEW_COUNT="+mv);sb.AppendLine("SECTION_VIEW_COUNT="+sec);sb.AppendLine("SURFACE_RELEASE_VISIBLE="+srf);sb.AppendLine("C12_VISIBLE="+c12);sb.AppendLine("INSPECTION_VISIBLE="+insp);sb.AppendLine("OBSOLETE_REVIEW_VISIBLE="+obsolete);File.WriteAllText(report,sb.ToString(),Encoding.UTF8);
            Console.WriteLine("STATUS: PASS_D006_V2_NATIVE_DELTA_QA");Console.WriteLine("VIEWS: "+mv+" sections="+sec);return 0;
        }catch(Exception ex){try{File.WriteAllText(report,"STATUS=HOLD\nERROR="+ex.ToString()+"\n",Encoding.UTF8);}catch{}Console.Error.WriteLine(ex.ToString());return 2;}
        finally{try{if(doc!=null&&sw!=null)sw.CloseDoc(doc.GetTitle());}catch{}try{if(sw!=null)sw.ExitApp();}catch{}}
    }
}
