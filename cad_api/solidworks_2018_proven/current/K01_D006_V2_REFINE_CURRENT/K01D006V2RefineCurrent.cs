using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using SolidWorks.Interop.sldworks;
using SolidWorks.Interop.swconst;

public class K01D006V2RefineCurrent
{
    static void Need(bool ok,string msg){if(!ok)throw new Exception(msg);}
    static string Arg(string[] a,string k){for(int i=0;i<a.Length-1;i++)if(a[i]==k)return a[i+1];return null;}
    static string Sha(string p){
        using(FileStream fs=new FileStream(p,FileMode.Open,FileAccess.Read,FileShare.ReadWrite|FileShare.Delete))
        using(SHA256 h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(fs)).Replace("-","").ToLowerInvariant();
    }
    static IEnumerable Items(object o){
        if(o==null)yield break;
        Array a=o as Array;if(a!=null){foreach(object x in a)yield return x;yield break;}
        IEnumerable e=o as IEnumerable;if(e!=null)foreach(object x in e)yield return x;
    }
    static string N(View v){try{return v.GetName2()??"";}catch{return "";}}
    static string Ref(View v){try{return v.GetReferencedModelName()??"";}catch{return "";}}
    static string One(string s){return (s??"").Replace("\r"," ").Replace("\n"," ").Trim();}
    static bool Visible(Annotation a){
        try{return a!=null && a.Visible!=(int)swAnnotationVisibilityState_e.swAnnotationHidden;}catch{return true;}
    }
    static void Hide(Annotation a){try{if(a!=null)a.Visible=(int)swAnnotationVisibilityState_e.swAnnotationHidden;}catch{}}
    static int HideObsoleteSurfaceReview(DrawingDoc dr){
        int n=0; View v=dr.GetFirstView() as View;
        while(v!=null){
            Note note=null;try{note=v.GetFirstNote() as Note;}catch{}
            while(note!=null){
                Note nx=null;try{nx=note.GetNext() as Note;}catch{}
                string t="";try{t=note.GetText()??"";}catch{}
                if(t.IndexOf("J2 MATING / SEAL-CONTACT FACE",StringComparison.OrdinalIgnoreCase)>=0 &&
                   t.IndexOf("ENGINEERING-REVIEW CANDIDATE",StringComparison.OrdinalIgnoreCase)>=0){
                    Annotation a=note.GetAnnotation() as Annotation;
                    if(Visible(a)){Hide(a);n++;}
                }
                note=nx;
            }
            v=v.GetNextView() as View;
        }
        return n;
    }
    static Note AddSheetNote(ModelDoc2 doc,DrawingDoc dr,string text,double x,double y,string id){
        try{
            Sheet s=dr.GetCurrentSheet() as Sheet;
            if(s!=null)dr.ActivateSheet(s.GetName());
        }catch{}
        doc.ClearSelection2(true);
        Note n=doc.InsertNote(text) as Note;Need(n!=null,"InsertNote failed: "+id);
        Annotation a=n.GetAnnotation() as Annotation;
        if(a!=null){a.SetPosition(x,y,0);try{a.SetName("K01DS_"+id);}catch{}}
        try{n.SetName("K01DS_"+id);}catch{}
        try{n.LockPosition=true;}catch{}
        return n;
    }
    static int CountMarker(DrawingDoc dr,string marker,bool visibleOnly){
        int c=0;View v=dr.GetFirstView() as View;
        while(v!=null){
            Note n=null;try{n=v.GetFirstNote() as Note;}catch{}
            while(n!=null){
                Note nx=null;try{nx=n.GetNext() as Note;}catch{}
                string t="";try{t=n.GetText()??"";}catch{}
                Annotation a=null;try{a=n.GetAnnotation() as Annotation;}catch{}
                if(t.IndexOf(marker,StringComparison.OrdinalIgnoreCase)>=0 && (!visibleOnly||Visible(a)))c++;
                n=nx;
            }
            v=v.GetNextView() as View;
        }
        return c;
    }
    static int CountViews(DrawingDoc dr,string modelBase,out int sectionCount){
        int c=0;sectionCount=0;View v=dr.GetFirstView() as View;if(v!=null)v=v.GetNextView() as View;
        while(v!=null){
            string r=Ref(v);
            if(!String.IsNullOrWhiteSpace(r)&&String.Equals(Path.GetFileName(r),modelBase,StringComparison.OrdinalIgnoreCase)){
                c++; string n=N(v).ToUpperInvariant();
                if(n.Contains("SECTION")||n.Contains("A-A")||n.Contains("B-B"))sectionCount++;
            }
            v=v.GetNextView() as View;
        }
        return c;
    }
    static void SetProp(ModelDoc2 doc,string k,string v){
        CustomPropertyManager c=doc.Extension.get_CustomPropertyManager("");
        try{c.Delete2(k);}catch{}
        try{c.Add(k,"Text",v??"");}catch{}
        try{c.Set2(k,v??"");}catch{}
    }
    static bool SaveAs(ModelDoc2 d,string p){
        int e=0,w=0;bool ok=d.Extension.SaveAs(p,(int)swSaveAsVersion_e.swSaveAsCurrentVersion,(int)swSaveAsOptions_e.swSaveAsOptions_Silent,null,ref e,ref w);
        if(!ok||e!=0)throw new Exception("SaveAs failed e="+e+" w="+w);return true;
    }
    public static int Main(string[] args){
        string drawing=Arg(args,"--drawing"),model=Arg(args,"--model"),outdir=Arg(args,"--outdir"),report=Arg(args,"--report");
        if(String.IsNullOrWhiteSpace(drawing)||String.IsNullOrWhiteSpace(model)||String.IsNullOrWhiteSpace(outdir)||String.IsNullOrWhiteSpace(report)){Console.Error.WriteLine("missing args");return 2;}
        try{
            Need(File.Exists(drawing),"current drawing missing");
            Need(File.Exists(model),"source model missing");
            string drawingSha=Sha(drawing),modelSha=Sha(model);
            Directory.CreateDirectory(outdir);
            string dst=Path.Combine(outdir,"K01-D-006_V2_REFINED_CANDIDATE.SLDDRW");
            File.Copy(drawing,dst,false);

            Type t=Type.GetTypeFromProgID("SldWorks.Application");Need(t!=null,"SW ProgID missing");
            SldWorks sw=Activator.CreateInstance(t) as SldWorks;Need(sw!=null,"SW activation failed");sw.Visible=true;
            Need(typeof(SldWorks).Assembly.GetName().Version.Major==26,"requires SW2018 interop major 26");
            int er=0,wr=0;
            ModelDoc2 doc=sw.OpenDoc6(dst,(int)swDocumentTypes_e.swDocDRAWING,(int)swOpenDocOptions_e.swOpenDocOptions_Silent,"",ref er,ref wr) as ModelDoc2;
            Need(doc!=null,"open clone failed e="+er+" w="+wr);
            DrawingDoc dr=doc as DrawingDoc;Need(dr!=null,"not drawing");
            int sections=0;int modelViews=CountViews(dr,Path.GetFileName(model),out sections);
            Need(modelViews>=2,"expected >=2 P007 model views in cloned current drawing; got "+modelViews);
            Need(sections>=1,"existing current drawing has no identifiable section view");

            int hidden=HideObsoleteSurfaceReview(dr);
            AddSheetNote(doc,dr,"[D006-SURFACE-J2-RELEASE] J2 MATING / SEAL-CONTACT FACE - Ra 0.8 um - EDR-037.",0.070,0.160,"D006-SURFACE-J2-RELEASE");
            AddSheetNote(doc,dr,"[D006-C12-J2-LEAK] ASSEMBLED J2 ACCEPTANCE (NOT BARE P007): qHe <= 1.0E-5 mbar*L/s @ |dP|=0.20 bar, 20+/-5 C; EDR-035.",0.165,0.055,"D006-C12-J2-LEAK");
            AddSheetNote(doc,dr,"[D006-INSPECTION-REF] CONTROLLED CHARACTERISTICS: INSPECT PER K01-P-007 INSPECTION PLAN. C12 IS ASSEMBLED-J2 ACCEPTANCE.",0.285,0.055,"D006-INSPECTION-REF");
            SetProp(doc,"D006SpecVersion","V2");
            SetProp(doc,"D006ProductDefinition","READY");
            SetProp(doc,"D006Lifecycle","L6_CANDIDATE_TPD");
            SetProp(doc,"ReleaseState","HOLD_D8_AND_RELEASE");
            doc.EditRebuild3();

            int surfaceCount=CountMarker(dr,"[D006-SURFACE-J2-RELEASE]",true);
            int c12Count=CountMarker(dr,"[D006-C12-J2-LEAK]",true);
            int inspectionCount=CountMarker(dr,"[D006-INSPECTION-REF]",true);
            int obsoleteVisible=CountMarker(dr,"ENGINEERING-REVIEW CANDIDATE",true);
            Need(surfaceCount==1,"surface release note readback failed");
            Need(c12Count==1,"C12 note readback failed");
            Need(inspectionCount==1,"inspection note readback failed");
            Need(obsoleteVisible==0,"obsolete visible surface-review note remains");

            SaveAs(doc,dst);
            string pdf=Path.ChangeExtension(dst,"PDF"),bmp=Path.ChangeExtension(dst,"BMP");
            int pe=0,pw=0;bool pdfOk=doc.Extension.SaveAs(pdf,(int)swSaveAsVersion_e.swSaveAsCurrentVersion,(int)swSaveAsOptions_e.swSaveAsOptions_Silent,null,ref pe,ref pw);
            doc.ViewZoomtofit2();bool bmpOk=doc.SaveBMP(bmp,1800,1273);
            sw.CloseDoc(doc.GetTitle());try{sw.ExitApp();}catch{}

            Need(Sha(drawing)==drawingSha,"current source drawing changed");
            Need(Sha(model)==modelSha,"P007 source model changed");
            Need(File.Exists(dst)&&new FileInfo(dst).Length>4096,"candidate missing/small");
            Need(pdfOk&&File.Exists(pdf),"PDF export failed");
            Need(bmpOk&&File.Exists(bmp),"BMP export failed");

            var sb=new StringBuilder();
            sb.AppendLine("STATUS=PASS_D006_V2_REFINED_FROM_CURRENT");
            sb.AppendLine("SOURCE_CURRENT_DRAWING="+drawing);
            sb.AppendLine("SOURCE_CURRENT_SHA256="+drawingSha);
            sb.AppendLine("SOURCE_MODEL="+model);
            sb.AppendLine("SOURCE_MODEL_SHA256="+modelSha);
            sb.AppendLine("OUTPUT_DRAWING="+dst);
            sb.AppendLine("OUTPUT_PDF="+pdf);
            sb.AppendLine("OUTPUT_BMP="+bmp);
            sb.AppendLine("MODEL_VIEW_COUNT="+modelViews);
            sb.AppendLine("SECTION_VIEW_COUNT="+sections);
            sb.AppendLine("HIDDEN_OBSOLETE_SURFACE_REVIEW_NOTES="+hidden);
            sb.AppendLine("SURFACE_RELEASE_NOTE_COUNT="+surfaceCount);
            sb.AppendLine("C12_NOTE_COUNT="+c12Count);
            sb.AppendLine("INSPECTION_NOTE_COUNT="+inspectionCount);
            sb.AppendLine("OBSOLETE_REVIEW_VISIBLE="+obsoleteVisible);
            sb.AppendLine("CURRENT_DRAWING_INVARIANT=True");
            sb.AppendLine("SOURCE_MODEL_INVARIANT=True");
            File.WriteAllText(report,sb.ToString(),Encoding.UTF8);
            Console.WriteLine("STATUS: PASS_D006_V2_REFINED_FROM_CURRENT");
            Console.WriteLine("OUTPUT: "+dst);
            Console.WriteLine("PDF: "+pdf);
            Console.WriteLine("BMP: "+bmp);
            Console.WriteLine("VIEWS: "+modelViews+" sections="+sections);
            Console.WriteLine("OBSOLETE SURFACE REVIEW NOTES HIDDEN: "+hidden);
            return 0;
        }catch(Exception ex){
            try{File.WriteAllText(report,"STATUS=HOLD\nERROR="+ex.ToString()+"\n",Encoding.UTF8);}catch{}
            Console.Error.WriteLine(ex.ToString());return 2;
        }
    }
}
