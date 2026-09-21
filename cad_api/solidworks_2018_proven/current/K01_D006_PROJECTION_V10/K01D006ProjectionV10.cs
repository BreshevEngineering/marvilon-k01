using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using SolidWorks.Interop.sldworks;
using SolidWorks.Interop.swconst;

public class K01D006ProjectionV10
{
    class NoteRec { public string id,zone,text; public double x,y; }
    class LayoutRec { public string selector,role; public double x,y,scale; }
    static string Arg(string[] a,string k){for(int i=0;i<a.Length-1;i++)if(a[i]==k)return a[i+1];return null;}
    static void Need(bool ok,string msg){if(!ok)throw new Exception(msg);}
    static string One(string s){return (s??"").Replace("\r"," ").Replace("\n"," ").Replace("=","-");}
    static string Sha(string p){using(FileStream fs=new FileStream(p,FileMode.Open,FileAccess.Read,FileShare.ReadWrite|FileShare.Delete))using(SHA256 h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(fs)).Replace("-","").ToLowerInvariant();}
    static IEnumerable Items(object o){if(o==null)yield break;Array a=o as Array;if(a!=null){foreach(object x in a)yield return x;yield break;}IEnumerable e=o as IEnumerable;if(e!=null)foreach(object x in e)yield return x;}
    static List<NoteRec> ReadNotes(string p){var r=new List<NoteRec>();foreach(string raw in File.ReadAllLines(p,Encoding.UTF8)){if(String.IsNullOrWhiteSpace(raw))continue;string[] a=raw.Split('\t');Need(a.Length>=5,"bad note TSV row");r.Add(new NoteRec{id=a[0],zone=a[1],x=Double.Parse(a[2],CultureInfo.InvariantCulture),y=Double.Parse(a[3],CultureInfo.InvariantCulture),text=a[4].Replace("\\n","\n")});}return r;}
    static List<LayoutRec> ReadLayout(string p){var r=new List<LayoutRec>();foreach(string raw in File.ReadAllLines(p,Encoding.UTF8)){if(String.IsNullOrWhiteSpace(raw))continue;string[] a=raw.Split('\t');Need(a.Length>=5,"bad layout TSV row");r.Add(new LayoutRec{selector=a[0],x=Double.Parse(a[1],CultureInfo.InvariantCulture),y=Double.Parse(a[2],CultureInfo.InvariantCulture),scale=Double.Parse(a[3],CultureInfo.InvariantCulture),role=a[4]});}return r;}
    static string VName(View v){try{return v.GetName2()??"";}catch{return "";}}
    static bool IsModelView(View v){try{return !String.IsNullOrWhiteSpace(v.GetReferencedModelName());}catch{return false;}}
    static List<View> ModelViews(DrawingDoc dr){var r=new List<View>();View v=dr.GetFirstView() as View;if(v!=null)v=v.GetNextView() as View;while(v!=null){if(IsModelView(v))r.Add(v);v=v.GetNextView() as View;}return r;}
    static bool DeleteAnnotation(ModelDoc2 doc,Annotation a){try{if(a==null)return false;doc.ClearSelection2(true);bool s=false;try{s=a.Select3(false,null);}catch{}if(!s)try{s=a.Select2(false,0);}catch{}if(!s)return false;bool ok=doc.Extension.DeleteSelection2((int)swDeleteSelectionOptions_e.swDelete_Absorbed);doc.ClearSelection2(true);return ok;}catch{doc.ClearSelection2(true);return false;}}
    static bool ObsoleteNote(string t){t=(t??"").Trim();string[] p={"K01-D-006 | K01-P-007","DESIGN REVIEW CANDIDATE","MODEL-BASED DESIGN REVIEW CANDIDATE","CURRENT PROVEN NATIVE PMI","3X Ø2.90 THRU","C02 BORE DEPTH","MATERIAL:","OPEN:","CONTROLLED PROJECTION","[C01]","[C02]","[C04]","[C05]","[C06]","[C07]","[C08]","[C09]","[K01-D006-BLIND-END]","[C10]","[C11]","[C12]","[PDG-"};foreach(string x in p)if(t.StartsWith(x,StringComparison.OrdinalIgnoreCase))return true;return false;}
    static void Cleanup(ModelDoc2 doc,DrawingDoc dr,List<string> log){int nt=0,tb=0;View v=dr.GetFirstView() as View;while(v!=null){TableAnnotation ta=null;try{ta=v.GetFirstTableAnnotation() as TableAnnotation;}catch{}while(ta!=null){TableAnnotation nx=null;try{nx=ta.GetNext();}catch{}try{if(ta.Type==(int)swTableAnnotationType_e.swTableAnnotation_General){if(DeleteAnnotation(doc,ta.GetAnnotation() as Annotation))tb++;}}catch{}ta=nx;}Note n=null;try{n=v.GetFirstNote() as Note;}catch{}while(n!=null){Note nx=null;try{nx=n.GetNext() as Note;}catch{}string tx="";try{tx=n.GetText()??"";}catch{}if(ObsoleteNote(tx)){try{if(DeleteAnnotation(doc,n.GetAnnotation() as Annotation))nt++;}catch{}}n=nx;}v=v.GetNextView() as View;}log.Add("CLEANUP tables="+tb+" notes="+nt);}
    static View FindView(List<View> views,string sel){if(String.Equals(sel,"SECTION",StringComparison.OrdinalIgnoreCase)){foreach(View v in views)if(VName(v).IndexOf("Section",StringComparison.OrdinalIgnoreCase)>=0)return v;return null;}foreach(View v in views)if(String.Equals(VName(v),sel,StringComparison.OrdinalIgnoreCase))return v;return null;}
    static void Layout(List<View> views,List<LayoutRec> layout,List<string> log){foreach(LayoutRec x in layout){View v=FindView(views,x.selector);if(v==null){log.Add("LAYOUT "+x.selector+" MISSING");continue;}try{v.PositionLocked=false;}catch{}try{v.UseSheetScale=0;}catch{}try{v.UseParentScale=false;}catch{}try{v.ScaleDecimal=x.scale;}catch{}try{v.Position=new double[]{x.x,x.y};}catch{}log.Add("LAYOUT "+x.selector+" role="+x.role+" scale="+x.scale.ToString("0.###",CultureInfo.InvariantCulture)+" pos="+x.x.ToString("0.000",CultureInfo.InvariantCulture)+","+x.y.ToString("0.000",CultureInfo.InvariantCulture));}}
    static bool AddNote(ModelDoc2 doc,NoteRec r,List<string> readback,List<string> log){try{doc.ClearSelection2(true);Note n=doc.InsertNote(r.text) as Note;if(n==null){log.Add("NOTE "+r.id+" FAIL InsertNote");return false;}Annotation a=n.GetAnnotation() as Annotation;if(a!=null){a.SetPosition(r.x,r.y,0);n.LockPosition=true;}string rb="";try{rb=n.GetText()??"";}catch{}bool ok=rb.IndexOf("["+r.id+"]",StringComparison.OrdinalIgnoreCase)>=0;if(ok)readback.Add(r.id);log.Add("NOTE "+r.id+" zone="+r.zone+" readback="+ok+" text="+One(rb));return ok;}catch(Exception ex){log.Add("NOTE "+r.id+" ERROR="+ex.GetType().Name+":"+One(ex.Message));return false;}}
    static bool SaveAs(ModelDoc2 doc,string p){int e=0,w=0;bool ok=doc.Extension.SaveAs(p,(int)swSaveAsVersion_e.swSaveAsCurrentVersion,(int)swSaveAsOptions_e.swSaveAsOptions_Silent,null,ref e,ref w);if(!ok||e!=0)throw new Exception("SaveAs failed "+p+" e="+e+" w="+w);return true;}

    public static int Main(string[] args){
        string drawing=Arg(args,"--drawing"),notesPath=Arg(args,"--notes"),layoutPath=Arg(args,"--layout"),fp=Arg(args,"--fingerprint"),outRoot=Arg(args,"--out-root"),report=Arg(args,"--report");
        if(String.IsNullOrWhiteSpace(drawing)||String.IsNullOrWhiteSpace(notesPath)||String.IsNullOrWhiteSpace(layoutPath)||String.IsNullOrWhiteSpace(fp)||String.IsNullOrWhiteSpace(outRoot)||String.IsNullOrWhiteSpace(report)){Console.Error.WriteLine("missing args");return 2;}
        SldWorks sw=null;ModelDoc2 doc=null;bool created=false;var log=new List<string>();
        try{
            Need(File.Exists(drawing),"source drawing missing");Need(File.Exists(notesPath),"notes TSV missing");Need(File.Exists(layoutPath),"layout TSV missing");
            string sourceSha=Sha(drawing);List<NoteRec> notes=ReadNotes(notesPath);List<LayoutRec> layout=ReadLayout(layoutPath);Need(notes.Count>0,"no projection notes");
            string stamp=DateTime.Now.ToString("yyyyMMdd_HHmmss"),dir=Path.Combine(outRoot,"projection_v10_"+stamp);Directory.CreateDirectory(dir);string dst=Path.Combine(dir,"K01-D-006_Hermetic_Magnetic_Can_PROJECTION_V10_CANDIDATE.SLDDRW");File.Copy(drawing,dst,false);
            Type t=Type.GetTypeFromProgID("SldWorks.Application");Need(t!=null,"SOLIDWORKS ProgID unavailable");sw=Activator.CreateInstance(t) as SldWorks;Need(sw!=null,"SOLIDWORKS activation failed");created=true;sw.Visible=true;Need(typeof(SldWorks).Assembly.GetName().Version.Major==26,"requires SOLIDWORKS 2018 interop major 26");
            int er=0,wr=0;doc=sw.OpenDoc6(dst,(int)swDocumentTypes_e.swDocDRAWING,(int)swOpenDocOptions_e.swOpenDocOptions_Silent,"",ref er,ref wr) as ModelDoc2;Need(doc!=null,"open drawing failed e="+er+" w="+wr);DrawingDoc dr=doc as DrawingDoc;Need(dr!=null,"not drawing");
            List<View> views=ModelViews(dr);Need(views.Count>=3,"expected >=3 linked model views, got "+views.Count);Cleanup(doc,dr,log);Layout(views,layout,log);doc.EditRebuild3();
            string[] sheets=dr.GetSheetNames() as string[];if(sheets!=null&&sheets.Length>0)dr.ActivateSheet(sheets[0]);doc.ClearSelection2(true);
            var readback=new List<string>();
            var header=new NoteRec{id="V10-HEADER",zone="META",x=0.012,y=0.289,text="CONTROLLED PROJECTION — DESIGN REVIEW / NOT RELEASED"};AddNote(doc,header,new List<string>(),log);
            foreach(NoteRec n in notes)AddNote(doc,n,readback,log);
            doc.ForceRebuild3(false);SaveAs(doc,dst);string pdf=Path.ChangeExtension(dst,"PDF"),bmp=Path.ChangeExtension(dst,"BMP");SaveAs(doc,pdf);doc.ViewZoomtofit2();bool bmpOk=doc.SaveBMP(bmp,1800,1273);string title=doc.GetTitle();sw.CloseDoc(title);doc=null;
            Need(Sha(drawing)==sourceSha,"source drawing changed");Need(File.Exists(dst)&&new FileInfo(dst).Length>4096,"output drawing missing/small");Need(File.Exists(pdf)&&new FileInfo(pdf).Length>1024,"PDF missing/small");
            var uniq=new HashSet<string>(readback,StringComparer.OrdinalIgnoreCase);StringBuilder sb=new StringBuilder();sb.AppendLine("STATUS=PASS_D006_PROJECTION_V10_BASE__VISUAL_QA_REQUIRED");sb.AppendLine("SOURCE_DRAWING="+drawing);sb.AppendLine("SOURCE_DRAWING_SHA256="+sourceSha);sb.AppendLine("SOURCE_DRAWING_INVARIANT=True");sb.AppendLine("COMPILED_DEFINITION_SHA256="+fp);sb.AppendLine("OUTPUT_DRAWING="+dst);sb.AppendLine("OUTPUT_PDF="+pdf);sb.AppendLine("OUTPUT_BMP="+bmp);sb.AppendLine("BMP_OK="+bmpOk);sb.AppendLine("MODEL_VIEW_COUNT="+views.Count);sb.AppendLine("NOTE_REQUESTED_COUNT="+notes.Count);sb.AppendLine("NOTE_READBACK_COUNT="+uniq.Count);sb.AppendLine("READBACK_IDS="+String.Join(",",new List<string>(uniq).ToArray()));for(int i=0;i<log.Count;i++)sb.AppendLine("LOG_"+(i+1)+"="+One(log[i]));File.WriteAllText(report,sb.ToString(),Encoding.UTF8);
            Console.WriteLine("STATUS: PASS_D006_PROJECTION_V10_BASE__VISUAL_QA_REQUIRED");Console.WriteLine("NOTES READBACK: "+uniq.Count+" / "+notes.Count);Console.WriteLine("DRAWING: "+dst);Console.WriteLine("PDF: "+pdf);Console.WriteLine("BMP: "+bmp);Console.WriteLine("REPORT: "+report);return 0;
        }catch(Exception ex){try{File.WriteAllText(report,"STATUS=HOLD_D006_PROJECTION_V10\nERROR="+ex.ToString()+"\n",Encoding.UTF8);}catch{}Console.Error.WriteLine(ex.ToString());return 2;}
        finally{try{if(doc!=null&&sw!=null)sw.CloseDoc(doc.GetTitle());}catch{}try{if(created&&sw!=null)sw.ExitApp();}catch{}}
    }
}
