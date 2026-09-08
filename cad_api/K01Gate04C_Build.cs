using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Runtime.InteropServices;
using System.Web.Script.Serialization;
using SolidWorks.Interop.sldworks;
using SolidWorks.Interop.swconst;

namespace Marvilon.K01.Gate04C
{
    public sealed class PathsCfg
    {
        public string stable_p003 { get; set; }
        public string stable_p007 { get; set; }
        public string candidate_dir { get; set; }
        public string report_dir { get; set; }
    }
    public sealed class P003Cfg
    {
        public string material { get; set; }
        public double current_rear_collar_OD_mm { get; set; }
        public double current_rear_collar_L_mm { get; set; }
        public double service_bore_minor_D_mm { get; set; }
        public double J2_flange_OD_mm { get; set; }
        public double J2_flange_depth_inward_mm { get; set; }
        public double pilot_OD_nominal_mm { get; set; }
        public string pilot_fit { get; set; }
        public double pilot_L_outward_mm { get; set; }
        public string oring_size { get; set; }
        public string oring_material { get; set; }
        public double gland_ID_mm { get; set; }
        public double gland_OD_nominal_mm { get; set; }
        public double gland_depth_mm { get; set; }
        public string thread { get; set; }
        public double tap_drill_D_mm { get; set; }
        public double tap_depth_mm { get; set; }
    }
    public sealed class P007Cfg
    {
        public string material { get; set; }
        public double overall_L_mm { get; set; }
        public double locator_ID_nominal_mm { get; set; }
        public string locator_fit { get; set; }
        public double thin_OD_mm { get; set; }
        public double thin_ID_mm { get; set; }
        public double J2_flange_OD_mm { get; set; }
        public double J2_flange_depth_inward_mm { get; set; }
        public double clearance_hole_D_mm { get; set; }
    }
    public sealed class J2Cfg
    {
        public int pattern_qty { get; set; }
        public double pattern_PCD_mm { get; set; }
        public double seed_angle_deg_local { get; set; }
        public double equal_spacing_deg { get; set; }
    }
    public sealed class GateCfg
    {
        public PathsCfg paths { get; set; }
        public P003Cfg P003 { get; set; }
        public P007Cfg P007 { get; set; }
        public J2Cfg J2 { get; set; }
    }
    public sealed class PlaneHit
    {
        public Face2 Face;
        public double X;
        public double NormalX;
        public double Area;
    }
    public sealed class Report
    {
        public string schema = "k01_gate04c_typed_build_v1";
        public string created_utc = DateTime.UtcNow.ToString("o");
        public string status = "RUNNING";
        public string solidworks_revision = "";
        public string production_p003_modified = "false";
        public string production_p007_modified = "false";
        public string p003_candidate = "";
        public string p007_candidate = "";
        public List<string> checks = new List<string>();
        public List<string> warnings = new List<string>();
        public string error = "";
    }

    public static class Program
    {
        const double MM = 0.001;
        const double PI = Math.PI;

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
                Log("K01 Gate04C typed BUILD v1");
                Connect();

                BuildP003();
                BuildP007();

                R.status = "PASS";
                R.checks.Add("PASS: stable P003/P007 were copied; only candidate files were modified.");
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
            if (Cfg == null || Cfg.paths == null || Cfg.P003 == null || Cfg.P007 == null || Cfg.J2 == null)
                throw new Exception("Invalid Gate04C parameter file.");

            P003Candidate = Path.Combine(Cfg.paths.candidate_dir, "K01-P-003_Cartridge_Body_GATE04C_CANDIDATE.SLDPRT");
            P007Candidate = Path.Combine(Cfg.paths.candidate_dir, "K01-P-007_Hermetic_Magnetic_Can_GATE04C_CANDIDATE.SLDPRT");
            R.p003_candidate = P003Candidate;
            R.p007_candidate = P007Candidate;
        }

        static void Prepare()
        {
            Directory.CreateDirectory(Cfg.paths.candidate_dir);
            Directory.CreateDirectory(Path.Combine(Cfg.paths.candidate_dir, "history"));
            Directory.CreateDirectory(Cfg.paths.report_dir);
            string stamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");
            LogPath = Path.Combine(Cfg.paths.report_dir, "K01_GATE04C_TYPED_BUILD_" + stamp + ".log");
            ReportPath = Path.Combine(Cfg.paths.report_dir, "K01_GATE04C_TYPED_BUILD.json");
            File.WriteAllText(LogPath, "K01 Gate04C strongly typed CAD build\r\n");
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
            Log("Connected by strongly typed SolidWorks.Interop. Revision=" + R.solidworks_revision);
            if (!R.solidworks_revision.StartsWith("26."))
                R.warnings.Add("Expected SOLIDWORKS 2018 revision 26.x; detected " + R.solidworks_revision);
        }

        static void BuildP003()
        {
            RequireFile(Cfg.paths.stable_p003);
            ArchiveThenCopy(Cfg.paths.stable_p003, P003Candidate);

            ModelDoc2 doc = OpenPart(P003Candidate);
            string title = doc.GetTitle();
            try
            {
                double[] bb0 = BodyBoxMm(doc);
                RequireCylinder(doc, Cfg.P003.current_rear_collar_OD_mm, 0.08, "P003 stable rear collar OD16");
                RequireCylinder(doc, Cfg.P003.service_bore_minor_D_mm, 0.08, "P003 service/minor bore D10.917");

                PlaneHit rear = ExtremeAxialPlane(doc, true);
                double datumX = rear.X;
                Log("P003 rear datum X=" + M(datumX) + " mm; normalX=" + rear.NormalX.ToString("0.###", CultureInfo.InvariantCulture));

                Feature flange = CreateAnnularBoss(
                    doc, rear,
                    Cfg.P003.J2_flange_OD_mm,
                    Cfg.P003.service_bore_minor_D_mm,
                    Cfg.P003.J2_flange_depth_inward_mm,
                    -1.0,
                    "K01_F_J2_FLANGE_OD36");
                MarkForDrawing(flange);
                doc.ForceRebuild3(false);
                ValidateXEnvelopeSame(bb0, BodyBoxMm(doc), 0.05, "P003 flange must grow inward only");

                PlaneHit face = AxialPlaneAtX(doc, datumX, 0.03);
                Feature gland = CreateAnnularCut(
                    doc, face,
                    Cfg.P003.gland_OD_nominal_mm,
                    Cfg.P003.gland_ID_mm,
                    Cfg.P003.gland_depth_mm,
                    -1.0,
                    "K01_F_J2_ORING_GLAND_16x1p5");
                MarkForDrawing(gland);

                face = AxialPlaneAtX(doc, datumX, 0.03);
                Feature seed = CreateCircularCutSeed(
                    doc, face,
                    Cfg.P003.tap_drill_D_mm,
                    Cfg.P003.tap_depth_mm,
                    -1.0,
                    Cfg.J2.pattern_PCD_mm / 2.0,
                    Cfg.J2.seed_angle_deg_local,
                    "K01_F_J2_M3_TAP_SEED");
                MarkForDrawing(seed);

                Feature pattern = CreateCircularPattern(doc, seed, "K01_F_J2_M3_PATTERN_3X120");
                MarkForDrawing(pattern);

                face = AxialPlaneAtX(doc, datumX, 0.03);
                Feature pilot = CreateAnnularBoss(
                    doc, face,
                    Cfg.P003.pilot_OD_nominal_mm,
                    Cfg.P003.service_bore_minor_D_mm,
                    Cfg.P003.pilot_L_outward_mm,
                    +1.0,
                    "K01_F_J2_PILOT_D14p10_g6_L1p50");
                MarkForDrawing(pilot);

                SetProperty(doc, "Project", "MARVILON K01");
                SetProperty(doc, "PartNo", "K01-P-003");
                SetProperty(doc, "MaterialSpec", Cfg.P003.material);
                SetProperty(doc, "K01_GATE", "Gate04C");
                SetProperty(doc, "K01_CandidateStatus", "CANDIDATE / NOT RELEASED");
                SetProperty(doc, "J2_Thread", Cfg.P003.thread);
                SetProperty(doc, "J2_ThreadImplementation", "Native D2.50 tap-drill geometry; M3x0.5-6H controlled by master/drawing");
                SetProperty(doc, "J2_Seal", Cfg.P003.oring_size);
                SetProperty(doc, "J2_SealMaterial", Cfg.P003.oring_material);
                SetProperty(doc, "J2_PilotFit", "D14.10 " + Cfg.P003.pilot_fit);

                doc.ForceRebuild3(false);
                ThrowOnFeatureErrors(doc, "P003");

                double[] bb1 = BodyBoxMm(doc);
                RequireNear(bb1[3] - bb0[3], Cfg.P003.pilot_L_outward_mm, 0.08, "P003 pilot Xmax extension");
                RequireNear(bb1[0] - bb0[0], 0.0, 0.05, "P003 Xmin unchanged");
                RequireCylinder(doc, Cfg.P003.J2_flange_OD_mm, 0.08, "P003 J2 flange OD36");
                RequireCylinder(doc, Cfg.P003.pilot_OD_nominal_mm, 0.08, "P003 J2 pilot D14.10");
                RequireCylinderCount(doc, Cfg.P003.tap_drill_D_mm, 0.10, 3, "P003 3x M3 tap-drill geometry");

                SaveCurrent(doc, "P003 candidate");
                R.checks.Add("PASS P003: OD36 flange + seal gland + 3x M3 seed/pattern + D14.10x1.50 pilot.");
                Log("P003 PASS");
            }
            finally
            {
                try { sw.CloseDoc(title); } catch { }
            }
        }

        static void BuildP007()
        {
            RequireFile(Cfg.paths.stable_p007);
            ArchiveThenCopy(Cfg.paths.stable_p007, P007Candidate);

            ModelDoc2 doc = OpenPart(P007Candidate);
            string title = doc.GetTitle();
            try
            {
                double[] bb0 = BodyBoxMm(doc);
                RequireNear(bb0[3] - bb0[0], Cfg.P007.overall_L_mm, 0.10, "P007 stable OAL");
                RequireCylinder(doc, Cfg.P007.locator_ID_nominal_mm, 0.08, "P007 stable locator D14.10");
                RequireCylinder(doc, Cfg.P007.thin_OD_mm, 0.08, "P007 stable thin OD10");
                RequireCylinder(doc, Cfg.P007.thin_ID_mm, 0.08, "P007 stable thin ID9.4");

                PlaneHit front = ExtremeAxialPlane(doc, false);
                double datumX = front.X;
                Log("P007 front datum X=" + M(datumX) + " mm; normalX=" + front.NormalX.ToString("0.###", CultureInfo.InvariantCulture));

                Feature flange = CreateAnnularBoss(
                    doc, front,
                    Cfg.P007.J2_flange_OD_mm,
                    Cfg.P007.locator_ID_nominal_mm,
                    Cfg.P007.J2_flange_depth_inward_mm,
                    +1.0,
                    "K01_F_J2_FLANGE_OD36_T3");
                MarkForDrawing(flange);
                doc.ForceRebuild3(false);
                ValidateXEnvelopeSame(bb0, BodyBoxMm(doc), 0.05, "P007 flange must stay inside L35");

                PlaneHit face = AxialPlaneAtX(doc, datumX, 0.03);
                Feature seed = CreateCircularCutSeed(
                    doc, face,
                    Cfg.P007.clearance_hole_D_mm,
                    Cfg.P007.J2_flange_depth_inward_mm + 0.20,
                    +1.0,
                    Cfg.J2.pattern_PCD_mm / 2.0,
                    Cfg.J2.seed_angle_deg_local,
                    "K01_F_J2_M3_CLEARANCE_SEED");
                MarkForDrawing(seed);

                Feature pattern = CreateCircularPattern(doc, seed, "K01_F_J2_M3_PATTERN_3X120");
                MarkForDrawing(pattern);

                SetProperty(doc, "Project", "MARVILON K01");
                SetProperty(doc, "PartNo", "K01-P-007");
                SetProperty(doc, "MaterialSpec", Cfg.P007.material);
                SetProperty(doc, "K01_GATE", "Gate04C");
                SetProperty(doc, "K01_CandidateStatus", "CANDIDATE / NOT RELEASED");
                SetProperty(doc, "J2_LocatorFit", "D14.10 " + Cfg.P007.locator_fit);

                doc.ForceRebuild3(false);
                ThrowOnFeatureErrors(doc, "P007");

                double[] bb1 = BodyBoxMm(doc);
                RequireNear(bb1[3] - bb1[0], Cfg.P007.overall_L_mm, 0.10, "P007 candidate OAL retained");
                RequireCylinder(doc, Cfg.P007.J2_flange_OD_mm, 0.08, "P007 J2 flange OD36");
                RequireCylinder(doc, Cfg.P007.locator_ID_nominal_mm, 0.08, "P007 D14.10 locator retained");
                RequireCylinder(doc, Cfg.P007.thin_OD_mm, 0.08, "P007 thin OD10 retained");
                RequireCylinder(doc, Cfg.P007.thin_ID_mm, 0.08, "P007 thin ID9.4 retained");
                RequireCylinderCount(doc, Cfg.P007.clearance_hole_D_mm, 0.10, 3, "P007 3x D3.40 clearance geometry");

                SaveCurrent(doc, "P007 candidate");
                R.checks.Add("PASS P007: OD36x3 flange + 3x D3.40 seed/pattern; L35 and thin can retained.");
                Log("P007 PASS");
            }
            finally
            {
                try { sw.CloseDoc(title); } catch { }
            }
        }

        // ---------------- geometry ----------------

        static Feature CreateAnnularBoss(ModelDoc2 doc, PlaneHit plane, double outerDmm, double innerDmm,
                                         double depthMm, double desiredXSign, string name)
        {
            BeginFaceSketch(doc, plane.Face);
            Sketch sk = doc.GetActiveSketch2() as Sketch;
            if (sk == null) throw new Exception(name + ": active sketch is null.");
            double[] c = ModelPointToSketch(sk, plane.X, 0.0, 0.0);

            SketchManager sm = doc.SketchManager;
            if (sm.CreateCircleByRadius(c[0], c[1], 0.0, outerDmm * 0.5 * MM) == null)
                throw new Exception(name + ": outer circle failed.");
            if (sm.CreateCircleByRadius(c[0], c[1], 0.0, innerDmm * 0.5 * MM) == null)
                throw new Exception(name + ": inner circle failed.");
            sm.InsertSketch(true);

            bool reverse = plane.NormalX * desiredXSign < 0.0;
            Feature f = doc.FeatureManager.FeatureExtrusion2(
                true, false, reverse,
                0, 0,
                depthMm * MM, 0.01,
                false, false, false, false,
                0.0, 0.0,
                false, false, false, false,
                true, true, true,
                0, 0.0, false);
            if (f == null) throw new Exception(name + ": FeatureExtrusion2 returned null.");
            f.Name = name;
            doc.ClearSelection2(true);
            return f;
        }

        static Feature CreateAnnularCut(ModelDoc2 doc, PlaneHit plane, double outerDmm, double innerDmm,
                                        double depthMm, double desiredXSign, string name)
        {
            BeginFaceSketch(doc, plane.Face);
            Sketch sk = doc.GetActiveSketch2() as Sketch;
            if (sk == null) throw new Exception(name + ": active sketch is null.");
            double[] c = ModelPointToSketch(sk, plane.X, 0.0, 0.0);

            SketchManager sm = doc.SketchManager;
            if (sm.CreateCircleByRadius(c[0], c[1], 0.0, outerDmm * 0.5 * MM) == null)
                throw new Exception(name + ": outer circle failed.");
            if (sm.CreateCircleByRadius(c[0], c[1], 0.0, innerDmm * 0.5 * MM) == null)
                throw new Exception(name + ": inner circle failed.");
            sm.InsertSketch(true);

            bool reverse = plane.NormalX * desiredXSign > 0.0;
            Log(name + ": cut normalX=" + plane.NormalX.ToString("0.###", CultureInfo.InvariantCulture) +
                " desiredXSign=" + desiredXSign.ToString("0", CultureInfo.InvariantCulture) +
                " Dir(reverseDefault)=" + reverse);
            Feature f = doc.FeatureManager.FeatureCut4(
                true, false, reverse,
                0, 0,
                depthMm * MM, 0.01,
                false, false, false, false,
                0.0, 0.0,
                false, false,
                false, false,
                false,
                true, true,
                false, false, false,
                0, 0.0, false,
                false);
            if (f == null) throw new Exception(name + ": FeatureCut4 returned null.");
            f.Name = name;
            doc.ClearSelection2(true);
            return f;
        }

        static Feature CreateCircularCutSeed(ModelDoc2 doc, PlaneHit plane, double holeDmm, double depthMm,
                                             double desiredXSign, double radiusMm, double angleDeg, string name)
        {
            BeginFaceSketch(doc, plane.Face);
            Sketch sk = doc.GetActiveSketch2() as Sketch;
            if (sk == null) throw new Exception(name + ": active sketch is null.");

            double a = angleDeg * PI / 180.0;
            double y = radiusMm * MM * Math.Cos(a);
            double z = radiusMm * MM * Math.Sin(a);
            double[] p = ModelPointToSketch(sk, plane.X, y, z);

            SketchManager sm = doc.SketchManager;
            if (sm.CreateCircleByRadius(p[0], p[1], 0.0, holeDmm * 0.5 * MM) == null)
                throw new Exception(name + ": seed circle failed.");
            sm.InsertSketch(true);

            bool reverse = plane.NormalX * desiredXSign > 0.0;
            Log(name + ": cut normalX=" + plane.NormalX.ToString("0.###", CultureInfo.InvariantCulture) +
                " desiredXSign=" + desiredXSign.ToString("0", CultureInfo.InvariantCulture) +
                " Dir(reverseDefault)=" + reverse);
            Feature f = doc.FeatureManager.FeatureCut4(
                true, false, reverse,
                0, 0,
                depthMm * MM, 0.01,
                false, false, false, false,
                0.0, 0.0,
                false, false,
                false, false,
                false,
                true, true,
                false, false, false,
                0, 0.0, false,
                false);
            if (f == null) throw new Exception(name + ": FeatureCut4 returned null.");
            f.Name = name;
            doc.ClearSelection2(true);
            return f;
        }

        static Feature CreateCircularPattern(ModelDoc2 doc, Feature seed, string name)
        {
            Face2 direction = FindAnyAxialCylinder(doc);
            if (direction == null) throw new Exception(name + ": no axial cylindrical face for pattern direction.");

            doc.ClearSelection2(true);
            SelectionMgr mgr = doc.SelectionManager as SelectionMgr;
            SelectData sd = mgr.CreateSelectData() as SelectData;
            sd.Mark = 1;
            Entity directionEntity = direction as Entity;
            if (directionEntity == null || !directionEntity.Select4(false, sd))
                throw new Exception(name + ": direction selection failed through IEntity.Select4.");
            if (!seed.Select2(true, 4)) throw new Exception(name + ": seed selection failed.");

            Feature p = doc.FeatureManager.FeatureCircularPattern5(
                Cfg.J2.pattern_qty,
                2.0 * PI,
                false,
                "",
                true,
                true,
                false,
                false,
                false,
                false,
                0,
                0.0,
                "",
                false);
            if (p == null) throw new Exception(name + ": FeatureCircularPattern5 returned null.");
            p.Name = name;
            doc.ClearSelection2(true);
            return p;
        }

        static void BeginFaceSketch(ModelDoc2 doc, Face2 face)
        {
            doc.ClearSelection2(true);
            Entity faceEntity = face as Entity;
            if (faceEntity == null || !faceEntity.Select4(false, null))
                throw new Exception("Planar face selection failed through IEntity.Select4.");
            doc.SketchManager.InsertSketch(true);
        }

        static double[] ModelPointToSketch(Sketch sk, double x, double y, double z)
        {
            MathUtility mu = sw.GetMathUtility() as MathUtility;
            MathPoint mp = mu.CreatePoint(new double[] { x, y, z }) as MathPoint;
            if (mp == null) throw new Exception("MathUtility.CreatePoint failed.");
            MathTransform tr = sk.ModelToSketchTransform;
            MathPoint sp = mp.MultiplyTransform(tr) as MathPoint;
            if (sp == null) throw new Exception("ModelToSketch transform failed.");
            return ToDoubleArray(sp.ArrayData);
        }

        // ---------------- BREP / QA ----------------

        static object[] SolidBodies(ModelDoc2 doc)
        {
            PartDoc p = doc as PartDoc;
            if (p == null) throw new Exception("Document did not cast to PartDoc: " + doc.GetTitle());
            return ToObjects(p.GetBodies2((int)swBodyType_e.swSolidBody, false));
        }

        static IEnumerable<Face2> AllFaces(ModelDoc2 doc)
        {
            foreach (object bo in SolidBodies(doc))
            {
                Body2 b = bo as Body2;
                if (b == null) continue;
                foreach (object fo in ToObjects(b.GetFaces()))
                {
                    Face2 f = fo as Face2;
                    if (f != null) yield return f;
                }
            }
        }

        static double[] BodyBoxMm(ModelDoc2 doc)
        {
            object[] b = SolidBodies(doc);
            if (b.Length != 1) throw new Exception("Expected 1 solid body; got " + b.Length + " in " + doc.GetTitle());
            Body2 body = b[0] as Body2;
            double[] bb = ToDoubleArray(body.GetBodyBox());
            if (bb.Length < 6) throw new Exception("Body box unavailable.");
            for (int i=0; i<6; i++) bb[i] *= 1000.0;
            return bb;
        }

        static PlaneHit ExtremeAxialPlane(ModelDoc2 doc, bool wantMax)
        {
            PlaneHit best = null;
            foreach (Face2 f in AllFaces(doc))
            {
                Surface s = f.GetSurface() as Surface;
                if (s == null || !s.IsPlane()) continue;
                double[] p = ToDoubleArray(s.PlaneParams);
                if (p.Length < 6) continue;
                if (Math.Abs(Math.Abs(p[0]) - 1.0) > 1e-5 || Math.Abs(p[1]) > 1e-5 || Math.Abs(p[2]) > 1e-5)
                    continue;
                if (best == null || (wantMax ? p[3] > best.X : p[3] < best.X))
                    best = new PlaneHit { Face = f, X = p[3], NormalX = p[0], Area = f.GetArea() };
            }
            if (best == null) throw new Exception("No axial planar face found.");
            return best;
        }

        static PlaneHit AxialPlaneAtX(ModelDoc2 doc, double targetX, double tolMm)
        {
            PlaneHit best = null;
            double tol = tolMm * MM;
            foreach (Face2 f in AllFaces(doc))
            {
                Surface s = f.GetSurface() as Surface;
                if (s == null || !s.IsPlane()) continue;
                double[] p = ToDoubleArray(s.PlaneParams);
                if (p.Length < 6) continue;
                if (Math.Abs(Math.Abs(p[0]) - 1.0) > 1e-5) continue;
                if (Math.Abs(p[3] - targetX) <= tol)
                {
                    double area = f.GetArea();
                    if (best == null || area > best.Area)
                        best = new PlaneHit { Face = f, X = p[3], NormalX = p[0], Area = area };
                }
            }
            if (best == null) throw new Exception("No axial face at X=" + M(targetX) + " mm.");
            return best;
        }

        static Face2 FindAnyAxialCylinder(ModelDoc2 doc)
        {
            Face2 best = null;
            double bestArea = -1.0;
            foreach (Face2 f in AllFaces(doc))
            {
                Surface s = f.GetSurface() as Surface;
                if (s == null || !s.IsCylinder()) continue;
                double[] p = ToDoubleArray(s.CylinderParams);
                if (p.Length < 7) continue;
                if (Math.Abs(Math.Abs(p[3]) - 1.0) > 1e-5 || Math.Abs(p[4]) > 1e-5 || Math.Abs(p[5]) > 1e-5)
                    continue;
                double area = f.GetArea();
                if (area > bestArea) { bestArea = area; best = f; }
            }
            return best;
        }

        static int CylinderCount(ModelDoc2 doc, double dmm, double tolMm)
        {
            int n = 0;
            foreach (Face2 f in AllFaces(doc))
            {
                Surface s = f.GetSurface() as Surface;
                if (s == null || !s.IsCylinder()) continue;
                double[] p = ToDoubleArray(s.CylinderParams);
                if (p.Length < 7) continue;
                double got = 2.0 * Math.Abs(p[6]) / MM;
                if (Math.Abs(got - dmm) <= tolMm) n++;
            }
            return n;
        }

        static void RequireCylinder(ModelDoc2 doc, double dmm, double tolMm, string label)
        {
            int n = CylinderCount(doc, dmm, tolMm);
            if (n < 1) throw new Exception(label + " not found. Target D=" + dmm + " mm.");
            Log(label + " PASS count=" + n);
        }

        static void RequireCylinderCount(ModelDoc2 doc, double dmm, double tolMm, int minCount, string label)
        {
            int n = CylinderCount(doc, dmm, tolMm);
            if (n < minCount) throw new Exception(label + " expected >= " + minCount + ", got " + n);
            Log(label + " PASS count=" + n);
        }

        static List<string> FeatureErrors(ModelDoc2 doc)
        {
            List<string> r = new List<string>();
            Feature f = doc.FirstFeature() as Feature;
            int guard = 0;
            while (f != null && guard++ < 3000)
            {
                bool warning;
                int code = f.GetErrorCode2(out warning);
                if (code != 0 && !warning) r.Add(f.Name + " [" + f.GetTypeName2() + "] code=" + code);
                f = f.GetNextFeature() as Feature;
            }
            return r;
        }

        static void ThrowOnFeatureErrors(ModelDoc2 doc, string label)
        {
            List<string> e = FeatureErrors(doc);
            if (e.Count > 0) throw new Exception(label + " feature errors: " + String.Join("; ", e.ToArray()));
        }

        static void ValidateXEnvelopeSame(double[] before, double[] after, double tolMm, string label)
        {
            RequireNear(after[0] - before[0], 0.0, tolMm, label + " Xmin delta");
            RequireNear(after[3] - before[3], 0.0, tolMm, label + " Xmax delta");
        }

        static void RequireNear(double actual, double expected, double tol, string label)
        {
            if (Math.Abs(actual - expected) > tol)
                throw new Exception(label + ": expected=" + expected.ToString("0.######", CultureInfo.InvariantCulture) +
                    " actual=" + actual.ToString("0.######", CultureInfo.InvariantCulture) +
                    " tol=" + tol.ToString("0.######", CultureInfo.InvariantCulture));
            Log(label + " PASS actual=" + actual.ToString("0.######", CultureInfo.InvariantCulture));
        }

        // ---------------- file/properties ----------------

        static ModelDoc2 OpenPart(string path)
        {
            int e = 0, w = 0;
            ModelDoc2 d = sw.OpenDoc6(
                path,
                (int)swDocumentTypes_e.swDocPART,
                (int)swOpenDocOptions_e.swOpenDocOptions_Silent,
                "",
                ref e,
                ref w) as ModelDoc2;
            if (d == null) throw new Exception("OpenDoc6 failed errors=" + e + " path=" + path);
            if (d.GetType() != (int)swDocumentTypes_e.swDocPART) throw new Exception("Not a part: " + path);
            return d;
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
                Log("Archived previous candidate: " + hist);
            }
            File.Copy(src, dst, true);
            Log("Copied stable -> candidate: " + dst);
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
            if (r == 0)
            {
                try { cpm.Set2(key, value ?? ""); } catch { }
            }
        }

        static void MarkForDrawing(Feature f)
        {
            if (f == null) return;
            try
            {
                object o = f.GetFirstDisplayDimension();
                int guard = 0;
                while (o != null && guard++ < 200)
                {
                    DisplayDimension dd = o as DisplayDimension;
                    if (dd != null) dd.MarkedForDrawing = true;
                    o = f.GetNextDisplayDimension(o);
                }
            }
            catch { }
        }

        static void RequireFile(string p)
        {
            if (!File.Exists(p)) throw new Exception("Required file missing: " + p);
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

        static string M(double meters)
        {
            return (meters / MM).ToString("0.######", CultureInfo.InvariantCulture);
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
