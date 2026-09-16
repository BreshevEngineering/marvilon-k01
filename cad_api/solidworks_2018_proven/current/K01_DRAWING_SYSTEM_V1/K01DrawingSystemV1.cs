using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using System.Web.Script.Serialization;
using SolidWorks.Interop.sldworks;
using SolidWorks.Interop.swconst;

public class K01DrawingSystemV1
{
    public class Spec
    {
        public string schema;
        public string drawing_id;
        public string part_id;
        public string title;
        public string status;
        public string model_path;
        public string output_root;
        public string sheet;
        public double sheet_scale;
        public string projection;
        public string units;
        public string material;
        public List<ViewSpec> view_definitions;
        public Dictionary<string,BindingSpec> bindings;
        public List<DatumSpec> datum_features;
        public List<AnnotationSpec> annotations;
        public Dictionary<string,string> title_block_properties;
        public List<string> release_blockers;
        public List<string> review_notes;
    }
    public class ViewSpec
    {
        public string id;
        public string kind;
        public string orientation;
        public string parent_orientation;
        public string section_label;
        public double x_m;
        public double y_m;
        public double scale;
    }
    public class BindingSpec
    {
        public string kind;
        public double diameter_mm;
        public int count;
        public string x_region;
        public string cylinder;
        public string end;
        public string selection;
        public string side;
        public List<double> area_m2_targets;
    }
    public class DatumSpec
    {
        public string id;
        public string interface_id;
        public string view;
        public string feature;
        public string selector;
        public string binding;
    }
    public class AnnotationSpec
    {
        public string id;
        public string kind;
        public string view;
        public string binding;
        public string from_binding;
        public string to_binding;
        public double nominal_mm;
        public double sym_tol_mm;
        public double upper_tol_mm;
        public double lower_tol_mm;
        public string hole_fit;
        public string shaft_fit;
        public string text;
        public string symbol;
        public bool diameter_zone;
        public double tolerance_mm;
        public string material_modifier;
        public string zone_modifier;
        public string prefix;
        public string suffix;
        public double ra_um;
        public string datum_1;
        public string datum_2;
        public string state;
        public double x_m;
        public double y_m;
    }
    public class PlacementPoint
    {
        public double x_m;
        public double y_m;
        public double scale;
    }
    public class PlacementProfile
    {
        public string schema;
        public string drawing_id;
        public Dictionary<string,PlacementPoint> views;
        public Dictionary<string,PlacementPoint> annotations;
    }

    static string Arg(string[] a,string k){for(int i=0;i<a.Length-1;i++)if(a[i]==k)return a[i+1];return null;}
    static void Need(bool ok,string msg){if(!ok)throw new Exception(msg);}
    static bool Eq(string a,string b){return String.Equals(a??"",b??"",StringComparison.OrdinalIgnoreCase);}
    static IEnumerable Items(object o){if(o==null)yield break;Array a=o as Array;if(a!=null){foreach(object x in a)yield return x;yield break;}IEnumerable e=o as IEnumerable;if(e!=null)foreach(object x in e)yield return x;}
    static string One(string s){return (s??"").Replace("\r"," ").Replace("\n"," ").Replace("=","-");}
    static string F(double x){return x.ToString("0.###",CultureInfo.InvariantCulture);}
    static string AName(string id){return "K01DS_"+(id??"").Replace(" ","_");}
    static PlacementPoint PPoint(PlacementProfile p,string id,double x,double y,double scale){PlacementPoint q=null;if(p!=null&&p.annotations!=null&&p.annotations.TryGetValue(id,out q)&&q!=null)return q;return new PlacementPoint{x_m=x,y_m=y,scale=scale};}
    static PlacementPoint VPoint(PlacementProfile p,string id,double x,double y,double scale){PlacementPoint q=null;if(p!=null&&p.views!=null&&p.views.TryGetValue(id,out q)&&q!=null)return q;return new PlacementPoint{x_m=x,y_m=y,scale=scale};}
    static PlacementProfile LoadPlacement(string path,string drawingId,List<string> log){if(String.IsNullOrWhiteSpace(path)||!File.Exists(path)){log.Add("PLACEMENT seed=SPEC");return null;}PlacementProfile p=new JavaScriptSerializer().Deserialize<PlacementProfile>(File.ReadAllText(path,Encoding.UTF8));Need(p!=null&&Eq(p.schema,"k01.drawing_placement.v1"),"bad placement schema");Need(Eq(p.drawing_id,drawingId),"placement drawing_id mismatch");log.Add("PLACEMENT profile="+path);return p;}
    static string Sha(string p){using(FileStream fs=new FileStream(p,FileMode.Open,FileAccess.Read,FileShare.ReadWrite|FileShare.Delete))using(SHA256 h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(fs)).Replace("-","").ToLowerInvariant();}
    static double[] DA(object o){var z=new List<double>();foreach(object q in Items(o))try{z.Add(Convert.ToDouble(q,CultureInfo.InvariantCulture));}catch{}return z.ToArray();}
    static string VName(View v){try{return v.GetName2()??"";}catch{return "";}}
    static double[] Outline(View v){try{return DA(v.GetOutline());}catch{return new double[0];}}
    static void SetView(View v,double x,double y,double scale){try{v.PositionLocked=false;}catch{}try{v.UseSheetScale=0;}catch{}try{v.UseParentScale=false;}catch{}try{v.ScaleDecimal=scale;}catch{}try{v.Position=new double[]{x,y};}catch{}}
    static bool SaveAs(ModelDoc2 doc,string p){int e=0,w=0;bool ok=doc.Extension.SaveAs(p,(int)swSaveAsVersion_e.swSaveAsCurrentVersion,(int)swSaveAsOptions_e.swSaveAsOptions_Silent,null,ref e,ref w);if(!ok||e!=0)throw new Exception("SaveAs failed "+p+" e="+e+" w="+w);return true;}
    static bool SheetFirstAngle(DrawingDoc dr){try{Sheet sh=dr.GetCurrentSheet() as Sheet;double[] p=sh==null?new double[0]:DA(sh.GetProperties2());return p.Length>=5&&Math.Abs(p[4])>0.5;}catch{return false;}}
    static bool SetSheetScale(DrawingDoc dr,double num,double den,List<string> log){try{Sheet sh=dr.GetCurrentSheet() as Sheet;Need(sh!=null,"current sheet missing");bool ok=sh.SetScale(num,den,false,false);log.Add("SHEET_SCALE "+F(num)+":"+F(den)+" ok="+ok);return ok;}catch(Exception ex){log.Add("SHEET_SCALE FAIL="+One(ex.Message));return false;}}

    static Surface Surf(Face2 f){try{return f.IGetSurface();}catch{return null;}}
    static double PlaneX(Face2 f){Surface s=Surf(f);if(s==null||!s.IsPlane())return Double.NaN;double[] p=DA(s.PlaneParams);return p.Length>=6?p[3]:Double.NaN;}
    static double CylRadiusMm(Face2 f){Surface s=Surf(f);if(s==null||!s.IsCylinder())return Double.NaN;double[] p=DA(s.CylinderParams);return p.Length>=7?p[6]*1000.0:Double.NaN;}
    static double Area(Face2 f){try{return f.GetArea();}catch{return 0;}}
    static double[] Box(Face2 f){try{return DA(f.GetBox());}catch{return new double[0];}}
    static double CenterXmm(Face2 f){double[] b=Box(f);return b.Length>=6?(b[0]+b[3])*500.0:Double.NaN;}
    static void XExtentsMm(Face2 f,out double mn,out double mx){double[] b=Box(f);Need(b.Length>=6,"face bbox unavailable");mn=Math.Min(b[0],b[3])*1000.0;mx=Math.Max(b[0],b[3])*1000.0;}
    static List<Face2> Faces(ModelDoc2 part){var r=new List<Face2>();PartDoc pd=part as PartDoc;if(pd==null)return r;foreach(object bo in Items(pd.GetBodies2((int)swBodyType_e.swSolidBody,true))){Body2 b=bo as Body2;if(b==null)continue;foreach(object fo in Items(b.GetFaces())){Face2 f=fo as Face2;if(f!=null)r.Add(f);}}return r;}
    static List<Face2> Cylinders(List<Face2> fs,double dia,string xr){var r=new List<Face2>();foreach(Face2 f in fs){double rr=CylRadiusMm(f);if(Double.IsNaN(rr)||Math.Abs(2.0*rr-dia)>0.02)continue;double cx=CenterXmm(f);if(Eq(xr,"NEGATIVE")&&(!Double.IsNaN(cx)&&cx>=0))continue;if(Eq(xr,"POSITIVE")&&(!Double.IsNaN(cx)&&cx<=0))continue;r.Add(f);}return r;}
    static Face2 PlaneAtX(List<Face2> fs,double xMm,string role,List<string> log){double best=1e99;var near=new List<Face2>();foreach(Face2 f in fs){double x=PlaneX(f);if(Double.IsNaN(x))continue;double d=Math.Abs(x*1000.0-xMm);if(d<best-0.005){best=d;near.Clear();near.Add(f);}else if(Math.Abs(d-best)<=0.005)near.Add(f);}Need(near.Count>0&&best<=0.25,role+" plane missing near approximate cylinder trim x="+F(xMm)+"; nearest delta mm="+F(best));double target=PlaneX(near[0])*1000.0;var cop=new List<Face2>();foreach(Face2 f in fs){double x=PlaneX(f);if(!Double.IsNaN(x)&&Math.Abs(x*1000.0-target)<=0.005)cop.Add(f);}cop.Sort(delegate(Face2 a,Face2 b){return Area(b).CompareTo(Area(a));});Need(cop.Count>0,role+" coplanar set missing");log.Add("BIND "+role+" approx_trim_x_mm="+F(xMm)+" resolved_plane_x_mm="+F(target)+" trim_delta_mm="+F(best)+" coplanar="+cop.Count+" selection=LARGEST_AREA");return cop[0];}
    static List<Face2> PlaneSetAtXByAreas(List<Face2> fs,double xMm,List<double> targets,string role,List<string> log){
        Need(targets!=null&&targets.Count>0,role+" area targets missing");double best=1e99;double targetX=Double.NaN;foreach(Face2 f in fs){double x=PlaneX(f);if(Double.IsNaN(x))continue;double d=Math.Abs(x*1000.0-xMm);if(d<best){best=d;targetX=x*1000.0;}}Need(!Double.IsNaN(targetX)&&best<=0.25,role+" plane-set missing near cylinder trim x="+F(xMm));var cop=new List<Face2>();foreach(Face2 f in fs){double x=PlaneX(f);if(!Double.IsNaN(x)&&Math.Abs(x*1000.0-targetX)<=0.005)cop.Add(f);}var outp=new List<Face2>();foreach(double ta in targets){var hit=new List<Face2>();foreach(Face2 f in cop){double tol=Math.Max(1e-9,Math.Abs(ta)*0.005);if(Math.Abs(Area(f)-ta)<=tol)hit.Add(f);}Need(hit.Count==1,role+" area signature ambiguous/missing target="+ta.ToString("0.############",CultureInfo.InvariantCulture)+" matches="+hit.Count+" coplanar="+cop.Count);outp.Add(hit[0]);}Need(outp.Count==targets.Count,role+" plane-set count mismatch");log.Add("BIND "+role+" kind=PLANE_SET_AT_CYL_END plane_x_mm="+F(targetX)+" selected="+outp.Count+" coplanar="+cop.Count);return outp;
    }

    static Face2 ExtremePlaneX(List<Face2> fs,string side,string role,List<string> log)
    {
        var planes=new List<Face2>();double target=Eq(side,"MIN_X")?Double.PositiveInfinity:Double.NegativeInfinity;
        foreach(Face2 f in fs){double x=PlaneX(f);if(Double.IsNaN(x))continue;planes.Add(f);if(Eq(side,"MIN_X")){if(x<target)target=x;}else{if(x>target)target=x;}}
        Need(planes.Count>0&&!Double.IsInfinity(target),role+" extreme plane missing");var cop=new List<Face2>();foreach(Face2 f in planes){double x=PlaneX(f);if(!Double.IsNaN(x)&&Math.Abs(x-target)<=0.000005)cop.Add(f);}
        Need(cop.Count>0,role+" extreme coplanar set missing");cop.Sort(delegate(Face2 a,Face2 b){return Area(b).CompareTo(Area(a));});Face2 pick=cop[0];
        if(cop.Count>1){double a0=Area(cop[0]),a1=Area(cop[1]);Need(Math.Abs(a0-a1)>Math.Max(1e-12,Math.Abs(a0)*1e-6),role+" extreme plane ambiguous: equal-area coplanar faces="+cop.Count);}
        log.Add("BIND "+role+" kind=PLANE_EXTREME_X side="+side+" plane_x_mm="+F(target*1000.0)+" coplanar="+cop.Count+" selection=LARGEST_AREA");return pick;
    }

    static Dictionary<string,List<Face2>> ResolveBindings(Spec spec,List<Face2> fs,List<string> log)
    {
        var outp=new Dictionary<string,List<Face2>>(StringComparer.OrdinalIgnoreCase);
        foreach(KeyValuePair<string,BindingSpec> kv in spec.bindings)
        {
            string id=kv.Key;BindingSpec b=kv.Value;
            if(Eq(b.kind,"CYLINDER")||Eq(b.kind,"CYLINDER_SET"))
            {
                List<Face2> q=Cylinders(fs,b.diameter_mm,b.x_region);
                int expected=b.count>0?b.count:(Eq(b.kind,"CYLINDER")?1:0);
                log.Add("BIND "+id+" kind="+b.kind+" dia="+F(b.diameter_mm)+" region="+(b.x_region??"ANY")+" matches="+q.Count+" expected="+expected);
                if(expected>0)Need(q.Count==expected,id+" binding ambiguous/missing: expected "+expected+" cylinder face(s), got "+q.Count);
                outp[id]=q;
            }
            else if(Eq(b.kind,"PLANE_EXTREME_X"))
            {
                Need(Eq(b.side,"MIN_X")||Eq(b.side,"MAX_X"),id+" PLANE_EXTREME_X side must be MIN_X or MAX_X");
                outp[id]=new List<Face2>{ExtremePlaneX(fs,b.side,id,log)};
            }
        }
        bool progress=true;int guard=0;
        while(progress&&guard++<20)
        {
            progress=false;
            foreach(KeyValuePair<string,BindingSpec> kv in spec.bindings)
            {
                if(outp.ContainsKey(kv.Key))continue;BindingSpec b=kv.Value;
                if((Eq(b.kind,"PLANE_AT_CYL_END")||Eq(b.kind,"PLANE_SET_AT_CYL_END"))&&!String.IsNullOrWhiteSpace(b.cylinder)&&outp.ContainsKey(b.cylinder))
                {
                    List<Face2> cq=outp[b.cylinder];Need(cq.Count==1,kv.Key+" requires one cylinder binding "+b.cylinder);double mn,mx;XExtentsMm(cq[0],out mn,out mx);double x=Eq(b.end,"MIN_X")?mn:mx;if(Eq(b.kind,"PLANE_SET_AT_CYL_END"))outp[kv.Key]=PlaneSetAtXByAreas(fs,x,b.area_m2_targets,kv.Key,log);else{Face2 p=PlaneAtX(fs,x,kv.Key,log);outp[kv.Key]=new List<Face2>{p};}progress=true;
                }
            }
        }
        foreach(string id in spec.bindings.Keys)Need(outp.ContainsKey(id),"unresolved binding: "+id);
        return outp;
    }

    static bool SelectInView(View v,object modelEntity,bool append){if(v==null||modelEntity==null)return false;try{Entity ce=v.GetCorrespondingEntity(modelEntity) as Entity;if(ce!=null&&ce.Select4(append,null))return true;}catch{}try{return v.SelectEntity(modelEntity,append);}catch{return false;}}
    static double UserMm(DisplayDimension dd,ModelDoc2 doc){try{Dimension d=dd.GetDimension2(0);return d==null?Double.NaN:d.IGetUserValueIn2(doc);}catch{return Double.NaN;}}
    static Annotation Ann(DisplayDimension dd){try{return dd==null?null:dd.GetAnnotation() as Annotation;}catch{return null;}}
    static void Hide(Annotation a){try{if(a!=null)a.Visible=(int)swAnnotationVisibilityState_e.swAnnotationHidden;}catch{}}
    static void FormatDim(DisplayDimension dd){if(dd==null)return;try{dd.ShowParenthesis=false;}catch{}try{dd.ShowLowerParenthesis=false;}catch{}try{dd.SetPrecision2(2,2,2,2);}catch{}}
    static void NameDim(DisplayDimension dd,string name){try{Dimension d=dd.GetDimension2(0);if(d!=null)d.Name=name;}catch{}}
    static DisplayDimension AcceptDim(ModelDoc2 doc,DisplayDimension dd,double expected,string id,string path,List<string> log){if(dd==null)return null;double mm=UserMm(dd,doc);if(!Double.IsNaN(mm)&&Math.Abs(Math.Abs(mm)-expected)>0.03){Hide(Ann(dd));log.Add("DIM "+id+" REJECT path="+path+" actual="+F(mm)+" expected="+F(expected));return null;}NameDim(dd,id);try{Annotation an=Ann(dd);if(an!=null)an.SetName(AName(id));}catch{}FormatDim(dd);log.Add("DIM "+id+" OK path="+path+" actual="+(Double.IsNaN(mm)?"NaN":F(mm)));doc.ClearSelection2(true);return dd;}
    static DisplayDimension TryDiameter(ModelDoc2 doc,View v,Face2 face,double expected,double x,double y,string id,List<string> log){var c=new List<object>();foreach(object eo in Items(face.GetEdges()))if(eo is Entity)c.Add(eo);c.Add(face);int k=0;foreach(object q in c){k++;doc.ClearSelection2(true);if(!SelectInView(v,q,false))continue;DisplayDimension dd=null;try{dd=doc.AddDiameterDimension2(x,y,0) as DisplayDimension;}catch{}DisplayDimension ok=AcceptDim(doc,dd,expected,id,"diameter_"+k,log);if(ok!=null)return ok;}log.Add("DIM "+id+" FAIL");return null;}
    static DisplayDimension TryLinear(ModelDoc2 doc,View v,Face2 a,Face2 b,double expected,double x,double y,string id,List<string> log){for(int mode=0;mode<2;mode++){doc.ClearSelection2(true);if(!SelectInView(v,a,false)||!SelectInView(v,b,true)){doc.ClearSelection2(true);continue;}DisplayDimension dd=null;try{dd=mode==0?doc.AddHorizontalDimension2(x,y,0) as DisplayDimension:doc.AddDimension2(x,y,0) as DisplayDimension;}catch{}DisplayDimension ok=AcceptDim(doc,dd,expected,id,"face_pair_"+mode,log);if(ok!=null)return ok;}var ea=new List<object>();foreach(object q in Items(a.GetEdges()))if(q is Entity)ea.Add(q);var eb=new List<object>();foreach(object q in Items(b.GetEdges()))if(q is Entity)eb.Add(q);int n=0;foreach(object qa in ea)foreach(object qb in eb){n++;doc.ClearSelection2(true);if(!SelectInView(v,qa,false)||!SelectInView(v,qb,true))continue;DisplayDimension dd=null;try{dd=doc.AddHorizontalDimension2(x,y,0) as DisplayDimension;}catch{}DisplayDimension ok=AcceptDim(doc,dd,expected,id,"edge_pair_"+n,log);if(ok!=null)return ok;}log.Add("DIM "+id+" FAIL");return null;}
    static List<Entity> VisibleEdgesOnPlane(ModelDoc2 doc,View v,Face2 plane,string role,List<string> log){var r=new List<Entity>();if(doc==null||v==null||plane==null)return r;double tx=PlaneX(plane);if(Double.IsNaN(tx))return r;try{DrawingComponent dc=v.RootDrawingComponent as DrawingComponent;Component2 comp=dc==null?null:dc.Component as Component2;if(comp==null){log.Add("VEDGE "+role+" no root component");return r;}object raw=v.GetVisibleEntities2(comp,(int)swViewEntityType_e.swViewEntityType_Edge);foreach(object q in Items(raw)){Entity ent=q as Entity;Edge e=q as Edge;if(ent==null||e==null)continue;bool hit=false;try{foreach(object fo in Items(e.GetTwoAdjacentFaces2())){Face2 f=fo as Face2;if(f==null)continue;double x=PlaneX(f);if(!Double.IsNaN(x)&&Math.Abs(x-tx)<=0.00003){hit=true;break;}}}catch{}if(hit)r.Add(ent);}log.Add("VEDGE "+role+" target_x_mm="+(tx*1000.0).ToString("0.######",CultureInfo.InvariantCulture)+" visible_matches="+r.Count);}catch(Exception ex){log.Add("VEDGE "+role+" FAIL="+One(ex.Message));}return r;}
    static bool SelectDrawingEntity(ModelDoc2 doc,View v,Entity ent,bool append){if(doc==null||v==null||ent==null)return false;try{SelectionMgr sm=doc.SelectionManager as SelectionMgr;if(sm==null)return false;SelectData sd=sm.CreateSelectData() as SelectData;if(sd!=null)sd.View=v;return ent.Select4(append,sd);}catch{return false;}}
    static DisplayDimension TryLinearVisiblePlaneEdges(ModelDoc2 doc,View v,Face2 a,Face2 b,double expected,double x,double y,string id,List<string> log){var ea=VisibleEdgesOnPlane(doc,v,a,id+"_A",log);var eb=VisibleEdgesOnPlane(doc,v,b,id+"_B",log);int n=0;foreach(Entity qa in ea)foreach(Entity qb in eb){n++;doc.ClearSelection2(true);if(!SelectDrawingEntity(doc,v,qa,false)||!SelectDrawingEntity(doc,v,qb,true))continue;DisplayDimension dd=null;try{dd=doc.AddHorizontalDimension2(x,y,0) as DisplayDimension;}catch{}DisplayDimension ok=AcceptDim(doc,dd,expected,id,"visible_edge_pair_"+n,log);if(ok!=null)return ok;doc.ClearSelection2(true);if(!SelectDrawingEntity(doc,v,qa,false)||!SelectDrawingEntity(doc,v,qb,true))continue;try{dd=doc.AddDimension2(x,y,0) as DisplayDimension;}catch{}ok=AcceptDim(doc,dd,expected,id,"visible_edge_generic_"+n,log);if(ok!=null)return ok;}log.Add("DIM "+id+" visible-plane-edge fallback failed pairs="+(ea.Count*eb.Count));return null;}
    static DisplayDimension TryLinearRobust(ModelDoc2 doc,View v,Face2 a,Face2 b,double expected,double x,double y,string id,List<string> log){DisplayDimension dd=TryLinear(doc,v,a,b,expected,x,y,id,log);return dd??TryLinearVisiblePlaneEdges(doc,v,a,b,expected,x,y,id,log);}
    static bool SetFit(DisplayDimension dd,string hole,string shaft){try{Dimension d=dd.GetDimension2(0);DimensionTolerance t=d==null?null:d.Tolerance as DimensionTolerance;if(t==null)return false;t.Type=(int)swTolType_e.swTolFIT;bool ok=t.SetFitValues(hole??"",shaft??"");FormatDim(dd);return ok;}catch{return false;}}
    static bool SetSymTol(DisplayDimension dd,double tolMm,List<string> log,string id){if(dd==null)return false;try{Dimension d=dd.GetDimension2(0);DimensionTolerance t=d==null?null:d.Tolerance as DimensionTolerance;if(t==null)return false;double v=tolMm/1000.0;t.Type=(int)swTolType_e.swTolSYMMETRIC;bool ok=t.SetValues2(-v,v,(int)swSetValueInConfiguration_e.swSetValue_InThisConfiguration,null);if(!ok)ok=t.SetValues2(-v,v,(int)swSetValueInConfiguration_e.swSetValue_InAllConfigurations,null);if(!ok){bool a=d.SetToleranceType((int)swTolType_e.swTolSYMMETRIC);bool b=d.SetToleranceValues(-v,v);ok=a&&b;}FormatDim(dd);log.Add("TOL "+id+" SYM "+F(tolMm)+" ok="+ok);return ok;}catch(Exception ex){log.Add("TOL "+id+" SYM FAIL="+One(ex.Message));return false;}}
    static bool SetAsymTolOrFallback(DisplayDimension dd,double lowerMm,double upperMm,List<string> log,string id){if(dd==null)return false;try{Dimension d=dd.GetDimension2(0);DimensionTolerance t=d==null?null:d.Tolerance as DimensionTolerance;bool ok=false;if(t!=null){double lo=lowerMm/1000.0,up=upperMm/1000.0;try{t.Type=1;ok=t.SetValues2(lo,up,(int)swSetValueInConfiguration_e.swSetValue_InThisConfiguration,null);}catch{}if(!ok){try{bool a=d.SetToleranceType(1);bool b=d.SetToleranceValues(lo,up);ok=a&&b;}catch{}}}if(!ok){try{dd.SetText((int)swDimensionTextParts_e.swDimensionTextSuffix," +"+F(upperMm)+"/"+F(lowerMm));ok=true;log.Add("TOL "+id+" ASYM native=FAIL presentation_fallback=PASS");}catch{}}else log.Add("TOL "+id+" ASYM native=PASS");FormatDim(dd);return ok;}catch(Exception ex){log.Add("TOL "+id+" ASYM FAIL="+One(ex.Message));return false;}}

    static DatumTag CreateDatum(ModelDoc2 doc,View v,Face2 f,string label,double x,double y,List<string> log){try{doc.ClearSelection2(true);Need(SelectInView(v,f,false),"datum "+label+" selection failed");DatumTag dt=doc.IInsertDatumTag2();Need(dt!=null,"datum "+label+" insert null");Need(dt.SetLabel(label),"datum "+label+" label failed");Annotation a=dt.GetAnnotation() as Annotation;if(a!=null){a.SetPosition(x,y,0);try{a.SetName(AName("DATUM_"+label));}catch{}}doc.ClearSelection2(true);log.Add("DATUM "+label+" OK view="+VName(v));return dt;}catch(Exception ex){doc.ClearSelection2(true);log.Add("DATUM "+label+" FAIL="+One(ex.Message));return null;}}
    static string GSymbol(string s){if(Eq(s,"PERP"))return "<IGTOL-PERP>";if(Eq(s,"FLAT"))return "<IGTOL-FLAT>";if(Eq(s,"POSITION"))return "<IGTOL-POSI>";if(Eq(s,"TOTAL_RUNOUT"))return "<IGTOL-TRUN>";return s??"";}
    static Gtol CreateGtol(ModelDoc2 doc,View v,List<Face2> faces,AnnotationSpec a,double x,double y,List<string> log){try{doc.ClearSelection2(true);Need(faces!=null&&faces.Count>0,a.id+" no faces");bool first=true;foreach(Face2 f in faces){Need(SelectInView(v,f,!first),a.id+" selection failed");first=false;}Gtol g=doc.IInsertGtol();Need(g!=null,a.id+" IInsertGtol null");string mc=Eq(a.material_modifier,"M")?"<MOD-MMC>":"";g.SetFrameSymbols2((short)1,GSymbol(a.symbol),a.diameter_zone,mc,false,"","","","");string tv=F(a.tolerance_mm);if(!String.IsNullOrWhiteSpace(a.zone_modifier))tv+=" "+a.zone_modifier.Trim();Need(g.SetFrameValues2((short)1,tv,"",a.datum_1??"",a.datum_2??"",""),a.id+" SetFrameValues2 failed");Annotation an=g.GetAnnotation() as Annotation;if(an!=null){an.SetPosition(x,y,0);try{an.SetName(AName(a.id));}catch{}}doc.ClearSelection2(true);log.Add("GTOL "+a.id+" OK symbol="+a.symbol+" zone="+(a.zone_modifier??"")+" state="+a.state);return g;}catch(Exception ex){doc.ClearSelection2(true);log.Add("GTOL "+a.id+" FAIL="+One(ex.Message));return null;}}
    static bool AddSurfaceFinish(ModelDoc2 doc,View v,Face2 face,double raUm,double x,double y,string id,List<string> log){try{doc.ClearSelection2(true);Need(SelectInView(v,face,false),id+" surface selection failed");string val=raUm.ToString("0.###",CultureInfo.InvariantCulture);bool ok=doc.InsertSurfaceFinishSymbol2((int)swSFSymType_e.swSFMachining_Req,(int)swLeaderStyle_e.swBENT,x,y,0,(int)swSFLaySym_e.swSFNone,(int)swArrowStyle_e.swOPEN_ARROWHEAD,"","Ra","","",val,"","");doc.ClearSelection2(true);log.Add("SURFACE "+id+" Ra="+val+" "+(ok?"OK":"FAIL"));return ok;}catch(Exception ex){doc.ClearSelection2(true);log.Add("SURFACE "+id+" FAIL="+One(ex.Message));return false;}}
    static Note AddNote(ModelDoc2 doc,string text,double x,double y,string id,List<string> log){try{doc.ClearSelection2(true);Note n=doc.InsertNote(text) as Note;if(n==null){log.Add("NOTE "+id+" FAIL");return null;}Annotation a=n.GetAnnotation() as Annotation;if(a!=null){a.SetPosition(x,y,0);try{a.SetName(AName(id));}catch{}}try{n.SetName(AName(id));}catch{}try{n.LockPosition=true;}catch{}log.Add("NOTE "+id+" OK");return n;}catch(Exception ex){log.Add("NOTE "+id+" FAIL="+One(ex.Message));return null;}}
    static Note AddTed(ModelDoc2 doc,string text,double x,double y,string id,List<string> log){try{Note n=doc.InsertNote(text) as Note;if(n==null)return null;bool box=false;try{box=n.SetBalloon((int)swBalloonStyle_e.swBS_Box,(int)swBalloonFit_e.swBF_Tightest);}catch{}Annotation a=n.GetAnnotation() as Annotation;if(a!=null){a.SetPosition(x,y,0);try{a.SetName(AName(id));}catch{}}try{n.SetName(AName(id));}catch{}try{n.LockPosition=true;}catch{}log.Add("TED "+id+" "+(box?"BOX_OK":"BOX_FAIL"));return box?n:null;}catch(Exception ex){log.Add("TED "+id+" FAIL="+One(ex.Message));return null;}}
    static void SetProp(ModelDoc2 doc,string k,string v){CustomPropertyManager c=doc.Extension.get_CustomPropertyManager("");try{c.Delete2(k);}catch{}int r=c.Add(k,"Text",v??"");if(r==0)try{c.Set2(k,v??"");}catch{}}

    static View CreateSection(DrawingDoc dr,ModelDoc2 doc,string model,ViewSpec s,PlacementPoint pp,List<string> log)
    {
        View basev=dr.CreateDrawViewFromModelView3(model,s.parent_orientation??"*Front",0.125,0.215,0) as View;Need(basev!=null,"section parent view creation failed");SetView(basev,0.125,0.215,s.scale);doc.EditRebuild3();
        View sec=null;try{dr.ActivateView(VName(basev));double[] o=Outline(basev);Need(o.Length>=4,"section parent outline missing");double cy=(o[1]+o[3])*0.5;doc.ClearSelection2(true);SketchSegment ln=doc.SketchManager.CreateLine(o[0]-0.003,cy,0,o[2]+0.003,cy,0);Need(ln!=null,"section line creation failed");sec=dr.CreateSectionViewAt5(pp.x_m,pp.y_m,0,String.IsNullOrWhiteSpace(s.section_label)?"S":s.section_label,32,null,0) as View;}catch(Exception ex){log.Add("VIEW SECTION FAIL="+One(ex.Message));}
        Need(sec!=null,"section view creation failed");SetView(sec,pp.x_m,pp.y_m,pp.scale>0?pp.scale:s.scale);try{sec.SetName2(AName("VIEW_"+s.id));}catch{}try{basev.SetVisible(false,false);}catch{try{basev.Position=new double[]{-0.08,0.32};}catch{}}log.Add("VIEW SECTION OK name="+VName(sec));return sec;
    }

    static Dictionary<string,View> CreateViews(DrawingDoc dr,ModelDoc2 doc,Spec spec,PlacementProfile placement,List<string> log)
    {
        var m=new Dictionary<string,View>(StringComparer.OrdinalIgnoreCase);
        foreach(ViewSpec s in spec.view_definitions)
        {
            PlacementPoint pp=VPoint(placement,s.id,s.x_m,s.y_m,s.scale);View v=null;if(Eq(s.kind,"LONGITUDINAL_SECTION"))v=CreateSection(dr,doc,spec.model_path,s,pp,log);else{v=dr.CreateDrawViewFromModelView3(spec.model_path,s.orientation,pp.x_m,pp.y_m,0) as View;Need(v!=null,"view "+s.id+" creation failed");SetView(v,pp.x_m,pp.y_m,pp.scale>0?pp.scale:s.scale);try{v.SetName2(AName("VIEW_"+s.id));}catch{}log.Add("VIEW "+s.id+" OK orient="+s.orientation);}m[s.id]=v;
        }
        doc.EditRebuild3();return m;
    }

    public static int Main(string[] args)
    {
        string specPath=Arg(args,"--spec"),report=Arg(args,"--report"),mode=Arg(args,"--mode"),placementPath=Arg(args,"--placement");SldWorks sw=null;ModelDoc2 part=null,doc=null;bool created=false;var log=new List<string>();
        try
        {
            Need(File.Exists(specPath),"spec missing");Need(!String.IsNullOrWhiteSpace(report),"report missing");Spec spec=new JavaScriptSerializer().Deserialize<Spec>(File.ReadAllText(specPath,Encoding.UTF8));Need(spec!=null&&Eq(spec.schema,"k01.drawing_system_spec.v1"),"bad spec schema");Need(File.Exists(spec.model_path),"model missing: "+spec.model_path);Need(spec.bindings!=null&&spec.annotations!=null&&spec.datum_features!=null,"spec authoring sections missing");
            string sourceSha=Sha(spec.model_path);PlacementProfile placement=LoadPlacement(placementPath,spec.drawing_id,log);string stamp=DateTime.Now.ToString("yyyyMMdd_HHmmss"),outDir=Path.Combine(spec.output_root,"drawing_system_v1_"+stamp),generatedDir=Path.Combine(outDir,"generated"),manualDir=Path.Combine(outDir,"manual_finish"),evidenceDir=Path.Combine(outDir,"evidence");Directory.CreateDirectory(generatedDir);Directory.CreateDirectory(manualDir);Directory.CreateDirectory(evidenceDir);string dwg=Path.Combine(generatedDir,spec.drawing_id+".SLDDRW"),pdf=Path.Combine(generatedDir,spec.drawing_id+".PDF"),bmp=Path.Combine(generatedDir,spec.drawing_id+".BMP");
            Type t=Type.GetTypeFromProgID("SldWorks.Application");Need(t!=null,"SOLIDWORKS ProgID missing");sw=Activator.CreateInstance(t) as SldWorks;Need(sw!=null,"SOLIDWORKS activation failed");created=true;sw.Visible=true;Need(typeof(SldWorks).Assembly.GetName().Version.Major==26,"requires SOLIDWORKS 2018 interop major 26");
            int pe=0,pw=0;part=sw.OpenDoc6(spec.model_path,(int)swDocumentTypes_e.swDocPART,(int)swOpenDocOptions_e.swOpenDocOptions_Silent,"",ref pe,ref pw) as ModelDoc2;Need(part!=null,"open source part failed e="+pe+" w="+pw);List<Face2> fs=Faces(part);Need(fs.Count>0,"source part has no resolvable faces");Dictionary<string,List<Face2>> bind=ResolveBindings(spec,fs,log);
            string templ=sw.GetUserPreferenceStringValue((int)swUserPreferenceStringValue_e.swDefaultTemplateDrawing);Need(!String.IsNullOrWhiteSpace(templ)&&File.Exists(templ),"default drawing template missing");doc=sw.NewDocument(templ,0,0,0) as ModelDoc2;Need(doc!=null,"new drawing failed");DrawingDoc dr=doc as DrawingDoc;Need(dr!=null,"new document is not drawing");bool setup=dr.SetupSheet5("Sheet1",(int)swDwgPaperSizes_e.swDwgPaperA3size,(int)swDwgTemplates_e.swDwgTemplateA3size,spec.sheet_scale,1,true,"",0.420,0.297,"",false);Need(setup,"SetupSheet5 failed");Need(SetSheetScale(dr,spec.sheet_scale,1,log),"sheet scale failed");Need(SheetFirstAngle(dr),"first-angle sheet property not active");
            Dictionary<string,View> views=CreateViews(dr,doc,spec,placement,log);
            foreach(KeyValuePair<string,string> p in spec.title_block_properties)SetProp(doc,p.Key,p.Value);SetProp(doc,"DrawingSystem","MARVILON_DRAWING_SYSTEM_V1");SetProp(doc,"SourceModelSHA256",sourceSha);SetProp(doc,"ReleaseState","HOLD");

            int datumOk=0;foreach(DatumSpec d in spec.datum_features){Need(bind.ContainsKey(d.binding)&&bind[d.binding].Count>0,"datum binding missing "+d.id);Need(!String.IsNullOrWhiteSpace(d.view)&&views.ContainsKey(d.view),"datum view missing/unknown "+d.id+" -> "+d.view);View v=views[d.view];double[] o=Outline(v);double x=o.Length>=4?o[0]-0.010:0.20,y=o.Length>=4?(o[1]+o[3])*0.5:0.10;PlacementPoint dp=PPoint(placement,"DATUM_"+d.id,x,y,0);if(CreateDatum(doc,v,bind[d.binding][0],d.id,dp.x_m,dp.y_m,log)!=null)datumOk++;}

            int dimOk=0,dimNeed=0,gtolOk=0,gtolNeed=0,tedOk=0,tedNeed=0,surfaceOk=0,surfaceNeed=0,noteOk=0;
            foreach(AnnotationSpec a in spec.annotations)
            {
                View v=views.ContainsKey(a.view)?views[a.view]:null;Need(v!=null,"annotation view missing: "+a.id+" -> "+a.view);PlacementPoint ap=PPoint(placement,a.id,a.x_m,a.y_m,0);
                if(Eq(a.kind,"DIAMETER")||Eq(a.kind,"DIAMETER_SET"))
                {
                    dimNeed++;Need(bind.ContainsKey(a.binding)&&bind[a.binding].Count>0,a.id+" binding missing");DisplayDimension dd=TryDiameter(doc,v,bind[a.binding][0],a.nominal_mm,ap.x_m,ap.y_m,a.id,log);bool ok=dd!=null;if(ok&&!String.IsNullOrWhiteSpace(a.hole_fit))ok=SetFit(dd,a.hole_fit,"");if(ok&&!String.IsNullOrWhiteSpace(a.shaft_fit))ok=SetFit(dd,"",a.shaft_fit);if(ok&&a.sym_tol_mm>0)ok=SetSymTol(dd,a.sym_tol_mm,log,a.id);if(ok&&(a.upper_tol_mm!=0||a.lower_tol_mm!=0))ok=SetAsymTolOrFallback(dd,a.lower_tol_mm,a.upper_tol_mm,log,a.id);if(ok&&!String.IsNullOrWhiteSpace(a.prefix)){try{dd.SetText((int)swDimensionTextParts_e.swDimensionTextPrefix,a.prefix);}catch{}}if(ok&&!String.IsNullOrWhiteSpace(a.suffix)){try{dd.SetText((int)swDimensionTextParts_e.swDimensionTextSuffix,a.suffix);}catch{}}if(ok)dimOk++;
                }
                else if(Eq(a.kind,"LINEAR"))
                {
                    dimNeed++;Need(bind.ContainsKey(a.from_binding)&&bind.ContainsKey(a.to_binding),a.id+" linear bindings missing");DisplayDimension dd=TryLinearRobust(doc,v,bind[a.from_binding][0],bind[a.to_binding][0],a.nominal_mm,ap.x_m,ap.y_m,a.id,log);bool ok=dd!=null;if(ok&&a.sym_tol_mm>0)ok=SetSymTol(dd,a.sym_tol_mm,log,a.id);if(ok)dimOk++;
                }
                else if(Eq(a.kind,"GTOL"))
                {
                    bool required=a.state!=null&&a.state.StartsWith("CONTROLLED",StringComparison.OrdinalIgnoreCase);if(required)gtolNeed++;Need(bind.ContainsKey(a.binding),a.id+" GTOL binding missing");Gtol g=CreateGtol(doc,v,bind[a.binding],a,ap.x_m,ap.y_m,log);if(g!=null&&required)gtolOk++;
                }
                else if(Eq(a.kind,"SURFACE_FINISH"))
                {
                    bool required=a.state!=null&&a.state.StartsWith("CONTROLLED",StringComparison.OrdinalIgnoreCase);if(required)surfaceNeed++;Need(bind.ContainsKey(a.binding)&&bind[a.binding].Count>0,a.id+" surface binding missing");bool ok=AddSurfaceFinish(doc,v,bind[a.binding][0],a.ra_um,ap.x_m,ap.y_m,a.id,log);if(ok&&required)surfaceOk++;
                }
                else if(Eq(a.kind,"TED_NOTE"))
                {
                    tedNeed++;if(AddTed(doc,a.text,ap.x_m,ap.y_m,a.id,log)!=null)tedOk++;
                }
                else if(Eq(a.kind,"NOTE"))
                {
                    if(AddNote(doc,a.text,ap.x_m,ap.y_m,a.id,log)!=null)noteOk++;
                }
            }

            // Generic controlled review notes come from the drawing spec. No part-specific text is embedded in the engine.
            if(spec.review_notes!=null)
            {
                int rn=0;
                foreach(string text in spec.review_notes)
                {
                    if(String.IsNullOrWhiteSpace(text))continue;
                    rn++;string id="REVIEW_NOTE_"+rn.ToString("00",CultureInfo.InvariantCulture);double dx=0.042,dy=0.032-(rn-1)*0.010;PlacementPoint rp=PPoint(placement,id,dx,dy,0);AddNote(doc,text,rp.x_m,rp.y_m,id,log);
                }
            }
            doc.EditRebuild3();SaveAs(doc,dwg);SaveAs(doc,pdf);doc.ViewZoomtofit2();bool bmpOk=doc.SaveBMP(bmp,1800,1273);

            string title=doc.GetTitle();try{sw.CloseDoc(title);}catch{}doc=null;string ptitle=part.GetTitle();try{sw.CloseDoc(ptitle);}catch{}part=null;string sourceShaAfter=Sha(spec.model_path);Need(Eq(sourceSha,sourceShaAfter),"SOURCE CAD MUTATION DETECTED: source part hash changed");
            bool viewsOk=views.Count==spec.view_definitions.Count,datumPass=datumOk==spec.datum_features.Count,dimPass=dimOk==dimNeed,gtolPass=gtolOk==gtolNeed,tedPass=tedOk==tedNeed,surfacePass=surfaceOk==surfaceNeed;bool authorPass=viewsOk&&datumPass&&dimPass&&gtolPass&&tedPass&&surfacePass;string status=authorPass?"PASS_DRAWING_SYSTEM_V1_REVIEW_CANDIDATE__RELEASE_HOLD":"PARTIAL_DRAWING_SYSTEM_V1_REVIEW_CANDIDATE__RELEASE_HOLD";
            var sb=new StringBuilder();sb.AppendLine("SCHEMA=k01.drawing_system_report.v1");sb.AppendLine("STATUS="+status);sb.AppendLine("DRAWING="+spec.drawing_id);sb.AppendLine("PART="+spec.part_id);sb.AppendLine("MODE="+(mode??"review"));sb.AppendLine("SOURCE_MODEL="+spec.model_path);sb.AppendLine("SOURCE_SHA256_BEFORE="+sourceSha);sb.AppendLine("SOURCE_SHA256_AFTER="+sourceShaAfter);sb.AppendLine("SOURCE_INVARIANCE="+(Eq(sourceSha,sourceShaAfter)?"PASS":"FAIL"));sb.AppendLine("VIEWS="+views.Count+"/"+spec.view_definitions.Count);sb.AppendLine("DATUMS="+datumOk+"/"+spec.datum_features.Count);sb.AppendLine("CONTROLLED_DIMENSIONS="+dimOk+"/"+dimNeed);sb.AppendLine("CONTROLLED_GTOLS="+gtolOk+"/"+gtolNeed);sb.AppendLine("TED_BOXES="+tedOk+"/"+tedNeed);sb.AppendLine("SURFACE_FINISH="+surfaceOk+"/"+surfaceNeed);sb.AppendLine("NOTES_AUTHORED="+noteOk);sb.AppendLine("CANDIDATE_ROOT="+outDir);sb.AppendLine("GENERATED_DIR="+generatedDir);sb.AppendLine("MANUAL_FINISH_DIR="+manualDir);sb.AppendLine("EVIDENCE_DIR="+evidenceDir);sb.AppendLine("PLACEMENT_PROFILE="+(String.IsNullOrWhiteSpace(placementPath)?"":placementPath));sb.AppendLine("PLACEMENT_APPLIED="+(placement!=null));sb.AppendLine("OUTPUT_DRAWING="+dwg);sb.AppendLine("OUTPUT_PDF="+pdf);sb.AppendLine("OUTPUT_BMP="+bmp);sb.AppendLine("BMP_OK="+bmpOk);sb.AppendLine("RELEASE=HOLD");if(spec.release_blockers!=null){sb.AppendLine("RELEASE_BLOCKERS="+spec.release_blockers.Count);foreach(string b in spec.release_blockers)sb.AppendLine("BLOCKER="+b);}sb.AppendLine("LOG_BEGIN");foreach(string z in log)sb.AppendLine(z);sb.AppendLine("LOG_END");Directory.CreateDirectory(Path.GetDirectoryName(report));File.WriteAllText(report,sb.ToString(),Encoding.UTF8);
            Console.WriteLine("STATUS: "+status);Console.WriteLine("RELEASE: HOLD (product-definition blockers preserved; Drawing System v1 candidate only)");Console.WriteLine("SOURCE CAD INVARIANCE: PASS");Console.WriteLine("VIEWS: "+views.Count+" / "+spec.view_definitions.Count);Console.WriteLine("SHEET: "+spec.sheet+" | SCALE: "+F(spec.sheet_scale)+":1 | PROJECTION PROPERTY: "+spec.projection);Console.WriteLine("DATUMS: "+datumOk+" / "+spec.datum_features.Count);Console.WriteLine("CONTROLLED DIMENSIONS: "+dimOk+" / "+dimNeed);Console.WriteLine("CONTROLLED GTOLS: "+gtolOk+" / "+gtolNeed+" (candidate-only GTOLs excluded from required count)");Console.WriteLine("TED BOXES: "+tedOk+" / "+tedNeed);Console.WriteLine("SURFACE FINISH: "+surfaceOk+" / "+surfaceNeed);Console.WriteLine("OPEN ITEMS: preserved in drawing/report; no invented tolerances");Console.WriteLine("CANDIDATE ROOT: "+outDir);Console.WriteLine("PLACEMENT PROFILE: "+(placement!=null?placementPath:"SPEC SEED"));Console.WriteLine("DRAWING: "+dwg);Console.WriteLine("PDF: "+pdf);Console.WriteLine("REPORT: "+report);Console.WriteLine("NEXT: inspect generated PDF, prepare manual_finish, then capture placement. Do not release while blockers remain.");
            if(created&&sw!=null){try{sw.ExitApp();}catch{}}return authorPass?0:3;
        }
        catch(Exception ex)
        {
            Console.WriteLine("STATUS: HOLD_DRAWING_SYSTEM_V1");Console.WriteLine("ERROR: "+ex.ToString());try{if(doc!=null&&sw!=null)sw.CloseDoc(doc.GetTitle());}catch{}try{if(part!=null&&sw!=null)sw.CloseDoc(part.GetTitle());}catch{}try{if(created&&sw!=null)sw.ExitApp();}catch{}return 2;
        }
    }
}
