using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Runtime.InteropServices;
using System.Web.Script.Serialization;
using SolidWorks.Interop.sldworks;
using SolidWorks.Interop.swconst;

namespace Marvilon.K01.Gate04C.MateDiag
{
    public sealed class EntityInfo
    {
        public int index;
        public string component_name = "";
        public string component_path = "";
        public int reference_type = -1;
        public string reference_runtime_type = "";
        public double[] entity_params = new double[0];
    }

    public sealed class MateInfo
    {
        public string name = "";
        public string feature_type = "";
        public int error_code = 0;
        public bool warning = false;
        public int entity_count = 0;
        public List<EntityInfo> entities = new List<EntityInfo>();
    }

    public sealed class AssemblyInfo
    {
        public string path = "";
        public int mate_count = 0;
        public int mate_error_count = 0;
        public List<MateInfo> mates = new List<MateInfo>();
        public MateInfo concentric5 = null;
    }

    public sealed class Report
    {
        public string schema = "k01_gate04c_mate_diag_v2";
        public string created_utc = DateTime.UtcNow.ToString("o");
        public string status = "RUNNING";
        public string solidworks_revision = "";
        public AssemblyInfo stable = null;
        public AssemblyInfo verification = null;
        public List<string> conclusions = new List<string>();
        public string error = "";
    }

    public static class Program
    {
        const string STABLE =
            @"D:\Marvilon\K01\cad\assemblies\K01-A-001_Calibration_Module.SLDASM";
        const string VERIFY =
            @"D:\Marvilon\K01\cad\candidates\gate04c\verification\K01-A-001_GATE04C_VERIFY.SLDASM";
        const string REPORT_DIR =
            @"D:\BreshevEngineering\marvilon-k01\reports\cad\current";

        static SldWorks sw;
        static Report R = new Report();
        static string LogPath;
        static string JsonPath;

        public static int Main(string[] args)
        {
            try
            {
                Directory.CreateDirectory(REPORT_DIR);
                string stamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");
                LogPath = Path.Combine(REPORT_DIR, "K01_GATE04C_MATE_DIAG_" + stamp + ".log");
                JsonPath = Path.Combine(REPORT_DIR, "K01_GATE04C_MATE_DIAG.json");
                File.WriteAllText(LogPath, "K01 Gate04C mate diagnostic v2\r\n");

                Connect();
                R.stable = InspectAssembly(STABLE, "STABLE");
                R.verification = InspectAssembly(VERIFY, "VERIFY");

                Compare();
                R.status = "PASS_DIAGNOSTIC";
                Save();
                Log("STATUS=PASS_DIAGNOSTIC");
                return 0;
            }
            catch (Exception ex)
            {
                R.status = "FAIL_DIAGNOSTIC";
                R.error = ex.ToString();
                try { Save(); } catch { }
                try { Log("STATUS=FAIL_DIAGNOSTIC\r\n" + ex); } catch { }
                return 1;
            }
        }

        static void Connect()
        {
            object active = null;
            try { active = Marshal.GetActiveObject("SldWorks.Application"); } catch { }
            if (active != null) sw = (SldWorks)active;
            else
            {
                Type t = Type.GetTypeFromProgID("SldWorks.Application", true);
                sw = (SldWorks)Activator.CreateInstance(t);
            }
            if (sw == null) throw new Exception("Could not connect to SOLIDWORKS.");
            sw.Visible = true;
            R.solidworks_revision = sw.RevisionNumber();
            Log("Connected. Revision=" + R.solidworks_revision);
        }

        static AssemblyInfo InspectAssembly(string path, string tag)
        {
            if (!File.Exists(path))
                throw new Exception(tag + " assembly missing: " + path);

            int e = 0, w = 0;
            int opts =
                (int)swOpenDocOptions_e.swOpenDocOptions_Silent |
                (int)swOpenDocOptions_e.swOpenDocOptions_ReadOnly;

            ModelDoc2 doc = sw.OpenDoc6(
                path,
                (int)swDocumentTypes_e.swDocASSEMBLY,
                opts,
                "",
                ref e,
                ref w) as ModelDoc2;

            if (doc == null)
                throw new Exception(tag + " OpenDoc6 failed errors=" + e + " warnings=" + w);

            string title = doc.GetTitle();
            try
            {
                AssemblyInfo a = new AssemblyInfo();
                a.path = path;

                Feature f = doc.FirstFeature() as Feature;
                int guard = 0;
                while (f != null && guard++ < 5000)
                {
                    if (String.Equals(f.GetTypeName2(), "MateGroup", StringComparison.OrdinalIgnoreCase))
                    {
                        Feature mf = f.GetFirstSubFeature() as Feature;
                        while (mf != null)
                        {
                            MateInfo mi = InspectMate(mf);
                            a.mates.Add(mi);
                            a.mate_count++;
                            if (mi.error_code != 0 && !mi.warning)
                                a.mate_error_count++;

                            if (String.Equals(mi.name, "Concentric5", StringComparison.OrdinalIgnoreCase))
                                a.concentric5 = mi;

                            mf = mf.GetNextSubFeature() as Feature;
                        }
                    }
                    f = f.GetNextFeature() as Feature;
                }

                Log(tag + " mates=" + a.mate_count + " errors=" + a.mate_error_count);
                if (a.concentric5 != null)
                    LogMate(tag + " Concentric5", a.concentric5);
                else
                    Log(tag + " Concentric5 NOT FOUND");

                return a;
            }
            finally
            {
                try { sw.CloseDoc(title); } catch { }
            }
        }

        static MateInfo InspectMate(Feature f)
        {
            MateInfo mi = new MateInfo();
            mi.name = f.Name ?? "";
            mi.feature_type = f.GetTypeName2() ?? "";

            bool warn = false;
            int ec = f.GetErrorCode2(out warn);
            mi.error_code = ec;
            mi.warning = warn;

            try
            {
                Mate2 mate = f.GetSpecificFeature2() as Mate2;
                if (mate != null)
                {
                    int n = mate.GetMateEntityCount();
                    mi.entity_count = n;
                    for (int i = 0; i < n; i++)
                    {
                        EntityInfo ei = new EntityInfo();
                        ei.index = i;
                        try
                        {
                            MateEntity2 me = mate.MateEntity(i);
                            if (me != null)
                            {
                                try
                                {
                                    Component2 c = me.ReferenceComponent;
                                    if (c != null)
                                    {
                                        ei.component_name = c.Name2 ?? "";
                                        ei.component_path = c.GetPathName() ?? "";
                                    }
                                }
                                catch { }

                                try { ei.reference_type = me.ReferenceType2; } catch { }

                                try
                                {
                                    object r = me.Reference;
                                    if (r != null) ei.reference_runtime_type = r.GetType().FullName ?? r.GetType().Name;
                                }
                                catch { }

                                try { ei.entity_params = ToDoubleArray(me.EntityParams); } catch { }
                            }
                        }
                        catch { }
                        mi.entities.Add(ei);
                    }
                }
            }
            catch { }

            return mi;
        }

        static void Compare()
        {
            if (R.stable == null || R.verification == null) return;

            if (R.stable.mate_error_count == 0)
                R.conclusions.Add("Stable A001 mate baseline is clean.");
            else
                R.conclusions.Add("Stable A001 already contains mate errors; do not attribute all errors to Gate04C.");

            if (R.stable.concentric5 != null && R.stable.concentric5.error_code == 0)
                R.conclusions.Add("Concentric5 is healthy in stable A001.");

            if (R.verification.concentric5 != null && R.verification.concentric5.error_code != 0)
                R.conclusions.Add("Concentric5 becomes broken in Gate04C verification.");

            if (R.stable.concentric5 != null)
            {
                string stableRefs = RefSummary(R.stable.concentric5);
                R.conclusions.Add("Stable Concentric5 references: " + stableRefs);
            }

            if (R.verification.concentric5 != null)
            {
                string verifyRefs = RefSummary(R.verification.concentric5);
                R.conclusions.Add("Verification Concentric5 references: " + verifyRefs);
            }
        }

        static string RefSummary(MateInfo m)
        {
            List<string> s = new List<string>();
            foreach (EntityInfo e in m.entities)
            {
                string token = String.IsNullOrWhiteSpace(e.component_name)
                    ? "(component unavailable)"
                    : e.component_name;
                token += " type=" + e.reference_type;
                if (e.entity_params != null && e.entity_params.Length > 0)
                    token += " params=[" + JoinDoubles(e.entity_params) + "]";
                s.Add(token);
            }
            return String.Join(" | ", s.ToArray());
        }

        static void LogMate(string prefix, MateInfo m)
        {
            Log(prefix + " type=" + m.feature_type +
                " error=" + m.error_code +
                " warning=" + m.warning +
                " entities=" + m.entity_count);

            foreach (EntityInfo e in m.entities)
            {
                Log("  entity " + e.index +
                    " component=" + e.component_name +
                    " path=" + e.component_path +
                    " reference_type=" + e.reference_type +
                    " runtime=" + e.reference_runtime_type +
                    " params=[" + JoinDoubles(e.entity_params) + "]");
            }
        }

        static string JoinDoubles(double[] a)
        {
            if (a == null) return "";
            string[] s = new string[a.Length];
            for (int i = 0; i < a.Length; i++)
                s[i] = a[i].ToString("0.#########", CultureInfo.InvariantCulture);
            return String.Join(",", s);
        }

        static double[] ToDoubleArray(object raw)
        {
            if (raw == null) return new double[0];
            double[] d = raw as double[];
            if (d != null) return d;

            Array a = raw as Array;
            if (a == null) return new double[0];

            double[] r = new double[a.Length];
            for (int i = 0; i < a.Length; i++)
                r[i] = Convert.ToDouble(a.GetValue(i), CultureInfo.InvariantCulture);
            return r;
        }

        static void Log(string s)
        {
            string line = "[" + DateTime.Now.ToString("s") + "] " + s;
            Console.WriteLine(line);
            File.AppendAllText(LogPath, line + global::System.Environment.NewLine);
        }

        static void Save()
        {
            var js = new JavaScriptSerializer();
            File.WriteAllText(JsonPath, js.Serialize(R));
        }
    }
}
