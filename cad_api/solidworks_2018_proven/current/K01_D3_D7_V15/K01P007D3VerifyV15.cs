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
using SolidWorks.Interop.swdimxpert;

public class K01P007D3VerifyV15
{
    static string Arg(string[] a,string k){for(int i=0;i<a.Length-1;i++)if(String.Equals(a[i],k,StringComparison.OrdinalIgnoreCase))return a[i+1];return null;}
    static void Need(bool ok,string m){if(!ok)throw new Exception(m);}
    static IEnumerable Items(object o){if(o==null)yield break;Array a=o as Array;if(a!=null){foreach(object x in a)yield return x;yield break;}IEnumerable e=o as IEnumerable;if(e!=null)foreach(object x in e)yield return x;}
    static bool Eq(string a,string b){return String.Equals(a??"",b??"",StringComparison.OrdinalIgnoreCase);}
    static bool Near(double a,double b,double t){return !Double.IsNaN(a)&&Math.Abs(a-b)<=t;}
    static string Sha(string p){using(var h=SHA256.Create())using(var f=new FileStream(p,FileMode.Open,FileAccess.Read,FileShare.ReadWrite|FileShare.Delete))return BitConverter.ToString(h.ComputeHash(f)).Replace("-","").ToLowerInvariant();}
    static double[] Dbl(object o){var x=new List<double>();foreach(object q in Items(o)){try{x.Add(Convert.ToDouble(q,CultureInfo.InvariantCulture));}catch{}}return x.ToArray();}
    static string F(double x){return Double.IsNaN(x)?"":x.ToString("G17",CultureInfo.InvariantCulture);}
    static string One(string s){return (s??"").Replace("\r"," ").Replace("\n"," ").Replace(";",",");}
    static string DxFeatureName(Annotation a){try{object f=a.GetDimXpertFeature();DimXpertFeature dx=f as DimXpertFeature;return dx==null?"":dx.Name;}catch{return "";}}
    static string DxName(Annotation a){try{return a.GetDimXpertName()??"";}catch{return "";}}
    static DisplayDimension Dd(Annotation a){try{return a==null?null:a.GetSpecificAnnotation() as DisplayDimension;}catch{return null;}}
    static Dimension Dim(DisplayDimension d){try{return d==null?null:d.GetDimension2(0);}catch{return null;}}
    static DimensionTolerance Tol(Dimension d){try{return d==null?null:d.Tolerance as DimensionTolerance;}catch{return null;}}
    static double SystemMm(Dimension d){try{return d==null?Double.NaN:d.SystemValue*1000.0;}catch{return Double.NaN;}}
    static bool H7(DimensionTolerance t,out string hole,out string shaft,out string typ){hole="";shaft="";typ="";if(t==null)return false;try{typ=((swTolType_e)t.Type).ToString();}catch{typ=Convert.ToString(t.Type);}try{hole=t.GetHoleFitValue()??"";}catch{}try{shaft=t.GetShaftFitValue()??"";}catch{}return t.Type==(int)swTolType_e.swTolFIT&&Eq(hole,"H7")&&String.IsNullOrWhiteSpace(shaft);}
    static string AnnName(Annotation a){try{return a==null?"":a.GetName()??"";}catch{return "";}}

    class FaceSig{
        public string surface=""; public double area=0; public double radius=Double.NaN; public double axisX=Double.NaN; public double centerYZ=Double.NaN; public double planeX=Double.NaN;
        public string Canon(){return surface+"|A="+F(area)+"|Rmm="+F(Double.IsNaN(radius)?Double.NaN:radius*1000.0)+"|AX="+F(axisX)+"|CYZmm="+F(Double.IsNaN(centerYZ)?Double.NaN:centerYZ*1000.0)+"|PXmm="+F(Double.IsNaN(planeX)?Double.NaN:planeX*1000.0);}
    }
    static FaceSig Sig(Face2 f){var r=new FaceSig();if(f==null)return r;try{r.area=Convert.ToDouble(f.GetArea(),CultureInfo.InvariantCulture);}catch{}try{Surface s=f.IGetSurface();if(s.IsPlane()){r.surface="plane";double[] p=Dbl(s.PlaneParams);if(p.Length>=6&&Math.Abs(p[0])>0.999999)r.planeX=p[3];}else if(s.IsCylinder()){r.surface="cylinder";double[] c=Dbl(s.CylinderParams);if(c.Length>=7){r.radius=Math.Abs(c[6]);r.axisX=Math.Abs(c[3]);r.centerYZ=Math.Sqrt(c[1]*c[1]+c[2]*c[2]);}}else if(s.IsCone())r.surface="cone";else if(s.IsSphere())r.surface="sphere";else r.surface="other";}catch{r.surface="unknown";}return r;}
    static List<FaceSig> AllFaceSigs(ModelDoc2 m){var z=new List<FaceSig>();PartDoc p=m as PartDoc;if(p==null)return z;foreach(object bo in Items(p.GetBodies2((int)swBodyType_e.swSolidBody,true))){Body2 b=bo as Body2;if(b==null)continue;foreach(object fo in Items(b.GetFaces())){Face2 f=fo as Face2;if(f!=null)z.Add(Sig(f));}}return z;}
    static double MinAxialPlaneX(ModelDoc2 m){double mn=Double.MaxValue;foreach(var s in AllFaceSigs(m))if(s.surface=="plane"&&!Double.IsNaN(s.planeX))mn=Math.Min(mn,s.planeX);return mn==Double.MaxValue?Double.NaN:mn;}
    static string GeometryFingerprint(ModelDoc2 m){var a=new List<string>();foreach(var s in AllFaceSigs(m))a.Add(s.Canon());a.Sort(StringComparer.Ordinal);using(var h=SHA256.Create()){byte[] b=h.ComputeHash(Encoding.UTF8.GetBytes(String.Join("\n",a.ToArray())));return BitConverter.ToString(b).Replace("-","").ToLowerInvariant();}}

    static string AnnotationViewName(ModelDoc2 m,Annotation target){
        if(target==null)return "";string tn=AnnName(target),tdx=DxName(target),tf=DxFeatureName(target);
        try{
            object raw=m.Extension.AnnotationViews;
            foreach(object vo in Items(raw)){
                AnnotationView av=vo as AnnotationView;if(av==null)continue;string name="";try{Feature vf=vo as Feature;if(vf!=null)name=vf.Name??"";}catch{}
                foreach(object ao in Items(av.GetAnnotations2(false,true))){Annotation a=ao as Annotation;if(a==null)continue;bool same=!String.IsNullOrWhiteSpace(tn)&&Eq(AnnName(a),tn);if(!same&&!String.IsNullOrWhiteSpace(tdx))same=Eq(DxName(a),tdx)&&Eq(DxFeatureName(a),tf);if(same)return name;}
            }
        }catch{}
        try{AnnotationView av=target.AnnotationView as AnnotationView;if(av!=null){Feature f=av as Feature;if(f!=null)return f.Name??"";}}catch{}
        return "";
    }

    static Annotation FindC02(ModelDoc2 m){foreach(object ao in Items(m.Extension.GetAnnotations())){Annotation a=ao as Annotation;if(a!=null&&Eq(DxFeatureName(a),"Cylinder1")&&Eq(DxName(a),"Diameter2"))return a;}return null;}
    static Annotation FindDatumA(ModelDoc2 m){foreach(object ao in Items(m.Extension.GetAnnotations())){Annotation a=ao as Annotation;if(a==null)continue;int t=-1;try{t=a.GetType();}catch{}if(t!=(int)swAnnotationType_e.swDatumTag)continue;DatumTag dt=null;try{dt=a.GetSpecificAnnotation() as DatumTag;}catch{}string lab="";try{lab=dt==null?"":dt.GetLabel()??"";}catch{}if(Eq(lab,"A"))return a;}return null;}
    static List<Face2> AttachedFaces(Annotation a){var z=new List<Face2>();if(a==null)return z;try{foreach(object o in Items(a.GetAttachedEntities3())){Face2 f=o as Face2;if(f!=null)z.Add(f);}}catch{}return z;}
    static List<Face2> DxFaces(Annotation a){var z=new List<Face2>();try{DimXpertFeature dx=a.GetDimXpertFeature() as DimXpertFeature;if(dx!=null)foreach(object o in Items(dx.GetFaces())){Face2 f=o as Face2;if(f!=null)z.Add(f);}}catch{}return z;}

    class Snap{
        public bool c02=false,c01=false,c02H7=false,c02Geom=false,c01Geom=false; public string c02View="",c01View="",c02Feat="",c02Ann="",c02Tol="",hole="",shaft="",c02Face="",c01Face="",geomFp="",material=""; public double c02Mm=Double.NaN; public int c02FaceCount=0,c01FaceCount=0;
        public string Core(){return "C01="+c01+"|C01V="+c01View+"|C01F="+c01Face+"|C02="+c02+"|C02V="+c02View+"|C02F="+c02Face+"|C02H7="+c02H7+"|C02MM="+F(c02Mm)+"|GEOM="+geomFp+"|MAT="+material;}
    }
    static Snap Snapshot(ModelDoc2 m){var s=new Snap();s.geomFp=GeometryFingerprint(m);string cfg="";try{cfg=m.ConfigurationManager.ActiveConfiguration.Name;}catch{}try{PartDoc p=m as PartDoc;string db="";s.material=p==null?"":p.GetMaterialPropertyName2(cfg,out db)??"";}catch{}
        Annotation c02=FindC02(m);if(c02!=null){s.c02=true;s.c02Feat=DxFeatureName(c02);s.c02Ann=DxName(c02);s.c02View=AnnotationViewName(m,c02);DisplayDimension dd=Dd(c02);Dimension d=Dim(dd);DimensionTolerance t=Tol(d);s.c02Mm=SystemMm(d);s.c02H7=H7(t,out s.hole,out s.shaft,out s.c02Tol);var fs=DxFaces(c02);s.c02FaceCount=fs.Count;if(fs.Count==1){FaceSig g=Sig(fs[0]);s.c02Face=g.Canon();s.c02Geom=g.surface=="cylinder"&&Near(g.radius,0.00705,0.000002)&&g.axisX>0.999999&&Near(g.centerYZ,0,0.00001);}}
        Annotation c01=FindDatumA(m);if(c01!=null){s.c01=true;s.c01View=AnnotationViewName(m,c01);var fs=AttachedFaces(c01);s.c01FaceCount=fs.Count;double xmin=MinAxialPlaneX(m);if(fs.Count==1){FaceSig g=Sig(fs[0]);s.c01Face=g.Canon();s.c01Geom=g.surface=="plane"&&!Double.IsNaN(g.planeX)&&!Double.IsNaN(xmin)&&Near(g.planeX,xmin,0.0000005);}}
        return s;}
    static void Emit(StringBuilder b,string p,Snap s){b.AppendLine(p+"_C01="+s.c01);b.AppendLine(p+"_C01_VIEW="+One(s.c01View));b.AppendLine(p+"_C01_FACE_COUNT="+s.c01FaceCount);b.AppendLine(p+"_C01_GEOM="+s.c01Geom);b.AppendLine(p+"_C01_FACE_SIG="+One(s.c01Face));b.AppendLine(p+"_C02="+s.c02);b.AppendLine(p+"_C02_FEATURE="+One(s.c02Feat));b.AppendLine(p+"_C02_ANNOTATION="+One(s.c02Ann));b.AppendLine(p+"_C02_VIEW="+One(s.c02View));b.AppendLine(p+"_C02_MM="+F(s.c02Mm));b.AppendLine(p+"_C02_H7="+s.c02H7);b.AppendLine(p+"_C02_TOLTYPE="+One(s.c02Tol));b.AppendLine(p+"_C02_HOLE="+One(s.hole));b.AppendLine(p+"_C02_SHAFT="+One(s.shaft));b.AppendLine(p+"_C02_FACE_COUNT="+s.c02FaceCount);b.AppendLine(p+"_C02_GEOM="+s.c02Geom);b.AppendLine(p+"_C02_FACE_SIG="+One(s.c02Face));b.AppendLine(p+"_GEOM_FP="+s.geomFp);b.AppendLine(p+"_MATERIAL="+One(s.material));}

    public static int Main(string[] args){string part=Arg(args,"--part"),report=Arg(args,"--report");SldWorks sw=null;ModelDoc2 m=null;bool created=false;try{Need(File.Exists(part),"part missing");string before=Sha(part);try{sw=Marshal.GetActiveObject("SldWorks.Application") as SldWorks;}catch{}if(sw==null){Type t=Type.GetTypeFromProgID("SldWorks.Application");Need(t!=null,"SldWorks ProgID missing");sw=Activator.CreateInstance(t) as SldWorks;Need(sw!=null,"SW activate failed");created=true;}sw.Visible=false;Need(typeof(SldWorks).Assembly.GetName().Version.Major==26,"requires SW2018 interop major 26");
        Func<ModelDoc2> open=()=>{int e=0,w=0;ModelDoc2 d=sw.OpenDoc6(part,(int)swDocumentTypes_e.swDocPART,(int)(swOpenDocOptions_e.swOpenDocOptions_Silent|swOpenDocOptions_e.swOpenDocOptions_ReadOnly),"",ref e,ref w) as ModelDoc2;Need(d!=null,"open part failed e="+e+" w="+w);return d;};
        m=open();Snap s0=Snapshot(m);sw.CloseDoc(m.GetTitle());m=null; // L1 close/reopen
        m=open();Snap s1=Snapshot(m);bool l1=s0.Core()==s1.Core();bool rb=false;try{rb=m.ForceRebuild3(false);}catch{}Snap s2=Snapshot(m);bool l2=rb&&s1.Core()==s2.Core();
        sw.CloseDoc(m.GetTitle());m=null;string after=Sha(part);bool invariant=Eq(before,after);bool material=s2.material.IndexOf("316",StringComparison.OrdinalIgnoreCase)>=0||s2.material.IndexOf("1.4404",StringComparison.OrdinalIgnoreCase)>=0;bool c02=s2.c02&&s2.c02H7&&Near(s2.c02Mm,14.10,0.005)&&s2.c02Geom&&!String.IsNullOrWhiteSpace(s2.c02View);bool c01=s2.c01&&s2.c01Geom&&!String.IsNullOrWhiteSpace(s2.c01View);string status=(c01&&c02&&material&&l1&&l2&&invariant)?"PASS_D3_EXEMPLAR_L1_L2__L3_RECIPE_REQUIRED":"HOLD_D3_EXEMPLAR";
        var b=new StringBuilder();b.AppendLine("STATUS="+status);b.AppendLine("SOURCE_SHA_INVARIANT="+invariant);b.AppendLine("L1_SAVE_REOPEN="+l1);b.AppendLine("L2_FORCE_REBUILD="+l2);b.AppendLine("L3_PERTURB_RESTORE=NOT_RUN_NO_QUALIFIED_RECIPE");b.AppendLine("C01_PASS="+c01);b.AppendLine("C02_PASS="+c02);b.AppendLine("C09_MATERIAL_PASS="+material);Emit(b,"S0",s0);Emit(b,"S1",s1);Emit(b,"S2",s2);File.WriteAllText(report,b.ToString(),Encoding.UTF8);
        Console.WriteLine("STATUS: "+status);Console.WriteLine("C01 DATUM A: "+c01+" view="+s2.c01View+" face="+s2.c01Face);Console.WriteLine("C02: "+c02+" "+s2.c02Feat+"/"+s2.c02Ann+" view="+s2.c02View+" mm="+F(s2.c02Mm)+" "+s2.c02Tol+" hole="+s2.hole);Console.WriteLine("MATERIAL: "+material+" raw="+s2.material);Console.WriteLine("L1: "+l1+" L2: "+l2+" L3: PENDING_RECIPE");Console.WriteLine("SOURCE SHA INVARIANT: "+invariant);return status.StartsWith("PASS_")?0:3;
    }catch(Exception ex){try{File.WriteAllText(report,"STATUS=HOLD_D3_ERROR\nERROR="+ex.ToString()+"\n",Encoding.UTF8);}catch{}Console.Error.WriteLine(ex.ToString());return 2;}finally{try{if(m!=null&&sw!=null)sw.CloseDoc(m.GetTitle());}catch{}try{if(created&&sw!=null)sw.ExitApp();}catch{}}}
}
