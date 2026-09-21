using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using SolidWorks.Interop.sldworks;
using SolidWorks.Interop.swconst;

public class K01D006TwoViewV1
{
    static string Arg(string[] a,string k){for(int i=0;i<a.Length-1;i++)if(a[i]==k)return a[i+1];return null;}
    static void Need(bool ok,string msg){if(!ok)throw new Exception(msg);}
    static bool Eq(string a,string b){return String.Equals(a??"",b??"",StringComparison.OrdinalIgnoreCase);}
    static IEnumerable Items(object o){if(o==null)yield break;Array a=o as Array;if(a!=null){foreach(object x in a)yield return x;yield break;}IEnumerable e=o as IEnumerable;if(e!=null)foreach(object x in e)yield return x;}
    static string Sha(string p){using(FileStream fs=new FileStream(p,FileMode.Open,FileAccess.Read,FileShare.ReadWrite|FileShare.Delete))using(SHA256 h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(fs)).Replace("-","").ToLowerInvariant();}
    static string One(string s){return (s??"").Replace("\r"," ").Replace("\n"," ").Replace("=","-");}
    static double D(string s){double v;return Double.TryParse(s,NumberStyles.Float,CultureInfo.InvariantCulture,out v)?v:Double.NaN;}
    static Dictionary<string,string> Manifest(string p){var d=new Dictionary<string,string>(StringComparer.OrdinalIgnoreCase);foreach(string raw in File.ReadAllLines(p,Encoding.UTF8)){if(String.IsNullOrWhiteSpace(raw))continue;string[] x=raw.Split(new char[]{'\t'},2);if(x.Length==2)d[x[0].Trim()]=x[1].Trim();}return d;}
    static string M(Dictionary<string,string> m,string k){string v;Need(m.TryGetValue(k,out v),"manifest key missing: "+k);return v;}
    static double MD(Dictionary<string,string> m,string k){double v=D(M(m,k));Need(!Double.IsNaN(v),"manifest numeric key invalid: "+k);return v;}

    static string VName(View v){try{return v.GetName2()??"";}catch{return "";}}
    static string VOrient(View v){try{return v.GetOrientationName()??"";}catch{return "";}}
    static string VRef(View v){try{return v.GetReferencedModelName()??"";}catch{return "";}}
    static double[] DA(object o){var z=new List<double>();foreach(object q in Items(o))try{z.Add(Convert.ToDouble(q,CultureInfo.InvariantCulture));}catch{}return z.ToArray();}
    static double[] Outline(View v){try{return DA(v.GetOutline());}catch{return new double[0];}}
    static void SetView(View v,double x,double y,double scale){try{v.PositionLocked=false;}catch{}try{v.UseSheetScale=0;}catch{}try{v.UseParentScale=false;}catch{}try{v.ScaleDecimal=scale;}catch{}try{v.Position=new double[]{x,y};}catch{}}

    class VRec{public View v;public string name,orient,refModel;public bool section;public double aspect;}
    static List<VRec> ModelViews(DrawingDoc dr,string partBase){var r=new List<VRec>();View v=dr.GetFirstView() as View;if(v!=null)v=v.GetNextView() as View;while(v!=null){string rm=VRef(v);if(!String.IsNullOrWhiteSpace(rm)&&Eq(Path.GetFileName(rm),partBase)){double[] b=Outline(v);double w=b.Length>=4?Math.Abs(b[2]-b[0]):0,h=b.Length>=4?Math.Abs(b[3]-b[1]):0;string n=VName(v),o=VOrient(v);r.Add(new VRec{v=v,name=n,orient=o,refModel=rm,section=n.IndexOf("SECTION",StringComparison.OrdinalIgnoreCase)>=0||n.IndexOf("A-A",StringComparison.OrdinalIgnoreCase)>=0||n.IndexOf("B-B",StringComparison.OrdinalIgnoreCase)>=0,aspect=h>1e-9?w/h:999});}v=v.GetNextView() as View;}return r;}

    static string FindP007Reference(SldWorks sw,string drawing){object deps=null;try{deps=sw.GetDocumentDependencies2(drawing,true,true,false);}catch{}foreach(object q in Items(deps)){string s=Convert.ToString(q)??"";if(File.Exists(s)&&s.EndsWith(".SLDPRT",StringComparison.OrdinalIgnoreCase)&&Path.GetFileName(s).IndexOf("K01-P-007",StringComparison.OrdinalIgnoreCase)>=0)return s;}return "";}
    static bool SaveAs(ModelDoc2 doc,string p){int e=0,w=0;bool ok=doc.Extension.SaveAs(p,(int)swSaveAsVersion_e.swSaveAsCurrentVersion,(int)swSaveAsOptions_e.swSaveAsOptions_Silent,null,ref e,ref w);if(!ok||e!=0)throw new Exception("SaveAs failed "+p+" e="+e+" w="+w);return true;}

    static Surface Surf(Face2 f){try{return f.IGetSurface();}catch{return null;}}
    static double PlaneX(Face2 f){Surface s=Surf(f);if(s==null||!s.IsPlane())return Double.NaN;double[] p=DA(s.PlaneParams);return p.Length>=6?p[3]:Double.NaN;}
    static double CylRadiusMm(Face2 f){Surface s=Surf(f);if(s==null||!s.IsCylinder())return Double.NaN;double[] p=DA(s.CylinderParams);return p.Length>=7?p[6]*1000.0:Double.NaN;}
    static double Area(Face2 f){try{return f.GetArea();}catch{return 0;}}
    static List<Face2> Faces(ModelDoc2 part){var r=new List<Face2>();PartDoc pd=part as PartDoc;if(pd==null)return r;foreach(object bo in Items(pd.GetBodies2((int)swBodyType_e.swSolidBody,true))){Body2 b=bo as Body2;if(b==null)continue;foreach(object fo in Items(b.GetFaces())){Face2 f=fo as Face2;if(f!=null)r.Add(f);}}return r;}
    static Face2 FindCylinder(List<Face2> fs,double diaMm){Face2 best=null;double e0=1e9;foreach(Face2 f in fs){double r=CylRadiusMm(f);if(Double.IsNaN(r))continue;double e=Math.Abs(2*r-diaMm);if(e<e0){e0=e;best=f;}}return e0<=0.02?best:null;}
    static List<Face2> FindCylinders(List<Face2> fs,double diaMm){var r=new List<Face2>();foreach(Face2 f in fs){double rr=CylRadiusMm(f);if(!Double.IsNaN(rr)&&Math.Abs(2*rr-diaMm)<=0.02)r.Add(f);}return r;}
    static Face2 FindPlane(List<Face2> fs,double xMm,bool largest){Face2 best=null;double e0=1e9,a0=-1;foreach(Face2 f in fs){double x=PlaneX(f);if(Double.IsNaN(x))continue;double e=Math.Abs(x*1000.0-xMm),a=Area(f);if(e<e0-1e-6||(Math.Abs(e-e0)<=1e-6&&largest&&a>a0)){e0=e;a0=a;best=f;}}return e0<=0.03?best:null;}
    static List<Face2> FindPlanes(List<Face2> fs,double xMm){var r=new List<Face2>();foreach(Face2 f in fs){double x=PlaneX(f);if(!Double.IsNaN(x)&&Math.Abs(x*1000.0-xMm)<=0.03)r.Add(f);}r.Sort(delegate(Face2 a,Face2 b){return Area(b).CompareTo(Area(a));});return r;}
    static void PlaneExtents(List<Face2> fs,out double minMm,out double maxMm){minMm=1e99;maxMm=-1e99;foreach(Face2 f in fs){double x=PlaneX(f);if(Double.IsNaN(x))continue;double mm=x*1000.0;if(mm<minMm)minMm=mm;if(mm>maxMm)maxMm=mm;}Need(minMm<1e90&&maxMm>-1e90,"plane extents unavailable");}

    static bool SelectInView(View v,object modelEntity,bool append){if(v==null||modelEntity==null)return false;try{Entity ce=v.GetCorrespondingEntity(modelEntity) as Entity;if(ce!=null&&ce.Select4(append,null))return true;}catch{}try{return v.SelectEntity(modelEntity,append);}catch{return false;}}
    static double UserMm(DisplayDimension dd,ModelDoc2 doc){try{Dimension d=dd.GetDimension2(0);return d==null?Double.NaN:d.IGetUserValueIn2(doc);}catch{return Double.NaN;}}
    static void NameDim(DisplayDimension dd,string name){try{Dimension d=dd.GetDimension2(0);if(d!=null)d.Name=name;}catch{}}
    static Annotation Ann(DisplayDimension dd){try{return dd==null?null:dd.GetAnnotation() as Annotation;}catch{return null;}}
    static void Hide(Annotation a){try{if(a!=null)a.Visible=(int)swAnnotationVisibilityState_e.swAnnotationHidden;}catch{}}
    static void HideOldControlledAnnotations(View v,List<string> log){int n=0;foreach(object ao in Items(v.GetAnnotations())){Annotation a=ao as Annotation;if(a==null)continue;int t=-1;try{t=a.GetType();}catch{}if(t==(int)swAnnotationType_e.swDisplayDimension||t==(int)swAnnotationType_e.swDatumTag||t==(int)swAnnotationType_e.swGTol||t==(int)swAnnotationType_e.swSFSymbol){Hide(a);n++;}}log.Add("HIDE_OLD view="+VName(v)+" count="+n);}

    static bool SetFit(DisplayDimension dd,string hole,string shaft){try{Dimension d=dd.GetDimension2(0);DimensionTolerance t=d==null?null:d.Tolerance as DimensionTolerance;if(t==null)return false;t.Type=(int)swTolType_e.swTolFIT;return t.SetFitValues(hole??"",shaft??"");}catch{return false;}}
    static bool SetSymTol(DisplayDimension dd,double tolMm){try{Dimension d=dd.GetDimension2(0);DimensionTolerance t=d==null?null:d.Tolerance as DimensionTolerance;if(t==null)return false;t.Type=(int)swTolType_e.swTolSYMMETRIC;return t.SetValues2(-tolMm/1000.0,tolMm/1000.0,2,null);}catch{return false;}}
    static void SetSuffix(DisplayDimension dd,string s){try{dd.SetText((int)swDimensionTextParts_e.swDimensionTextSuffix,s);}catch{}}
    static void SetPrefix(DisplayDimension dd,string s){try{dd.SetText((int)swDimensionTextParts_e.swDimensionTextPrefix,s);}catch{}}

    static DisplayDimension TryDiameter(ModelDoc2 doc,View v,Face2 face,double expectedMm,double x,double y,string name,List<string> log){if(face==null){log.Add("DIM "+name+" face=MISSING");return null;}var c=new List<object>();foreach(object eo in Items(face.GetEdges()))if(eo is Entity)c.Add(eo);c.Add(face);foreach(object q in c){doc.ClearSelection2(true);if(!SelectInView(v,q,false))continue;DisplayDimension dd=null;try{dd=doc.AddDiameterDimension2(x,y,0) as DisplayDimension;}catch(Exception ex){log.Add("DIM "+name+" add_err="+ex.GetType().Name);}if(dd==null)continue;double mm=UserMm(dd,doc);if(!Double.IsNaN(mm)&&Math.Abs(Math.Abs(mm)-expectedMm)>0.03){Hide(Ann(dd));log.Add("DIM "+name+" wrong="+mm.ToString("0.#####",CultureInfo.InvariantCulture));continue;}NameDim(dd,name);log.Add("DIM "+name+" OK mm="+(Double.IsNaN(mm)?"NaN":mm.ToString("0.#####",CultureInfo.InvariantCulture)));doc.ClearSelection2(true);return dd;}log.Add("DIM "+name+" FAILED");return null;}
    static DisplayDimension TryLinear(ModelDoc2 doc,View v,Face2 a,Face2 b,double expectedMm,double x,double y,string name,List<string> log){if(a==null||b==null){log.Add("DIM "+name+" plane=MISSING");return null;}for(int mode=1;mode<=2;mode++){doc.ClearSelection2(true);if(!SelectInView(v,a,false)||!SelectInView(v,b,true)){doc.ClearSelection2(true);continue;}DisplayDimension dd=null;try{dd=mode==1?doc.AddHorizontalDimension2(x,y,0) as DisplayDimension:doc.AddDimension2(x,y,0) as DisplayDimension;}catch{}if(dd==null)continue;double mm=UserMm(dd,doc);if(!Double.IsNaN(mm)&&Math.Abs(Math.Abs(mm)-expectedMm)>0.03){Hide(Ann(dd));log.Add("DIM "+name+" wrong="+mm.ToString("0.#####",CultureInfo.InvariantCulture));continue;}NameDim(dd,name);log.Add("DIM "+name+" OK mm="+(Double.IsNaN(mm)?"NaN":mm.ToString("0.#####",CultureInfo.InvariantCulture)));doc.ClearSelection2(true);return dd;}log.Add("DIM "+name+" FAILED");return null;}

    static DatumTag CreateDatum(ModelDoc2 doc,View v,Face2 f,string label,double x,double y,List<string> log){try{doc.ClearSelection2(true);Need(SelectInView(v,f,false),"datum "+label+" entity selection failed");DatumTag dt=doc.IInsertDatumTag2();Need(dt!=null,"IInsertDatumTag2 "+label+" returned null");Need(dt.SetLabel(label),"datum "+label+" SetLabel failed");Annotation a=dt.GetAnnotation() as Annotation;if(a!=null)a.SetPosition(x,y,0);doc.ClearSelection2(true);log.Add("DATUM "+label+" OK view="+VName(v));return dt;}catch(Exception ex){doc.ClearSelection2(true);log.Add("DATUM "+label+" FAIL="+One(ex.Message));return null;}}

    static Gtol CreateGtol(ModelDoc2 doc,View v,List<Face2> faces,string symbol,bool dia,string tolMc,string tol,string d1,string d2,double x,double y,string tag,bool czBelow,List<string> log){try{Need(faces!=null&&faces.Count>0,"no faces");doc.ClearSelection2(true);bool first=true;foreach(Face2 f in faces){Need(SelectInView(v,f,!first),tag+" selection failed");first=false;}Gtol g=doc.IInsertGtol();Need(g!=null,tag+" IInsertGtol null");g.SetFrameSymbols2((short)1,symbol,dia,tolMc??"",false,"","","","");Need(g.SetFrameValues2((short)1,tol,"",d1??"",d2??"",""),tag+" SetFrameValues2 failed");if(czBelow){try{g.InsertBelowFrameTextAt(1,"CZ");}catch{try{g.SetBelowFrameTextAt(1,"CZ",true);}catch{}}}Annotation a=g.GetAnnotation() as Annotation;if(a!=null)a.SetPosition(x,y,0);doc.ClearSelection2(true);log.Add("GTOL "+tag+" OK view="+VName(v));return g;}catch(Exception ex){doc.ClearSelection2(true);log.Add("GTOL "+tag+" FAIL="+One(ex.Message));return null;}}

    static Note AddNote(ModelDoc2 doc,string text,double x,double y,List<string> log,string tag){try{doc.ClearSelection2(true);Note n=doc.InsertNote(text) as Note;if(n==null){log.Add("NOTE "+tag+" FAIL");return null;}Annotation a=n.GetAnnotation() as Annotation;if(a!=null)a.SetPosition(x,y,0);try{n.LockPosition=true;}catch{}log.Add("NOTE "+tag+" OK");return n;}catch(Exception ex){log.Add("NOTE "+tag+" FAIL="+One(ex.Message));return null;}}

    public static int Main(string[] args)
    {
        string drawing=Arg(args,"--drawing"),partPath=Arg(args,"--part"),manifestPath=Arg(args,"--manifest"),outRoot=Arg(args,"--out-root"),report=Arg(args,"--report");
        SldWorks sw=null;ModelDoc2 part=null,doc=null;bool created=false;var log=new List<string>();
        try{
            Need(File.Exists(drawing),"source drawing missing");Need(File.Exists(partPath),"source part missing");Need(File.Exists(manifestPath),"manifest missing");Need(!String.IsNullOrWhiteSpace(outRoot),"out-root missing");Need(!String.IsNullOrWhiteSpace(report),"report missing");
            Dictionary<string,string> mf=Manifest(manifestPath);
            double c01=MD(mf,"C01_FLATNESS_MM"),c02=MD(mf,"C02_DIA_MM"),c02depth=MD(mf,"C02_DEPTH_MM"),c03=MD(mf,"C03_PERP_MM"),c04=MD(mf,"C04_HOLE_DIA_MM"),c04pcd=MD(mf,"C04_PCD_MM"),c04ang=MD(mf,"C04_ANGLE_DEG"),c04pos=MD(mf,"C04_POSITION_MM"),c05=MD(mf,"C05_OD_MM"),c05tol=MD(mf,"C05_OD_TOL_MM"),c05t=MD(mf,"C05_THK_MM"),c05ttol=MD(mf,"C05_THK_TOL_MM"),c06=MD(mf,"C06_OAL_MM"),c06tol=MD(mf,"C06_TOL_MM"),c07=MD(mf,"C07_DIA_MM"),c08=MD(mf,"C08_DIA_MM"),wall=MD(mf,"C08_WALL_REF_MM"),c11=MD(mf,"C11_RUNOUT_MM"),bt=MD(mf,"BLIND_THK_MM"),bttol=MD(mf,"BLIND_TOL_MM");
            string dsha=Sha(drawing),psha=Sha(partPath);

            string stamp=DateTime.Now.ToString("yyyyMMdd_HHmmss"),dir=Path.Combine(outRoot,"two_view_v1_"+stamp);Directory.CreateDirectory(dir);
            string partCopy=Path.Combine(dir,"K01-P-007_Hermetic_Magnetic_Can_TWO_VIEW_SOURCE_CANDIDATE.SLDPRT");
            string drawCopy=Path.Combine(dir,"K01-D-006_Hermetic_Magnetic_Can_TWO_VIEW_CANDIDATE.SLDDRW");
            File.Copy(partPath,partCopy,false);File.Copy(drawing,drawCopy,false);

            Type t=Type.GetTypeFromProgID("SldWorks.Application");Need(t!=null,"SOLIDWORKS ProgID missing");sw=Activator.CreateInstance(t) as SldWorks;Need(sw!=null,"SOLIDWORKS activation failed");created=true;sw.Visible=true;Need(typeof(SldWorks).Assembly.GetName().Version.Major==26,"requires SOLIDWORKS 2018 interop major 26");
            string oldRef=FindP007Reference(sw,drawCopy);Need(!String.IsNullOrWhiteSpace(oldRef),"P007 drawing reference not found");Need(sw.ReplaceReferencedDocument(drawCopy,oldRef,partCopy),"ReplaceReferencedDocument failed");log.Add("RELINK old="+oldRef+" new="+partCopy);

            int pe=0,pw=0;part=sw.OpenDoc6(partCopy,(int)swDocumentTypes_e.swDocPART,(int)swOpenDocOptions_e.swOpenDocOptions_Silent,"",ref pe,ref pw) as ModelDoc2;Need(part!=null,"open part copy failed e="+pe+" w="+pw);
            List<Face2> fs=Faces(part);Need(fs.Count>5,"too few part faces");double xmin,xmax;PlaneExtents(fs,out xmin,out xmax);log.Add("GEOM XMIN="+xmin.ToString("0.######",CultureInfo.InvariantCulture)+" XMAX="+xmax.ToString("0.######",CultureInfo.InvariantCulture));
            List<Face2> aFaces=FindPlanes(fs,xmin);Need(aFaces.Count>=1,"Datum-A plane faces not found");Face2 aFace=aFaces[0];
            Face2 c02f=FindCylinder(fs,c02),c05f=FindCylinder(fs,c05),c07f=FindCylinder(fs,c07),c08f=FindCylinder(fs,c08);List<Face2> c04fs=FindCylinders(fs,c04);Need(c02f!=null&&c05f!=null&&c07f!=null&&c08f!=null,"critical cylindrical face scan failed");Need(c04fs.Count>=3,"C04 pattern faces <3");
            Face2 flangeRear=FindPlane(fs,xmin+c05t,true),locatorBack=FindPlane(fs,xmin+c02depth,true),blindOuter=FindPlane(fs,xmax,true),blindInner=FindPlane(fs,xmax-bt,true);Need(flangeRear!=null&&locatorBack!=null&&blindOuter!=null&&blindInner!=null,"critical axial planes not found");

            int de=0,dw=0;doc=sw.OpenDoc6(drawCopy,(int)swDocumentTypes_e.swDocDRAWING,(int)swOpenDocOptions_e.swOpenDocOptions_Silent,"",ref de,ref dw) as ModelDoc2;Need(doc!=null,"open drawing copy failed e="+de+" w="+dw);DrawingDoc dr=doc as DrawingDoc;Need(dr!=null,"not drawing");
            List<VRec> views=ModelViews(dr,Path.GetFileName(partCopy));Need(views.Count>=3,"expected >=3 P007 views");VRec end=null,section=null,front=null,iso=null;foreach(VRec vr in views){if(vr.section&&section==null)section=vr;if(vr.orient.IndexOf("Right",StringComparison.OrdinalIgnoreCase)>=0&&end==null)end=vr;if(vr.orient.IndexOf("Front",StringComparison.OrdinalIgnoreCase)>=0&&front==null)front=vr;if(vr.orient.IndexOf("Isometric",StringComparison.OrdinalIgnoreCase)>=0&&iso==null)iso=vr;}if(end==null)foreach(VRec vr in views)if(!vr.section&&vr.aspect>0.8&&vr.aspect<1.2){end=vr;break;}Need(end!=null&&section!=null,"cannot identify end/section views");

            // Existing V2 is used only as a proven linked-sheet seed. Keep only two manufacturing views.
            if(front!=null&&front!=end){try{front.v.SetVisible(false,false);log.Add("VIEW_HIDE "+front.name);}catch{}}
            if(iso!=null){try{iso.v.SetVisible(false,false);log.Add("VIEW_HIDE "+iso.name);}catch{}}
            foreach(VRec vr in views)if(vr!=end&&vr!=section&&vr!=front&&vr!=iso){try{vr.v.SetVisible(false,false);log.Add("VIEW_HIDE "+vr.name);}catch{}}
            SetView(end.v,0.105,0.190,5.0);SetView(section.v,0.295,0.190,5.0);doc.EditRebuild3();

            // Capture/hide only old product annotations in retained views. Never delete.
            HideOldControlledAnnotations(end.v,log);HideOldControlledAnnotations(section.v,log);

            double[] eo=Outline(end.v),so=Outline(section.v);Need(eo.Length>=4&&so.Length>=4,"view outlines unavailable after layout");
            double ex=eo[2]+0.012,ecy=(eo[1]+eo[3])*0.5;double sx0=so[0],sx1=so[2],sy0=so[1],sy1=so[3],scx=(sx0+sx1)*0.5;

            // Controlled dimensions.
            DisplayDimension d02=TryDiameter(doc,end.v,c02f,c02,ex,ecy+0.035,"C02_LOCATOR_DIA",log);bool b02=d02!=null&&SetFit(d02,"H7","");
            DisplayDimension d05=TryDiameter(doc,end.v,c05f,c05,ex,ecy+0.065,"C05_FLANGE_OD",log);bool b05=d05!=null&&SetSymTol(d05,c05tol);
            DisplayDimension d04=TryDiameter(doc,end.v,c04fs[0],c04,ex,ecy-0.035,"C04_HOLE_DIA",log);bool b04=d04!=null&&SetFit(d04,"H10","");if(d04!=null)SetPrefix(d04,"3X ");
            DisplayDimension d07=TryDiameter(doc,section.v,c07f,c07,sx1+0.015,sy1-0.035,"C07_CAN_OD",log);bool b07=d07!=null&&SetFit(d07,"","h9");
            DisplayDimension d08=TryDiameter(doc,section.v,c08f,c08,sx1+0.015,sy1-0.065,"C08_CAN_ID",log);bool b08=d08!=null&&SetFit(d08,"H9","");
            DisplayDimension d5t=TryLinear(doc,section.v,aFace,flangeRear,c05t,scx-0.045,sy1+0.015,"C05_FLANGE_THK",log);bool b5t=d5t!=null&&SetSymTol(d5t,c05ttol);
            DisplayDimension d06=TryLinear(doc,section.v,aFace,blindOuter,c06,scx,sy1+0.028,"C06_OAL",log);bool b06=d06!=null&&SetSymTol(d06,c06tol);
            DisplayDimension ddep=TryLinear(doc,section.v,aFace,locatorBack,c02depth,sx0+0.045,sy0-0.016,"C02_LOCATOR_DEPTH",log);bool bdep=ddep!=null;if(ddep!=null)SetSuffix(ddep," NOM");
            DisplayDimension dbt=TryLinear(doc,section.v,blindInner,blindOuter,bt,sx1-0.025,sy1+0.015,"BLIND_END_THK",log);bool bbt=dbt!=null&&SetSymTol(dbt,bttol);

            // Native datum tags from functional features.
            DatumTag da=CreateDatum(doc,section.v,aFace,"A",sx0-0.018,scx>0?ecy:ecy,log); // position refined below
            if(da!=null){try{Annotation aa=da.GetAnnotation() as Annotation;if(aa!=null)aa.SetPosition(sx0-0.010,(sy0+sy1)*0.5,0);}catch{}}
            DatumTag db=CreateDatum(doc,end.v,c02f,"B",eo[0]-0.012,ecy,log);

            // Native GPS feature-control frames. CZ is carried as native GTol below-frame review text because
            // SW2018 legacy SetFrameSymbols2 has no proven controlled CZ modifier API in this project yet.
            Gtol g01=CreateGtol(doc,section.v,aFaces,"<IGTOL-FLAT>",false,"",c01.ToString("0.###",CultureInfo.InvariantCulture),"","",sx0+0.015,sy1+0.012,"C01_FLATNESS_CZ",true,log);
            Gtol g03=CreateGtol(doc,section.v,new List<Face2>{c02f},"<IGTOL-PERP>",true,"<MOD-MMC>",c03.ToString("0.###",CultureInfo.InvariantCulture),"A","",sx0+0.020,sy0+0.020,"C03_PERP_A",false,log);
            Gtol g04=CreateGtol(doc,end.v,c04fs.GetRange(0,3),"<IGTOL-POSI>",true,"",c04pos.ToString("0.###",CultureInfo.InvariantCulture),"A","B",eo[0]+0.010,eo[1]-0.018,"C04_POSITION_AB",false,log);
            Gtol g11o=CreateGtol(doc,section.v,new List<Face2>{c07f},"<IGTOL-TRUN>",false,"",c11.ToString("0.###",CultureInfo.InvariantCulture),"B","",sx1+0.010,sy0+0.042,"C11_RUNOUT_OD_B",false,log);
            Gtol g11i=CreateGtol(doc,section.v,new List<Face2>{c08f},"<IGTOL-TRUN>",false,"",c11.ToString("0.###",CultureInfo.InvariantCulture),"B","",sx1+0.010,sy0+0.026,"C11_RUNOUT_ID_B",false,log);

            // Controlled supplemental semantics. These are notes by design (not substitutes for datum/FCF objects).
            AddNote(doc,"PCD Ø"+c04pcd.ToString("0.00",CultureInfo.InvariantCulture)+" BASIC  |  "+c04ang.ToString("0",CultureInfo.InvariantCulture)+"° BASIC",eo[0],eo[1]-0.032,log,"C04_BASIC_PATTERN");
            AddNote(doc,"WALL "+wall.ToString("0.00",CultureInfo.InvariantCulture)+" REF",sx1-0.055,sy0+0.010,log,"C08_WALL_REF");
            AddNote(doc,"MATERIAL: "+M(mf,"MATERIAL"),0.205,0.072,log,"C09_MATERIAL");
            AddNote(doc,"DEBURR; BREAK NON-FUNCTIONAL SHARP EDGES 0.1–0.2 mm. FUNCTIONAL DATUM/FIT/SEAL EDGES EXCLUDED.",0.205,0.060,log,"EDGE_CONDITION");
            AddNote(doc,"P007 MONOLITHIC — NO PERMANENT P003↔P007 WELD.  ENGINEERING REVIEW — NOT FOR MANUFACTURE.",0.205,0.048,log,"STATUS_ARCH");

            doc.ClearSelection2(true);doc.ForceRebuild3(false);doc.ViewZoomtofit2();doc.WindowRedraw();
            SaveAs(doc,drawCopy);string pdf=Path.ChangeExtension(drawCopy,"PDF"),bmp=Path.ChangeExtension(drawCopy,"BMP");SaveAs(doc,pdf);doc.ViewZoomtofit2();bool bmpOk=doc.SaveBMP(bmp,1800,1273);

            int dimCount=(b02?1:0)+(b04?1:0)+(b05?1:0)+(b5t?1:0)+(b06?1:0)+(b07?1:0)+(b08?1:0)+(bdep?1:0)+(bbt?1:0);
            int datumCount=(da!=null?1:0)+(db!=null?1:0);int gtolCount=(g01!=null?1:0)+(g03!=null?1:0)+(g04!=null?1:0)+(g11o!=null?1:0)+(g11i!=null?1:0);
            string status=(dimCount>=8&&datumCount==2&&gtolCount==5)?"PASS_D006_TWO_VIEW_V1_ENGINEERING_REVIEW__CZ_VISUAL_CONFIRM":"PARTIAL_D006_TWO_VIEW_V1__MANUAL_FINISH_REQUIRED";
            string title=doc.GetTitle();sw.CloseDoc(title);doc=null;sw.CloseDoc(part.GetTitle());part=null;
            Need(Sha(drawing)==dsha,"source drawing changed");Need(Sha(partPath)==psha,"source part changed");

            var sb=new StringBuilder();sb.AppendLine("STATUS="+status);sb.AppendLine("SOURCE_DRAWING="+drawing);sb.AppendLine("SOURCE_DRAWING_SHA256="+dsha);sb.AppendLine("SOURCE_PART="+partPath);sb.AppendLine("SOURCE_PART_SHA256="+psha);sb.AppendLine("OUTPUT_DRAWING="+drawCopy);sb.AppendLine("OUTPUT_PART_COPY="+partCopy);sb.AppendLine("OUTPUT_PDF="+pdf);sb.AppendLine("OUTPUT_BMP="+bmp);sb.AppendLine("BMP_OK="+bmpOk);sb.AppendLine("END_VIEW="+end.name);sb.AppendLine("SECTION_VIEW="+section.name);sb.AppendLine("VISIBLE_MANUFACTURING_VIEWS=2");sb.AppendLine("CONTROLLED_DIMENSIONS_OK="+dimCount+"/9");sb.AppendLine("DATUMS_OK="+datumCount+"/2");sb.AppendLine("GTOLS_OK="+gtolCount+"/5");sb.AppendLine("C01_CZ_REPRESENTATION=GTOL_BELOW_FRAME_TEXT_REVIEW_CONFIRM");sb.AppendLine("SOURCE_DRAWING_INVARIANT=True");sb.AppendLine("SOURCE_PART_INVARIANT=True");for(int i=0;i<log.Count;i++)sb.AppendLine("LOG_"+(i+1)+"="+One(log[i]));File.WriteAllText(report,sb.ToString(),Encoding.UTF8);
            Console.WriteLine("STATUS: "+status);Console.WriteLine("TWO VIEWS: end="+end.name+" section="+section.name);Console.WriteLine("CONTROLLED DIMENSIONS: "+dimCount+" / 9");Console.WriteLine("DATUMS: "+datumCount+" / 2");Console.WriteLine("GTOLS: "+gtolCount+" / 5");Console.WriteLine("C01 CZ: native flatness FCF + native GTol below-frame 'CZ'; visual ISO placement confirmation required");Console.WriteLine("DRAWING: "+drawCopy);Console.WriteLine("PDF: "+pdf);Console.WriteLine("BMP: "+bmp);Console.WriteLine("REPORT: "+report);Console.WriteLine("NEXT: Open candidate; only move annotations / resolve overlaps / confirm CZ presentation. Do not re-enter engineering values manually.");return status.StartsWith("PASS_")?0:3;
        }
        catch(Exception ex){try{File.WriteAllText(report,"STATUS=HOLD_D006_TWO_VIEW_V1\nERROR="+ex.ToString()+"\n",Encoding.UTF8);}catch{}Console.Error.WriteLine(ex.ToString());return 2;}
        finally{try{if(doc!=null&&sw!=null)sw.CloseDoc(doc.GetTitle());}catch{}try{if(part!=null&&sw!=null)sw.CloseDoc(part.GetTitle());}catch{}try{if(created&&sw!=null)sw.ExitApp();}catch{}}
    }
}
