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

public class K01D006D7VerifyV15
{
    static string Arg(string[] a,string k){for(int i=0;i<a.Length-1;i++)if(String.Equals(a[i],k,StringComparison.OrdinalIgnoreCase))return a[i+1];return null;}
    static void Need(bool ok,string m){if(!ok)throw new Exception(m);}
    static IEnumerable Items(object o){if(o==null)yield break;Array a=o as Array;if(a!=null){foreach(object x in a)yield return x;yield break;}IEnumerable e=o as IEnumerable;if(e!=null)foreach(object x in e)yield return x;}
    static bool Eq(string a,string b){return String.Equals(a??"",b??"",StringComparison.OrdinalIgnoreCase);}
    static bool Near(double a,double b,double t){return !Double.IsNaN(a)&&Math.Abs(a-b)<=t;}
    static string One(string s){return (s??"").Replace("\r"," ").Replace("\n"," ").Replace(";",",");}
    static string DxFeatureName(Annotation a){try{object f=a.GetDimXpertFeature();DimXpertFeature dx=f as DimXpertFeature;return dx==null?"":dx.Name;}catch{return "";}}
    static string DxName(Annotation a){try{return a.GetDimXpertName()??"";}catch{return "";}}
    static Dimension Dim(DisplayDimension d){try{return d==null?null:d.GetDimension2(0);}catch{return null;}}
    static DimensionTolerance Tol(Dimension d){try{return d==null?null:d.Tolerance as DimensionTolerance;}catch{return null;}}
    static double Mm(Dimension d){try{return d==null?Double.NaN:d.SystemValue*1000.0;}catch{return Double.NaN;}}
    static bool H7(DimensionTolerance t,out string hole,out string shaft,out string typ){hole="";shaft="";typ="";if(t==null)return false;try{typ=((swTolType_e)t.Type).ToString();}catch{typ=Convert.ToString(t.Type);}try{hole=t.GetHoleFitValue()??"";}catch{}try{shaft=t.GetShaftFitValue()??"";}catch{}return t.Type==(int)swTolType_e.swTolFIT&&Eq(hole,"H7")&&String.IsNullOrWhiteSpace(shaft);}
    static string RefModel(View v){try{return v.GetReferencedModelName()??"";}catch{return "";}}
    static string VName(View v){try{return v.GetName2()??"";}catch{return "";}}
    static bool Visible(Annotation a){try{return a!=null&&a.Visible==(int)swAnnotationVisibilityState_e.swAnnotationVisible;}catch{return false;}}
    static bool Dangling(Annotation a){try{return a!=null&&a.IsDangling();}catch{return false;}}
    static string NoteText(Annotation a){try{Note n=a.GetSpecificAnnotation() as Note;return n==null?"":n.GetText()??"";}catch{return "";}}
    static bool ContainsAny(string s,params string[] x){foreach(string q in x)if((s??"").IndexOf(q,StringComparison.OrdinalIgnoreCase)>=0)return true;return false;}
    static bool UseDocUnits(DisplayDimension dd){try{return dd.GetUseDocUnits();}catch{return true;}}
    static bool Override(DisplayDimension dd){try{return dd.GetOverride();}catch{return false;}}
    static double[] Dbl(object o){var z=new List<double>();foreach(object q in Items(o)){try{z.Add(Convert.ToDouble(q,CultureInfo.InvariantCulture));}catch{}}return z.ToArray();}
    static bool Overlap(double[] a,double[] b){if(a==null||b==null||a.Length<4||b.Length<4)return false;double ix=Math.Min(a[2],b[2])-Math.Max(a[0],b[0]);double iy=Math.Min(a[3],b[3])-Math.Max(a[1],b[1]);return ix>0&&iy>0;}

    class Rec{public string view="",kind="",feat="",name="",label="",text="";public bool visible=false,dx=false,dangling=false,h7=false,useDoc=true,over=false;public double mm=Double.NaN;public string tol="",hole="",shaft="";}

    public static int Main(string[] args){string drawing=Arg(args,"--drawing"),part=Arg(args,"--part"),report=Arg(args,"--report");SldWorks sw=null;ModelDoc2 doc=null,pm=null;bool created=false;var recs=new List<Rec>();try{Need(File.Exists(drawing),"drawing missing");Need(File.Exists(part),"part missing");try{sw=Marshal.GetActiveObject("SldWorks.Application") as SldWorks;}catch{}if(sw==null){Type t=Type.GetTypeFromProgID("SldWorks.Application");Need(t!=null,"SW ProgID missing");sw=Activator.CreateInstance(t) as SldWorks;Need(sw!=null,"SW activate failed");created=true;}sw.Visible=false;Need(typeof(SldWorks).Assembly.GetName().Version.Major==26,"requires SW2018 interop major 26");
        int pe=0,pw=0;pm=sw.OpenDoc6(part,(int)swDocumentTypes_e.swDocPART,(int)(swOpenDocOptions_e.swOpenDocOptions_Silent|swOpenDocOptions_e.swOpenDocOptions_ReadOnly),"",ref pe,ref pw) as ModelDoc2;Need(pm!=null,"open part failed");string cfg="";try{cfg=pm.ConfigurationManager.ActiveConfiguration.Name;}catch{}string mat="";try{PartDoc pd=pm as PartDoc;string db="";mat=pd==null?"":pd.GetMaterialPropertyName2(cfg,out db)??"";}catch{}bool material=ContainsAny(mat,"316","1.4404");sw.CloseDoc(pm.GetTitle());pm=null;
        int de=0,dw=0;doc=sw.OpenDoc6(drawing,(int)swDocumentTypes_e.swDocDRAWING,(int)(swOpenDocOptions_e.swOpenDocOptions_Silent|swOpenDocOptions_e.swOpenDocOptions_ReadOnly),"",ref de,ref dw) as ModelDoc2;Need(doc!=null,"open drawing failed e="+de+" w="+dw);DrawingDoc dr=doc as DrawingDoc;Need(dr!=null,"not drawing");
        bool mm=doc.LengthUnit==(int)swLengthUnit_e.swMM;int std=-1;try{std=doc.Extension.GetUserPreferenceInteger((int)swUserPreferenceIntegerValue_e.swDetailingDimensionStandard,(int)swUserPreferenceOption_e.swDetailingNoOptionSpecified);}catch{}bool iso=std==(int)swDetailingStandard_e.swDetailingStandardISO;
        Sheet sh=dr.GetCurrentSheet() as Sheet;double[] sp=null;try{sp=Dbl(sh.GetProperties2());}catch{}bool first=sp!=null&&sp.Length>=5&&Math.Abs(sp[4])>0.5;double swid=sp!=null&&sp.Length>=7?sp[5]:0,shgt=sp!=null&&sp.Length>=7?sp[6]:0;bool a3=(Near(swid,0.420,0.003)&&Near(shgt,0.297,0.003))||(Near(swid,0.297,0.003)&&Near(shgt,0.420,0.003));
        int pviews=0;var outlines=new List<Tuple<string,double[]>>();var scales=new List<string>();string allNotes="";
        int c01=0,c02=0,c05=0,otherDim=0,manualDim=0,dang=0,otherDatum=0,gtol=0,surf=0,overrideN=0,unitOverrideN=0,fallbackNotes=0;double c02mm=Double.NaN;
        View v=dr.GetFirstView() as View;if(v!=null)v=v.GetNextView() as View;
        while(v!=null){string rm=RefModel(v);bool p007=!String.IsNullOrWhiteSpace(rm)&&Eq(Path.GetFullPath(rm),Path.GetFullPath(part));if(p007){pviews++;double sc=0;try{sc=v.ScaleDecimal;}catch{}scales.Add(VName(v)+":"+sc.ToString("G17",CultureInfo.InvariantCulture));try{outlines.Add(Tuple.Create(VName(v),Dbl(v.GetOutline())));}catch{}
            foreach(object ao in Items(v.GetAnnotations())){Annotation a=ao as Annotation;if(a==null)continue;bool vis=Visible(a);int typ=-1;try{typ=a.GetType();}catch{}bool dl=Dangling(a);if(vis&&dl)dang++;
                if(typ==(int)swAnnotationType_e.swDisplayDimension){DisplayDimension dd=null;try{dd=a.GetSpecificAnnotation() as DisplayDimension;}catch{}Dimension d=Dim(dd);DimensionTolerance tt=Tol(d);string h="",s="",tn="";bool hh=H7(tt,out h,out s,out tn);double val=Mm(d);bool dx=false;try{dx=a.IsDimXpert();}catch{}if(!dx&&dd!=null){try{dx=dd.IsDimXpert();}catch{}}string f=DxFeatureName(a),n=DxName(a);bool is02=(Eq(f,"Cylinder1")&&Eq(n,"Diameter2")&&hh)||Near(val,14.10,0.005)&&hh;bool is05=(Eq(f,"Cylinder2")&&Eq(n,"Diameter4"))||Near(val,33.0,0.005);bool ov=dd!=null&&Override(dd);bool ud=dd==null?true:UseDocUnits(dd);if(vis){if(is02){c02++;c02mm=val;}else if(is05)c05++;else otherDim++;if(!dx)manualDim++;if(ov)overrideN++;if(!ud)unitOverrideN++;}
                    recs.Add(new Rec{view=VName(v),kind="DIM",feat=f,name=n,visible=vis,dx=dx,dangling=dl,h7=hh,useDoc=ud,over=ov,mm=val,tol=tn,hole=h,shaft=s});}
                else if(typ==(int)swAnnotationType_e.swDatumTag){DatumTag dt=null;try{dt=a.GetSpecificAnnotation() as DatumTag;}catch{}string lab="";try{lab=dt==null?"":dt.GetLabel()??"";}catch{}if(vis){if(Eq(lab,"A"))c01++;else otherDatum++;}recs.Add(new Rec{view=VName(v),kind="DATUM",label=lab,visible=vis,dangling=dl});}
                else if(typ==(int)swAnnotationType_e.swGTol){if(vis)gtol++;recs.Add(new Rec{view=VName(v),kind="GTOL",visible=vis,dangling=dl});}
                else if(typ==(int)swAnnotationType_e.swSFSymbol){if(vis)surf++;recs.Add(new Rec{view=VName(v),kind="SURFACE",visible=vis,dangling=dl});}
                else if(typ==(int)swAnnotationType_e.swNote){string tx=NoteText(a);if(vis){allNotes+="\n"+tx;if(ContainsAny(tx,"[C01]","[C02]","[C03]","[C04]","[C05]","[C06]","[C07]","[C08]","[C09]","[C10]","[C11]","[C12]","RELEASE TOL:"))fallbackNotes++;}recs.Add(new Rec{view=VName(v),kind="NOTE",text=One(tx),visible=vis,dangling=dl});}
            }
        }v=v.GetNextView() as View;}
        int ovlp=0;for(int i=0;i<outlines.Count;i++)for(int j=i+1;j<outlines.Count;j++)if(Overlap(outlines[i].Item2,outlines[j].Item2))ovlp++;
        bool generalTol=ContainsAny(allNotes,"ISO 2768","GENERAL TOLERANCE","GENERAL TOLERANCES");bool defaultRough=ContainsAny(allNotes,"DEFAULT ROUGHNESS","GENERAL ROUGHNESS");bool titleMaterial=ContainsAny(allNotes,"AISI 316L","1.4404");
        bool dqa1=c01==1&&c02==1;bool dqa2=c05==0&&otherDim==0&&otherDatum==0&&gtol==0&&surf==0&&fallbackNotes==0;bool dqa3=dang==0;bool dqa4=c01==1&&c02==1;bool dqa5=c02==1;bool dqa6=c01==1;bool dqa8=material;bool dqa10=manualDim==0&&overrideN==0;bool dqa13=!generalTol;bool dqa14=!defaultRough;bool dqa17=mm;bool dqa18=unitOverrideN==0;bool dqa19=Near(c02mm,14.10,0.005);bool dqa20=mm&&iso&&first&&a3;
        string status=(dqa1&&dqa2&&dqa3&&dqa4&&dqa5&&dqa6&&dqa8&&dqa10&&dqa13&&dqa14&&dqa17&&dqa18&&dqa19&&dqa20)?"PASS_D7_EXEMPLAR_SCOPE__RELEASE_D7_STILL_HOLD":"HOLD_D7_EXEMPLAR_SCOPE";
        var b=new StringBuilder();b.AppendLine("STATUS="+status);b.AppendLine("P007_VIEW_REFS="+pviews);b.AppendLine("C01_VISIBLE_COUNT="+c01);b.AppendLine("C02_VISIBLE_COUNT="+c02);b.AppendLine("C05_VISIBLE_UNAUTHORIZED_COUNT="+c05);b.AppendLine("OTHER_VISIBLE_DIM_COUNT="+otherDim);b.AppendLine("VISIBLE_NON_DIMXPERT_DIM_COUNT="+manualDim);b.AppendLine("VISIBLE_OTHER_DATUM_COUNT="+otherDatum);b.AppendLine("VISIBLE_GTOL_COUNT="+gtol);b.AppendLine("VISIBLE_SURFACE_COUNT="+surf);b.AppendLine("DANGLING_VISIBLE_COUNT="+dang);b.AppendLine("DISPLAY_OVERRIDE_COUNT="+overrideN);b.AppendLine("UNIT_OVERRIDE_COUNT="+unitOverrideN);b.AppendLine("FALLBACK_NOTE_COUNT="+fallbackNotes);b.AppendLine("DRAWING_MM="+mm);b.AppendLine("DETAILING_STANDARD_RAW="+std);b.AppendLine("DETAILING_STANDARD_ISO="+iso);b.AppendLine("FIRST_ANGLE="+first);b.AppendLine("SHEET_WIDTH_M="+swid.ToString("G17",CultureInfo.InvariantCulture));b.AppendLine("SHEET_HEIGHT_M="+shgt.ToString("G17",CultureInfo.InvariantCulture));b.AppendLine("SHEET_A3="+a3);b.AppendLine("MODEL_MATERIAL_RAW="+One(mat));b.AppendLine("MODEL_MATERIAL_CONTROLLED="+material);b.AppendLine("TITLE_TEXT_MATERIAL_FOUND="+titleMaterial);b.AppendLine("GENERAL_TOLERANCE_NOTE_FOUND="+generalTol);b.AppendLine("DEFAULT_ROUGHNESS_NOTE_FOUND="+defaultRough);b.AppendLine("VIEW_OVERLAP_PAIRS="+ovlp);b.AppendLine("VIEW_SCALES="+One(String.Join("|",scales.ToArray())));b.AppendLine("C02_MM="+(Double.IsNaN(c02mm)?"":c02mm.ToString("G17",CultureInfo.InvariantCulture)));
        b.AppendLine("DQA-001="+dqa1);b.AppendLine("DQA-002="+dqa2);b.AppendLine("DQA-003="+dqa3);b.AppendLine("DQA-004="+dqa4);b.AppendLine("DQA-005="+dqa5);b.AppendLine("DQA-006="+dqa6);b.AppendLine("DQA-008="+dqa8);b.AppendLine("DQA-010="+dqa10);b.AppendLine("DQA-013="+dqa13);b.AppendLine("DQA-014="+dqa14);b.AppendLine("DQA-017="+dqa17);b.AppendLine("DQA-018="+dqa18);b.AppendLine("DQA-019="+dqa19);b.AppendLine("DQA-020="+dqa20);foreach(var r in recs)b.AppendLine("REC=VIEW="+One(r.view)+"|KIND="+r.kind+"|VIS="+r.visible+"|DX="+r.dx+"|DANGLING="+r.dangling+"|F="+One(r.feat)+"|N="+One(r.name)+"|LABEL="+One(r.label)+"|MM="+(Double.IsNaN(r.mm)?"":r.mm.ToString("G17",CultureInfo.InvariantCulture))+"|H7="+r.h7+"|USEDOC="+r.useDoc+"|OVERRIDE="+r.over+"|TEXT="+One(r.text));File.WriteAllText(report,b.ToString(),Encoding.UTF8);
        Console.WriteLine("STATUS: "+status);Console.WriteLine("AUTHORIZED: C01="+c01+" C02="+c02);Console.WriteLine("UNAUTHORIZED: C05="+c05+" other_dims="+otherDim+" other_datums="+otherDatum+" gtol="+gtol+" surface="+surf+" fallback_notes="+fallbackNotes);Console.WriteLine("DANGLING: "+dang+" MANUAL_DIMS: "+manualDim+" OVERRIDES: "+overrideN+" UNIT_OVERRIDES: "+unitOverrideN);Console.WriteLine("ENV: MM="+mm+" ISO="+iso+" FIRST_ANGLE="+first+" A3="+a3+" overlaps="+ovlp);Console.WriteLine("MATERIAL MODEL: "+material+" raw="+mat+" title_text_found="+titleMaterial);return status.StartsWith("PASS_")?0:3;
    }catch(Exception ex){try{File.WriteAllText(report,"STATUS=HOLD_D7_ERROR\nERROR="+ex.ToString()+"\n",Encoding.UTF8);}catch{}Console.Error.WriteLine(ex.ToString());return 2;}finally{try{if(doc!=null&&sw!=null)sw.CloseDoc(doc.GetTitle());}catch{}try{if(pm!=null&&sw!=null)sw.CloseDoc(pm.GetTitle());}catch{}try{if(created&&sw!=null)sw.ExitApp();}catch{}}}
}
