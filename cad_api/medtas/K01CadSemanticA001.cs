using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Web.Script.Serialization;
using SolidWorks.Interop.sldworks;
using SolidWorks.Interop.swconst;

public class K01CadSemanticA001
{
    static readonly List<string> Errors = new List<string>();
    static string Stage = "BOOT";
    static string LogPath = null;
    static string OutPath = null;
    static string AssemblyPath = null;

    static void Log(string text)
    {
        string line = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss.fff") + " | " + Stage + " | " + text;
        try { Console.WriteLine(line); } catch { }
        if (!String.IsNullOrEmpty(LogPath)) {
            try {
                Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(LogPath)));
                File.AppendAllText(LogPath, line + System.Environment.NewLine, new UTF8Encoding(false));
            } catch { }
        }
    }

    static string Arg(string[] args, string name)
    {
        for (int i = 0; i < args.Length - 1; i++)
            if (args[i].Equals(name, StringComparison.OrdinalIgnoreCase)) return args[i + 1];
        return null;
    }

    static IEnumerable Items(object obj)
    {
        if (obj == null) yield break;
        Array a = obj as Array;
        if (a != null) {
            foreach (object x in a) yield return x;
            yield break;
        }
        IEnumerable en = obj as IEnumerable;
        if (en != null) foreach (object x in en) yield return x;
    }

    static bool SafeSuppressed(Feature f)
    {
        if (f == null) return false;
        try { return f.IsSuppressed(); } catch { return false; }
    }

    static bool SafeSuppressed(Component2 c)
    {
        if (c == null) return false;
        try {
            int s = c.GetSuppression();
            return s == (int)swComponentSuppressionState_e.swComponentSuppressed;
        } catch { return false; }
    }

    static string ReadMaterial(ModelDoc2 model, string configuration, out string database)
    {
        database = "";
        try {
            PartDoc part = model as PartDoc;
            if (part == null) return "";
            string db = "";
            string mat = part.GetMaterialPropertyName2(configuration ?? "", out db);
            database = db ?? "";
            return mat ?? "";
        } catch (Exception ex) {
            Errors.Add("material:" + ex.Message);
            return "";
        }
    }

    static List<object> ReadDimensions(Feature feat, string featurePath)
    {
        List<object> result = new List<object>();
        if (feat == null) return result;
        try {
            DisplayDimension dd = feat.GetFirstDisplayDimension() as DisplayDimension;
            int guard = 0;
            while (dd != null && guard++ < 500) {
                try {
                    Dimension dim = dd.GetDimension2(0);
                    if (dim != null) {
                        Dictionary<string, object> d = new Dictionary<string, object>();
                        string name = "";
                        try { name = dim.Name; } catch { }
                        d["name"] = name ?? "";
                        try { d["full_name"] = dim.FullName; }
                        catch { d["full_name"] = featurePath + "/" + name; }
                        try { d["system_value_SI"] = Convert.ToDouble(dim.SystemValue); }
                        catch { d["system_value_SI"] = null; }
                        result.Add(d);
                    }
                } catch (Exception ex) {
                    Errors.Add("dimension:" + featurePath + ":" + ex.Message);
                }
                try { dd = feat.GetNextDisplayDimension(dd) as DisplayDimension; } catch { dd = null; }
            }
        } catch (Exception ex) {
            Errors.Add("dimensions:" + featurePath + ":" + ex.Message);
        }
        return result;
    }

    static void ReadFeatureTree(Feature first, string parent, List<object> output, int depth)
    {
        if (depth > 16 || first == null) return;
        Feature f = first;
        int guard = 0;
        while (f != null && guard++ < 5000) {
            string name = "", type = "";
            try { name = f.Name; } catch { }
            try { type = f.GetTypeName2(); } catch { }
            string path = String.IsNullOrEmpty(parent) ? name : (parent + "/" + name);
            Dictionary<string, object> x = new Dictionary<string, object>();
            x["path"] = path;
            x["name"] = name;
            x["type"] = type;
            x["suppressed"] = SafeSuppressed(f);
            x["dimensions"] = ReadDimensions(f, path);
            output.Add(x);
            try {
                Feature sub = f.GetFirstSubFeature() as Feature;
                if (sub != null) ReadFeatureTree(sub, path, output, depth + 1);
            } catch (Exception ex) { Errors.Add("subfeature:" + path + ":" + ex.Message); }
            try { f = (depth == 0 ? f.GetNextFeature() : f.GetNextSubFeature()) as Feature; }
            catch { f = null; }
        }
    }

    static List<double> ObjectDoubleArray(object raw)
    {
        List<double> a = new List<double>();
        foreach (object v in Items(raw)) {
            try { a.Add(Convert.ToDouble(v)); } catch { }
        }
        return a;
    }

    static List<object> ReadFaceInventory(ModelDoc2 model)
    {
        List<object> faces = new List<object>();
        try {
            PartDoc part = model as PartDoc;
            if (part == null) return faces;
            object bodyObj = part.GetBodies2((int)swBodyType_e.swSolidBody, true);
            int bi = 0;
            foreach (object bo in Items(bodyObj)) {
                bi++;
                Body2 body = bo as Body2;
                if (body == null) continue;
                string bodyName = "BODY_" + bi;
                try { bodyName = body.Name; } catch { }
                object faceObj = null;
                try { faceObj = body.GetFaces(); }
                catch (Exception ex) { Errors.Add("faces:" + bodyName + ":" + ex.Message); }
                int fi = 0;
                foreach (object fo in Items(faceObj)) {
                    fi++;
                    Face2 face = fo as Face2;
                    if (face == null) continue;
                    Dictionary<string, object> fd = new Dictionary<string, object>();
                    fd["body"] = bodyName;
                    fd["face_index_runtime"] = fi;
                    try { fd["area_m2"] = Convert.ToDouble(face.GetArea()); } catch { fd["area_m2"] = null; }
                    try { fd["box_m"] = ObjectDoubleArray(face.GetBox()); } catch { fd["box_m"] = new List<double>(); }
                    try { fd["normal"] = ObjectDoubleArray(face.Normal); } catch { fd["normal"] = new List<double>(); }
                    try {
                        Surface surf = face.IGetSurface();
                        bool isPlane=false,isCylinder=false,isCone=false,isSphere=false,isTorus=false;
                        try { isPlane=surf.IsPlane(); } catch { }
                        try { isCylinder=surf.IsCylinder(); } catch { }
                        try { isCone=surf.IsCone(); } catch { }
                        try { isSphere=surf.IsSphere(); } catch { }
                        try { isTorus=surf.IsTorus(); } catch { }
                        fd["surface_type"] = isPlane?"plane":isCylinder?"cylinder":isCone?"cone":isSphere?"sphere":isTorus?"torus":"other";
                        // Stable primitive parameters improve topology-independent face matching.
                        // Runtime face indices remain diagnostic only.
                        try { if (isPlane) fd["plane_params"] = ObjectDoubleArray(surf.PlaneParams); } catch { fd["plane_params"] = new List<double>(); }
                        try { if (isCylinder) fd["cylinder_params"] = ObjectDoubleArray(surf.CylinderParams); } catch { fd["cylinder_params"] = new List<double>(); }
                        try { if (isCone) fd["cone_params"] = ObjectDoubleArray(surf.ConeParams2); } catch { fd["cone_params"] = new List<double>(); }
                        try { if (isSphere) fd["sphere_params"] = ObjectDoubleArray(surf.SphereParams); } catch { fd["sphere_params"] = new List<double>(); }
                        try { if (isTorus) fd["torus_params"] = ObjectDoubleArray(surf.TorusParams); } catch { fd["torus_params"] = new List<double>(); }
                    } catch { fd["surface_type"] = "unknown"; }
                    try {
                        int ec = 0; foreach (object _ in Items(face.GetEdges())) ec++; fd["edge_count"] = ec;
                    } catch { fd["edge_count"] = null; }
                    faces.Add(fd);
                }
            }
        } catch (Exception ex) { Errors.Add("face_inventory:" + ex.Message); }
        return faces;
    }

    static Dictionary<string, object> ReadDocument(ModelDoc2 model, string path, string configuration)
    {
        Dictionary<string, object> d = new Dictionary<string, object>();
        string title = "";
        try { title = model.GetTitle(); } catch { }
        d["title"] = title;
        d["native_path"] = path;
        d["configuration"] = configuration ?? "";
        string matDb = "";
        d["material_name"] = ReadMaterial(model, configuration ?? "", out matDb);
        d["material_database"] = matDb;
        try {
            PartDoc part = model as PartDoc;
            object bodies = part == null ? null : part.GetBodies2((int)swBodyType_e.swSolidBody, true);
            int count = 0; foreach (object _ in Items(bodies)) count++;
            d["solid_body_count"] = count;
        } catch { d["solid_body_count"] = null; }
        List<object> features = new List<object>();
        try { Feature first = model.FirstFeature() as Feature; if (first != null) ReadFeatureTree(first, "", features, 0); }
        catch (Exception ex) { Errors.Add("feature_tree:" + title + ":" + ex.Message); }
        d["features"] = features;
        d["faces"] = ReadFaceInventory(model);
        return d;
    }

    static List<double> TransformArray(Component2 comp)
    {
        List<double> a = new List<double>();
        try {
            MathTransform t = comp.Transform2;
            if (t == null) return a;
            return ObjectDoubleArray(t.ArrayData);
        } catch (Exception ex) { Errors.Add("transform:" + ex.Message); return a; }
    }

    static void WriteJson(string path, object obj)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(path)));
        JavaScriptSerializer js = new JavaScriptSerializer(); js.MaxJsonLength = Int32.MaxValue;
        File.WriteAllText(path, js.Serialize(obj), new UTF8Encoding(false));
    }

    static void WriteFailure(Exception ex)
    {
        if (String.IsNullOrEmpty(OutPath)) return;
        try {
            Dictionary<string, object> fail = new Dictionary<string, object>();
            fail["schema"] = "k01_sw_semantic_raw_a001_error_v1_7";
            fail["status"] = "ERROR"; fail["stage"] = Stage; fail["assembly"] = AssemblyPath;
            fail["error"] = ex.Message; fail["stack_trace"] = ex.ToString(); fail["errors"] = Errors;
            WriteJson(OutPath, fail);
        } catch { }
    }

    static ModelDoc2 GetOrOpenAssembly(SldWorks sw, string assemblyPath, out int er, out int wr, out bool alreadyOpen)
    {
        er = 0; wr = 0; alreadyOpen = false;
        ModelDoc2 model = null;
        try {
            model = sw.IGetOpenDocumentByName2(assemblyPath);
            if (model != null) { alreadyOpen = true; return model; }
        } catch (Exception ex) { Log("GetOpenDocumentByName warning: " + ex.Message); }
        model = sw.OpenDoc6(assemblyPath, (int)swDocumentTypes_e.swDocASSEMBLY,
            (int)swOpenDocOptions_e.swOpenDocOptions_Silent, "", ref er, ref wr);
        return model;
    }

    static SldWorks AttachSolidWorks()
    {
        try {
            object o = Marshal.GetActiveObject("SldWorks.Application");
            SldWorks sw = o as SldWorks;
            if (sw == null) throw new Exception("Active COM object cannot be cast to SolidWorks.Interop.sldworks.SldWorks");
            Log("Attached to active SolidWorks instance via early-bound interop");
            return sw;
        } catch (Exception first) {
            Log("Active attach unavailable: " + first.Message);
            Type t = Type.GetTypeFromProgID("SldWorks.Application");
            if (t == null) throw new Exception("SolidWorks.Application ProgID not found");
            object o = Activator.CreateInstance(t);
            SldWorks sw = o as SldWorks;
            if (sw == null) throw new Exception("Started COM object cannot be cast to SolidWorks.Interop.sldworks.SldWorks");
            try { sw.Visible = true; } catch { }
            Log("Started new SolidWorks instance via early-bound interop");
            return sw;
        }
    }

    static void MainImpl(string[] args)
    {
        AssemblyPath = Arg(args, "--assembly"); OutPath = Arg(args, "--out"); LogPath = Arg(args, "--log");
        if (String.IsNullOrEmpty(AssemblyPath) || String.IsNullOrEmpty(OutPath))
            throw new Exception("Usage: --assembly <path> --out <json> [--log <log>]");
        if (!File.Exists(AssemblyPath)) throw new FileNotFoundException("Assembly not found", AssemblyPath);

        Stage = "ATTACH_SOLIDWORKS"; Log("Starting semantic extraction v1.7");
        SldWorks sw = AttachSolidWorks();

        Stage = "OPEN_ASSEMBLY";
        int er=0, wr=0; bool alreadyOpen=false;
        ModelDoc2 model = GetOrOpenAssembly(sw, AssemblyPath, out er, out wr, out alreadyOpen);
        if (model == null) throw new Exception("OpenDoc6 failed, errors=" + er + ", warnings=" + wr);
        if (model.GetType() != (int)swDocumentTypes_e.swDocASSEMBLY)
            throw new Exception("Selected document is not an assembly. swDocType=" + model.GetType());
        Log((alreadyOpen ? "Using already open assembly" : "Opened assembly") + "; errors=" + er + "; warnings=" + wr);
        AssemblyDoc asm = model as AssemblyDoc;
        if (asm == null) throw new Exception("ModelDoc2 cannot be cast to AssemblyDoc");

        Stage = "RESOLVE_COMPONENTS";
        try { int rc = asm.ResolveAllLightWeightComponents(true); Log("ResolveAllLightWeightComponents rc=" + rc); }
        catch (Exception ex) { Errors.Add("ResolveAllLightWeightComponents:" + ex.Message); Log("Resolve warning: " + ex.Message); }

        Dictionary<string, object> root = new Dictionary<string, object>();
        root["schema"] = "k01_sw_semantic_raw_a001_v1_4"; root["status"] = "OK";
        try { root["solidworks_revision"] = sw.RevisionNumber(); } catch { root["solidworks_revision"] = ""; }
        Dictionary<string, object> assembly = new Dictionary<string, object>();
        assembly["title"] = model.GetTitle(); assembly["native_path"] = AssemblyPath;
        string activeCfg = "";
        try { activeCfg = model.ConfigurationManager.ActiveConfiguration.Name; } catch { }
        assembly["configuration"] = activeCfg; root["assembly"] = assembly;
        Log("Assembly title=" + assembly["title"] + "; config=" + activeCfg);

        Stage = "READ_COMPONENTS";
        List<object> instances = new List<object>(); List<object> documents = new List<object>();
        Dictionary<string, bool> docSeen = new Dictionary<string, bool>(StringComparer.OrdinalIgnoreCase);
        object compObj = asm.GetComponents(false);
        int compIndex=0;
        foreach (object co in Items(compObj)) {
            compIndex++;
            Component2 c = co as Component2; if (c == null) continue;
            Dictionary<string, object> ci = new Dictionary<string, object>();
            string name="", path="", cfg=""; bool suppressed=false;
            try { name=c.Name2; } catch { }
            try { path=c.GetPathName(); } catch { }
            try { cfg=c.ReferencedConfiguration; } catch { }
            suppressed=SafeSuppressed(c);
            ci["name"]=name; ci["path"]=path; ci["referenced_configuration"]=cfg; ci["suppressed"]=suppressed; ci["transform"]=TransformArray(c);
            instances.Add(ci); Log("Component " + compIndex + ": " + name + "; suppressed=" + suppressed + "; cfg=" + cfg);
            if (!suppressed && !String.IsNullOrEmpty(path)) {
                string key=path+"|"+cfg;
                if (!docSeen.ContainsKey(key)) {
                    docSeen[key]=true;
                    try {
                        ModelDoc2 cm = c.GetModelDoc2() as ModelDoc2;
                        if (cm != null) { Stage="READ_DOCUMENT:"+name; documents.Add(ReadDocument(cm,path,cfg)); Stage="READ_COMPONENTS"; }
                        else { Errors.Add("GetModelDoc2:null:"+name); Log("WARNING GetModelDoc2 returned null for "+name); }
                    } catch (Exception ex) { Errors.Add("document:"+name+":"+ex.Message); Log("WARNING document read failed for "+name+": "+ex.Message); }
                }
            }
        }
        assembly["component_count"]=instances.Count; root["instances"]=instances; root["documents"]=documents;
        Log("Components read="+instances.Count+"; unique documents="+documents.Count);

        Stage="READ_MATES";
        List<object> mates=new List<object>();
        try {
            Feature f=model.FirstFeature() as Feature; int guard=0;
            while(f!=null && guard++<10000) {
                string type="",name=""; try{type=f.GetTypeName2();}catch{} try{name=f.Name;}catch{}
                if((type??"").IndexOf("Mate",StringComparison.OrdinalIgnoreCase)>=0) {
                    Dictionary<string,object> m=new Dictionary<string,object>(); m["name"]=name;m["type"]=type;m["suppressed"]=SafeSuppressed(f);mates.Add(m);
                    try { Feature sf=f.GetFirstSubFeature() as Feature; int sg=0; while(sf!=null&&sg++<1000){string st="",sn="";try{st=sf.GetTypeName2();}catch{}try{sn=sf.Name;}catch{}Dictionary<string,object> sm=new Dictionary<string,object>();sm["name"]=sn;sm["type"]=st;sm["suppressed"]=SafeSuppressed(sf);mates.Add(sm);try{sf=sf.GetNextSubFeature() as Feature;}catch{sf=null;}} } catch { }
                }
                try{f=f.GetNextFeature() as Feature;}catch{f=null;}
            }
        } catch(Exception ex){Errors.Add("mates:"+ex.Message);Log("WARNING mate extraction failed: "+ex.Message);}
        root["mates"]=mates; root["errors"]=Errors;
        Log("Mates read="+mates.Count+"; accumulated warnings="+Errors.Count);

        Stage="WRITE_JSON"; WriteJson(OutPath,root); Log("Raw semantic JSON written: "+OutPath);
        Stage="DONE"; Log("PASS K01CadSemanticA001 v1.7");
        Console.WriteLine("PASS K01CadSemanticA001 v1.7");
        Console.WriteLine("assembly="+AssemblyPath); Console.WriteLine("components="+instances.Count+" documents="+documents.Count+" mates="+mates.Count+" warnings="+Errors.Count); Console.WriteLine("out="+OutPath);
    }

    [STAThread]
    public static int Main(string[] args)
    {
        try { Console.OutputEncoding=Encoding.UTF8; MainImpl(args); return 0; }
        catch(Exception ex){try{Log("ERROR: "+ex);}catch{} WriteFailure(ex); try{Console.Error.WriteLine("ERROR: "+ex);}catch{} return 1;}
    }
}
