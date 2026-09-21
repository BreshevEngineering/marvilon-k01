using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using SolidWorks.Interop.sldworks;
using SolidWorks.Interop.swconst;

public class K01D006TwoViewV2
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
    static bool MB(Dictionary<string,string> m,string k){string v=M(m,k);return Eq(v,"TRUE")||Eq(v,"YES")||Eq(v,"1");}

    static string VName(View v){try{return v.GetName2()??"";}catch{return "";}}
    static string VOrient(View v){try{return v.GetOrientationName()??"";}catch{return "";}}
    static string VRef(View v){try{return v.GetReferencedModelName()??"";}catch{return "";}}
    static double[] DA(object o){var z=new List<double>();foreach(object q in Items(o))try{z.Add(Convert.ToDouble(q,CultureInfo.InvariantCulture));}catch{}return z.ToArray();}
    static double[] Outline(View v){try{return DA(v.GetOutline());}catch{return new double[0];}}
    static void SetView(View v,double x,double y,double scale){try{v.PositionLocked=false;}catch{}try{v.UseSheetScale=0;}catch{}try{v.UseParentScale=false;}catch{}try{v.ScaleDecimal=scale;}catch{}try{v.Position=new double[]{x,y};}catch{}}
    static bool SetSheetScale(DrawingDoc dr,double num,double den,List<string> log){try{Sheet sh=dr.GetCurrentSheet() as Sheet;Need(sh!=null,"current sheet missing");bool ok=sh.SetScale(num,den,false,false);log.Add("SHEET_SCALE "+num.ToString("0.###",CultureInfo.InvariantCulture)+":"+den.ToString("0.###",CultureInfo.InvariantCulture)+" ok="+ok);return ok;}catch(Exception ex){log.Add("SHEET_SCALE FAIL="+One(ex.Message));return false;}}
    static bool SheetFirstAngle(DrawingDoc dr){try{Sheet sh=dr.GetCurrentSheet() as Sheet;double[] p=sh==null?new double[0]:DA(sh.GetProperties2());return p.Length>=5&&Math.Abs(p[4])>0.5;}catch{return false;}}
    static bool SaveAs(ModelDoc2 doc,string p){int e=0,w=0;bool ok=doc.Extension.SaveAs(p,(int)swSaveAsVersion_e.swSaveAsCurrentVersion,(int)swSaveAsOptions_e.swSaveAsOptions_Silent,null,ref e,ref w);if(!ok||e!=0)throw new Exception("SaveAs failed "+p+" e="+e+" w="+w);return true;}

    class VRec{public View v;public string name="",orient="",refModel="";public bool section=false;}
    static List<VRec> Views(DrawingDoc dr,string partBase){var r=new List<VRec>();View v=dr.GetFirstView() as View;if(v!=null)v=v.GetNextView() as View;while(v!=null){string rm=VRef(v);if(!String.IsNullOrWhiteSpace(rm)&&Eq(Path.GetFileName(rm),partBase)){string n=VName(v),o=VOrient(v);r.Add(new VRec{v=v,name=n,orient=o,refModel=rm,section=n.IndexOf("SECTION",StringComparison.OrdinalIgnoreCase)>=0||n.IndexOf("B-B",StringComparison.OrdinalIgnoreCase)>=0||n.IndexOf("A-A",StringComparison.OrdinalIgnoreCase)>=0});}v=v.GetNextView() as View;}return r;}
    static string FindP007Reference(SldWorks sw,string drawing){object deps=null;try{deps=sw.GetDocumentDependencies2(drawing,true,true,false);}catch{}foreach(object q in Items(deps)){string s=Convert.ToString(q)??"";if(File.Exists(s)&&s.EndsWith(".SLDPRT",StringComparison.OrdinalIgnoreCase)&&Path.GetFileName(s).IndexOf("K01-P-007",StringComparison.OrdinalIgnoreCase)>=0)return s;}return "";}

    static Surface Surf(Face2 f){try{return f.IGetSurface();}catch{return null;}}
    static double PlaneX(Face2 f){Surface s=Surf(f);if(s==null||!s.IsPlane())return Double.NaN;double[] p=DA(s.PlaneParams);return p.Length>=6?p[3]:Double.NaN;}
    static double CylRadiusMm(Face2 f){Surface s=Surf(f);if(s==null||!s.IsCylinder())return Double.NaN;double[] p=DA(s.CylinderParams);return p.Length>=7?p[6]*1000.0:Double.NaN;}
    static double Area(Face2 f){try{return f.GetArea();}catch{return 0;}}
    static List<Face2> Faces(ModelDoc2 part){var r=new List<Face2>();PartDoc pd=part as PartDoc;if(pd==null)return r;foreach(object bo in Items(pd.GetBodies2((int)swBodyType_e.swSolidBody,true))){Body2 b=bo as Body2;if(b==null)continue;foreach(object fo in Items(b.GetFaces())){Face2 f=fo as Face2;if(f!=null)r.Add(f);}}return r;}
    static List<Face2> FindCylinders(List<Face2> fs,double diaMm){var r=new List<Face2>();foreach(Face2 f in fs){double rr=CylRadiusMm(f);if(!Double.IsNaN(rr)&&Math.Abs(2*rr-diaMm)<=0.02)r.Add(f);}return r;}
    static Face2 FindUniqueCylinder(List<Face2> fs,double diaMm,string role,List<string> log){List<Face2> q=FindCylinders(fs,diaMm);log.Add("BIND "+role+" dia="+diaMm.ToString("0.###",CultureInfo.InvariantCulture)+" candidates="+q.Count);Need(q.Count==1,role+" ambiguous/missing cylinder: expected 1 candidate, got "+q.Count);return q[0];}
    static List<Face2> FindPlanes(List<Face2> fs,double xMm){var r=new List<Face2>();foreach(Face2 f in fs){double x=PlaneX(f);if(!Double.IsNaN(x)&&Math.Abs(x*1000.0-xMm)<=0.03)r.Add(f);}r.Sort(delegate(Face2 a,Face2 b){return Area(b).CompareTo(Area(a));});return r;}
    static string FaceAreaList(List<Face2> fs){var b=new StringBuilder();for(int i=0;i<fs.Count;i++){if(i>0)b.Append(",");b.Append(Area(fs[i]).ToString("0.000000000000",CultureInfo.InvariantCulture));}return b.ToString();}
    static Face2 FindControlledPlaneByArea(List<Face2> coplanar,double targetAreaM2,string role,List<string> log){var q=new List<Face2>();double tol=Math.Max(1e-10,Math.Abs(targetAreaM2)*1e-5);foreach(Face2 f in coplanar)if(Math.Abs(Area(f)-targetAreaM2)<=tol)q.Add(f);log.Add("BIND "+role+" target_area_m2="+targetAreaM2.ToString("0.000000000000",CultureInfo.InvariantCulture)+" tol_m2="+tol.ToString("0.000000000000",CultureInfo.InvariantCulture)+" matches="+q.Count+" coplanar_areas_m2=["+FaceAreaList(coplanar)+"]");Need(q.Count==1,role+" controlled plane area signature unresolved: expected 1 match, got "+q.Count+"; coplanar areas m2=["+FaceAreaList(coplanar)+"]");return q[0];}
    static Face2 FindPlane(List<Face2> fs,double xMm,string role,List<string> log){List<Face2> r=FindPlanes(fs,xMm);log.Add("BIND "+role+" x="+xMm.ToString("0.###",CultureInfo.InvariantCulture)+" coplanar_candidates="+r.Count);Need(r.Count>=1,role+" plane missing at x="+xMm.ToString("0.###",CultureInfo.InvariantCulture));return r[0];}
    static void PlaneExtents(List<Face2> fs,out double minMm,out double maxMm){minMm=1e99;maxMm=-1e99;foreach(Face2 f in fs){double x=PlaneX(f);if(Double.IsNaN(x))continue;double mm=x*1000.0;if(mm<minMm)minMm=mm;if(mm>maxMm)maxMm=mm;}Need(minMm<1e90&&maxMm>-1e90,"plane extents unavailable");}

    static bool SelectInView(View v,object modelEntity,bool append){if(v==null||modelEntity==null)return false;try{Entity ce=v.GetCorrespondingEntity(modelEntity) as Entity;if(ce!=null&&ce.Select4(append,null))return true;}catch{}try{return v.SelectEntity(modelEntity,append);}catch{return false;}}
    static double UserMm(DisplayDimension dd,ModelDoc2 doc){try{Dimension d=dd.GetDimension2(0);return d==null?Double.NaN:d.IGetUserValueIn2(doc);}catch{return Double.NaN;}}
    static void NameDim(DisplayDimension dd,string name){try{Dimension d=dd.GetDimension2(0);if(d!=null)d.Name=name;}catch{}}
    static Annotation Ann(DisplayDimension dd){try{return dd==null?null:dd.GetAnnotation() as Annotation;}catch{return null;}}
    static void Hide(Annotation a){try{if(a!=null)a.Visible=(int)swAnnotationVisibilityState_e.swAnnotationHidden;}catch{}}
    static void HideOldControlledAnnotations(View v,List<string> log){int n=0;foreach(object ao in Items(v.GetAnnotations())){Annotation a=ao as Annotation;if(a==null)continue;int t=-1;try{t=a.GetType();}catch{}if(t==(int)swAnnotationType_e.swDisplayDimension||t==(int)swAnnotationType_e.swDatumTag||t==(int)swAnnotationType_e.swGTol||t==(int)swAnnotationType_e.swSFSymbol){Hide(a);n++;}}log.Add("HIDE_OLD view="+VName(v)+" count="+n);}
    static void HideLegacySheetNotes(DrawingDoc dr,List<string> log){int n=0;View v=dr.GetFirstView() as View;while(v!=null){Note note=null;try{note=v.GetFirstNote() as Note;}catch{}while(note!=null){Note next=null;try{next=note.GetNext() as Note;}catch{}string s="";try{s=note.GetText()??"";}catch{}if(s.StartsWith("PCD ",StringComparison.OrdinalIgnoreCase)||s.StartsWith("WALL ",StringComparison.OrdinalIgnoreCase)||s.StartsWith("MATERIAL:",StringComparison.OrdinalIgnoreCase)||s.StartsWith("DEBURR;",StringComparison.OrdinalIgnoreCase)||s.StartsWith("P007 MONOLITHIC",StringComparison.OrdinalIgnoreCase)){try{Hide(note.GetAnnotation() as Annotation);n++;}catch{}}note=next;}v=v.GetNextView() as View;}log.Add("HIDE_LEGACY_NOTES count="+n);}

    static void FormatControlledDim(DisplayDimension dd,int primary,int tol){if(dd==null)return;try{dd.ShowParenthesis=false;}catch{}try{dd.ShowLowerParenthesis=false;}catch{}try{dd.SetPrecision2(primary,primary,tol,tol);}catch{}}
    static bool SetFit(DisplayDimension dd,string hole,string shaft){try{Dimension d=dd.GetDimension2(0);DimensionTolerance t=d==null?null:d.Tolerance as DimensionTolerance;if(t==null)return false;t.Type=(int)swTolType_e.swTolFIT;bool ok=t.SetFitValues(hole??"",shaft??"");FormatControlledDim(dd,2,2);return ok;}catch{return false;}}
    static bool SetSymTol(DisplayDimension dd,double tolMm,List<string> log,string tag){
        if(dd==null)return false;Dimension d=null;DimensionTolerance t=null;double v=tolMm/1000.0;bool ok=false;
        try{d=dd.GetDimension2(0);t=d==null?null:d.Tolerance as DimensionTolerance;}catch(Exception ex){log.Add("TOL "+tag+" acquire FAIL="+One(ex.Message));}
        if(d==null||t==null){log.Add("TOL "+tag+" missing Dimension/DimensionTolerance");return false;}
        try{t.Type=(int)swTolType_e.swTolSYMMETRIC;ok=t.SetValues2(-v,v,(int)swSetValueInConfiguration_e.swSetValue_InThisConfiguration,null);log.Add("TOL "+tag+" SetValues2(this-config)="+ok);}catch(Exception ex){log.Add("TOL "+tag+" SetValues2(this-config) EX="+One(ex.Message));}
        if(!ok){try{t.Type=(int)swTolType_e.swTolSYMMETRIC;ok=t.SetValues2(-v,v,(int)swSetValueInConfiguration_e.swSetValue_InAllConfigurations,null);log.Add("TOL "+tag+" SetValues2(all-configs)="+ok);}catch(Exception ex){log.Add("TOL "+tag+" SetValues2(all-configs) EX="+One(ex.Message));}}
        if(!ok){try{bool a=d.SetToleranceType((int)swTolType_e.swTolSYMMETRIC);bool b=d.SetToleranceValues(-v,v);ok=a&&b;log.Add("TOL "+tag+" legacy type="+a+" values="+b);}catch(Exception ex){log.Add("TOL "+tag+" legacy EX="+One(ex.Message));}}
        FormatControlledDim(dd,2,2);
        try{double mn=0,mx=0;int smn=t.GetMinValue2(out mn),smx=t.GetMaxValue2(out mx);bool rb=t.Type==(int)swTolType_e.swTolSYMMETRIC&&Math.Abs(mn+v)<=1e-7&&Math.Abs(mx-v)<=1e-7;log.Add("TOL "+tag+" readback type="+t.Type+" min="+mn.ToString("0.######",CultureInfo.InvariantCulture)+" max="+mx.ToString("0.######",CultureInfo.InvariantCulture)+" status="+smn+"/"+smx+" verify="+rb);if(rb)ok=true;}catch(Exception ex){log.Add("TOL "+tag+" readback EX="+One(ex.Message));}
        return ok;
    }
    static void SetSuffix(DisplayDimension dd,string s){try{dd.SetText((int)swDimensionTextParts_e.swDimensionTextSuffix,s);}catch{}}
    static void SetPrefix(DisplayDimension dd,string s){try{dd.SetText((int)swDimensionTextParts_e.swDimensionTextPrefix,s);}catch{}}

    static DisplayDimension AcceptDim(ModelDoc2 doc,DisplayDimension dd,double expectedMm,string name,string path,List<string> log){if(dd==null)return null;double mm=UserMm(dd,doc);if(!Double.IsNaN(mm)&&Math.Abs(Math.Abs(mm)-expectedMm)>0.03){Hide(Ann(dd));log.Add("DIM "+name+" reject path="+path+" wrong="+mm.ToString("0.#####",CultureInfo.InvariantCulture));return null;}NameDim(dd,name);FormatControlledDim(dd,2,2);log.Add("DIM "+name+" OK path="+path+" mm="+(Double.IsNaN(mm)?"NaN":mm.ToString("0.#####",CultureInfo.InvariantCulture)));doc.ClearSelection2(true);return dd;}
    static DisplayDimension TryDiameter(ModelDoc2 doc,View v,Face2 face,double expectedMm,double x,double y,string name,List<string> log){if(face==null){log.Add("DIM "+name+" face=MISSING");return null;}var c=new List<object>();foreach(object eo in Items(face.GetEdges()))if(eo is Entity)c.Add(eo);c.Add(face);int k=0;foreach(object q in c){k++;doc.ClearSelection2(true);if(!SelectInView(v,q,false))continue;DisplayDimension dd=null;try{dd=doc.AddDiameterDimension2(x,y,0) as DisplayDimension;}catch(Exception ex){log.Add("DIM "+name+" add_err="+ex.GetType().Name);}DisplayDimension ok=AcceptDim(doc,dd,expectedMm,name,"diameter_entity_"+k,log);if(ok!=null)return ok;}log.Add("DIM "+name+" FAILED");return null;}
    static DisplayDimension TryLinear(ModelDoc2 doc,View v,Face2 a,Face2 b,double expectedMm,double x,double y,string name,List<string> log){if(a==null||b==null){log.Add("DIM "+name+" plane=MISSING");return null;}
        for(int mode=1;mode<=2;mode++){doc.ClearSelection2(true);if(!SelectInView(v,a,false)||!SelectInView(v,b,true)){doc.ClearSelection2(true);continue;}DisplayDimension dd=null;try{dd=mode==1?doc.AddHorizontalDimension2(x,y,0) as DisplayDimension:doc.AddDimension2(x,y,0) as DisplayDimension;}catch{}DisplayDimension ok=AcceptDim(doc,dd,expectedMm,name,"face_pair_mode_"+mode,log);if(ok!=null)return ok;}
        var ea=new List<object>();foreach(object q in Items(a.GetEdges()))if(q is Entity)ea.Add(q);var eb=new List<object>();foreach(object q in Items(b.GetEdges()))if(q is Entity)eb.Add(q);int attempt=0;foreach(object qa in ea)foreach(object qb in eb){attempt++;doc.ClearSelection2(true);if(!SelectInView(v,qa,false)||!SelectInView(v,qb,true)){doc.ClearSelection2(true);continue;}DisplayDimension dd=null;try{dd=doc.AddHorizontalDimension2(x,y,0) as DisplayDimension;}catch{}DisplayDimension ok=AcceptDim(doc,dd,expectedMm,name,"edge_pair_"+attempt,log);if(ok!=null)return ok;}
        log.Add("DIM "+name+" FAILED face_pairs=2 edge_pairs="+(ea.Count*eb.Count));return null;}

    static List<Entity> VisibleEdgesOnPlane(ModelDoc2 doc,View v,Face2 plane,string role,List<string> log){
        var r=new List<Entity>();if(doc==null||v==null||plane==null)return r;double tx=PlaneX(plane);if(Double.IsNaN(tx))return r;
        try{DrawingComponent dc=v.RootDrawingComponent as DrawingComponent;Component2 comp=dc==null?null:dc.Component as Component2;if(comp==null){log.Add("VEDGE "+role+" no root component");return r;}object raw=v.GetVisibleEntities2(comp,(int)swViewEntityType_e.swViewEntityType_Edge);foreach(object q in Items(raw)){Entity ent=q as Entity;Edge e=q as Edge;if(ent==null||e==null)continue;bool hit=false;try{foreach(object fo in Items(e.GetTwoAdjacentFaces2())){Face2 f=fo as Face2;if(f==null)continue;double x=PlaneX(f);if(!Double.IsNaN(x)&&Math.Abs(x-tx)<=0.00003){hit=true;break;}}}catch{}if(hit)r.Add(ent);}log.Add("VEDGE "+role+" target_x_mm="+(tx*1000.0).ToString("0.######",CultureInfo.InvariantCulture)+" visible_matches="+r.Count);}catch(Exception ex){log.Add("VEDGE "+role+" FAIL="+One(ex.Message));}return r;
    }
    static bool SelectDrawingEntity(ModelDoc2 doc,View v,Entity ent,bool append){if(doc==null||v==null||ent==null)return false;try{SelectionMgr sm=doc.SelectionManager as SelectionMgr;if(sm==null)return false;SelectData sd=sm.CreateSelectData() as SelectData;if(sd!=null)sd.View=v;return ent.Select4(append,sd);}catch{return false;}}
    static DisplayDimension TryLinearVisiblePlaneEdges(ModelDoc2 doc,View v,Face2 a,Face2 b,double expectedMm,double x,double y,string name,List<string> log){
        var ea=VisibleEdgesOnPlane(doc,v,a,name+"_A",log);var eb=VisibleEdgesOnPlane(doc,v,b,name+"_B",log);int attempt=0;
        foreach(Entity qa in ea)foreach(Entity qb in eb){attempt++;doc.ClearSelection2(true);if(!SelectDrawingEntity(doc,v,qa,false)||!SelectDrawingEntity(doc,v,qb,true)){doc.ClearSelection2(true);continue;}DisplayDimension dd=null;try{dd=doc.AddHorizontalDimension2(x,y,0) as DisplayDimension;}catch(Exception ex){log.Add("DIM "+name+" visible_edge AddHorizontal EX="+One(ex.Message));}DisplayDimension ok=AcceptDim(doc,dd,expectedMm,name,"visible_plane_edge_pair_"+attempt,log);if(ok!=null)return ok;doc.ClearSelection2(true);if(!SelectDrawingEntity(doc,v,qa,false)||!SelectDrawingEntity(doc,v,qb,true)){doc.ClearSelection2(true);continue;}try{dd=doc.AddDimension2(x,y,0) as DisplayDimension;}catch(Exception ex){log.Add("DIM "+name+" visible_edge AddDimension EX="+One(ex.Message));}ok=AcceptDim(doc,dd,expectedMm,name,"visible_plane_edge_pair_generic_"+attempt,log);if(ok!=null)return ok;}
        log.Add("DIM "+name+" visible-plane-edge FALLBACK FAILED pairs="+(ea.Count*eb.Count));return null;
    }
    static DisplayDimension TryLinearRobust(ModelDoc2 doc,View v,Face2 a,Face2 b,double expectedMm,double x,double y,string name,List<string> log){DisplayDimension dd=TryLinear(doc,v,a,b,expectedMm,x,y,name,log);if(dd!=null)return dd;return TryLinearVisiblePlaneEdges(doc,v,a,b,expectedMm,x,y,name,log);}

    static DatumTag CreateDatum(ModelDoc2 doc,View v,Face2 f,string label,double x,double y,List<string> log){try{doc.ClearSelection2(true);Need(SelectInView(v,f,false),"datum "+label+" entity selection failed");DatumTag dt=doc.IInsertDatumTag2();Need(dt!=null,"IInsertDatumTag2 "+label+" returned null");Need(dt.SetLabel(label),"datum "+label+" SetLabel failed");Annotation a=dt.GetAnnotation() as Annotation;if(a!=null)a.SetPosition(x,y,0);doc.ClearSelection2(true);log.Add("DATUM "+label+" OK view="+VName(v));return dt;}catch(Exception ex){doc.ClearSelection2(true);log.Add("DATUM "+label+" FAIL="+One(ex.Message));return null;}}
    static Gtol CreateGtol(ModelDoc2 doc,View v,List<Face2> faces,string symbol,bool dia,string tolMc,string tol,string d1,string d2,double x,double y,string tag,bool czBelow,List<string> log){try{Need(faces!=null&&faces.Count>0,"no faces");doc.ClearSelection2(true);bool first=true;foreach(Face2 f in faces){Need(SelectInView(v,f,!first),tag+" selection failed");first=false;}Gtol g=doc.IInsertGtol();Need(g!=null,tag+" IInsertGtol null");g.SetFrameSymbols2((short)1,symbol,dia,tolMc??"",false,"","","","");Need(g.SetFrameValues2((short)1,tol,"",d1??"",d2??"",""),tag+" SetFrameValues2 failed");if(czBelow){try{g.InsertBelowFrameTextAt(1,"CZ");}catch{try{g.SetBelowFrameTextAt(1,"CZ",true);}catch{}}}Annotation a=g.GetAnnotation() as Annotation;if(a!=null)a.SetPosition(x,y,0);doc.ClearSelection2(true);log.Add("GTOL "+tag+" OK view="+VName(v));return g;}catch(Exception ex){doc.ClearSelection2(true);log.Add("GTOL "+tag+" FAIL="+One(ex.Message));return null;}}
    static bool AddSurfaceFinish(ModelDoc2 doc,View section,Face2 aFace,double raUm,double x,double y,List<string> log){try{doc.ClearSelection2(true);Need(SelectInView(section,aFace,false),"surface face select failed");string val=raUm.ToString("0.###",CultureInfo.InvariantCulture);bool ok=doc.InsertSurfaceFinishSymbol2((int)swSFSymType_e.swSFMachining_Req,(int)swLeaderStyle_e.swBENT,x,y,0,(int)swSFLaySym_e.swSFNone,(int)swArrowStyle_e.swOPEN_ARROWHEAD,"","Ra","","",val,"","");doc.ClearSelection2(true);log.Add("SURFACE J2_RA "+val+" "+(ok?"OK":"FAIL"));return ok;}catch(Exception ex){doc.ClearSelection2(true);log.Add("SURFACE J2_RA FAIL "+One(ex.Message));return false;}}
    static Note AddNote(ModelDoc2 doc,string text,double x,double y,List<string> log,string tag){try{doc.ClearSelection2(true);Note n=doc.InsertNote(text) as Note;if(n==null){log.Add("NOTE "+tag+" FAIL");return null;}Annotation a=n.GetAnnotation() as Annotation;if(a!=null)a.SetPosition(x,y,0);try{n.LockPosition=true;}catch{}log.Add("NOTE "+tag+" OK");return n;}catch(Exception ex){log.Add("NOTE "+tag+" FAIL="+One(ex.Message));return null;}}
    static Note AddTedNote(ModelDoc2 doc,string text,double x,double y,List<string> log,string tag){try{doc.ClearSelection2(true);Note n=doc.InsertNote(text) as Note;if(n==null){log.Add("TED "+tag+" FAIL insert");return null;}bool box=false;try{box=n.SetBalloon((int)swBalloonStyle_e.swBS_Box,(int)swBalloonFit_e.swBF_Tightest);}catch(Exception ex){log.Add("TED "+tag+" box EX="+One(ex.Message));}Annotation a=n.GetAnnotation() as Annotation;if(a!=null)a.SetPosition(x,y,0);try{n.LockPosition=true;}catch{}log.Add("TED "+tag+" "+(box?"BOX_OK":"BOX_FAIL"));return box?n:null;}catch(Exception ex){log.Add("TED "+tag+" FAIL="+One(ex.Message));return null;}}

    public static int Main(string[] args)
    {
        string drawing=Arg(args,"--drawing"),partPath=Arg(args,"--part"),manifestPath=Arg(args,"--manifest"),outRoot=Arg(args,"--out-root"),report=Arg(args,"--report");
        SldWorks sw=null;ModelDoc2 doc=null,part=null;bool created=false;var log=new List<string>();
        try{
            Need(File.Exists(drawing),"input V1 drawing missing");Need(File.Exists(partPath),"input V1 part missing");Need(File.Exists(manifestPath),"manifest missing");Need(!String.IsNullOrWhiteSpace(outRoot),"out-root missing");Need(!String.IsNullOrWhiteSpace(report),"report missing");
            Dictionary<string,string> mf=Manifest(manifestPath);
            double c01=MD(mf,"C01_FLATNESS_MM"),c02=MD(mf,"C02_DIA_MM"),c02depth=MD(mf,"C02_DEPTH_MM"),c02depthtol=MD(mf,"C02_DEPTH_TOL_MM"),c03=MD(mf,"C03_PERP_MM"),c04=MD(mf,"C04_HOLE_DIA_MM"),c04pcd=MD(mf,"C04_PCD_MM"),c04ang=MD(mf,"C04_ANGLE_DEG"),c04pos=MD(mf,"C04_POSITION_MM"),c05=MD(mf,"C05_OD_MM"),c05tol=MD(mf,"C05_OD_TOL_MM"),c05t=MD(mf,"C05_THK_MM"),c05ttol=MD(mf,"C05_THK_TOL_MM"),c06=MD(mf,"C06_OAL_MM"),c06tol=MD(mf,"C06_TOL_MM"),c07=MD(mf,"C07_DIA_MM"),c08=MD(mf,"C08_DIA_MM"),wall=MD(mf,"C08_WALL_REF_MM"),c11=MD(mf,"C11_RUNOUT_MM"),bt=MD(mf,"BLIND_THK_MM"),bttol=MD(mf,"BLIND_TOL_MM"),ra=MD(mf,"J2_SEAL_RA_UM_MAX"),datumAArea1=MD(mf,"DATUM_A_FACE_AREA_1_M2"),datumAArea2=MD(mf,"DATUM_A_FACE_AREA_2_M2");
            string c02fit=M(mf,"C02_FIT"),c04fit=M(mf,"C04_FIT"),c07fit=M(mf,"C07_FIT"),c08fit=M(mf,"C08_FIT");bool c04cz=MB(mf,"C04_PATTERN_CZ"),c04mmr=MB(mf,"C04_POSITION_MMR"),c04datumBmmr=MB(mf,"C04_DATUM_B_MMR");
            Need(c04cz&&c04mmr&&!c04datumBmmr,"C04 manifest must be CZ+MMR with datum B RFS per EDR-033");
            Need(M(mf,"D006_RELEASE_STATE")=="HOLD","D006 release state must remain HOLD during engineering-review authoring");
            Need(M(mf,"C12")=="OPEN_DO_NOT_AUTHOR_NUMERIC","C12 must remain OPEN; numeric leak acceptance shall not be authored");
            string dsha=Sha(drawing),psha=Sha(partPath);

            string stamp=DateTime.Now.ToString("yyyyMMdd_HHmmss"),dir=Path.Combine(outRoot,"two_view_v2_"+stamp);Directory.CreateDirectory(dir);
            string partCopy=Path.Combine(dir,"K01-P-007.SLDPRT");
            string drawCopy=Path.Combine(dir,"K01-D-006.SLDDRW");
            string compatPart=Path.Combine(dir,"K01-P-007_Hermetic_Magnetic_Can_TWO_VIEW_V2_SOURCE_CANDIDATE.SLDPRT");
            string compatDraw=Path.Combine(dir,"K01-D-006_Hermetic_Magnetic_Can_TWO_VIEW_V2_CANDIDATE.SLDDRW");
            string compatPdf=Path.ChangeExtension(compatDraw,"PDF");
            File.Copy(partPath,partCopy,false);File.Copy(drawing,drawCopy,false);

            Type t=Type.GetTypeFromProgID("SldWorks.Application");Need(t!=null,"SOLIDWORKS ProgID missing");
            sw=Activator.CreateInstance(t) as SldWorks;Need(sw!=null,"SOLIDWORKS activation failed");created=true;sw.Visible=true;
            Need(typeof(SldWorks).Assembly.GetName().Version.Major==26,"requires SOLIDWORKS 2018 interop major 26");
            string oldRef=FindP007Reference(sw,drawCopy);Need(!String.IsNullOrWhiteSpace(oldRef),"P007 ref not found");Need(sw.ReplaceReferencedDocument(drawCopy,oldRef,partCopy),"ReplaceReferencedDocument failed");log.Add("RELINK old="+oldRef+" new="+partCopy);

            int pe=0,pw=0;part=sw.OpenDoc6(partCopy,(int)swDocumentTypes_e.swDocPART,(int)swOpenDocOptions_e.swOpenDocOptions_Silent,"",ref pe,ref pw) as ModelDoc2;Need(part!=null,"open part failed e="+pe+" w="+pw);
            List<Face2> fs=Faces(part);Need(fs.Count>5,"too few part faces");double xmin,xmax;PlaneExtents(fs,out xmin,out xmax);log.Add("GEOM XMIN="+xmin.ToString("0.######",CultureInfo.InvariantCulture)+" XMAX="+xmax.ToString("0.######",CultureInfo.InvariantCulture));
            List<Face2> aPlaneCandidates=FindPlanes(fs,xmin);log.Add("BIND C01_DATUM_A_COPLANAR candidates="+aPlaneCandidates.Count+" areas_m2=["+FaceAreaList(aPlaneCandidates)+"]");Need(aPlaneCandidates.Count>=2,"C01/Datum-A missing: fewer than two coplanar faces at J2 mating plane");
            Face2 a1=FindControlledPlaneByArea(aPlaneCandidates,datumAArea1,"C01_DATUM_A_PATCH_1",log),a2=FindControlledPlaneByArea(aPlaneCandidates,datumAArea2,"C01_DATUM_A_PATCH_2",log);Need(!Object.ReferenceEquals(a1,a2),"C01/Datum-A authority resolved both patches to the same face");List<Face2> aFaces=new List<Face2>{a1,a2};Face2 aFace=a1;log.Add("BIND C01_DATUM_A controlled_patches=2 ignored_other_coplanar="+(aPlaneCandidates.Count-2));
            Face2 c02f=FindUniqueCylinder(fs,c02,"C02_LOCATOR",log),c05f=FindUniqueCylinder(fs,c05,"C05_FLANGE_OD",log),c07f=FindUniqueCylinder(fs,c07,"C07_CAN_OD",log),c08f=FindUniqueCylinder(fs,c08,"C08_CAN_ID",log);
            List<Face2> c04fs=FindCylinders(fs,c04);log.Add("BIND C04_PATTERN candidates="+c04fs.Count);Need(c04fs.Count==3,"C04 ambiguous/missing pattern: expected 3 cylinders, got "+c04fs.Count);
            Face2 flangeRear=FindPlane(fs,xmin+c05t,"C05_FLANGE_REAR",log),locatorBack=FindPlane(fs,xmin+c02depth,"C02_LOCATOR_BACK",log),blindOuter=FindPlane(fs,xmax,"BLIND_OUTER",log),blindInner=FindPlane(fs,xmax-bt,"BLIND_INNER",log);

            int de=0,dw=0;doc=sw.OpenDoc6(drawCopy,(int)swDocumentTypes_e.swDocDRAWING,(int)swOpenDocOptions_e.swOpenDocOptions_Silent,"",ref de,ref dw) as ModelDoc2;Need(doc!=null,"open drawing failed e="+de+" w="+dw);DrawingDoc dr=doc as DrawingDoc;Need(dr!=null,"not drawing");
            List<VRec> vr=Views(dr,Path.GetFileName(partCopy));VRec section=null;foreach(VRec q in vr)if(q.section&&section==null)section=q;Need(section!=null,"section view missing");
            foreach(VRec q in vr)if(q!=section){try{q.v.SetVisible(false,false);log.Add("VIEW_HIDE "+q.name+" orient="+q.orient);}catch{}}
            HideOldControlledAnnotations(section.v,log);HideLegacySheetNotes(dr,log);
            Need(SetSheetScale(dr,5.0,1.0,log),"cannot set A3 sheet scale 5:1");bool firstAngle=SheetFirstAngle(dr);log.Add("SHEET_PROJECTION_FIRST_ANGLE="+firstAngle);Need(firstAngle,"drawing sheet must use first-angle projection per controlled K01 profile");

            View mating=dr.CreateDrawViewFromModelView3(partCopy,"*Left",0.302,0.170,0) as View;Need(mating!=null,"create *Left mating-side view failed");
            SetView(section.v,0.105,0.155,5.0);SetView(mating,0.302,0.165,5.0);doc.EditRebuild3();
            double[] so=Outline(section.v),mo=Outline(mating);Need(so.Length>=4&&mo.Length>=4,"view outlines missing");
            double sx0=so[0],sx1=so[2],sy0=so[1],sy1=so[3],scx=(sx0+sx1)*0.5,scy=(sy0+sy1)*0.5;double mx0=mo[0],mx1=mo[2],my0=mo[1],my1=mo[3],mcy=(my0+my1)*0.5;

            // ISO/GPS manufacturing dimensions: one controlled occurrence only; no model-item bulk import.
            DisplayDimension d06=TryLinearRobust(doc,section.v,aFace,blindOuter,c06,scx,sy1+0.032,"C06_OAL",log);bool b06=d06!=null&&SetSymTol(d06,c06tol,log,"C06_OAL");
            DisplayDimension d5t=TryLinearRobust(doc,section.v,aFace,flangeRear,c05t,scx-0.038,sy1+0.018,"C05_FLANGE_THK",log);bool b5t=d5t!=null&&SetSymTol(d5t,c05ttol,log,"C05_FLANGE_THK");
            DisplayDimension dbt=TryLinearRobust(doc,section.v,blindInner,blindOuter,bt,sx1-0.010,sy1+0.018,"BLIND_END_THK",log);bool bbt=dbt!=null&&SetSymTol(dbt,bttol,log,"BLIND_END_THK");
            DisplayDimension ddep=TryLinearRobust(doc,section.v,aFace,locatorBack,c02depth,sx0+0.030,sy0-0.014,"C02_LOCATOR_DEPTH",log);bool bdep=ddep!=null&&SetSymTol(ddep,c02depthtol,log,"C02_LOCATOR_DEPTH");

            // Radial sizes are authored on the mating end view where the cylindrical features project as true circles.
            // This is more robust in SW2018 than trying to create diameter dimensions from longitudinal section silhouettes.
            DisplayDimension d07=TryDiameter(doc,mating,c07f,c07,mx0-0.018,mcy+0.045,"C07_CAN_OD",log);bool b07=d07!=null&&SetFit(d07,"",c07fit);
            DisplayDimension d08=TryDiameter(doc,mating,c08f,c08,mx0-0.018,mcy-0.040,"C08_CAN_ID",log);bool b08=d08!=null&&SetFit(d08,c08fit,"");
            DisplayDimension d05=TryDiameter(doc,mating,c05f,c05,mx1+0.016,mcy+0.050,"C05_FLANGE_OD",log);bool b05=d05!=null&&SetSymTol(d05,c05tol,log,"C05_FLANGE_OD");
            DisplayDimension d02=TryDiameter(doc,mating,c02f,c02,mx1+0.016,mcy+0.018,"C02_LOCATOR_DIA",log);bool b02=d02!=null&&SetFit(d02,c02fit,"");
            DisplayDimension d04=TryDiameter(doc,mating,c04fs[0],c04,mx1+0.016,mcy-0.045,"C04_HOLE_DIA",log);bool b04=d04!=null&&SetFit(d04,c04fit,"");if(d04!=null){SetPrefix(d04,"3× ");SetSuffix(d04," THRU");}

            DatumTag da=CreateDatum(doc,section.v,aFace,"A",sx0-0.012,scy+0.006,log);
            DatumTag db=CreateDatum(doc,mating,c02f,"B",mx0-0.016,mcy+0.010,log);

            // Functional ISO GPS controls. C11 is relative to datum B only per EDR-029.
            string c01tol=c01.ToString("0.###",CultureInfo.InvariantCulture)+" CZ";
            Gtol g01=CreateGtol(doc,section.v,aFaces,"<IGTOL-FLAT>",false,"",c01tol,"","",sx0-0.012,sy1+0.004,"C01_FLATNESS_CZ_INLINE",false,log);
            Gtol g03=CreateGtol(doc,section.v,new List<Face2>{c02f},"<IGTOL-PERP>",true,"<MOD-MMC>",c03.ToString("0.###",CultureInfo.InvariantCulture),"A","",sx0+0.020,sy0-0.020,"C03_PERP_A",false,log);
            Gtol g11o=CreateGtol(doc,section.v,new List<Face2>{c07f},"<IGTOL-TRUN>",false,"",c11.ToString("0.###",CultureInfo.InvariantCulture),"B","",sx1+0.006,scy+0.023,"C11_RUNOUT_OD_B",false,log);
            Gtol g11i=CreateGtol(doc,section.v,new List<Face2>{c08f},"<IGTOL-TRUN>",false,"",c11.ToString("0.###",CultureInfo.InvariantCulture),"B","",sx1+0.006,scy-0.023,"C11_RUNOUT_ID_B",false,log);
            string c04tol=c04pos.ToString("0.###",CultureInfo.InvariantCulture)+" CZ";
            string c04mc=c04mmr?"<MOD-MMC>":"";
            Gtol g04=CreateGtol(doc,mating,c04fs,"<IGTOL-POSI>",true,c04mc,c04tol,"A","B",mx0+0.010,my0-0.018,"C04_POSITION_CZ_MMR_AB",false,log);

            bool sf=AddSurfaceFinish(doc,section.v,aFace,ra,sx0-0.012,scy+0.037,log);

            // Local, concise supplemental information. No ISO 2768 blanket tolerance and no generic all-over roughness.
            Note tedPcd=AddTedNote(doc,"Ø"+c04pcd.ToString("0.00",CultureInfo.InvariantCulture),mx0+0.008,my1+0.020,log,"C04_PCD_TED");
            Note tedAng=AddTedNote(doc,c04ang.ToString("0.###",CultureInfo.InvariantCulture)+"°",mx0+0.056,my1+0.020,log,"C04_ANGLE_TED");
            AddNote(doc,"PCD",mx0-0.006,my1+0.020,log,"C04_PCD_LABEL");
            AddNote(doc,"WALL "+wall.ToString("0.00",CultureInfo.InvariantCulture)+" REF",sx1-0.050,sy0-0.012,log,"C08_WALL_AUX");
            AddNote(doc,"MATERIAL: "+M(mf,"MATERIAL"),0.018,0.072,log,"C09_MATERIAL");
            AddNote(doc,"DEBURR; BREAK NON-FUNCTIONAL SHARP EDGES 0.1–0.2 mm.",0.018,0.060,log,"EDGE_1");
            AddNote(doc,"DO NOT BREAK/ABRADE DATUM A, Ø"+c02.ToString("0.00",CultureInfo.InvariantCulture)+" "+c02fit+" LOCATOR OR SEAL-CONTACT EDGES.",0.018,0.050,log,"EDGE_2");
            AddNote(doc,"P007 MONOLITHIC; NO PERMANENT P003↔P007 WELD.",0.018,0.040,log,"C10_ARCHITECTURE");
            AddNote(doc,"ENGINEERING REVIEW — NOT FOR MANUFACTURE",0.018,0.030,log,"RELEASE_STATE");

            doc.ClearSelection2(true);doc.ForceRebuild3(false);doc.ViewZoomtofit2();doc.WindowRedraw();
            SaveAs(doc,drawCopy);string pdf=Path.ChangeExtension(drawCopy,"PDF"),bmp=Path.ChangeExtension(drawCopy,"BMP");SaveAs(doc,pdf);doc.ViewZoomtofit2();bool bmpOk=doc.SaveBMP(bmp,1800,1273);

            int prodDimCount=(b02?1:0)+(bdep?1:0)+(b04?1:0)+(b05?1:0)+(b5t?1:0)+(b06?1:0)+(b07?1:0)+(b08?1:0)+(bbt?1:0);
            int auxDimCount=0;int datumCount=(da!=null?1:0)+(db!=null?1:0);int gtolCount=(g01!=null?1:0)+(g03!=null?1:0)+(g04!=null?1:0)+(g11o!=null?1:0)+(g11i!=null?1:0);
            string status=(prodDimCount==9&&datumCount==2&&gtolCount==5&&sf)?"PASS_D006_TWO_VIEW_V2_ISO_SEMANTIC_COMPLETE__MANUAL_VISUAL_FINISH":"PARTIAL_D006_TWO_VIEW_V2_ISO__MANUAL_FINISH_REQUIRED";
            string title=doc.GetTitle();sw.CloseDoc(title);doc=null;sw.CloseDoc(part.GetTitle());part=null;
            Need(Sha(drawing)==dsha,"input V1 drawing changed");Need(Sha(partPath)==psha,"input V1 part changed");

            File.Copy(partCopy,compatPart,true);File.Copy(drawCopy,compatDraw,true);File.Copy(pdf,compatPdf,true);

            var sb=new StringBuilder();
            sb.AppendLine("STATUS="+status);sb.AppendLine("TZ_PROTOCOL=K01-TZ-AI-OPERATING_v1.0");sb.AppendLine("GOAL_LOCK=FULL_K01-D-006_MANUFACTURING_DRAWING");sb.AppendLine("WIP_LIMIT=1");sb.AppendLine("RELEASE_STATE=HOLD");sb.AppendLine("P007_READINESS="+M(mf,"P007_READINESS"));
            sb.AppendLine("INPUT_DRAWING="+drawing);sb.AppendLine("INPUT_DRAWING_SHA256="+dsha);sb.AppendLine("INPUT_PART="+partPath);sb.AppendLine("INPUT_PART_SHA256="+psha);sb.AppendLine("OUTPUT_DRAWING="+drawCopy);sb.AppendLine("OUTPUT_PDF="+pdf);sb.AppendLine("OUTPUT_BMP="+bmp);sb.AppendLine("COMPAT_DRAWING_ALIAS="+compatDraw);sb.AppendLine("COMPAT_PDF_ALIAS="+compatPdf);sb.AppendLine("BMP_OK="+bmpOk);
            sb.AppendLine("SECTION_VIEW="+VName(section.v));sb.AppendLine("MATING_VIEW="+VName(mating));sb.AppendLine("MATING_ORIENTATION=*Left");sb.AppendLine("VISIBLE_MANUFACTURING_VIEWS=2");sb.AppendLine("SHEET_SCALE=5:1");sb.AppendLine("SHEET_FIRST_ANGLE="+firstAngle);sb.AppendLine("MODEL_ITEM_BULK_IMPORT=False");sb.AppendLine("CONSTRUCTION_MODEL_DIMS_IMPORTED=0");
            sb.AppendLine("PRODUCTION_DIMENSIONS_OK="+prodDimCount+"/9");sb.AppendLine("AUXILIARY_DIMENSIONS_OK=0/0");sb.AppendLine("DATUMS_OK="+datumCount+"/2");sb.AppendLine("GTOLS_OK="+gtolCount+"/5");sb.AppendLine("SURFACE_RA_0_8_CREATED="+sf);sb.AppendLine("SURFACE_TEXTURE_SCOPE=J2_DATUM_A_ONLY__ENGINEERING_REVIEW_CONDITIONAL");sb.AppendLine("GENERIC_SURFACE_FINISH_AUTHORED=False");sb.AppendLine("GENERAL_TOLERANCE_NOTE_AUTHORED=False");sb.AppendLine("C12_NUMERIC_AUTHORED=False");sb.AppendLine("C02_DEPTH_PRESENTATION=2.00_PM0.05__EDR_032");sb.AppendLine("C08_WALL_PRESENTATION=REF_NOTE");sb.AppendLine("C01_CZ_REPRESENTATION=INLINE_LITERAL_IN_TOLERANCE_COMPARTMENT__SEMANTIC_AUTHORITY_EDR_030");sb.AppendLine("C04_PATTERN_SEMANTICS=POSITION_0.15_CZ_MMR_A_B__EDR_033__DATUM_B_RFS");sb.AppendLine("C04_TED_PRESENTATION=BOXED_CONTROLLED_NOTES_FROM_MANIFEST__ISO_TED");sb.AppendLine("C04_TED_BOXES_OK="+((tedPcd!=null&&tedAng!=null)?"2/2":"PARTIAL"));sb.AppendLine("SW2018_ISO5458_LIMITATION=NO_NATIVE_CZ_OBJECT__INLINE_CONTROLLED_REPRESENTATION_REQUIRES_VISUAL_QA");sb.AppendLine("SOURCE_INVARIANT=True");
            for(int i=0;i<log.Count;i++)sb.AppendLine("LOG_"+(i+1)+"="+One(log[i]));File.WriteAllText(report,sb.ToString(),Encoding.UTF8);

            Console.WriteLine("STATUS: "+status);Console.WriteLine("RELEASE: HOLD (project release unchanged; drawing semantic candidate only)");Console.WriteLine("VIEWS: SECTION + J2 MATING (*Left)");Console.WriteLine("SHEET SCALE: 5:1");Console.WriteLine("PRODUCTION DIMENSIONS: "+prodDimCount+" / 9");Console.WriteLine("DIM STATUS: C02_DIA="+(b02?"PASS":"FAIL")+" C02_DEPTH="+(bdep?"PASS":"FAIL")+" C04="+(b04?"PASS":"FAIL")+" C05_OD="+(b05?"PASS":"FAIL")+" C05_THK="+(b5t?"PASS":"FAIL")+" C06="+(b06?"PASS":"FAIL")+" C07="+(b07?"PASS":"FAIL")+" C08="+(b08?"PASS":"FAIL")+" BLIND="+(bbt?"PASS":"FAIL"));Console.WriteLine("AUXILIARY DIMENSIONS: 0 / 0");Console.WriteLine("DATUMS: "+datumCount+" / 2");Console.WriteLine("GTOLS: "+gtolCount+" / 5");Console.WriteLine("C04: POSITION ⌀"+c04pos.ToString("0.###",CultureInfo.InvariantCulture)+" CZ M | A | B (datum B RFS)");Console.WriteLine("SURFACE FINISH J2 Ra "+ra.ToString("0.###",CultureInfo.InvariantCulture)+": "+(sf?"PASS":"HOLD"));Console.WriteLine("MODEL-ITEM BULK IMPORT: DISABLED");if(prodDimCount<9){Console.WriteLine("FAILED-DIM DIAGNOSTICS:");foreach(string z in log)if(z.StartsWith("DIM C02_",StringComparison.Ordinal)||z.StartsWith("DIM C05_",StringComparison.Ordinal)||z.StartsWith("DIM C06_",StringComparison.Ordinal)||z.StartsWith("DIM BLIND_",StringComparison.Ordinal)||z.StartsWith("TOL C02_",StringComparison.Ordinal)||z.StartsWith("TOL C05_",StringComparison.Ordinal)||z.StartsWith("TOL C06_",StringComparison.Ordinal)||z.StartsWith("TOL BLIND_",StringComparison.Ordinal)||z.StartsWith("VEDGE C02_",StringComparison.Ordinal)||z.StartsWith("VEDGE C05_",StringComparison.Ordinal)||z.StartsWith("VEDGE C06_",StringComparison.Ordinal)||z.StartsWith("VEDGE BLIND_",StringComparison.Ordinal))Console.WriteLine("  "+z);}Console.WriteLine("DRAWING: "+drawCopy);Console.WriteLine("PDF: "+pdf);Console.WriteLine("REPORT: "+report);Console.WriteLine("C04 TED BOXES: "+((tedPcd!=null&&tedAng!=null)?"2 / 2":"PARTIAL"));Console.WriteLine("NEXT: visual-only ISO D8 finish. Verify inline CZ rendering in C01/C04, leader routing, title block, first-angle symbol and readability. Do not re-enter engineering values.");
            return status.StartsWith("PASS_")?0:3;
        }
        catch(Exception ex){try{File.WriteAllText(report,"STATUS=HOLD_D006_TWO_VIEW_V2\nERROR="+ex.ToString()+"\n",Encoding.UTF8);}catch{}Console.Error.WriteLine(ex.ToString());return 2;}
        finally{try{if(doc!=null&&sw!=null)sw.CloseDoc(doc.GetTitle());}catch{}try{if(part!=null&&sw!=null)sw.CloseDoc(part.GetTitle());}catch{}try{if(created&&sw!=null)sw.ExitApp();}catch{}}
    }
}
