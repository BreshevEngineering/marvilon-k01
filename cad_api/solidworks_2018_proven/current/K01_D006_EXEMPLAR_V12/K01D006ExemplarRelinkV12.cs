using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using SolidWorks.Interop.sldworks;
using SolidWorks.Interop.swconst;

public class K01D006ExemplarRelinkV12
{
    static void Need(bool ok,string msg){if(!ok)throw new Exception(msg);}
    static string Arg(string[] a,string k){for(int i=0;i<a.Length-1;i++)if(a[i]==k)return a[i+1];return null;}
    static IEnumerable Items(object o){if(o==null)yield break;Array a=o as Array;if(a!=null){foreach(object x in a)yield return x;yield break;}IEnumerable e=o as IEnumerable;if(e!=null)foreach(object x in e)yield return x;}
    static bool Eq(string a,string b){return String.Equals(a??"",b??"",StringComparison.OrdinalIgnoreCase);}
    static string RefModel(View v){try{return v.GetReferencedModelName()??"";}catch{return "";}}
    static string ViewName(View v){try{return v.GetName2()??"";}catch{return "";}}
    static string FindP007Reference(SldWorks sw,string drawing,List<string> log){
        object dep=sw.GetDocumentDependencies2(drawing,false,true,false);var xs=new List<string>();foreach(object x in Items(dep))xs.Add(Convert.ToString(x)??"");
        for(int i=0;i+1<xs.Count;i+=2){string p=xs[i+1];log.Add("DEPENDENCY name="+xs[i]+" path="+p);if(Path.GetFileName(p).StartsWith("K01-P-007_Hermetic_Magnetic_Can",StringComparison.OrdinalIgnoreCase)&&p.EndsWith(".SLDPRT",StringComparison.OrdinalIgnoreCase))return p;}return "";
    }
    public static int Main(string[] args){
        string drawing=Arg(args,"--drawing"),part=Arg(args,"--part"),report=Arg(args,"--report");SldWorks sw=null;ModelDoc2 doc=null;bool created=false;var log=new List<string>();
        try{
            Need(!String.IsNullOrWhiteSpace(drawing)&&File.Exists(drawing),"drawing missing");Need(!String.IsNullOrWhiteSpace(part)&&File.Exists(part),"part missing");Need(!String.IsNullOrWhiteSpace(report),"report missing");
            try{sw=Marshal.GetActiveObject("SldWorks.Application") as SldWorks;}catch{}if(sw==null){Type t=Type.GetTypeFromProgID("SldWorks.Application");Need(t!=null,"SW ProgID missing");sw=Activator.CreateInstance(t) as SldWorks;Need(sw!=null,"SW activation failed");created=true;}sw.Visible=false;Need(typeof(SldWorks).Assembly.GetName().Version.Major==26,"requires SOLIDWORKS 2018 interop major 26");
            string oldRef=FindP007Reference(sw,drawing,log);Need(!String.IsNullOrWhiteSpace(oldRef),"cannot resolve P007 reference");bool repl=sw.ReplaceReferencedDocument(drawing,oldRef,part);log.Add("RELINK old="+oldRef+" new="+part+" return="+repl);Need(repl,"ReplaceReferencedDocument failed");
            int e=0,w=0;doc=sw.OpenDoc6(drawing,(int)swDocumentTypes_e.swDocDRAWING,(int)swOpenDocOptions_e.swOpenDocOptions_Silent,"",ref e,ref w) as ModelDoc2;Need(doc!=null,"open drawing failed e="+e+" w="+w);DrawingDoc dr=doc as DrawingDoc;Need(dr!=null,"not drawing");
            int refs=0,total=0;View v=dr.GetFirstView() as View;if(v!=null)v=v.GetNextView() as View;while(v!=null){total++;string rm=RefModel(v);log.Add("VIEW name="+ViewName(v)+" ref="+rm);if(!String.IsNullOrWhiteSpace(rm)&&Eq(Path.GetFullPath(rm),Path.GetFullPath(part)))refs++;v=v.GetNextView() as View;}
            int se=0,swarn=0;bool saved=doc.Extension.SaveAs(drawing,(int)swSaveAsVersion_e.swSaveAsCurrentVersion,(int)swSaveAsOptions_e.swSaveAsOptions_Silent,null,ref se,ref swarn);Need(saved&&se==0,"save drawing failed e="+se+" w="+swarn);Need(refs>0,"no drawing views reference exemplar part after relink");
            var sb=new StringBuilder();sb.AppendLine("STATUS=PASS_EXEMPLAR_RELINK");sb.AppendLine("OLD_REF="+oldRef);sb.AppendLine("NEW_REF="+part);sb.AppendLine("P007_VIEW_REFS="+refs);sb.AppendLine("TOTAL_VIEWS="+total);sb.AppendLine("SAVED=True");foreach(string x in log)sb.AppendLine("LOG="+x.Replace("\r"," ").Replace("\n"," "));File.WriteAllText(report,sb.ToString(),Encoding.UTF8);
            Console.WriteLine("STATUS: PASS_EXEMPLAR_RELINK");Console.WriteLine("P007 VIEW REFS: "+refs);return 0;
        }catch(Exception ex){try{File.WriteAllText(report,"STATUS=HOLD_EXEMPLAR_RELINK\nERROR="+ex.ToString()+"\n",Encoding.UTF8);}catch{}Console.Error.WriteLine(ex.ToString());return 2;}
        finally{try{if(doc!=null&&sw!=null)sw.CloseDoc(doc.GetTitle());}catch{}try{if(created&&sw!=null)sw.ExitApp();}catch{}}
    }
}
