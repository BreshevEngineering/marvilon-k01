using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using SolidWorks.Interop.sldworks;
using SolidWorks.Interop.swconst;
using SolidWorks.Interop.swdimxpert;

public class K01D006ExemplarScanV12
{
    static void Need(bool ok,string msg){if(!ok)throw new Exception(msg);}
    static string Arg(string[] a,string k){for(int i=0;i<a.Length-1;i++)if(a[i]==k)return a[i+1];return null;}
    static IEnumerable Items(object o){if(o==null)yield break;Array a=o as Array;if(a!=null){foreach(object x in a)yield return x;yield break;}IEnumerable e=o as IEnumerable;if(e!=null)foreach(object x in e)yield return x;}
    static bool Eq(string a,string b){return String.Equals(a??"",b??"",StringComparison.OrdinalIgnoreCase);}
    static string DxFeatureName(Annotation a){if(a==null)return "";try{object f=a.GetDimXpertFeature();DimXpertFeature dx=f as DimXpertFeature;return dx==null?"":dx.Name;}catch{return "";}}
    static string DxName(Annotation a){if(a==null)return "";try{return a.GetDimXpertName()??"";}catch{return "";}}
    static bool IsDx(Annotation a,DisplayDimension dd){try{if(a!=null&&a.IsDimXpert())return true;}catch{}try{if(dd!=null&&dd.IsDimXpert())return true;}catch{}return false;}
    static Dimension DimFrom(DisplayDimension dd){try{return dd==null?null:dd.GetDimension2(0);}catch{return null;}}
    static DimensionTolerance TolFrom(Dimension d){try{return d==null?null:d.Tolerance as DimensionTolerance;}catch{return null;}}
    static DimensionTolerance TolFrom(Annotation a){if(a==null)return null;try{DisplayDimension dd=a.GetSpecificAnnotation() as DisplayDimension;return TolFrom(DimFrom(dd));}catch{return null;}}
    static Annotation FindDx(ModelDoc2 m,string feat,string name){foreach(object ao in Items(m.Extension.GetAnnotations())){Annotation a=ao as Annotation;if(a!=null&&Eq(DxFeatureName(a),feat)&&Eq(DxName(a),name))return a;}return null;}
    static string RefModel(View v){try{return v.GetReferencedModelName()??"";}catch{return "";}}
    static string ViewName(View v){try{return v.GetName2()??"";}catch{return "";}}
    static string DimName(Dimension d){try{return d==null?"":d.Name??"";}catch{return "";}}
    static string DimFullName(Dimension d){try{return d==null?"":d.FullName??"";}catch{return "";}}
    static double SystemMm(Dimension d){try{return d==null?Double.NaN:d.SystemValue*1000.0;}catch{return Double.NaN;}}
    static bool H7NoShaft(DimensionTolerance t,out string hole,out string shaft,out string typ){hole="";shaft="";typ="";if(t==null)return false;try{typ=((swTolType_e)t.Type).ToString();}catch{typ=Convert.ToString(t.Type);}try{hole=t.GetHoleFitValue()??"";}catch{}try{shaft=t.GetShaftFitValue()??"";}catch{}return t.Type==(int)swTolType_e.swTolFIT&&Eq(hole,"H7")&&String.IsNullOrWhiteSpace(shaft);}
    static bool Near(double a,double b,double tol){return !Double.IsNaN(a)&&Math.Abs(a-b)<=tol;}

    public static int Main(string[] args)
    {
        string drawing=Arg(args,"--drawing"),part=Arg(args,"--part"),report=Arg(args,"--report");
        SldWorks sw=null;ModelDoc2 doc=null;bool created=false;var rows=new List<string>();
        try
        {
            Need(File.Exists(drawing),"drawing missing");Need(File.Exists(part),"part missing");
            try{sw=Marshal.GetActiveObject("SldWorks.Application") as SldWorks;}catch{}
            if(sw==null){Type t=Type.GetTypeFromProgID("SldWorks.Application");Need(t!=null,"SW ProgID missing");sw=Activator.CreateInstance(t) as SldWorks;Need(sw!=null,"SW activation failed");created=true;}
            sw.Visible=false;Need(typeof(SldWorks).Assembly.GetName().Version.Major==26,"requires SW2018 interop major 26");

            int pe=0,pw=0;
            doc=sw.OpenDoc6(part,(int)swDocumentTypes_e.swDocPART,(int)(swOpenDocOptions_e.swOpenDocOptions_Silent|swOpenDocOptions_e.swOpenDocOptions_ReadOnly),"",ref pe,ref pw) as ModelDoc2;
            Need(doc!=null,"open part failed e="+pe+" w="+pw);
            Annotation a02=FindDx(doc,"Cylinder1","Diameter2");
            bool c02Model=false;string c02Type="",hole="",shaft="";
            if(a02!=null){DimensionTolerance t=TolFrom(a02);c02Model=H7NoShaft(t,out hole,out shaft,out c02Type);}
            Annotation a05=FindDx(doc,"Cylinder2","Diameter4");
            bool c05Safe=false;string c05Type="";
            if(a05!=null){DimensionTolerance t=TolFrom(a05);if(t!=null){try{c05Type=((swTolType_e)t.Type).ToString();}catch{c05Type=Convert.ToString(t.Type);}c05Safe=t.Type==(int)swTolType_e.swTolNONE;}}
            sw.CloseDoc(doc.GetTitle());doc=null;

            int de=0,dw=0;
            doc=sw.OpenDoc6(drawing,(int)swDocumentTypes_e.swDocDRAWING,(int)(swOpenDocOptions_e.swOpenDocOptions_Silent|swOpenDocOptions_e.swOpenDocOptions_ReadOnly),"",ref de,ref dw) as ModelDoc2;
            Need(doc!=null,"open drawing failed e="+de+" w="+dw);DrawingDoc dr=doc as DrawingDoc;Need(dr!=null,"not drawing");

            int lengthUnit=doc.LengthUnit;bool drawingMm=lengthUnit==(int)swLengthUnit_e.swMM;
            int refs=0,displayCount=0,dxFlagCount=0,datumCount=0;
            bool c02Drawing=false,c01DatumA=false;string c02View="",c02Evidence="",datumView="";
            View v=dr.GetFirstView() as View;if(v!=null)v=v.GetNextView() as View;
            while(v!=null)
            {
                string rm=RefModel(v);bool p007=!String.IsNullOrWhiteSpace(rm)&&Eq(Path.GetFullPath(rm),Path.GetFullPath(part));
                if(p007)
                {
                    refs++;
                    foreach(object ddo in Items(v.GetDisplayDimensions()))
                    {
                        DisplayDimension dd=ddo as DisplayDimension;if(dd==null)continue;displayCount++;
                        Annotation a=null;try{a=dd.GetAnnotation() as Annotation;}catch{}
                        bool isDx=IsDx(a,dd);if(isDx)dxFlagCount++;
                        string f=DxFeatureName(a),n=DxName(a);Dimension d=DimFrom(dd);DimensionTolerance t=TolFrom(d);
                        string th="",ts="",tt="";bool h7=H7NoShaft(t,out th,out ts,out tt);double mm=SystemMm(d);
                        string dn=DimName(d),df=DimFullName(d);
                        rows.Add("DISPLAY;VIEW="+ViewName(v)+";IS_DX="+isDx+";F="+f+";N="+n+";DIM="+dn+";FULL="+df+";MM="+(Double.IsNaN(mm)?"":mm.ToString("R"))+";TOL="+tt+";HOLE="+th+";SHAFT="+ts);
                        bool strong=Eq(f,"Cylinder1")&&Eq(n,"Diameter2")&&h7;
                        bool linkedSemanticFallback=Near(mm,14.10,0.005)&&h7;
                        if(!c02Drawing&&(strong||linkedSemanticFallback))
                        {
                            c02Drawing=true;c02View=ViewName(v);c02Evidence=strong?"DIMXPERT_IDENTITY":"LINKED_MODEL_DISPLAY_DIMENSION_SEMANTIC_FALLBACK";
                        }
                    }
                    foreach(object dto in Items(v.GetDatumTags()))
                    {
                        DatumTag dt=dto as DatumTag;if(dt==null)continue;datumCount++;string label="";try{label=dt.GetLabel()??"";}catch{}
                        rows.Add("DATUM;VIEW="+ViewName(v)+";LABEL="+label);
                        if(!c01DatumA&&Eq(label,"A")){c01DatumA=true;datumView=ViewName(v);}
                    }
                }
                v=v.GetNextView() as View;
            }

            string pdf=Path.ChangeExtension(drawing,"PDF"),bmp=Path.ChangeExtension(drawing,"BMP");int ee=0,ew=0;
            bool pdfOk=doc.Extension.SaveAs(pdf,(int)swSaveAsVersion_e.swSaveAsCurrentVersion,(int)swSaveAsOptions_e.swSaveAsOptions_Silent,null,ref ee,ref ew);
            doc.ViewZoomtofit2();bool bmpOk=doc.SaveBMP(bmp,1800,1273);
            string status=(c02Model&&c02Drawing&&c01DatumA&&refs>0&&drawingMm)?"PASS_EXEMPLAR_NATIVE_C01_C02_CAPTURED":"HOLD_EXEMPLAR_NATIVE_C01_C02_OR_LINK_ENV_MISSING";
            var sb=new StringBuilder();
            sb.AppendLine("STATUS="+status);
            sb.AppendLine("C02_MODEL_H7="+c02Model);sb.AppendLine("C02_MODEL_TOLTYPE="+c02Type);sb.AppendLine("C02_MODEL_HOLE_FIT="+hole);sb.AppendLine("C02_MODEL_SHAFT_FIT="+shaft);
            sb.AppendLine("C05_MODEL_NONE="+c05Safe);sb.AppendLine("C05_MODEL_TOLTYPE="+c05Type);
            sb.AppendLine("P007_VIEW_REFS="+refs);sb.AppendLine("DRAWING_DISPLAY_DIM_COUNT="+displayCount);sb.AppendLine("DRAWING_DIMXPERT_FLAG_COUNT="+dxFlagCount);sb.AppendLine("DRAWING_DATUM_COUNT="+datumCount);
            sb.AppendLine("DRAWING_LENGTH_UNIT="+lengthUnit);sb.AppendLine("DRAWING_LENGTH_UNIT_MM="+drawingMm);
            sb.AppendLine("C01_DRAWING_DATUM_A="+c01DatumA);sb.AppendLine("C01_DRAWING_VIEW="+datumView);
            sb.AppendLine("C02_DRAWING_H7="+c02Drawing);sb.AppendLine("C02_DRAWING_VIEW="+c02View);sb.AppendLine("C02_DRAWING_EVIDENCE_MODE="+c02Evidence);
            sb.AppendLine("PDF="+pdf);sb.AppendLine("PDF_OK="+pdfOk);sb.AppendLine("BMP="+bmp);sb.AppendLine("BMP_OK="+bmpOk);
            foreach(string x in rows)sb.AppendLine("SCAN="+x);
            File.WriteAllText(report,sb.ToString(),Encoding.UTF8);
            Console.WriteLine("STATUS: "+status);
            Console.WriteLine("C01 DRAWING DATUM A: "+c01DatumA+" view="+datumView);
            Console.WriteLine("C02 MODEL H7: "+c02Model+" type="+c02Type+" hole="+hole);
            Console.WriteLine("C02 DRAWING H7: "+c02Drawing+" view="+c02View+" evidence="+c02Evidence);
            Console.WriteLine("P007 VIEW REFS: "+refs);
            Console.WriteLine("DRAWING DISPLAY DIM COUNT: "+displayCount+" DIMXPERT FLAG COUNT: "+dxFlagCount+" DATUM COUNT: "+datumCount);
            Console.WriteLine("DRAWING LENGTH UNIT: "+((swLengthUnit_e)lengthUnit).ToString()+" mm_ok="+drawingMm);
            Console.WriteLine("PDF: "+pdf+" refreshed="+pdfOk);Console.WriteLine("BMP: "+bmp+" refreshed="+bmpOk);
            return status.StartsWith("PASS_")?0:3;
        }
        catch(Exception ex){try{File.WriteAllText(report,"STATUS=HOLD_EXEMPLAR_SCAN_ERROR\nERROR="+ex.ToString()+"\n",Encoding.UTF8);}catch{}Console.Error.WriteLine(ex.ToString());return 2;}
        finally{try{if(doc!=null&&sw!=null)sw.CloseDoc(doc.GetTitle());}catch{}try{if(created&&sw!=null)sw.ExitApp();}catch{}}
    }
}
