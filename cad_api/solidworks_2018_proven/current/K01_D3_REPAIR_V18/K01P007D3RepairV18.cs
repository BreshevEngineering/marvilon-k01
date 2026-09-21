using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using SolidWorks.Interop.sldworks;
using SolidWorks.Interop.swconst;
using SolidWorks.Interop.swdimxpert;

public class K01P007D3RepairV18
{
    static string Arg(string[] a,string k){for(int i=0;i<a.Length-1;i++)if(String.Equals(a[i],k,StringComparison.OrdinalIgnoreCase))return a[i+1];return null;}
    static void Need(bool ok,string m){if(!ok)throw new Exception(m);}
    static bool Eq(string a,string b){return String.Equals(a??"",b??"",StringComparison.OrdinalIgnoreCase);}
    static bool Near(double a,double b,double t){return !Double.IsNaN(a)&&!Double.IsNaN(b)&&Math.Abs(a-b)<=t;}
    static IEnumerable Items(object o){if(o==null)yield break;Array a=o as Array;if(a!=null){foreach(object x in a)yield return x;yield break;}IEnumerable e=o as IEnumerable;if(e!=null)foreach(object x in e)yield return x;}
    static double[] Dbl(object o){var x=new List<double>();foreach(object q in Items(o)){try{x.Add(Convert.ToDouble(q,CultureInfo.InvariantCulture));}catch{}}return x.ToArray();}
    static string F(double x){return Double.IsNaN(x)?"":x.ToString("G17",CultureInfo.InvariantCulture);}
    static string One(string s){return (s??"").Replace("\r"," ").Replace("\n"," ").Replace("=","-");}

    class FaceSig {
        public string surface="";
        public double area=Double.NaN;
        public double planeX=Double.NaN;
        public string Canon(){return surface+"|A="+F(area)+"|PXmm="+F(Double.IsNaN(planeX)?Double.NaN:planeX*1000.0);}
    }

    static FaceSig Sig(Face2 f){
        var r=new FaceSig();
        if(f==null)return r;
        try{r.area=Convert.ToDouble(f.GetArea(),CultureInfo.InvariantCulture);}catch{}
        try{
            Surface s=f.IGetSurface();
            if(s!=null&&s.IsPlane()){
                r.surface="plane";
                double[] p=Dbl(s.PlaneParams);
                if(p.Length>=6&&Math.Abs(p[0])>0.999999)r.planeX=p[3];
            } else r.surface="other";
        }catch{r.surface="unknown";}
        return r;
    }

    static List<Face2> AllFaces(ModelDoc2 m){
        var z=new List<Face2>();PartDoc p=m as PartDoc;if(p==null)return z;
        foreach(object bo in Items(p.GetBodies2((int)swBodyType_e.swSolidBody,true))){
            Body2 b=bo as Body2;if(b==null)continue;
            foreach(object fo in Items(b.GetFaces())){Face2 f=fo as Face2;if(f!=null)z.Add(f);}
        }
        return z;
    }

    static Face2 FindTargetFace(ModelDoc2 m,double pxMm,double area){
        var hits=new List<Face2>();
        foreach(Face2 f in AllFaces(m)){
            FaceSig s=Sig(f);
            if(s.surface=="plane" && Near(s.planeX*1000.0,pxMm,0.002) && Near(s.area,area,2e-9)) hits.Add(f);
        }
        Need(hits.Count==1,"controlled C01 member signature resolved to "+hits.Count+" faces");
        return hits[0];
    }

    static string DxFeatureName(Annotation a){try{DimXpertFeature dx=a.GetDimXpertFeature() as DimXpertFeature;return dx==null?"":dx.Name??"";}catch{return "";}}
    static string DxName(Annotation a){try{return a.GetDimXpertName()??"";}catch{return "";}}
    static Annotation FindC02(ModelDoc2 m){
        foreach(object ao in Items(m.Extension.GetAnnotations())){
            Annotation a=ao as Annotation;
            if(a!=null&&Eq(DxFeatureName(a),"Cylinder1")&&Eq(DxName(a),"Diameter2"))return a;
        }
        return null;
    }

    static Annotation FindDatumA(ModelDoc2 m){
        foreach(object ao in Items(m.Extension.GetAnnotations())){
            Annotation a=ao as Annotation;if(a==null)continue;
            int t=-1;try{t=a.GetType();}catch{}
            if(t!=(int)swAnnotationType_e.swDatumTag)continue;
            DatumTag dt=null;try{dt=a.GetSpecificAnnotation() as DatumTag;}catch{}
            string lab="";try{lab=dt==null?"":dt.GetLabel()??"";}catch{}
            if(Eq(lab,"A"))return a;
        }
        return null;
    }

    static AnnotationView FindAnnotationView(ModelDoc2 m,string wanted){
        try{
            foreach(object vo in Items(m.Extension.AnnotationViews)){
                AnnotationView av=vo as AnnotationView;if(av==null)continue;
                Feature f=vo as Feature;string n=f==null?"":f.Name??"";
                if(Eq(n,wanted))return av;
            }
        }catch{}
        return null;
    }

    static string AnnotationViewName(Annotation a){
        if(a==null)return "";
        try{
            AnnotationView av=a.AnnotationView as AnnotationView;
            Feature f=av as Feature;
            if(f!=null)return f.Name??"";
        }catch{}
        return "";
    }

    static List<Face2> AttachedFaces(Annotation a){
        var z=new List<Face2>();if(a==null)return z;
        try{foreach(object o in Items(a.GetAttachedEntities3())){Face2 f=o as Face2;if(f!=null)z.Add(f);}}catch{}
        return z;
    }

    static bool DeleteAnnotation(ModelDoc2 m,Annotation a){
        if(a==null)return false;
        m.ClearSelection2(true);
        bool sel=false;try{sel=a.Select3(false,null);}catch{}
        if(!sel)return false;
        bool ok=false;try{ok=m.Extension.DeleteSelection2((int)swDeleteSelectionOptions_e.swDelete_Absorbed);}catch{}
        m.ClearSelection2(true);
        return ok;
    }

    static double[] Pos(Annotation a){
        try{
            object o=a.GetPosition();
            return Dbl(o);
        }catch{return new double[0];}
    }

    static void RestorePos(Annotation a,double[] p){
        if(a==null||p==null||p.Length<3)return;
        try{a.SetPosition(p[0],p[1],p[2]);}catch{}
    }

    static bool MoveOne(AnnotationView av,Annotation a){
        if(av==null||a==null)return false;
        try{return av.MoveAnnotations(new Annotation[]{a});}catch{return false;}
    }

    static bool AttachedToTarget(Annotation a,double pxMm,double area,out string sig){
        sig="";
        var fs=AttachedFaces(a);
        if(fs.Count!=1)return false;
        FaceSig s=Sig(fs[0]);sig=s.Canon();
        return s.surface=="plane" && Near(s.planeX*1000.0,pxMm,0.002) && Near(s.area,area,2e-9);
    }

    public static int Main(string[] args){
        string mode=Arg(args,"--mode");
        string part=Arg(args,"--part");
        string report=Arg(args,"--report");
        string viewName=Arg(args,"--view")??"*Front";
        double pxMm=Double.Parse(Arg(args,"--plane-x-mm"),CultureInfo.InvariantCulture);
        double area=Double.Parse(Arg(args,"--area-m2"),CultureInfo.InvariantCulture);

        SldWorks sw=null;ModelDoc2 m=null;bool created=false;
        try{
            Need(Eq(mode,"preflight")||Eq(mode,"apply"),"mode must be preflight/apply");
            Need(File.Exists(part),"part missing");
            try{sw=Marshal.GetActiveObject("SldWorks.Application") as SldWorks;}catch{}
            Need(sw==null,"SolidWorks must be closed before V18 repair");
            Type t=Type.GetTypeFromProgID("SldWorks.Application");Need(t!=null,"SldWorks ProgID missing");
            sw=Activator.CreateInstance(t) as SldWorks;Need(sw!=null,"SW activate failed");created=true;sw.Visible=false;
            Need(typeof(SldWorks).Assembly.GetName().Version.Major==26,"requires SW2018 interop major 26");

            int oe=0,ow=0;
            int opts=(int)swOpenDocOptions_e.swOpenDocOptions_Silent;
            if(Eq(mode,"preflight"))opts|=(int)swOpenDocOptions_e.swOpenDocOptions_ReadOnly;
            m=sw.OpenDoc6(part,(int)swDocumentTypes_e.swDocPART,opts,"",ref oe,ref ow) as ModelDoc2;
            Need(m!=null,"open part failed e="+oe+" w="+ow);

            Face2 target=FindTargetFace(m,pxMm,area);
            FaceSig targetSig=Sig(target);
            Annotation datum=FindDatumA(m);Need(datum!=null,"Datum A missing");
            Annotation c02=FindC02(m);Need(c02!=null,"C02 Cylinder1/Diameter2 missing");

            string beforeDatumView=AnnotationViewName(datum);
            string beforeC02View=AnnotationViewName(c02);

            var sb=new StringBuilder();
            sb.AppendLine("MODE="+mode);
            sb.AppendLine("TARGET_FACE_SIG="+targetSig.Canon());
            sb.AppendLine("ANNOTATION_VIEW_RELOCATION=SKIPPED_FOR_EXEMPLAR");
            sb.AppendLine("BEFORE_C01_VIEW="+beforeDatumView);
            sb.AppendLine("BEFORE_C02_VIEW="+beforeC02View);
            sb.AppendLine("FACE_SELECTION_API=Face2->Entity->IEntity.Select4");

            if(Eq(mode,"preflight")){
                sb.Insert(0,"STATUS=PASS_D3_REPAIR_V18_PREFLIGHT\n");
                Directory.CreateDirectory(Path.GetDirectoryName(report));
                File.WriteAllText(report,sb.ToString(),Encoding.UTF8);
                Console.WriteLine("STATUS: PASS_D3_REPAIR_V18_PREFLIGHT");
                Console.WriteLine("TARGET FACE: "+targetSig.Canon());
                Console.WriteLine("ANNOTATION VIEW RELOCATION: SKIPPED_FOR_EXEMPLAR");
                Console.WriteLine("C01 CURRENT VIEW: "+beforeDatumView);
                Console.WriteLine("C02 CURRENT VIEW: "+beforeC02View);
                Console.WriteLine("REPORT: "+report);
                return 0;
            }

            double[] oldPos=Pos(datum);
            Need(DeleteAnnotation(m,datum),"failed to delete old Datum A annotation");
            m.ClearSelection2(true);
            Entity targetEntity=target as Entity;
            Need(targetEntity!=null,"controlled C01 member Face2 -> Entity cast failed");
            bool selected=false;try{selected=targetEntity.Select4(false,null);}catch{}
            Need(selected,"failed to select controlled C01 member face through IEntity.Select4");
            SelectionMgr sm=m.SelectionManager as SelectionMgr;
            Need(sm!=null,"SelectionMgr missing after controlled C01 face selection");
            int selectedCount=sm.GetSelectedObjectCount2(-1);
            int selectedType=selectedCount>0?sm.GetSelectedObjectType3(selectedCount,-1):-1;
            Need(selectedCount==1,"controlled C01 selection count="+selectedCount+" expected=1");
            Need(selectedType==(int)swSelectType_e.swSelFACES,
                 "controlled C01 selected type="+selectedType+" expected=swSelFACES");
            DatumTag ndt=m.IInsertDatumTag2();
            Need(ndt!=null,"IInsertDatumTag2 returned null");
            Need(ndt.SetLabel("A"),"failed to set Datum label A");
            Annotation newDatum=null;try{newDatum=ndt.GetAnnotation() as Annotation;}catch{}
            Need(newDatum!=null,"new Datum A annotation readback failed");
            RestorePos(newDatum,oldPos);

            // Exemplar recovery scope is deliberately limited to C01 identity.
            // Annotation-view role mismatches are preserved as explicit release limitations.
            m.ForceRebuild3(false);
            int se=0,swarn=0;
            bool saved=m.Save3((int)swSaveAsOptions_e.swSaveAsOptions_Silent,ref se,ref swarn);
            Need(saved&&se==0,"save failed e="+se+" w="+swarn);
            string title=m.GetTitle();sw.CloseDoc(title);m=null;

            int re=0,rw=0;
            m=sw.OpenDoc6(part,(int)swDocumentTypes_e.swDocPART,(int)swOpenDocOptions_e.swOpenDocOptions_Silent,"",ref re,ref rw) as ModelDoc2;
            Need(m!=null,"reopen failed e="+re+" w="+rw);
            Annotation rd=FindDatumA(m);Need(rd!=null,"Datum A missing after reopen");
            Annotation rc=FindC02(m);Need(rc!=null,"C02 missing after reopen");
            string attachedSig="";
            bool datumTarget=AttachedToTarget(rd,pxMm,area,out attachedSig);
            string afterDatumView=AnnotationViewName(rd);
            string afterC02View=AnnotationViewName(rc);
            Need(datumTarget,"Datum A is not attached to selected controlled C01 authority member after reopen: "+attachedSig);

            sb.AppendLine("AFTER_C01_FACE_SIG="+attachedSig);
            sb.AppendLine("AFTER_C01_VIEW="+afterDatumView);
            sb.AppendLine("AFTER_C02_VIEW="+afterC02View);
            sb.AppendLine("ANNOTATION_VIEW_RELOCATION=SKIPPED_FOR_EXEMPLAR");
            sb.AppendLine("SAVE_ERROR="+se);
            sb.AppendLine("SAVE_WARNING="+swarn);
            sb.Insert(0,"STATUS=PASS_D3_REPAIR_V18_APPLY\n");

            Directory.CreateDirectory(Path.GetDirectoryName(report));
            File.WriteAllText(report,sb.ToString(),Encoding.UTF8);
            Console.WriteLine("STATUS: PASS_D3_REPAIR_V18_APPLY");
            Console.WriteLine("C01: "+attachedSig+" view="+afterDatumView);
            Console.WriteLine("ANNOTATION VIEW RELOCATION: SKIPPED_FOR_EXEMPLAR");
            Console.WriteLine("C02 VIEW PRESERVED: "+afterC02View);
            Console.WriteLine("REPORT: "+report);
            return 0;
        }
        catch(Exception ex){
            try{
                Directory.CreateDirectory(Path.GetDirectoryName(report));
                File.WriteAllText(report,"STATUS=HOLD_D3_REPAIR_V18\nERROR="+One(ex.ToString())+"\n",Encoding.UTF8);
            }catch{}
            Console.Error.WriteLine("STATUS: HOLD_D3_REPAIR_V18");
            Console.Error.WriteLine(ex.ToString());
            return 3;
        }
        finally{
            try{if(m!=null&&sw!=null)sw.CloseDoc(m.GetTitle());}catch{}
            try{if(created&&sw!=null)sw.ExitApp();}catch{}
        }
    }
}
