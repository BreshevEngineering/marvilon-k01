using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using System.Web.Script.Serialization;
using SolidWorks.Interop.sldworks;
using SolidWorks.Interop.swconst;

public class K01DrawingPlacementCaptureV1
{
    public class Spec
    {
        public string schema;
        public string drawing_id;
        public List<ViewSpec> view_definitions;
        public List<DatumSpec> datum_features;
        public List<AnnotationSpec> annotations;
    }
    public class ViewSpec
    {
        public string id;
        public string kind;
        public string orientation;
        public double x_m;
        public double y_m;
        public double scale;
    }
    public class DatumSpec { public string id; }
    public class AnnotationSpec { public string id; }
    public class PlacementPoint
    {
        public double x_m;
        public double y_m;
        public double scale;
        public string evidence;
    }
    public class PlacementProfile
    {
        public string schema="k01.drawing_placement.v1";
        public string drawing_id;
        public string source_drawing;
        public string captured_utc;
        public Dictionary<string,PlacementPoint> views=new Dictionary<string,PlacementPoint>(StringComparer.OrdinalIgnoreCase);
        public Dictionary<string,PlacementPoint> annotations=new Dictionary<string,PlacementPoint>(StringComparer.OrdinalIgnoreCase);
    }

    static string Arg(string[] a,string k){for(int i=0;i<a.Length-1;i++)if(a[i]==k)return a[i+1];return null;}
    static void Need(bool ok,string msg){if(!ok)throw new Exception(msg);}
    static bool Eq(string a,string b){return String.Equals(a??"",b??"",StringComparison.OrdinalIgnoreCase);}
    static IEnumerable Items(object o){if(o==null)yield break;Array a=o as Array;if(a!=null){foreach(object x in a)yield return x;yield break;}IEnumerable e=o as IEnumerable;if(e!=null)foreach(object x in e)yield return x;}
    static double[] DA(object o){var z=new List<double>();foreach(object q in Items(o))try{z.Add(Convert.ToDouble(q,CultureInfo.InvariantCulture));}catch{}return z.ToArray();}
    static string AName(string id){return "K01DS_"+(id??"").Replace(" ","_");}
    static string StripAName(string s){return s!=null&&s.StartsWith("K01DS_",StringComparison.OrdinalIgnoreCase)?s.Substring(6):s??"";}
    static string VName(View v){try{return v.GetName2()??"";}catch{return "";}}
    static string VUnique(View v){try{string x=v.GetUniqueName();return String.IsNullOrWhiteSpace(x)?VName(v):x;}catch{return VName(v);}}
    static string VOrient(View v){try{return v.GetOrientationName()??"";}catch{return "";}}
    static double[] VPos(View v){try{return DA(v.Position);}catch{return new double[0];}}
    static double VScale(View v){try{return v.ScaleDecimal;}catch{return 0;}}
    static double Dist2(double x,double y,double a,double b){double dx=x-a,dy=y-b;return dx*dx+dy*dy;}
    static List<View> DrawingViews(DrawingDoc dr){var r=new List<View>();View v=dr.GetFirstView() as View;if(v!=null)v=v.GetNextView() as View;while(v!=null){r.Add(v);v=v.GetNextView() as View;}return r;}

    static View MatchView(ViewSpec s,List<View> views)
    {
        string target=AName("VIEW_"+s.id);
        foreach(View v in views)if(Eq(VName(v),target))return v;
        if(!String.IsNullOrWhiteSpace(s.orientation))
        {
            var q=new List<View>();foreach(View v in views)if(Eq(VOrient(v),s.orientation))q.Add(v);
            if(q.Count==1)return q[0];
        }
        View best=null;double bd=1e99;
        foreach(View v in views)
        {
            string o=VOrient(v);
            if(!Eq(s.kind,"LONGITUDINAL_SECTION")&&!String.IsNullOrWhiteSpace(s.orientation)&&!Eq(o,s.orientation))continue;
            if(Eq(s.kind,"LONGITUDINAL_SECTION")&&!String.IsNullOrWhiteSpace(o))continue;
            double[] p=VPos(v);if(p.Length<2)continue;double d=Dist2(p[0],p[1],s.x_m,s.y_m);if(d<bd){bd=d;best=v;}
        }
        return best;
    }

    static void CaptureNamedAnnotations(View v,PlacementProfile profile,List<string> log)
    {
        Annotation a=null;try{a=v.GetFirstAnnotation3() as Annotation;}catch{}
        while(a!=null)
        {
            string n="";try{n=a.GetName()??"";}catch{}
            if(n.StartsWith("K01DS_",StringComparison.OrdinalIgnoreCase))
            {
                double[] p=DA(a.GetPosition());
                if(p.Length>=2)
                {
                    string id=StripAName(n);
                    if(profile.annotations.ContainsKey(id))throw new Exception("duplicate named annotation in drawing: "+id);
                    profile.annotations[id]=new PlacementPoint{x_m=p[0],y_m=p[1],scale=0,evidence="ANNOTATION_NAME:"+n+"@"+VUnique(v)};
                    log.Add("ANN "+id+" x="+p[0].ToString("R",CultureInfo.InvariantCulture)+" y="+p[1].ToString("R",CultureInfo.InvariantCulture));
                }
            }
            try{a=a.GetNext3() as Annotation;}catch{a=null;}
        }
    }

    public static int Main(string[] args)
    {
        string drawing=Arg(args,"--drawing"),specPath=Arg(args,"--spec"),outPath=Arg(args,"--out"),report=Arg(args,"--report");
        SldWorks sw=null;ModelDoc2 doc=null;bool created=false;var log=new List<string>();
        try
        {
            Need(File.Exists(drawing),"drawing missing: "+drawing);Need(File.Exists(specPath),"spec missing: "+specPath);Need(!String.IsNullOrWhiteSpace(outPath),"output missing");
            Spec spec=new JavaScriptSerializer().Deserialize<Spec>(File.ReadAllText(specPath,Encoding.UTF8));Need(spec!=null&&Eq(spec.schema,"k01.drawing_system_spec.v1"),"bad spec schema");
            Type t=Type.GetTypeFromProgID("SldWorks.Application");Need(t!=null,"SOLIDWORKS ProgID missing");sw=Activator.CreateInstance(t) as SldWorks;Need(sw!=null,"SOLIDWORKS activation failed");created=true;sw.Visible=false;Need(typeof(SldWorks).Assembly.GetName().Version.Major==26,"requires SOLIDWORKS 2018 interop major 26");
            int e=0,w=0;doc=sw.OpenDoc6(drawing,(int)swDocumentTypes_e.swDocDRAWING,(int)(swOpenDocOptions_e.swOpenDocOptions_Silent|swOpenDocOptions_e.swOpenDocOptions_ReadOnly),"",ref e,ref w) as ModelDoc2;Need(doc!=null,"open drawing failed e="+e+" w="+w);DrawingDoc dr=doc as DrawingDoc;Need(dr!=null,"not drawing");
            var profile=new PlacementProfile();profile.drawing_id=spec.drawing_id;profile.source_drawing=drawing;profile.captured_utc=DateTime.UtcNow.ToString("o",CultureInfo.InvariantCulture);
            List<View> views=DrawingViews(dr);var used=new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach(ViewSpec vs in spec.view_definitions)
            {
                View v=MatchView(vs,views);Need(v!=null,"view capture unresolved: "+vs.id);string un=VUnique(v);Need(!used.Contains(un),"view capture collision: "+vs.id+" -> "+un);used.Add(un);double[] p=VPos(v);Need(p.Length>=2,"view position unavailable: "+vs.id);profile.views[vs.id]=new PlacementPoint{x_m=p[0],y_m=p[1],scale=VScale(v),evidence="VIEW:"+un+" ORIENT:"+VOrient(v)};log.Add("VIEW "+vs.id+" -> "+un);
            }
            // Traverse sheet plus all drawing views; named annotations are unique and survive manual movement.
            View sheet=dr.GetFirstView() as View;if(sheet!=null)CaptureNamedAnnotations(sheet,profile,log);foreach(View v in views)CaptureNamedAnnotations(v,profile,log);
            var expected=new List<string>();if(spec.annotations!=null)foreach(AnnotationSpec a in spec.annotations)expected.Add(a.id);if(spec.datum_features!=null)foreach(DatumSpec d in spec.datum_features)expected.Add("DATUM_"+d.id);
            var missing=new List<string>();foreach(string id in expected)if(!profile.annotations.ContainsKey(id))missing.Add(id);
            Need(missing.Count==0,"placement capture missing semantic annotations: "+String.Join(",",missing.ToArray()));
            Directory.CreateDirectory(Path.GetDirectoryName(outPath));File.WriteAllText(outPath,new JavaScriptSerializer().Serialize(profile),Encoding.UTF8);
            if(!String.IsNullOrWhiteSpace(report)){Directory.CreateDirectory(Path.GetDirectoryName(report));var sb=new StringBuilder();sb.AppendLine("STATUS=PASS_DRAWING_PLACEMENT_CAPTURE_V1");sb.AppendLine("DRAWING="+spec.drawing_id);sb.AppendLine("SOURCE_DRAWING="+drawing);sb.AppendLine("VIEWS="+profile.views.Count+"/"+spec.view_definitions.Count);sb.AppendLine("ANNOTATIONS="+profile.annotations.Count+"/"+expected.Count);sb.AppendLine("OUTPUT="+outPath);foreach(string z in log)sb.AppendLine("LOG="+z);File.WriteAllText(report,sb.ToString(),Encoding.UTF8);}
            Console.WriteLine("STATUS: PASS_DRAWING_PLACEMENT_CAPTURE_V1");Console.WriteLine("DRAWING: "+spec.drawing_id);Console.WriteLine("VIEWS: "+profile.views.Count+" / "+spec.view_definitions.Count);Console.WriteLine("ANNOTATIONS: "+profile.annotations.Count+" / "+expected.Count);Console.WriteLine("PLACEMENT: "+outPath);return 0;
        }
        catch(Exception ex){try{if(!String.IsNullOrWhiteSpace(report))File.WriteAllText(report,"STATUS=HOLD_DRAWING_PLACEMENT_CAPTURE_V1\nERROR="+ex.ToString()+"\n",Encoding.UTF8);}catch{}Console.Error.WriteLine(ex.ToString());return 2;}
        finally{try{if(doc!=null&&sw!=null)sw.CloseDoc(doc.GetTitle());}catch{}try{if(created&&sw!=null)sw.ExitApp();}catch{}}
    }
}
