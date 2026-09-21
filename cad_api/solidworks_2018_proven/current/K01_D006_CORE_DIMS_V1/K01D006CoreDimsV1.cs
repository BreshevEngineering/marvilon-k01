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

public class K01D006CoreDimsV1
{
    class Target {
        public string id;
        public string dimName;
        public double mm;
        public Target(string i,string n,double v){id=i;dimName=n;mm=v;}
    }

    static string Arg(string[] a,string k){for(int i=0;i<a.Length-1;i++)if(a[i]==k)return a[i+1];return null;}
    static void Need(bool ok,string msg){if(!ok)throw new Exception(msg);}
    static IEnumerable Items(object o){if(o==null)yield break;Array a=o as Array;if(a!=null){foreach(object x in a)yield return x;yield break;}IEnumerable e=o as IEnumerable;if(e!=null)foreach(object x in e)yield return x;}
    static string Sha(string p){using(FileStream fs=new FileStream(p,FileMode.Open,FileAccess.Read,FileShare.ReadWrite|FileShare.Delete))using(SHA256 h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(fs)).Replace("-","").ToLowerInvariant();}
    static string One(string s){return (s??"").Replace("\r"," ").Replace("\n"," ").Replace("=","-");}
    static string VName(View v){try{return v.GetName2()??"";}catch{return "";}}
    static string VRef(View v){try{return v.GetReferencedModelName()??"";}catch{return "";}}
    static double Mm(Dimension d){try{return d==null?Double.NaN:d.SystemValue*1000.0;}catch{return Double.NaN;}}
    static bool Near(double a,double b){return !Double.IsNaN(a)&&Math.Abs(Math.Abs(a)-b)<=0.015;}

    static List<Target> Targets(){
        var r=new List<Target>();
        r.Add(new Target("C05_FLANGE_OD","C05_FLANGE_OD",33.00));
        r.Add(new Target("C05_FLANGE_THK","C05_FLANGE_THK",3.00));
        r.Add(new Target("C06_OAL","C06_OAL",35.00));
        r.Add(new Target("C07_CAN_OD","C07_CAN_OD",10.00));
        r.Add(new Target("C08_CAN_ID","C08_CAN_ID",9.40));
        r.Add(new Target("C04_HOLE_DIA","C04_HOLE_DIA",2.90));
        r.Add(new Target("C02_LOCATOR_DEPTH","C02_LOCATOR_DEPTH",2.00));
        r.Add(new Target("BLIND_END_THK","BLIND_END_THK",1.00));
        r.Add(new Target("C04_PCD","C04_PCD",26.50));
        return r;
    }

    static Target Match(double mm,List<Target> ts){
        Target best=null;double err=1e9;
        foreach(Target t in ts){
            double e=Math.Abs(Math.Abs(mm)-t.mm);
            if(e<=0.015&&e<err){err=e;best=t;}
        }
        return best;
    }

    static HashSet<string> ExistingTargets(DrawingDoc dr,List<Target> ts,List<string> log){
        var found=new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        View v=dr.GetFirstView() as View;
        if(v!=null)v=v.GetNextView() as View;
        while(v!=null){
            foreach(object o in Items(v.GetDisplayDimensions())){
                DisplayDimension dd=o as DisplayDimension;if(dd==null)continue;
                Dimension d=null;try{d=dd.GetDimension2(0);}catch{}
                double mm=Mm(d);Target t=Match(mm,ts);
                if(t!=null){
                    found.Add(t.id);
                    string full="";try{full=d.FullName??"";}catch{}
                    log.Add("EXISTING "+t.id+" view="+VName(v)+" mm="+mm.ToString("0.#####",CultureInfo.InvariantCulture)+" full="+One(full));
                }
            }
            v=v.GetNextView() as View;
        }
        return found;
    }

    static bool DeleteAnnotation(ModelDoc2 doc,Annotation a){
        try{
            if(a==null)return false;
            doc.ClearSelection2(true);
            SelectionMgr sm=doc.SelectionManager as SelectionMgr;
            if(sm==null)return false;
            SelectData sd=sm.CreateSelectData() as SelectData;
            if(sd==null)return false;
            if(!a.Select3(false,sd))return false;
            bool ok=doc.Extension.DeleteSelection2((int)swDeleteSelectionOptions_e.swDelete_Absorbed);
            doc.ClearSelection2(true);
            return ok;
        }catch{try{doc.ClearSelection2(true);}catch{}return false;}
    }

    static string FindP007Reference(SldWorks sw,string drawing){
        object deps=null;try{deps=sw.GetDocumentDependencies2(drawing,true,true,false);}catch{}
        foreach(object q in Items(deps)){
            string s=Convert.ToString(q)??"";
            if(File.Exists(s)&&s.EndsWith(".SLDPRT",StringComparison.OrdinalIgnoreCase)&&Path.GetFileName(s).IndexOf("K01-P-007",StringComparison.OrdinalIgnoreCase)>=0)return s;
        }
        return "";
    }

    static List<View> ModelViews(DrawingDoc dr,string partBase){
        var r=new List<View>();View v=dr.GetFirstView() as View;if(v!=null)v=v.GetNextView() as View;
        while(v!=null){
            string p=VRef(v);
            if(!String.IsNullOrWhiteSpace(p)&&String.Equals(Path.GetFileName(p),partBase,StringComparison.OrdinalIgnoreCase))r.Add(v);
            v=v.GetNextView() as View;
        }
        return r;
    }

    static bool SelectView(ModelDoc2 doc,DrawingDoc dr,View v){
        string n=VName(v);if(String.IsNullOrWhiteSpace(n))return false;
        try{dr.ActivateView(n);}catch{}
        doc.ClearSelection2(true);
        string sel=n;try{string u=v.GetUniqueName();if(!String.IsNullOrWhiteSpace(u))sel=u;}catch{}
        bool ok=false;try{ok=doc.Extension.SelectByID2(sel,"DRAWINGVIEW",0,0,0,false,0,null,0);}catch{}
        if(!ok&&!String.Equals(sel,n,StringComparison.OrdinalIgnoreCase))try{ok=doc.Extension.SelectByID2(n,"DRAWINGVIEW",0,0,0,false,0,null,0);}catch{}
        return ok;
    }

    static bool SaveAs(ModelDoc2 doc,string p){
        int e=0,w=0;
        bool ok=doc.Extension.SaveAs(p,(int)swSaveAsVersion_e.swSaveAsCurrentVersion,(int)swSaveAsOptions_e.swSaveAsOptions_Silent,null,ref e,ref w);
        if(!ok||e!=0)throw new Exception("SaveAs failed "+p+" e="+e+" w="+w);
        return true;
    }

    public static int Main(string[] args){
        string drawing=Arg(args,"--drawing"),part=Arg(args,"--part"),outroot=Arg(args,"--out-root"),report=Arg(args,"--report");
        SldWorks sw=null;ModelDoc2 doc=null;bool created=false;var log=new List<string>();
        try{
            Need(!String.IsNullOrWhiteSpace(drawing)&&File.Exists(drawing),"source drawing missing");
            Need(!String.IsNullOrWhiteSpace(part)&&File.Exists(part),"source part missing");
            Need(!String.IsNullOrWhiteSpace(outroot),"out-root missing");
            Need(!String.IsNullOrWhiteSpace(report),"report missing");
            string dsha=Sha(drawing),psha=Sha(part);

            string stamp=DateTime.Now.ToString("yyyyMMdd_HHmmss");
            string dir=Path.Combine(outroot,"core_dims_v1_"+stamp);Directory.CreateDirectory(dir);
            string partCopy=Path.Combine(dir,"K01-P-007_Hermetic_Magnetic_Can_CORE_DIMS_SOURCE_CANDIDATE.SLDPRT");
            string drawCopy=Path.Combine(dir,"K01-D-006_Hermetic_Magnetic_Can_CORE_DIMS_CANDIDATE.SLDDRW");
            File.Copy(part,partCopy,false);File.Copy(drawing,drawCopy,false);

            Type t=Type.GetTypeFromProgID("SldWorks.Application");Need(t!=null,"SOLIDWORKS ProgID missing");
            sw=Activator.CreateInstance(t) as SldWorks;Need(sw!=null,"SOLIDWORKS activation failed");created=true;sw.Visible=true;
            Need(typeof(SldWorks).Assembly.GetName().Version.Major==26,"requires SOLIDWORKS 2018 interop major 26");

            string oldRef=FindP007Reference(sw,drawCopy);Need(!String.IsNullOrWhiteSpace(oldRef),"P007 drawing reference not found");
            bool repl=sw.ReplaceReferencedDocument(drawCopy,oldRef,partCopy);Need(repl,"ReplaceReferencedDocument failed");
            log.Add("RELINK old="+oldRef+" new="+partCopy);

            int er=0,wr=0;
            doc=sw.OpenDoc6(drawCopy,(int)swDocumentTypes_e.swDocDRAWING,(int)swOpenDocOptions_e.swOpenDocOptions_Silent,"",ref er,ref wr) as ModelDoc2;
            Need(doc!=null,"open drawing failed e="+er+" w="+wr);
            DrawingDoc dr=doc as DrawingDoc;Need(dr!=null,"not drawing");

            List<View> views=ModelViews(dr,Path.GetFileName(partCopy));Need(views.Count>=3,"expected >=3 P007 model views; got "+views.Count);
            var targets=Targets();HashSet<string> have=ExistingTargets(dr,targets,log);
            Need(SelectView(doc,dr,views[0]),"cannot select P007 drawing view for model-item import");

            int types=(int)swInsertAnnotation_e.swInsertDimensionsMarkedForDrawing |
                      (int)swInsertAnnotation_e.swInsertDimensionsNotMarkedForDrawing;
            object raw=dr.InsertModelAnnotations3((int)swImportModelItemsSource_e.swImportModelItemsFromEntireModel,types,true,false,true,false);

            var kept=new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            int inserted=0,removed=0,nonDim=0;
            foreach(object x in Items(raw)){
                Annotation a=x as Annotation;if(a==null)continue;inserted++;
                DisplayDimension dd=null;try{dd=a.GetSpecificAnnotation() as DisplayDimension;}catch{}
                if(dd==null){nonDim++;continue;}
                Dimension d=null;try{d=dd.GetDimension2(0);}catch{}
                double mm=Mm(d);Target tg=Match(mm,targets);
                if(tg==null){
                    if(DeleteAnnotation(doc,a))removed++;
                    continue;
                }
                if(have.Contains(tg.id)||kept.Contains(tg.id)){
                    if(DeleteAnnotation(doc,a))removed++;
                    continue;
                }
                try{if(d!=null)d.Name=tg.dimName;}catch{}
                kept.Add(tg.id);
                string full="";try{full=d==null?"":d.FullName??"";}catch{}
                log.Add("KEEP "+tg.id+" mm="+mm.ToString("0.#####",CultureInfo.InvariantCulture)+" full="+One(full));
            }
            doc.ClearSelection2(true);doc.ForceRebuild3(false);
            SaveAs(doc,drawCopy);
            string pdf=Path.ChangeExtension(drawCopy,"PDF"),bmp=Path.ChangeExtension(drawCopy,"BMP");
            SaveAs(doc,pdf);doc.ViewZoomtofit2();bool bmpOk=doc.SaveBMP(bmp,1800,1273);
            string title=doc.GetTitle();sw.CloseDoc(title);doc=null;

            Need(Sha(drawing)==dsha,"source drawing changed");
            Need(Sha(part)==psha,"source part changed");
            Need(File.Exists(drawCopy)&&new FileInfo(drawCopy).Length>4096,"output drawing missing/small");
            Need(File.Exists(pdf)&&new FileInfo(pdf).Length>1024,"PDF missing/small");

            var coverage=new HashSet<string>(have,StringComparer.OrdinalIgnoreCase);
            foreach(string x in kept)coverage.Add(x);
            int coverageCount=coverage.Count;
            string status=coverageCount>=6?"PASS_D006_CORE_DIMS_V1__MANUAL_FINISH_REQUIRED":(coverageCount>=3?"PARTIAL_D006_CORE_DIMS_V1__MANUAL_FINISH_REQUIRED":"HOLD_D006_CORE_DIMS_V1_INSUFFICIENT_IMPORT");

            var sb=new StringBuilder();
            sb.AppendLine("STATUS="+status);
            sb.AppendLine("SOURCE_DRAWING="+drawing);
            sb.AppendLine("SOURCE_DRAWING_SHA256="+dsha);
            sb.AppendLine("SOURCE_PART="+part);
            sb.AppendLine("SOURCE_PART_SHA256="+psha);
            sb.AppendLine("OUTPUT_DRAWING="+drawCopy);
            sb.AppendLine("OUTPUT_PART_COPY="+partCopy);
            sb.AppendLine("OUTPUT_PDF="+pdf);
            sb.AppendLine("OUTPUT_BMP="+bmp);
            sb.AppendLine("BMP_OK="+bmpOk);
            sb.AppendLine("P007_MODEL_VIEWS="+views.Count);
            sb.AppendLine("IMPORTED_RAW_COUNT="+inserted);
            sb.AppendLine("FILTERED_REMOVED_COUNT="+removed);
            sb.AppendLine("NON_DIM_IMPORTED_COUNT="+nonDim);
            sb.AppendLine("PREEXISTING_TARGETS="+String.Join(",",new List<string>(have).ToArray()));
            sb.AppendLine("NEW_CORE_TARGETS="+String.Join(",",new List<string>(kept).ToArray()));
            sb.AppendLine("CORE_TARGET_COVERAGE_COUNT="+coverageCount);
            sb.AppendLine("CORE_TARGET_COVERAGE="+String.Join(",",new List<string>(coverage).ToArray()));
            sb.AppendLine("SOURCE_DRAWING_INVARIANT=True");
            sb.AppendLine("SOURCE_PART_INVARIANT=True");
            for(int i=0;i<log.Count;i++)sb.AppendLine("LOG_"+(i+1)+"="+One(log[i]));
            File.WriteAllText(report,sb.ToString(),Encoding.UTF8);

            Console.WriteLine("STATUS: "+status);
            Console.WriteLine("CORE TARGET COVERAGE: "+coverageCount+" / "+targets.Count);
            Console.WriteLine("PREEXISTING: "+String.Join(",",new List<string>(have).ToArray()));
            Console.WriteLine("NEW CORE DIMS: "+String.Join(",",new List<string>(kept).ToArray()));
            Console.WriteLine("RAW IMPORTED: "+inserted+"  FILTERED: "+removed);
            Console.WriteLine("DRAWING: "+drawCopy);
            Console.WriteLine("PDF: "+pdf);
            Console.WriteLine("REPORT: "+report);
            Console.WriteLine("NEXT: Open the populated candidate, correct layout/tolerance display, then add only remaining GPS/FCF items.");
            return status.StartsWith("HOLD_")?3:0;
        }catch(Exception ex){
            try{File.WriteAllText(report,"STATUS=HOLD_D006_CORE_DIMS_V1\nERROR="+ex.ToString()+"\n",Encoding.UTF8);}catch{}
            Console.Error.WriteLine(ex.ToString());return 2;
        }finally{
            try{if(doc!=null&&sw!=null)sw.CloseDoc(doc.GetTitle());}catch{}
            try{if(created&&sw!=null)sw.ExitApp();}catch{}
        }
    }
}
