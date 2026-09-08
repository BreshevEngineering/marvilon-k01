using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Web.Script.Serialization;
using SolidWorks.Interop.sldworks;
using SolidWorks.Interop.cosworks;

public class K01SimulationStudySelections
{
    static IEnumerable Items(object obj) {
        if (obj == null) yield break;
        Array a = obj as Array; if (a != null) { foreach(object x in a) yield return x; yield break; }
        IEnumerable en = obj as IEnumerable; if (en != null) foreach(object x in en) yield return x;
    }
    static List<double> DArr(object raw) { var a=new List<double>(); foreach(object v in Items(raw)) try{a.Add(Convert.ToDouble(v));}catch{} return a; }
    static string PartId(Component2 c) {
        string s=""; try{s=c==null?"":c.GetPathName();}catch{}
        if(String.IsNullOrEmpty(s)) try{s=c==null?"":c.Name2;}catch{}
        var m=System.Text.RegularExpressions.Regex.Match(s??"",@"(K01-[PBA]-\d{3})",System.Text.RegularExpressions.RegexOptions.IgnoreCase);
        return m.Success?m.Groups[1].Value.ToUpperInvariant():(s??"");
    }
    static Dictionary<string,object> FaceDescriptor(Face2 face, Component2 comp) {
        var d=new Dictionary<string,object>(); d["part_no"]=PartId(comp);
        try { Body2 b=face.GetBody() as Body2; d["body"]=b==null?"":b.Name; } catch { d["body"]=""; }
        try{d["area_m2"]=Convert.ToDouble(face.GetArea());}catch{d["area_m2"]=null;}
        try{d["box_m"]=DArr(face.GetBox());}catch{d["box_m"]=new List<double>();}
        try{d["normal"]=DArr(face.Normal);}catch{d["normal"]=new List<double>();}
        try { int ec=0; foreach(object _ in Items(face.GetEdges())) ec++; d["edge_count"]=ec; } catch { d["edge_count"]=null; }
        try {
            Surface s=face.IGetSurface(); bool pl=s.IsPlane(),cy=s.IsCylinder(),co=s.IsCone(),sp=s.IsSphere(),to=s.IsTorus();
            d["surface_type"]=pl?"plane":cy?"cylinder":co?"cone":sp?"sphere":to?"torus":"other";
            try{if(pl)d["plane_params"]=DArr(s.PlaneParams);}catch{}
            try{if(cy)d["cylinder_params"]=DArr(s.CylinderParams);}catch{}
            try{if(co)d["cone_params"]=DArr(s.ConeParams2);}catch{}
            try{if(sp)d["sphere_params"]=DArr(s.SphereParams);}catch{}
            try{if(to)d["torus_params"]=DArr(s.TorusParams);}catch{}
        } catch { d["surface_type"]="unknown"; }
        return d;
    }
    static Component2 ComponentForFace(ModelDoc2 model, Face2 face) {
        try {
            model.ClearSelection2(true); face.Select4(false,null);
            SelectionMgr sm=model.SelectionManager as SelectionMgr;
            Component2 c=sm==null?null:sm.GetSelectedObjectsComponent4(1,-1) as Component2;
            model.ClearSelection2(true); return c;
        } catch { try{model.ClearSelection2(true);}catch{} return null; }
    }
    static void Write(string p,object o) { Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(p))); var js=new JavaScriptSerializer();js.MaxJsonLength=Int32.MaxValue;File.WriteAllText(p,js.Serialize(o),new UTF8Encoding(false)); }
    [STAThread]
    public static int Main(string[] args) {
        string outp=null,studyName="Static 1";
        for(int i=0;i<args.Length-1;i++){ if(args[i]=="--out")outp=args[i+1]; if(args[i]=="--study")studyName=args[i+1]; }
        if(String.IsNullOrEmpty(outp)){Console.Error.WriteLine("--out required");return 2;}
        try {
            SldWorks sw=(SldWorks)Marshal.GetActiveObject("SldWorks.Application"); ModelDoc2 model=sw.ActiveDoc as ModelDoc2;
            if(model==null)throw new Exception("No active SOLIDWORKS document");
            CwAddincallback cb=(CwAddincallback)sw.GetAddInObject("SldWorks.Simulation"); if(cb==null)throw new Exception("SOLIDWORKS Simulation add-in not available");
            CosmosWorks cw=(CosmosWorks)cb.CosmosWorks; CWModelDoc act=(CWModelDoc)cw.ActiveDoc; if(act==null)throw new Exception("Simulation ActiveDoc unavailable");
            CWStudyManager mgr=(CWStudyManager)act.StudyManager; CWStudy study=null;
            for(int i=0;i<mgr.StudyCount;i++){ CWStudy x=(CWStudy)mgr.GetStudy(i); if(x!=null && String.Equals(x.Name,studyName,StringComparison.OrdinalIgnoreCase)){study=x;break;} }
            if(study==null)throw new Exception("Simulation study not found: "+studyName);
            var loads=new List<object>(); CWLoadsAndRestraintsManager lm=(CWLoadsAndRestraintsManager)study.LoadsAndRestraintsManager;
            for(int i=0;i<lm.Count;i++){
                int er=0; CWLoadsAndRestraints lr=(CWLoadsAndRestraints)lm.GetLoadsAndRestraints(i,out er); if(lr==null)continue;
                var row=new Dictionary<string,object>();row["name"]=lr.Name;row["type"]=lr.Type;row["state"]=lr.State;row["error_code"]=er;row["entity_count"]=lr.EntityCount;
                var ents=new List<object>();
                for(int j=0;j<lr.EntityCount;j++){
                    int st=0;object e=lr.GetEntityAt(j,out st);var ed=new Dictionary<string,object>();ed["select_type"]=st;ed["index"]=j;
                    Face2 f=e as Face2;if(f!=null){Component2 c=ComponentForFace(model,f);ed["entity_kind"]="FACE";ed["face"]=FaceDescriptor(f,c);}else{ed["entity_kind"]=e==null?"NULL":e.GetType().FullName;}
                    ents.Add(ed);
                }
                row["entities"]=ents;loads.Add(row);
            }
            var contact=new Dictionary<string,object>();
            try { CWContactManager cm=(CWContactManager)study.ContactManager; contact["contact_set_count"]=cm==null?0:cm.ContactSetCount; contact["contact_component_count"]=cm==null?0:cm.ContactComponentCount; }
            catch(Exception ex){contact["api_warning"]=ex.Message;}
            var payload=new Dictionary<string,object>();payload["schema"]="k01.swsim.study_selections.raw.v1_7";payload["status"]="PASS";payload["study_name"]=study.Name;payload["loads_and_restraints"]=loads;payload["contact_summary"]=contact;
            Write(outp,payload);Console.WriteLine("PASS Simulation selections study="+study.Name+" items="+loads.Count);return 0;
        } catch(Exception ex) { Write(outp,new Dictionary<string,object>{{"schema","k01.swsim.study_selections.raw.v1_7"},{"status","ERROR"},{"error",ex.ToString()}}); Console.Error.WriteLine(ex); return 3; }
    }
}
