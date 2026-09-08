using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Runtime.InteropServices;
using System.Web.Script.Serialization;
using SolidWorks.Interop.sldworks;
using SolidWorks.Interop.swconst;

namespace Marvilon.K01.Gate04C.Verify
{
    public sealed class PathsCfg
    {
        public string stable_p003 { get; set; }
        public string stable_p007 { get; set; }
        public string stable_a001 { get; set; }
        public string candidate_dir { get; set; }
        public string verification_dir { get; set; }
        public string report_dir { get; set; }
    }
    public sealed class GateCfg { public PathsCfg paths { get; set; } }

    public sealed class Report
    {
        public string schema = "k01_gate04c_typed_verify_v1";
        public string created_utc = DateTime.UtcNow.ToString("o");
        public string status = "RUNNING";
        public string solidworks_revision = "";
        public string verification_assembly = "";
        public int mate_feature_errors = -1;
        public int interference_count = -1;
        public bool p003_candidate_link = false;
        public bool p007_candidate_link = false;
        public bool p007_rotation_aligned_to_p003 = false;
        public bool persistent_clocking_mate_added = false;
        public List<string> checks = new List<string>();
        public List<string> warnings = new List<string>();
        public string error = "";
    }

    public static class Program
    {
        static SldWorks sw;
        static GateCfg Cfg;
        static Report R = new Report();
        static string Root;
        static string P003Candidate;
        static string P007Candidate;
        static string VerifyAssembly;
        static string LogPath;
        static string ReportPath;

        public static int Main(string[] args)
        {
            Root = ResolvePackageRoot();
            try
            {
                LoadConfig();
                Prepare();
                Log("K01 Gate04C typed VERIFY v1");
                Connect();
                Verify();
                R.status = "PASS";
                SaveReport();
                Log("STATUS=PASS");
                return 0;
            }
            catch (Exception ex)
            {
                R.status = "FAIL";
                R.error = ex.ToString();
                try { SaveReport(); } catch { }
                try { Log("STATUS=FAIL\r\n" + ex); } catch { }
                return 1;
            }
        }

        static void LoadConfig()
        {
            string p = Path.Combine(Root, "K01_GATE04C_PARAMS_v1.json");
            if (!File.Exists(p)) throw new Exception("Missing parameter file: " + p);
            var js = new JavaScriptSerializer();
            Cfg = js.Deserialize<GateCfg>(File.ReadAllText(p));
            if (Cfg == null || Cfg.paths == null) throw new Exception("Invalid parameter file.");

            P003Candidate = Path.Combine(Cfg.paths.candidate_dir, "K01-P-003_Cartridge_Body_GATE04C_CANDIDATE.SLDPRT");
            P007Candidate = Path.Combine(Cfg.paths.candidate_dir, "K01-P-007_Hermetic_Magnetic_Can_GATE04C_CANDIDATE.SLDPRT");
            VerifyAssembly = Path.Combine(Cfg.paths.verification_dir, "K01-A-001_GATE04C_VERIFY.SLDASM");
            R.verification_assembly = VerifyAssembly;
        }

        static void Prepare()
        {
            Directory.CreateDirectory(Cfg.paths.verification_dir);
            Directory.CreateDirectory(Path.Combine(Cfg.paths.verification_dir, "history"));
            Directory.CreateDirectory(Cfg.paths.report_dir);
            string stamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");
            LogPath = Path.Combine(Cfg.paths.report_dir, "K01_GATE04C_TYPED_VERIFY_" + stamp + ".log");
            ReportPath = Path.Combine(Cfg.paths.report_dir, "K01_GATE04C_TYPED_VERIFY.json");
            File.WriteAllText(LogPath, "K01 Gate04C strongly typed assembly verification\r\n");
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

        static void Verify()
        {
            RequireFile(Cfg.paths.stable_a001);
            RequireFile(P003Candidate);
            RequireFile(P007Candidate);

            ArchiveThenCopy(Cfg.paths.stable_a001, VerifyAssembly);

            int e = 0, w = 0;
            ModelDoc2 doc = sw.OpenDoc6(
                VerifyAssembly,
                (int)swDocumentTypes_e.swDocASSEMBLY,
                (int)swOpenDocOptions_e.swOpenDocOptions_Silent,
                "",
                ref e,
                ref w) as ModelDoc2;
            if (doc == null) throw new Exception("Open verification A001 failed errors=" + e);
            string title = doc.GetTitle();

            try
            {
                AssemblyDoc asm = doc as AssemblyDoc;
                if (asm == null) throw new Exception("Verification document did not cast to AssemblyDoc.");

                Component2 old3 = FindByPath(asm, Cfg.paths.stable_p003);
                Component2 old7 = FindByPath(asm, Cfg.paths.stable_p007);
                if (old3 == null) throw new Exception("Stable P003 component not found in A001 copy.");
                if (old7 == null) throw new Exception("Stable P007 component not found in A001 copy.");

                ReplaceOne(asm, doc, old3, P003Candidate, "P003");
                ReplaceOne(asm, doc, old7, P007Candidate, "P007");

                Component2 p003 = FindByPath(asm, P003Candidate);
                Component2 p007 = FindByPath(asm, P007Candidate);
                R.p003_candidate_link = p003 != null;
                R.p007_candidate_link = p007 != null;
                if (p003 == null || p007 == null)
                    throw new Exception("Candidate links were not found after replacement.");

                // P007 was axisymmetric before Gate04C and its current assembly rotation was arbitrary.
                // New PCD holes make clocking physical. Align local rotation to P003 while keeping P007 translation.
                AlignRotationOnly(p003, p007);
                R.p007_rotation_aligned_to_p003 = true;

                R.persistent_clocking_mate_added = TryAddTopPlaneClockingMate(asm, doc, p003, p007);
                if (!R.persistent_clocking_mate_added)
                    R.warnings.Add("Typed transform is aligned, but persistent Top Plane clocking mate was not added. Treat verification as HOLD for final promotion until existing K01 assembly QA confirms rotational constraint.");

                doc.ForceRebuild3(false);

                R.mate_feature_errors = CountMateErrors(doc);
                if (R.mate_feature_errors != 0)
                    throw new Exception("Mate feature errors detected: " + R.mate_feature_errors);

                R.interference_count = RunInterference(asm);
                Log("Interference count=" + R.interference_count);
                R.warnings.Add("Absolute interference count is evidence only. Known pre-existing K01 interference pairs must be dispositioned by the existing interference QA; this tool does not silently redefine them.");

                SetProperty(doc, "K01_GATE", "Gate04C_VERIFY");
                SetProperty(doc, "K01_CandidateStatus", "VERIFICATION / NOT RELEASED");

                SaveCurrent(doc, "Gate04C verification A001");

                R.checks.Add("PASS: verification assembly references candidate P003 and P007.");
                R.checks.Add("PASS: P007 rotational transform aligned to P003 for the new J2 hole pattern.");
                R.checks.Add("PASS: mate feature errors = 0.");
                Log("Verification stage PASS.");
            }
            finally
            {
                try { sw.CloseDoc(title); } catch { }
            }
        }

        static void ReplaceOne(AssemblyDoc asm, ModelDoc2 doc, Component2 oldComp, string newPath, string tag)
        {
            doc.ClearSelection2(true);
            if (!oldComp.Select4(false, null, false))
                throw new Exception(tag + ": component Select4 failed.");

            bool ok = asm.ReplaceComponents2(
                newPath,
                "",
                false,
                (int)swReplaceComponentsConfiguration_e.swReplaceComponentsConfiguration_MatchName,
                true);
            if (!ok) throw new Exception(tag + ": ReplaceComponents2 returned false.");
            Log(tag + " replaced with candidate.");
        }

        static Component2 FindByPath(AssemblyDoc asm, string path)
        {
            foreach (object o in ToObjects(asm.GetComponents(false)))
            {
                Component2 c = o as Component2;
                if (c == null) continue;
                string p = "";
                try { p = c.GetPathName(); } catch { }
                if (String.Equals(Normalize(p), Normalize(path), StringComparison.OrdinalIgnoreCase))
                    return c;
            }
            return null;
        }

        static void AlignRotationOnly(Component2 reference, Component2 moving)
        {
            MathTransform tr = reference.Transform2;
            MathTransform tm = moving.Transform2;
            if (tr == null || tm == null) throw new Exception("Component Transform2 unavailable.");

            double[] ar = ToDoubleArray(tr.ArrayData);
            double[] am = ToDoubleArray(tm.ArrayData);
            if (ar.Length < 16 || am.Length < 16) throw new Exception("Unexpected transform array size.");

            for (int i = 0; i < 9; i++) am[i] = ar[i]; // rotation
            // am[9..11] translation stays exactly as it was.

            MathUtility mu = sw.GetMathUtility() as MathUtility;
            MathTransform nt = mu.CreateTransform(am) as MathTransform;
            if (nt == null) throw new Exception("CreateTransform failed.");
            moving.Transform2 = nt;
            Log("P007 rotation aligned to P003; translation preserved.");
        }

        static bool TryAddTopPlaneClockingMate(AssemblyDoc asm, ModelDoc2 doc, Component2 p003, Component2 p007)
        {
            try
            {
                Feature f3 = p003.FeatureByName("Top Plane") as Feature;
                Feature f7 = p007.FeatureByName("Top Plane") as Feature;
                if (f3 == null || f7 == null)
                {
                    Log("Clocking mate warning: Top Plane not found.");
                    return false;
                }

                doc.ClearSelection2(true);
                if (!f3.Select2(false, 1) || !f7.Select2(true, 1))
                {
                    Log("Clocking mate warning: plane selection failed.");
                    return false;
                }

                int mateError = 0;
                object result = asm.AddMate5(
                    (int)swMateType_e.swMateCOINCIDENT,
                    (int)swMateAlign_e.swMateAlignALIGNED,
                    false,
                    0.0, 0.0, 0.0,
                    1.0, 1.0,
                    0.0, 0.0, 0.0,
                    false,
                    false,
                    0,
                    out mateError);

                if (result == null || mateError != 0)
                {
                    Log("Clocking mate warning: AddMate5 result=" + (result == null ? "null" : "object") + " error=" + mateError);
                    return false;
                }
                Log("Persistent Top Plane clocking mate added.");
                return true;
            }
            catch (Exception ex)
            {
                Log("Clocking mate warning: " + ex.Message);
                return false;
            }
        }

        static int CountMateErrors(ModelDoc2 doc)
        {
            int n = 0;
            Feature f = doc.FirstFeature() as Feature;
            int guard = 0;
            while (f != null && guard++ < 5000)
            {
                if (String.Equals(f.GetTypeName2(), "MateGroup", StringComparison.OrdinalIgnoreCase))
                {
                    Feature sf = f.GetFirstSubFeature() as Feature;
                    while (sf != null)
                    {
                        bool warning;
                        int code = sf.GetErrorCode2(out warning);
                        if (code != 0 && !warning)
                        {
                            n++;
                            Log("MATE ERROR " + sf.Name + " code=" + code);
                        }
                        sf = sf.GetNextSubFeature() as Feature;
                    }
                }
                f = f.GetNextFeature() as Feature;
            }
            return n;
        }

        static int RunInterference(AssemblyDoc asm)
        {
            try
            {
                InterferenceDetectionMgr mgr = asm.InterferenceDetectionManager;
                if (mgr == null)
                {
                    R.warnings.Add("InterferenceDetectionManager unavailable.");
                    return -1;
                }

                mgr.GetInterferences();
                return mgr.GetInterferenceCount();
            }
            catch (Exception ex)
            {
                R.warnings.Add("Interference API warning: " + ex.Message);
                return -1;
            }
        }

        static void SaveCurrent(ModelDoc2 doc, string label)
        {
            int e = 0, w = 0;
            bool ok = doc.Save3((int)swSaveAsOptions_e.swSaveAsOptions_Silent, ref e, ref w);
            if (!ok || e != 0) throw new Exception(label + " Save3 failed errors=" + e + " warnings=" + w);
            Log(label + " saved.");
        }

        static void SetProperty(ModelDoc2 doc, string key, string value)
        {
            CustomPropertyManager cpm = doc.Extension.get_CustomPropertyManager("");
            try { cpm.Delete2(key); } catch { }
            int r = cpm.Add(key, "Text", value ?? "");
            if (r == 0) try { cpm.Set2(key, value ?? ""); } catch { }
        }

        static void ArchiveThenCopy(string src, string dst)
        {
            RequireFile(src);
            Directory.CreateDirectory(Path.GetDirectoryName(dst));
            CloseIfOpen(dst);

            if (File.Exists(dst))
            {
                string hdir = Path.Combine(Path.GetDirectoryName(dst), "history");
                Directory.CreateDirectory(hdir);
                string hist = Path.Combine(
                    hdir,
                    Path.GetFileNameWithoutExtension(dst) + "_" + DateTime.Now.ToString("yyyyMMdd_HHmmss") + Path.GetExtension(dst));
                File.Copy(dst, hist, true);
                File.Delete(dst);
                Log("Archived previous verification assembly: " + hist);
            }
            File.Copy(src, dst, true);
            Log("Copied stable A001 -> verification assembly.");
        }

        static void CloseIfOpen(string path)
        {
            try
            {
                ModelDoc2 d = sw.GetOpenDocumentByName(path) as ModelDoc2;
                if (d != null) sw.CloseDoc(d.GetTitle());
            }
            catch { }
        }

        static void RequireFile(string p)
        {
            if (!File.Exists(p)) throw new Exception("Required file missing: " + p);
        }

        static string Normalize(string p)
        {
            if (String.IsNullOrWhiteSpace(p)) return "";
            try { return Path.GetFullPath(p).TrimEnd('\\').ToLowerInvariant(); }
            catch { return p.Trim().ToLowerInvariant(); }
        }

        static object[] ToObjects(object raw)
        {
            if (raw == null) return new object[0];
            object[] o = raw as object[];
            if (o != null) return o;
            Array a = raw as Array;
            if (a == null) return new object[] { raw };
            object[] r = new object[a.Length];
            for (int i = 0; i < a.Length; i++) r[i] = a.GetValue(i);
            return r;
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

        static string ResolvePackageRoot()
        {
            string exeDir = AppDomain.CurrentDomain.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar);
            string cwd = global::System.Environment.CurrentDirectory.TrimEnd(Path.DirectorySeparatorChar);

            string[] candidates = new string[]
            {
                exeDir,
                Directory.GetParent(exeDir) != null ? Directory.GetParent(exeDir).FullName : exeDir,
                cwd,
                Directory.GetParent(cwd) != null ? Directory.GetParent(cwd).FullName : cwd
            };

            foreach (string c in candidates)
            {
                if (String.IsNullOrWhiteSpace(c)) continue;
                string p = Path.Combine(c, "K01_GATE04C_PARAMS_v1.json");
                if (File.Exists(p))
                    return c.TrimEnd(Path.DirectorySeparatorChar);
            }

            throw new Exception(
                "Cannot locate K01_GATE04C_PARAMS_v1.json. " +
                "Checked EXE directory, its parent, current working directory, and its parent. " +
                "EXE=" + exeDir + "; CWD=" + cwd);
        }

        static void Log(string s)
        {
            string line = "[" + DateTime.Now.ToString("s") + "] " + s;
            Console.WriteLine(line);
            if (!String.IsNullOrWhiteSpace(LogPath))
                File.AppendAllText(LogPath, line + global::System.Environment.NewLine);
        }

        static void SaveReport()
        {
            var js = new JavaScriptSerializer();
            File.WriteAllText(ReportPath, js.Serialize(R));
        }
    }
}
