using System;
using System.IO;
using System.Runtime.InteropServices;
using System.Web.Script.Serialization;
using SolidWorks.Interop.sldworks;
using SolidWorks.Interop.swconst;

namespace Marvilon.K01.Gate04E
{
    public sealed class Report
    {
        public string schema = "k01_gate04e_p006_service_build_v3";
        public string created_utc = DateTime.UtcNow.ToString("o");
        public string status = "OPEN";
        public string solidworks_revision = "";
        public string stable = @"D:\Marvilon\K01\cad\parts\K01-P-006_Retaining_Plug.SLDPRT";
        public string candidate = @"D:\Marvilon\K01\cad\candidates\gate04e_p006_service\K01-P-006_Retaining_Plug_GATE04E_SERVICE_CANDIDATE.SLDPRT";
        public string feature_name = "K01_F_P006_SERVICE_2PIN_D1p50_PCD8p50";
        public double pin_hole_diameter_mm = 1.50;
        public double pin_hole_depth_mm = 1.20;
        public double pin_hole_pcd_mm = 8.50;
        public int pin_hole_count = 2;
        public double front_plane_x_mm = 0.0;
        public string verification = "";
        public string planeparams_contract = "Surface.PlaneParams = normal.x,normal.y,normal.z,rootPoint.x,rootPoint.y,rootPoint.z; root point values are meters.";
        public string face_selection_diagnostics = "";
        public string error = "";
    }

    public static class Program
    {
        const double MM = 0.001;
        static SldWorks sw;
        static readonly Report r = new Report();
        static readonly string reportPath =
            @"D:\BreshevEngineering\marvilon-k01\reports\cad\current\K01_GATE04E_P006_SERVICE_BUILD.json";

        public static int Main()
        {
            string openedTitle = "";
            try
            {
                Connect();
                Directory.CreateDirectory(Path.GetDirectoryName(r.candidate));
                Directory.CreateDirectory(Path.GetDirectoryName(reportPath));

                if (!File.Exists(r.stable))
                    throw new Exception("Stable P006 is missing: " + r.stable);

                ArchiveAndCopyStable();

                int openErrors = 0, openWarnings = 0;
                ModelDoc2 doc = sw.OpenDoc6(
                    r.candidate,
                    (int)swDocumentTypes_e.swDocPART,
                    (int)swOpenDocOptions_e.swOpenDocOptions_Silent,
                    "",
                    ref openErrors,
                    ref openWarnings) as ModelDoc2;

                if (doc == null)
                    throw new Exception("Open candidate failed. OpenDoc6 errors=" + openErrors);

                openedTitle = doc.GetTitle();

                try
                {
                    Face2 frontFace = FindPositiveXEndFace(doc);
                    if (frontFace == null)
                        throw new Exception("Could not identify the maximum-X planar service face of P006. Diagnostics: " + r.face_selection_diagnostics);

                    double frontX = PlaneX(frontFace);
                    r.front_plane_x_mm = frontX / MM;

                    doc.ClearSelection2(true);
                    Entity faceEntity = frontFace as Entity;
                    if (faceEntity == null || !faceEntity.Select4(false, null))
                        throw new Exception("Front face selection failed.");

                    doc.SketchManager.InsertSketch(true);
                    Sketch sketch = doc.GetActiveSketch2() as Sketch;
                    if (sketch == null)
                        throw new Exception("Active sketch is null after InsertSketch.");

                    MathUtility mathUtil = sw.GetMathUtility() as MathUtility;
                    if (mathUtil == null)
                        throw new Exception("MathUtility unavailable.");

                    MathPoint modelPoint = mathUtil.CreatePoint(new double[] { frontX, 0.0, 0.0 }) as MathPoint;
                    MathPoint sketchPoint = modelPoint.MultiplyTransform(sketch.ModelToSketchTransform) as MathPoint;
                    if (sketchPoint == null)
                        throw new Exception("Model-to-sketch point transform failed.");

                    double[] center = (double[])sketchPoint.ArrayData;
                    double pitchRadius = (r.pin_hole_pcd_mm * 0.5) * MM;
                    double holeRadius = (r.pin_hole_diameter_mm * 0.5) * MM;

                    // Two diametrically opposite face-drive holes. Their center line is along sketch Y.
                    doc.SketchManager.CreateCircleByRadius(center[0], center[1] + pitchRadius, 0.0, holeRadius);
                    doc.SketchManager.CreateCircleByRadius(center[0], center[1] - pitchRadius, 0.0, holeRadius);
                    doc.SketchManager.InsertSketch(true);

                    Feature cut = doc.FeatureManager.FeatureCut4(
                        true,   // Sd
                        false,  // Flip
                        false,  // Dir
                        0,      // T1 blind
                        0,      // T2
                        r.pin_hole_depth_mm * MM,
                        0.01,
                        false, false, false, false,
                        0, 0,
                        false, false, false, false,
                        false,
                        true, true,
                        false, false, false,
                        0,
                        0,
                        false,
                        false);

                    if (cut == null)
                        throw new Exception("FeatureCut4 returned null.");

                    cut.Name = r.feature_name;
                    MarkFeatureDimensionsForDrawing(cut);

                    doc.ForceRebuild3(false);

                    Feature built = FindFeatureByName(doc, r.feature_name);
                    if (built == null)
                        throw new Exception("Created service feature was not found after rebuild.");

                    int saveErrors = 0, saveWarnings = 0;
                    bool saveOk = doc.Save3(
                        (int)swSaveAsOptions_e.swSaveAsOptions_Silent,
                        ref saveErrors,
                        ref saveWarnings);

                    if (!saveOk || saveErrors != 0)
                        throw new Exception("Candidate Save3 failed. errors=" + saveErrors + " warnings=" + saveWarnings);

                    r.verification =
                        "PASS: candidate-only cut feature exists after rebuild; stable source was copied before modification; external P006 envelope is unchanged because the operation removes material only.";
                    r.status = "PASS_CANDIDATE_BUILD";
                }
                finally
                {
                    try { if (!String.IsNullOrWhiteSpace(openedTitle)) sw.CloseDoc(openedTitle); } catch { }
                }

                SaveReport();
                Console.WriteLine("STATUS=" + r.status);
                Console.WriteLine("Candidate: " + r.candidate);
                Console.WriteLine("Feature: " + r.feature_name);
                return 0;
            }
            catch (Exception ex)
            {
                r.status = "FAIL";
                r.error = ex.ToString();
                try { SaveReport(); } catch { }
                Console.Error.WriteLine(ex);
                return 1;
            }
        }

        static void Connect()
        {
            object appObject = null;
            try { appObject = Marshal.GetActiveObject("SldWorks.Application"); } catch { }

            sw = appObject != null
                ? (SldWorks)appObject
                : (SldWorks)Activator.CreateInstance(Type.GetTypeFromProgID("SldWorks.Application", true));

            sw.Visible = true;
            r.solidworks_revision = sw.RevisionNumber();
        }

        static void ArchiveAndCopyStable()
        {
            if (File.Exists(r.candidate))
            {
                string history = Path.Combine(Path.GetDirectoryName(r.candidate), "history");
                Directory.CreateDirectory(history);
                string archived = Path.Combine(
                    history,
                    "K01-P-006_Retaining_Plug_GATE04E_SERVICE_CANDIDATE_" +
                    DateTime.Now.ToString("yyyyMMdd_HHmmss") + ".SLDPRT");
                File.Copy(r.candidate, archived, true);
                File.Delete(r.candidate);
            }

            File.Copy(r.stable, r.candidate, true);
        }

        static Face2 FindPositiveXEndFace(ModelDoc2 doc)
        {
            PartDoc part = doc as PartDoc;
            if (part == null)
                throw new Exception("Active candidate is not a PartDoc.");

            object bodiesObject = part.GetBodies2((int)swBodyType_e.swSolidBody, true);
            object[] bodies = bodiesObject as object[];
            if (bodies == null || bodies.Length == 0)
                throw new Exception("No solid bodies found in P006 candidate.");

            Face2 best = null;
            double bestX = Double.NegativeInfinity;
            int planarCount = 0;
            int xNormalCount = 0;
            string diagnostics = "";

            foreach (object bodyObject in bodies)
            {
                Body2 body = bodyObject as Body2;
                if (body == null) continue;

                object facesObject = body.GetFaces();
                object[] faces = facesObject as object[];
                if (faces == null) continue;

                foreach (object faceObject in faces)
                {
                    Face2 face = faceObject as Face2;
                    if (face == null) continue;

                    Surface surface = face.GetSurface() as Surface;
                    if (surface == null || !surface.IsPlane()) continue;
                    planarCount++;

                    double[] plane = surface.PlaneParams as double[];
                    if (plane == null || plane.Length < 6) continue;

                    double[] faceNormal = face.Normal as double[];
                    double nx = 0.0;
                    if (faceNormal != null && faceNormal.Length >= 3)
                        nx = faceNormal[0];
                    else
                        nx = plane[0];

                    double x = plane[3];
                    double area = 0.0;
                    try { area = face.GetArea(); } catch { }

                    diagnostics += String.Format(
                        System.Globalization.CultureInfo.InvariantCulture,
                        "[x={0:F6}mm faceNx={1:F6} area={2:F6}mm2] ",
                        x / MM,
                        nx,
                        area / (MM * MM));

                    // The controlled P006 model axis is X. The sign of the underlying
                    // planar-surface normal is not an end-face discriminator:
                    // IFace2.Normal is the actual planar face normal, and either end
                    // can legally carry +X or -X sense depending on topology.
                    if (Math.Abs(nx) > 0.90)
                    {
                        xNormalCount++;
                        if (x > bestX)
                        {
                            bestX = x;
                            best = face;
                        }
                    }
                }
            }

            r.face_selection_diagnostics =
                "planar=" + planarCount +
                "; xAligned=" + xNormalCount +
                "; selectedMaxXmm=" +
                (best == null ? "NONE" : (bestX / MM).ToString("F6", System.Globalization.CultureInfo.InvariantCulture)) +
                "; candidates=" + diagnostics;

            return best;
        }

        static double PlaneX(Face2 face)
        {
            Surface surface = face.GetSurface() as Surface;
            if (surface == null || !surface.IsPlane())
                throw new Exception("Selected P006 service face is not planar.");

            double[] plane = surface.PlaneParams as double[];
            if (plane == null || plane.Length < 6)
                throw new Exception("PlaneParams unavailable for selected P006 face.");

            return plane[3];
        }

        static Feature FindFeatureByName(ModelDoc2 doc, string name)
        {
            Feature f = doc.FirstFeature() as Feature;
            int guard = 0;
            while (f != null && guard++ < 10000)
            {
                if (String.Equals(f.Name, name, StringComparison.Ordinal))
                    return f;
                f = f.GetNextFeature() as Feature;
            }
            return null;
        }

        static void MarkFeatureDimensionsForDrawing(Feature feature)
        {
            try
            {
                object display = feature.GetFirstDisplayDimension();
                int guard = 0;
                while (display != null && guard++ < 50)
                {
                    DisplayDimension dd = display as DisplayDimension;
                    if (dd != null) dd.MarkedForDrawing = true;
                    display = feature.GetNextDisplayDimension(display);
                }
            }
            catch { }
        }

        static void SaveReport()
        {
            File.WriteAllText(reportPath, new JavaScriptSerializer().Serialize(r));
        }
    }
}
