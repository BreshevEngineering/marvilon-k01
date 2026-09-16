using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using System.Web.Script.Serialization;
using SolidWorks.Interop.sldworks;
using SolidWorks.Interop.swconst;

public class K01DrawingPresentationAuditV1
{
    public class Spec { public string schema; public string drawing_id; public List<ViewSpec> view_definitions; public List<DatumSpec> datum_features; public List<AnnotationSpec> annotations; }
    public class ViewSpec { public string id; public string kind; public string orientation; public double x_m; public double y_m; public double scale; }
    public class DatumSpec { public string id; }
    public class AnnotationSpec { public string id; }
    public class P3 { public double x; public double y; public double z; }
    public class LeaderRec { public int index; public int style; public List<P3> points=new List<P3>(); }
    public class AnnRec { public string id; public string name; public string view; public int type; public bool visible; public bool dangling; public P3 position; public int leader_count; public List<LeaderRec> leaders=new List<LeaderRec>(); public double[] note_extent; }
    public class ViewRec { public string id; public string name; public string orientation; public double[] outline; public P3 position; public double scale; }
    public class Evidence { public string schema="k01.drawing_presentation_evidence.v1"; public string drawing_id; public string source_drawing; public string captured_utc; public List<ViewRec> views=new List<ViewRec>(); public List<AnnRec> annotations=new List<AnnRec>(); public List<string> warnings=new List<string>(); }

    static string Arg(string[] a,string k){for(int i=0;i<a.Length-1;i++)if(a[i]==k)return a[i+1];return null;}
    static void Need(bool ok,string msg){if(!ok)throw new Exception(msg);}
    static bool Eq(string a,string b){return String.Equals(a??"",b??"",StringComparison.OrdinalIgnoreCase);}
    static IEnumerable Items(object o){if(o==null)yield break;Array a=o as Array;if(a!=null){foreach(object x in a)yield return x;yield break;}IEnumerable e=o as IEnumerable;if(e!=null)foreach(object x in e)yield return x;}
    static double[] DA(object o){var z=new List<double>();foreach(object q in Items(o))try{z.Add(Convert.ToDouble(q,CultureInfo.InvariantCulture));}catch{}return z.ToArray();}
    static string AName(string id){return "K01DS_"+(id??"").Replace(" ","_");}
    static string Strip(string n){return n!=null&&n.StartsWith("K01DS_",StringComparison.OrdinalIgnoreCase)?n.Substring(6):n??"";}
    static P3 P(object o){double[] a=DA(o);return new P3{x=a.Length>0?a[0]:Double.NaN,y=a.Length>1?a[1]:Double.NaN,z=a.Length>2?a[2]:0};}
    static string VName(View v){try{return v.GetName2()??"";}catch{return "";}}
    static string VOrient(View v){try{return v.GetOrientationName()??"";}catch{return "";}}
    static double[] VPos(View v){try{return DA(v.Position);}catch{return new double[0];}}
    static double Dist2(double x,double y,double a,double b){double dx=x-a,dy=y-b;return dx*dx+dy*dy;}
    static List<View> Views(DrawingDoc dr){var r=new List<View>();View v=dr.GetFirstView() as View;if(v!=null)v=v.GetNextView() as View;while(v!=null){r.Add(v);v=v.GetNextView() as View;}return r;}
    static View FindView(ViewSpec s,List<View> vs)
    {
        // Primary contract: semantic view name authored by Drawing System v1.
        string n=AName("VIEW_"+s.id);foreach(View v in vs)if(Eq(VName(v),n))return v;
        // Model views can be resolved by a unique SolidWorks orientation.
        if(!String.IsNullOrWhiteSpace(s.orientation)){var q=new List<View>();foreach(View v in vs)if(Eq(VOrient(v),s.orientation))q.Add(v);if(q.Count==1)return q[0];}
        // Backward-compatible recovery for candidates generated before section views were semantically named.
        // Section views normally have no model orientation, so choose the nearest orientation-less view
        // to the controlled spec seed. This is the same fail-closed strategy already proven by placement capture.
        View best=null;double bd=1e99;int ties=0;
        foreach(View v in vs)
        {
            string o=VOrient(v);
            if(!Eq(s.kind,"LONGITUDINAL_SECTION")&&!String.IsNullOrWhiteSpace(s.orientation)&&!Eq(o,s.orientation))continue;
            if(Eq(s.kind,"LONGITUDINAL_SECTION")&&!String.IsNullOrWhiteSpace(o))continue;
            double[] p=VPos(v);if(p.Length<2)continue;double d=Dist2(p[0],p[1],s.x_m,s.y_m);
            if(d<bd-1e-12){bd=d;best=v;ties=1;}else if(Math.Abs(d-bd)<=1e-12)ties++;
        }
        if(ties>1)return null;
        return best;
    }
    static double[] NoteExtent(Annotation a){try{Note n=a.GetSpecificAnnotation() as Note;if(n==null)return null;double[] x=DA(n.GetExtent());return x.Length>=6?x:null;}catch{return null;}}
    static List<LeaderRec> Leaders(Annotation a,List<string> warn,string id){var outp=new List<LeaderRec>();int c=0;try{c=a.GetLeaderCount();}catch{}for(int i=0;i<c;i++){var lr=new LeaderRec();lr.index=i;try{lr.style=a.GetLeaderStyle();}catch{lr.style=-1;}try{double[] p=DA(a.GetLeaderPointsAtIndex(i));for(int j=0;j+2<p.Length;j+=3)lr.points.Add(new P3{x=p[j],y=p[j+1],z=p[j+2]});}catch(Exception ex){warn.Add("LEADER_POINTS "+id+"["+i+"] "+ex.GetType().Name+":"+ex.Message);}outp.Add(lr);}return outp;}
    static void ScanAnnotations(View v,Evidence ev,HashSet<string> seen){Annotation a=null;try{a=v.GetFirstAnnotation3() as Annotation;}catch{}while(a!=null){string n="";try{n=a.GetName()??"";}catch{}if(n.StartsWith("K01DS_",StringComparison.OrdinalIgnoreCase)){string id=Strip(n);if(seen.Contains(id))throw new Exception("duplicate semantic annotation: "+id);seen.Add(id);var r=new AnnRec();r.id=id;r.name=n;r.view=VName(v);try{r.type=a.GetType();}catch{r.type=-1;}try{r.visible=a.Visible==(int)swAnnotationVisibilityState_e.swAnnotationVisible;}catch{r.visible=true;}try{r.dangling=a.IsDangling();}catch{r.dangling=false;}try{r.position=P(a.GetPosition());}catch{r.position=new P3{x=Double.NaN,y=Double.NaN,z=0};}try{r.leader_count=a.GetLeaderCount();}catch{r.leader_count=0;}r.leaders=Leaders(a,ev.warnings,id);r.note_extent=NoteExtent(a);ev.annotations.Add(r);}try{a=a.GetNext3() as Annotation;}catch{a=null;}}
    }

    public static int Main(string[] args)
    {
        string drawing=Arg(args,"--drawing"),specPath=Arg(args,"--spec"),outPath=Arg(args,"--out");SldWorks sw=null;ModelDoc2 doc=null;bool created=false;
        try{
            Need(File.Exists(drawing),"drawing missing: "+drawing);Need(File.Exists(specPath),"spec missing: "+specPath);Need(!String.IsNullOrWhiteSpace(outPath),"output missing");
            Spec spec=new JavaScriptSerializer().Deserialize<Spec>(File.ReadAllText(specPath,Encoding.UTF8));Need(spec!=null&&Eq(spec.schema,"k01.drawing_system_spec.v1"),"bad spec schema");
            Type t=Type.GetTypeFromProgID("SldWorks.Application");Need(t!=null,"SOLIDWORKS ProgID missing");sw=Activator.CreateInstance(t) as SldWorks;Need(sw!=null,"SOLIDWORKS activation failed");created=true;sw.Visible=false;Need(typeof(SldWorks).Assembly.GetName().Version.Major==26,"requires SOLIDWORKS 2018 interop major 26");
            int e=0,w=0;doc=sw.OpenDoc6(drawing,(int)swDocumentTypes_e.swDocDRAWING,(int)(swOpenDocOptions_e.swOpenDocOptions_Silent|swOpenDocOptions_e.swOpenDocOptions_ReadOnly),"",ref e,ref w) as ModelDoc2;Need(doc!=null,"open drawing failed e="+e+" w="+w);DrawingDoc dr=doc as DrawingDoc;Need(dr!=null,"not drawing");
            Evidence ev=new Evidence();ev.drawing_id=spec.drawing_id;ev.source_drawing=drawing;ev.captured_utc=DateTime.UtcNow.ToString("o",CultureInfo.InvariantCulture);List<View> views=Views(dr);
            foreach(ViewSpec s in spec.view_definitions){View v=FindView(s,views);Need(v!=null,"view not found: "+s.id);var vr=new ViewRec();vr.id=s.id;vr.name=VName(v);vr.orientation=VOrient(v);try{vr.outline=DA(v.GetOutline());}catch{vr.outline=new double[0];}try{vr.position=P(v.Position);}catch{vr.position=new P3{x=Double.NaN,y=Double.NaN,z=0};}try{vr.scale=v.ScaleDecimal;}catch{vr.scale=0;}ev.views.Add(vr);}
            var seen=new HashSet<string>(StringComparer.OrdinalIgnoreCase);View sheet=dr.GetFirstView() as View;if(sheet!=null)ScanAnnotations(sheet,ev,seen);foreach(View v in views)ScanAnnotations(v,ev,seen);
            var expected=new List<string>();if(spec.annotations!=null)foreach(AnnotationSpec a in spec.annotations)expected.Add(a.id);if(spec.datum_features!=null)foreach(DatumSpec d in spec.datum_features)expected.Add("DATUM_"+d.id);var miss=new List<string>();foreach(string id in expected)if(!seen.Contains(id))miss.Add(id);Need(miss.Count==0,"presentation capture missing semantic annotations: "+String.Join(",",miss.ToArray()));
            Directory.CreateDirectory(Path.GetDirectoryName(outPath));File.WriteAllText(outPath,new JavaScriptSerializer().Serialize(ev),Encoding.UTF8);Console.WriteLine("STATUS: PASS_DRAWING_PRESENTATION_CAPTURE_V1");Console.WriteLine("DRAWING: "+spec.drawing_id);Console.WriteLine("VIEWS: "+ev.views.Count+" / "+spec.view_definitions.Count);Console.WriteLine("ANNOTATIONS: "+ev.annotations.Count+" / "+expected.Count);Console.WriteLine("EVIDENCE: "+outPath);return 0;
        }catch(Exception ex){Console.Error.WriteLine(ex.ToString());return 2;}finally{try{if(doc!=null&&sw!=null)sw.CloseDoc(doc.GetTitle());}catch{}try{if(created&&sw!=null)sw.ExitApp();}catch{}}
    }
}
