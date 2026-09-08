using System;
using System.Collections.Generic;
using System.IO;
using System.Runtime.InteropServices;
using System.Web.Script.Serialization;
using SolidWorks.Interop.sldworks;
using SolidWorks.Interop.swconst;

namespace Marvilon.K01.Gate04D_C2.Drawings
{
    public sealed class PathsCfg
    {
        public string candidate_dir { get; set; }
        public string drawing_dir { get; set; }
        public string report_dir { get; set; }
    }
    public sealed class P003Cfg
    {
        public string material { get; set; }
        public string pilot_fit { get; set; }
        public string oring_size { get; set; }
        public string oring_material { get; set; }
        public double gland_ID_mm { get; set; }
        public double gland_OD_nominal_mm { get; set; }
        public double gland_depth_mm { get; set; }
        public string thread { get; set; }
    }
    public sealed class P007Cfg
    {
        public string material { get; set; }
        public string locator_fit { get; set; }
        public double overall_L_mm { get; set; }
        public double thin_OD_mm { get; set; }
        public double thin_ID_mm { get; set; }
        public double clearance_hole_D_mm { get; set; }
    }
    public sealed class J2Cfg
    {
        public double pattern_PCD_mm { get; set; }
        public int pattern_qty { get; set; }
        public double equal_spacing_deg { get; set; }
    }
    public sealed class GateCfg
    {
        public PathsCfg paths { get; set; }
        public P003Cfg P003 { get; set; }
        public P007Cfg P007 { get; set; }
        public J2Cfg J2 { get; set; }
    }
    public sealed class Report
    {
        public string schema = "k01_gate04d_c2_typed_drawings_v1";
        public string created_utc = DateTime.UtcNow.ToString("o");
        public string status = "RUNNING";
        public string solidworks_revision = "";
        public string p003_slddrw = "";
        public string p003_pdf = "";
        public string p007_slddrw = "";
        public string p007_pdf = "";
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
        static string LogPath;
        static string ReportPath;

        public static int Main(string[] args)
        {
            Root = ResolvePackageRoot();
            try
            {
                LoadConfig();
                Prepare();
                Log("K01 Gate04D-C2 typed DRAWINGS DRAFT v1");
                Connect();

                GenerateP003();
                GenerateP007();

                R.status = "PASS";
                R.checks.Add("PASS: K01-D-003 and K01-D-006 DRAFT_C2_API drawings generated as native SLDDRW + PDF.");
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
            string p = Path.Combine(Root, "K01_GATE04D_C2_PARAMS_v1.json");
            if (!File.Exists(p)) throw new Exception("Missing parameter file: " + p);
            var js = new JavaScriptSerializer();
            Cfg = js.Deserialize<GateCfg>(File.ReadAllText(p));
            if (Cfg == null || Cfg.paths == null) throw new Exception("Invalid parameter file.");

            P003Candidate = Path.Combine(Cfg.paths.candidate_dir, "K01-P-003_Cartridge_Body_GATE04D_C2_CANDIDATE.SLDPRT");
            P007Candidate = Path.Combine(Cfg.paths.candidate_dir, "K01-P-007_Hermetic_Magnetic_Can_GATE04D_C2_CANDIDATE.SLDPRT");
        }

        static void Prepare()
        {
            Directory.CreateDirectory(Cfg.paths.drawing_dir);
            Directory.CreateDirectory(Path.Combine(Cfg.paths.drawing_dir, "history"));
            Directory.CreateDirectory(Cfg.paths.report_dir);
            string stamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");
            LogPath = Path.Combine(Cfg.paths.report_dir, "K01_GATE04D_C2_TYPED_DRAWINGS_" + stamp + ".log");
            ReportPath = Path.Combine(Cfg.paths.report_dir, "K01_GATE04D_C2_TYPED_DRAWINGS.json");
            File.WriteAllText(LogPath, "K01 Gate04D-C2 strongly typed drawing generation\r\n");
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

        static void GenerateP003()
        {
            string notes =
                "DRAFT_C2_API - NOT RELEASED\r\n" +
                "K01-D-003 / K01-P-003 Cartridge Body / Gate04D-C2\r\n" +
                "MATERIAL: " + Cfg.P003.material + "\r\n" +
                "J2 FLANGE: OD33; existing 5 mm rear zone; rear mating datum station retained.\r\n" +
                "PILOT: OD14.10 " + Cfg.P003.pilot_fit + " x 1.50.\r\n" +
                "CLAMP: " + Cfg.J2.pattern_qty + "x " + Cfg.P003.thread +
                " equally spaced " + Cfg.J2.equal_spacing_deg.ToString("0") +
                " deg on PCD" + Cfg.J2.pattern_PCD_mm.ToString("0.##") + ".\r\n" +
                "STATIC SEAL: O-ring " + Cfg.P003.oring_size +
                "; gland ID" + Cfg.P003.gland_ID_mm.ToString("0.00") +
                " / OD" + Cfg.P003.gland_OD_nominal_mm.ToString("0.00") +
                " / depth" + Cfg.P003.gland_depth_mm.ToString("0.00") + ".\r\n" +
                "O-RING COMPOUND: " + Cfg.P003.oring_material + ". DO NOT RELEASE UNTIL COMPATIBILITY IS CLOSED.";

            string[] outp = GenerateDrawing(P003Candidate, "K01-D-003", notes);
            R.p003_slddrw = outp[0];
            R.p003_pdf = outp[1];
        }

        static void GenerateP007()
        {
            string notes =
                "DRAFT_C2_API - NOT RELEASED\r\n" +
                "K01-D-006 / K01-P-007 Hermetic Magnetic Can / Gate04D-C2\r\n" +
                "MATERIAL: " + Cfg.P007.material + "\r\n" +
                "OAL: " + Cfg.P007.overall_L_mm.ToString("0.00") + " retained.\r\n" +
                "J2 FLANGE: OD33 x 3.\r\n" +
                "LOCATOR: existing ID14.10 " + Cfg.P007.locator_fit + ".\r\n" +
                "CLAMP: " + Cfg.J2.pattern_qty + "x D" + Cfg.P007.clearance_hole_D_mm.ToString("0.00") +
                " equally spaced " + Cfg.J2.equal_spacing_deg.ToString("0") +
                " deg on PCD" + Cfg.J2.pattern_PCD_mm.ToString("0.##") + ".\r\n" +
                "CONTAINMENT THIN ZONE RETAINED: OD" + Cfg.P007.thin_OD_mm.ToString("0.00") +
                " / ID" + Cfg.P007.thin_ID_mm.ToString("0.00") + ".";

            string[] outp = GenerateDrawing(P007Candidate, "K01-D-006", notes);
            R.p007_slddrw = outp[0];
            R.p007_pdf = outp[1];
        }

        static string[] GenerateDrawing(string modelPath, string drawingNo, string engineeringNote)
        {
            RequireFile(modelPath);

            int e = 0, w = 0;
            ModelDoc2 model = sw.OpenDoc6(
                modelPath,
                (int)swDocumentTypes_e.swDocPART,
                (int)swOpenDocOptions_e.swOpenDocOptions_Silent,
                "",
                ref e,
                ref w) as ModelDoc2;
            if (model == null) throw new Exception("Could not open drawing source: " + modelPath + " errors=" + e);
            string modelTitle = model.GetTitle();

            try
            {
                MarkK01FeatureDimensions(model);
                SaveCurrent(model, "mark dimensions for " + drawingNo);

                string template = sw.GetUserPreferenceStringValue(
                    (int)swUserPreferenceStringValue_e.swDefaultTemplateDrawing);
                if (String.IsNullOrWhiteSpace(template) || !File.Exists(template))
                    throw new Exception("Default drawing template not found: " + template);

                ModelDoc2 dm = sw.NewDocument(template, 0, 0.0, 0.0) as ModelDoc2;
                if (dm == null) throw new Exception("NewDocument drawing failed for " + drawingNo);
                string drawTitle = dm.GetTitle();

                try
                {
                    DrawingDoc dr = dm as DrawingDoc;
                    if (dr == null) throw new Exception("New document did not cast to DrawingDoc.");

                    bool ok = dr.Create3rdAngleViews2(modelPath);
                    if (!ok) throw new Exception("Create3rdAngleViews2 failed for " + drawingNo);

                    try
                    {
                        dr.CreateDrawViewFromModelView3(modelPath, "*Isometric", 0.27, 0.07, 0.0);
                    }
                    catch (Exception ex)
                    {
                        R.warnings.Add(drawingNo + ": isometric view warning: " + ex.Message);
                    }

                    ImportAnnotations(dr, drawingNo);

                    try
                    {
                        Note n = dm.InsertNote(engineeringNote) as Note;
                        if (n != null)
                        {
                            Annotation a = n.GetAnnotation() as Annotation;
                            if (a != null) a.SetPosition2(0.02, 0.02, 0.0);
                        }
                    }
                    catch (Exception ex)
                    {
                        R.warnings.Add(drawingNo + ": engineering note insertion warning: " + ex.Message);
                    }

                    SetProperty(dm, "DrawingNo", drawingNo);
                    SetProperty(dm, "K01_DrawingStatus", "DRAFT_C2_API");
                    SetProperty(dm, "K01_SourceModel", modelPath);

                    dm.ForceRebuild3(false);

                    string stem = drawingNo + "_" + Path.GetFileNameWithoutExtension(modelPath) + "_DRAFT_C2_API";
                    string slddrw = Path.Combine(Cfg.paths.drawing_dir, stem + ".SLDDRW");
                    string pdf = Path.Combine(Cfg.paths.drawing_dir, stem + ".PDF");

                    ArchiveIfExists(slddrw);
                    ArchiveIfExists(pdf);

                    SaveAs3Checked(dm, slddrw);
                    SaveAs3Checked(dm, pdf);

                    Log("Generated " + slddrw);
                    Log("Generated " + pdf);
                    return new string[] { slddrw, pdf };
                }
                finally
                {
                    try { sw.CloseDoc(drawTitle); } catch { }
                }
            }
            finally
            {
                try { sw.CloseDoc(modelTitle); } catch { }
            }
        }

        static void ImportAnnotations(DrawingDoc dr, string drawingNo)
        {
            try
            {
                dr.InsertModelAnnotations3(
                    (int)swImportModelItemsSource_e.swImportModelItemsFromEntireModel,
                    (int)swInsertAnnotation_e.swInsertDimensionsMarkedForDrawing,
                    true, true, false, true);
            }
            catch (Exception ex) { R.warnings.Add(drawingNo + ": marked-dimension import: " + ex.Message); }

            try
            {
                dr.InsertModelAnnotations3(
                    (int)swImportModelItemsSource_e.swImportModelItemsFromEntireModel,
                    (int)swInsertAnnotation_e.swInsertDatums,
                    true, true, false, true);
            }
            catch (Exception ex) { R.warnings.Add(drawingNo + ": datum import: " + ex.Message); }

            try
            {
                dr.InsertModelAnnotations3(
                    (int)swImportModelItemsSource_e.swImportModelItemsFromEntireModel,
                    (int)swInsertAnnotation_e.swInsertGTols,
                    true, true, false, true);
            }
            catch (Exception ex) { R.warnings.Add(drawingNo + ": GTol import: " + ex.Message); }

            try
            {
                dr.InsertModelAnnotations3(
                    (int)swImportModelItemsSource_e.swImportModelItemsFromEntireModel,
                    (int)swInsertAnnotation_e.swInsertSFSymbols,
                    true, true, false, true);
            }
            catch (Exception ex) { R.warnings.Add(drawingNo + ": surface-finish import: " + ex.Message); }
        }

        static void MarkK01FeatureDimensions(ModelDoc2 model)
        {
            Feature f = model.FirstFeature() as Feature;
            int guard = 0;
            while (f != null && guard++ < 3000)
            {
                if (!String.IsNullOrEmpty(f.Name) && f.Name.StartsWith("K01_", StringComparison.OrdinalIgnoreCase))
                {
                    try
                    {
                        object o = f.GetFirstDisplayDimension();
                        int dg = 0;
                        while (o != null && dg++ < 200)
                        {
                            DisplayDimension dd = o as DisplayDimension;
                            if (dd != null) dd.MarkedForDrawing = true;
                            o = f.GetNextDisplayDimension(o);
                        }
                    }
                    catch { }
                }
                f = f.GetNextFeature() as Feature;
            }
        }

        static void SaveCurrent(ModelDoc2 doc, string label)
        {
            int e = 0, w = 0;
            bool ok = doc.Save3((int)swSaveAsOptions_e.swSaveAsOptions_Silent, ref e, ref w);
            if (!ok || e != 0) throw new Exception(label + " Save3 failed errors=" + e + " warnings=" + w);
        }

        static void SaveAs3Checked(ModelDoc2 doc, string path)
        {
            Directory.CreateDirectory(Path.GetDirectoryName(path));
            int status = doc.SaveAs3(path, 0, 0);
            if (status != 0 || !File.Exists(path))
                throw new Exception("SaveAs3 failed status=" + status + " path=" + path);
        }

        static void ArchiveIfExists(string path)
        {
            if (!File.Exists(path)) return;
            string hdir = Path.Combine(Path.GetDirectoryName(path), "history");
            Directory.CreateDirectory(hdir);
            string hist = Path.Combine(
                hdir,
                Path.GetFileNameWithoutExtension(path) + "_" + DateTime.Now.ToString("yyyyMMdd_HHmmss") + Path.GetExtension(path));
            File.Copy(path, hist, true);
            File.Delete(path);
        }

        static void SetProperty(ModelDoc2 doc, string key, string value)
        {
            CustomPropertyManager cpm = doc.Extension.get_CustomPropertyManager("");
            try { cpm.Delete2(key); } catch { }
            int r = cpm.Add(key, "Text", value ?? "");
            if (r == 0) try { cpm.Set2(key, value ?? ""); } catch { }
        }

        static void RequireFile(string p)
        {
            if (!File.Exists(p)) throw new Exception("Required file missing: " + p);
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
                string p = Path.Combine(c, "K01_GATE04D_C2_PARAMS_v1.json");
                if (File.Exists(p))
                    return c.TrimEnd(Path.DirectorySeparatorChar);
            }

            throw new Exception(
                "Cannot locate K01_GATE04D_C2_PARAMS_v1.json. " +
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
