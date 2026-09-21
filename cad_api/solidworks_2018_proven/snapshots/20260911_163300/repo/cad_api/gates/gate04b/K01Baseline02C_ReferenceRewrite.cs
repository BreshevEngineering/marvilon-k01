using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Runtime.InteropServices;
using System.Web.Script.Serialization;
using SolidWorks.Interop.sldworks;
using SolidWorks.Interop.swconst;

namespace Marvilon.K01.Baseline02C.ReferenceRewrite
{
    public sealed class RewriteRow
    {
        public string id="";
        public string old_path="";
        public string new_path="";
        public int old_count_before=0;
        public int new_count_after=0;
    }

    public sealed class RewriteReport
    {
        public string schema="k01_baseline_02c_reference_rewrite_v1";
        public string created_utc=DateTime.UtcNow.ToString("o");
        public string status="RUNNING";
        public string assembly="";
        public string solidworks_revision="";
        public int open_errors=0;
        public int open_warnings=0;
        public int active_mate_errors=-1;
        public int modeled_occurrences=0;
        public List<RewriteRow> replacements=new List<RewriteRow>();
        public List<string> candidate_links=new List<string>();
        public string error="";
    }

    public static class Program
    {
        static SldWorks sw;
        static bool createdSw=false;
        static string assemblyPath="";
        static string reportPath="";
        static readonly Dictionary<string,string> oldp=new Dictionary<string,string>(StringComparer.OrdinalIgnoreCase);
        static readonly Dictionary<string,string> newp=new Dictionary<string,string>(StringComparer.OrdinalIgnoreCase);
        static RewriteReport R=new RewriteReport();

        static string Norm(string p)
        {
            try{return Path.GetFullPath(p).TrimEnd('\\').ToLowerInvariant();}
            catch{return (p??"").ToLowerInvariant();}
        }

        static string SafePath(Component2 c)
        {
            try{return c.GetPathName()??"";}catch{return "";}
        }

        static object[] ToObjects(object x)
        {
            if(x==null)return new object[0];
            object[] o=x as object[]; if(o!=null)return o;
            Array a=x as Array; if(a==null)return new object[]{x};
            object[] r=new object[a.Length];
            for(int i=0;i<a.Length;i++)r[i]=a.GetValue(i);
            return r;
        }

        static List<Component2> FindAll(AssemblyDoc asm,string path)
        {
            List<Component2> r=new List<Component2>();
            string q=Norm(path);
            foreach(object o in ToObjects(asm.GetComponents(false)))
            {
                Component2 c=o as Component2;
                if(c!=null && String.Equals(Norm(SafePath(c)),q,StringComparison.OrdinalIgnoreCase))
                    r.Add(c);
            }
            return r;
        }

        static int CountModeled(AssemblyDoc asm)
        {
            int n=0;
            foreach(object o in ToObjects(asm.GetComponents(false)))
            {
                Component2 c=o as Component2; if(c==null)continue;
                if(c.GetSuppression()==(int)swComponentSuppressionState_e.swComponentSuppressed)continue;
                if(!String.IsNullOrWhiteSpace(SafePath(c)))n++;
            }
            return n;
        }

        static Feature MateGroup(ModelDoc2 model)
        {
            Feature f=model.FirstFeature() as Feature;
            while(f!=null)
            {
                if(String.Equals(f.GetTypeName2(),"MateGroup",StringComparison.OrdinalIgnoreCase))
                    return f;
                f=f.GetNextFeature() as Feature;
            }
            return null;
        }

        static bool IsSuppressed(Feature f)
        {
            try
            {
                object o=f.IsSuppressed2(
                    (int)swInConfigurationOpts_e.swThisConfiguration,null);
                if(o is bool) return (bool)o;
                Array a=o as Array;
                if(a!=null && a.Length>0) return Convert.ToBoolean(a.GetValue(0));
            }
            catch{}
            return false;
        }

        static int ActiveMateErrors(ModelDoc2 model)
        {
            int n=0;
            Feature g=MateGroup(model);
            if(g==null)return 0;

            Feature f=g.GetFirstSubFeature() as Feature;
            while(f!=null)
            {
                if(!IsSuppressed(f))
                {
                    try
                    {
                        bool warning=false;
                        int code=f.GetErrorCode2(out warning);
                        if(code!=0 && !warning)n++;
                    }
                    catch{}
                }
                f=f.GetNextSubFeature() as Feature;
            }
            return n;
        }

        static void Need(string p)
        {
            if(String.IsNullOrWhiteSpace(p)||!File.Exists(p))
                throw new Exception("Missing "+p);
        }

        static void Parse(string[] args)
        {
            for(int i=0;i<args.Length;i++)
            {
                string a=args[i]??"";
                if(a.Equals("--assembly",StringComparison.OrdinalIgnoreCase)&&i+1<args.Length)
                    assemblyPath=args[++i];
                else if(a.Equals("--report",StringComparison.OrdinalIgnoreCase)&&i+1<args.Length)
                    reportPath=args[++i];
                else if(a.Equals("--old-p003",StringComparison.OrdinalIgnoreCase)&&i+1<args.Length)
                    oldp["P003"]=args[++i];
                else if(a.Equals("--new-p003",StringComparison.OrdinalIgnoreCase)&&i+1<args.Length)
                    newp["P003"]=args[++i];
                else if(a.Equals("--old-p016",StringComparison.OrdinalIgnoreCase)&&i+1<args.Length)
                    oldp["P016"]=args[++i];
                else if(a.Equals("--new-p016",StringComparison.OrdinalIgnoreCase)&&i+1<args.Length)
                    newp["P016"]=args[++i];
                else if(a.Equals("--old-p017",StringComparison.OrdinalIgnoreCase)&&i+1<args.Length)
                    oldp["P017"]=args[++i];
                else if(a.Equals("--new-p017",StringComparison.OrdinalIgnoreCase)&&i+1<args.Length)
                    newp["P017"]=args[++i];
            }
            if(String.IsNullOrWhiteSpace(assemblyPath))throw new Exception("--assembly required");
            if(String.IsNullOrWhiteSpace(reportPath))throw new Exception("--report required");
            foreach(string id in new string[]{"P003","P016","P017"})
                if(!oldp.ContainsKey(id)||!newp.ContainsKey(id))
                    throw new Exception("old/new path pair missing for "+id);
        }

        static void Connect()
        {
            object a=null;
            try{a=Marshal.GetActiveObject("SldWorks.Application");}catch{}
            createdSw=(a==null);
            sw=a!=null?(SldWorks)a:(SldWorks)Activator.CreateInstance(Type.GetTypeFromProgID("SldWorks.Application",true));
            sw.Visible=true;
            R.solidworks_revision=sw.RevisionNumber();
            if(!R.solidworks_revision.StartsWith("26."))
                throw new Exception("Expected SOLIDWORKS 2018 / revision 26; got "+R.solidworks_revision);
        }

        static void ReplaceOne(AssemblyDoc asm,ModelDoc2 doc,string id)
        {
            List<Component2> before=FindAll(asm,oldp[id]);
            RewriteRow row=new RewriteRow{id=id,old_path=oldp[id],new_path=newp[id],old_count_before=before.Count};
            R.replacements.Add(row);
            if(before.Count!=1)
                throw new Exception(id+" old reference count="+before.Count+" expected 1");

            doc.ClearSelection2(true);
            if(!before[0].Select4(false,null,false))
                throw new Exception(id+" Select4 failed");
            bool ok=asm.ReplaceComponents2(newp[id],"",false,
                (int)swReplaceComponentsConfiguration_e.swReplaceComponentsConfiguration_MatchName,true);
            if(!ok)throw new Exception(id+" ReplaceComponents2 returned false");
            doc.ForceRebuild3(false);

            row.new_count_after=FindAll(asm,newp[id]).Count;
            if(row.new_count_after!=1)
                throw new Exception(id+" new reference count="+row.new_count_after+" expected 1");
            if(FindAll(asm,oldp[id]).Count!=0)
                throw new Exception(id+" old candidate reference still present");
        }

        static void Save(ModelDoc2 doc)
        {
            int e=0,w=0;
            bool ok=doc.Save3((int)swSaveAsOptions_e.swSaveAsOptions_Silent,ref e,ref w);
            if(!ok||e!=0)throw new Exception("Save3 failed errors="+e+" warnings="+w);
        }

        static void WriteReport()
        {
            if(String.IsNullOrWhiteSpace(reportPath))return;
            Directory.CreateDirectory(Path.GetDirectoryName(reportPath));
            JavaScriptSerializer js=new JavaScriptSerializer();
            js.MaxJsonLength=Int32.MaxValue;
            File.WriteAllText(reportPath,js.Serialize(R));
        }

        public static int Main(string[] args)
        {
            try
            {
                Parse(args);
                Need(assemblyPath);
                foreach(string id in new string[]{"P003","P016","P017"})
                {
                    Need(oldp[id]); Need(newp[id]);
                }

                R.assembly=assemblyPath;
                Connect();

                int e=0,w=0;
                ModelDoc2 doc=sw.OpenDoc6(assemblyPath,(int)swDocumentTypes_e.swDocASSEMBLY,
                    (int)swOpenDocOptions_e.swOpenDocOptions_Silent,"",ref e,ref w) as ModelDoc2;
                R.open_errors=e;R.open_warnings=w;
                if(doc==null)throw new Exception("OpenDoc6 failed errors="+e+" warnings="+w);
                string title=doc.GetTitle();
                try
                {
                    AssemblyDoc asm=doc as AssemblyDoc;
                    if(asm==null)throw new Exception("Not an AssemblyDoc");
                    asm.ResolveAllLightWeightComponents(false);

                    ReplaceOne(asm,doc,"P003");
                    ReplaceOne(asm,doc,"P016");
                    ReplaceOne(asm,doc,"P017");

                    R.modeled_occurrences=CountModeled(asm);
                    if(R.modeled_occurrences!=14)
                        throw new Exception("Modeled occurrence count="+R.modeled_occurrences+" expected 14");

                    foreach(object o in ToObjects(asm.GetComponents(false)))
                    {
                        Component2 c=o as Component2;if(c==null)continue;
                        string p=SafePath(c);
                        if(p.IndexOf(@"\candidates\",StringComparison.OrdinalIgnoreCase)>=0)
                            R.candidate_links.Add((c.Name2??"")+" -> "+p);
                    }
                    if(R.candidate_links.Count!=0)
                        throw new Exception("Candidate references remain: "+String.Join(" | ",R.candidate_links.ToArray()));

                    R.active_mate_errors=ActiveMateErrors(doc);
                    if(R.active_mate_errors!=0)
                        throw new Exception("Active mate errors="+R.active_mate_errors);

                    Save(doc);
                    R.status="PASS_REFERENCE_REWRITE";
                }
                finally
                {
                    try{sw.CloseDoc(title);}catch{}
                }

                WriteReport();
                Console.WriteLine("STATUS: "+R.status);
                Console.WriteLine("REPORT: "+reportPath);
                return 0;
            }
            catch(Exception ex)
            {
                R.status="FAIL";
                R.error=ex.ToString();
                try{WriteReport();}catch{}
                Console.WriteLine("FAIL: K01 Baseline-02C reference rewrite");
                Console.WriteLine(ex.ToString());
                return 1;
            }
            finally
            {
                try{if(createdSw&&sw!=null)sw.ExitApp();}catch{}
                try
                {
                    if(sw!=null && Marshal.IsComObject(sw))
                        Marshal.FinalReleaseComObject(sw);
                }
                catch{}
                sw=null;
                try
                {
                    GC.Collect();
                    GC.WaitForPendingFinalizers();
                    GC.Collect();
                    GC.WaitForPendingFinalizers();
                }
                catch{}
            }
        }
    }
}
