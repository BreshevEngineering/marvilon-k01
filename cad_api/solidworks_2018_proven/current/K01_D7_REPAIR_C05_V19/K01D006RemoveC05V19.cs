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

public class K01D006RemoveC05V19
{
    static string Arg(string[] a,string k){for(int i=0;i<a.Length-1;i++)if(String.Equals(a[i],k,StringComparison.OrdinalIgnoreCase))return a[i+1];return null;}
    static void Need(bool ok,string m){if(!ok)throw new Exception(m);}
    static IEnumerable Items(object o){if(o==null)yield break;Array a=o as Array;if(a!=null){foreach(object x in a)yield return x;yield break;}IEnumerable e=o as IEnumerable;if(e!=null)foreach(object x in e)yield return x;}
    static bool Eq(string a,string b){return String.Equals(a??"",b??"",StringComparison.OrdinalIgnoreCase);}
    static bool Near(double a,double b,double t){return !Double.IsNaN(a)&&Math.Abs(a-b)<=t;}
    static string DxFeatureName(Annotation a){try{object f=a.GetDimXpertFeature();DimXpertFeature dx=f as DimXpertFeature;return dx==null?"":dx.Name;}catch{return "";}}
    static string DxName(Annotation a){try{return a.GetDimXpertName()??"";}catch{return "";}}
    static Dimension Dim(DisplayDimension d){try{return d==null?null:d.GetDimension2(0);}catch{return null;}}
    static DimensionTolerance Tol(Dimension d){try{return d==null?null:d.Tolerance as DimensionTolerance;}catch{return null;}}
    static double Mm(Dimension d){try{return d==null?Double.NaN:d.SystemValue*1000.0;}catch{return Double.NaN;}}
    static bool H7(DimensionTolerance t,out string hole,out string shaft,out string typ){hole="";shaft="";typ="";if(t==null)return false;try{typ=((swTolType_e)t.Type).ToString();}catch{typ=Convert.ToString(t.Type);}try{hole=t.GetHoleFitValue()??"";}catch{}try{shaft=t.GetShaftFitValue()??"";}catch{}return t.Type==(int)swTolType_e.swTolFIT&&Eq(hole,"H7")&&String.IsNullOrWhiteSpace(shaft);}
    static string RefModel(View v){try{return v.GetReferencedModelName()??"";}catch{return "";}}
    static string VName(View v){try{return v.GetName2()??"";}catch{return "";}}
    static bool Visible(Annotation a){try{return a!=null&&a.Visible==(int)swAnnotationVisibilityState_e.swAnnotationVisible;}catch{return false;}}

    static bool DeleteAnnotation(ModelDoc2 doc,Annotation a)
    {
        try
        {
            doc.ClearSelection2(true);
            SelectionMgr sm=doc.SelectionManager as SelectionMgr;
            if(sm==null)return false;
            SelectData sd=sm.CreateSelectData() as SelectData;
            if(sd==null)return false;
            if(!a.Select3(false,sd))return false;
            return doc.Extension.DeleteSelection2((int)swDeleteSelectionOptions_e.swDelete_Absorbed);
        }
        catch{return false;}
    }

    class Scan
    {
        public int pviews=0,c01=0,c02=0,c05=0,otherDim=0;
        public List<Annotation> c05Annotations=new List<Annotation>();
        public List<string> rows=new List<string>();
    }

    static Scan ScanDrawing(DrawingDoc dr,string part)
    {
        var r=new Scan();
        View v=dr.GetFirstView() as View;
        if(v!=null)v=v.GetNextView() as View; // skip sheet
        while(v!=null)
        {
            string rm=RefModel(v);
            bool p007=!String.IsNullOrWhiteSpace(rm)&&Eq(Path.GetFullPath(rm),Path.GetFullPath(part));
            if(p007)
            {
                r.pviews++;
                foreach(object ao in Items(v.GetAnnotations()))
                {
                    Annotation a=ao as Annotation;if(a==null||!Visible(a))continue;
                    int typ=-1;try{typ=a.GetType();}catch{}
                    if(typ==(int)swAnnotationType_e.swDisplayDimension)
                    {
                        DisplayDimension dd=null;try{dd=a.GetSpecificAnnotation() as DisplayDimension;}catch{}
                        Dimension d=Dim(dd);DimensionTolerance tt=Tol(d);
                        string h="",s="",tn="";bool hh=H7(tt,out h,out s,out tn);double val=Mm(d);
                        string f=DxFeatureName(a),n=DxName(a);
                        bool is02=(Eq(f,"Cylinder1")&&Eq(n,"Diameter2")&&hh)||(Near(val,14.10,0.005)&&hh);
                        bool is05=(Eq(f,"Cylinder2")&&Eq(n,"Diameter4"))||Near(val,33.0,0.005);
                        if(is02)r.c02++;
                        else if(is05){r.c05++;r.c05Annotations.Add(a);}
                        else r.otherDim++;
                        r.rows.Add("DIM;VIEW="+VName(v)+";F="+f+";N="+n+";MM="+(Double.IsNaN(val)?"":val.ToString("G17",CultureInfo.InvariantCulture))+";H7="+hh+";C02="+is02+";C05="+is05);
                    }
                    else if(typ==(int)swAnnotationType_e.swDatumTag)
                    {
                        DatumTag dt=null;try{dt=a.GetSpecificAnnotation() as DatumTag;}catch{}
                        string lab="";try{lab=dt==null?"":dt.GetLabel()??"";}catch{}
                        if(Eq(lab,"A"))r.c01++;
                        r.rows.Add("DATUM;VIEW="+VName(v)+";LABEL="+lab);
                    }
                }
            }
            v=v.GetNextView() as View;
        }
        return r;
    }

    public static int Main(string[] args)
    {
        string drawing=Arg(args,"--drawing"),part=Arg(args,"--part"),report=Arg(args,"--report");
        SldWorks sw=null;ModelDoc2 doc=null;bool created=false;
        try
        {
            Need(File.Exists(drawing),"drawing missing");
            Need(File.Exists(part),"part missing");

            try{sw=Marshal.GetActiveObject("SldWorks.Application") as SldWorks;}catch{}
            Need(sw==null,"SolidWorks must be closed before V19 drawing repair");

            Type t=Type.GetTypeFromProgID("SldWorks.Application");
            Need(t!=null,"SldWorks ProgID missing");
            sw=Activator.CreateInstance(t) as SldWorks;
            Need(sw!=null,"SW activate failed");
            created=true;sw.Visible=false;
            Need(typeof(SldWorks).Assembly.GetName().Version.Major==26,"requires SW2018 interop major 26");

            int de=0,dw=0;
            doc=sw.OpenDoc6(drawing,(int)swDocumentTypes_e.swDocDRAWING,(int)swOpenDocOptions_e.swOpenDocOptions_Silent,"",ref de,ref dw) as ModelDoc2;
            Need(doc!=null,"open drawing failed e="+de+" w="+dw);
            DrawingDoc dr=doc as DrawingDoc;Need(dr!=null,"not drawing");

            Scan before=ScanDrawing(dr,part);
            Need(before.pviews>0,"no P007 drawing views");
            Need(before.c01==1,"expected exactly one visible Datum A before repair, got "+before.c01);
            Need(before.c02==1,"expected exactly one visible C02 before repair, got "+before.c02);
            Need(before.c05==1,"expected exactly one visible C05 before repair, got "+before.c05);
            Need(before.otherDim==0,"unexpected other visible dimensions before repair: "+before.otherDim);
            Need(before.c05Annotations.Count==1,"C05 annotation candidate count="+before.c05Annotations.Count);

            Need(DeleteAnnotation(doc,before.c05Annotations[0]),"failed to delete the single unauthorized C05 drawing annotation");

            doc.ForceRebuild3(false);
            int se=0,swarn=0;
            bool saved=doc.Save3((int)swSaveAsOptions_e.swSaveAsOptions_Silent,ref se,ref swarn);
            Need(saved&&se==0,"save failed e="+se+" w="+swarn);

            string title=doc.GetTitle();
            sw.CloseDoc(title);doc=null;

            int re=0,rw=0;
            doc=sw.OpenDoc6(drawing,(int)swDocumentTypes_e.swDocDRAWING,(int)(swOpenDocOptions_e.swOpenDocOptions_Silent|swOpenDocOptions_e.swOpenDocOptions_ReadOnly),"",ref re,ref rw) as ModelDoc2;
            Need(doc!=null,"reopen drawing failed e="+re+" w="+rw);
            dr=doc as DrawingDoc;Need(dr!=null,"reopened document is not drawing");

            Scan after=ScanDrawing(dr,part);
            Need(after.c01==1,"Datum A count changed after repair: "+after.c01);
            Need(after.c02==1,"C02 count changed after repair: "+after.c02);
            Need(after.c05==0,"C05 still visible after repair: "+after.c05);
            Need(after.otherDim==0,"other visible dimensions after repair: "+after.otherDim);

            var sb=new StringBuilder();
            sb.AppendLine("STATUS=PASS_D7_REPAIR_C05_V19_APPLY");
            sb.AppendLine("P007_VIEW_REFS_BEFORE="+before.pviews);
            sb.AppendLine("C01_BEFORE="+before.c01);
            sb.AppendLine("C02_BEFORE="+before.c02);
            sb.AppendLine("C05_BEFORE="+before.c05);
            sb.AppendLine("OTHER_DIM_BEFORE="+before.otherDim);
            sb.AppendLine("C01_AFTER="+after.c01);
            sb.AppendLine("C02_AFTER="+after.c02);
            sb.AppendLine("C05_AFTER="+after.c05);
            sb.AppendLine("OTHER_DIM_AFTER="+after.otherDim);
            sb.AppendLine("SAVE_ERROR="+se);
            sb.AppendLine("SAVE_WARNING="+swarn);
            foreach(string x in before.rows)sb.AppendLine("BEFORE="+x);
            foreach(string x in after.rows)sb.AppendLine("AFTER="+x);
            Directory.CreateDirectory(Path.GetDirectoryName(report));
            File.WriteAllText(report,sb.ToString(),Encoding.UTF8);

            Console.WriteLine("STATUS: PASS_D7_REPAIR_C05_V19_APPLY");
            Console.WriteLine("BEFORE: C01="+before.c01+" C02="+before.c02+" C05="+before.c05+" other_dims="+before.otherDim);
            Console.WriteLine("AFTER: C01="+after.c01+" C02="+after.c02+" C05="+after.c05+" other_dims="+after.otherDim);
            Console.WriteLine("REPORT: "+report);
            return 0;
        }
        catch(Exception ex)
        {
            try
            {
                Directory.CreateDirectory(Path.GetDirectoryName(report));
                File.WriteAllText(report,"STATUS=HOLD_D7_REPAIR_C05_V19\nERROR="+ex.ToString().Replace("\r"," ").Replace("\n"," ")+"\n",Encoding.UTF8);
            }catch{}
            Console.Error.WriteLine("STATUS: HOLD_D7_REPAIR_C05_V19");
            Console.Error.WriteLine(ex.ToString());
            return 3;
        }
        finally
        {
            try{if(doc!=null&&sw!=null)sw.CloseDoc(doc.GetTitle());}catch{}
            try{if(created&&sw!=null)sw.ExitApp();}catch{}
        }
    }
}
