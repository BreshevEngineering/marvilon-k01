using System;
using System.IO;
using System.Runtime.InteropServices;
using System.Web.Script.Serialization;
using SolidWorks.Interop.sldworks;
using SolidWorks.Interop.swconst;

namespace Marvilon.K01.Gate04E
{
    public sealed class VerifyReport
    {
        public string schema = "k01_gate04e_p006_service_verify_v1";
        public string created_utc = DateTime.UtcNow.ToString("o");
        public string status = "OPEN";
        public string solidworks_revision = "";
        public string source_assembly =
            @"D:\Marvilon\K01\cad\candidates\gate04d_c2r1\verification\K01-A-001_GATE04D_C2R1_VERIFY.SLDASM";
        public string verify_assembly =
            @"D:\Marvilon\K01\cad\candidates\gate04e_p006_service\verification\K01-A-001_GATE04E_P006_SERVICE_VERIFY.SLDASM";
        public string p006_candidate =
            @"D:\Marvilon\K01\cad\candidates\gate04e_p006_service\K01-P-006_Retaining_Plug_GATE04E_SERVICE_CANDIDATE.SLDPRT";
        public string replaced_component_before = "";
        public string replaced_component_after = "";
        public int top_level_component_count = 0;
        public string note = "";
        public string error = "";
    }

    public static class Program
    {
        static SldWorks sw;
        static readonly VerifyReport r = new VerifyReport();
        static readonly string reportPath =
            @"D:\BreshevEngineering\marvilon-k01\reports\cad\current\K01_GATE04E_P006_SERVICE_VERIFY.json";

        public static int Main()
        {
            string title = "";
            try
            {
                Connect();

                if (!File.Exists(r.source_assembly))
                    throw new Exception("C2R1 verification assembly is missing: " + r.source_assembly);
                if (!File.Exists(r.p006_candidate))
                    throw new Exception("P006 service candidate is missing: " + r.p006_candidate);

                Directory.CreateDirectory(Path.GetDirectoryName(r.verify_assembly));
                Directory.CreateDirectory(Path.GetDirectoryName(reportPath));

                if (File.Exists(r.verify_assembly))
                {
                    string history = Path.Combine(Path.GetDirectoryName(r.verify_assembly), "history");
                    Directory.CreateDirectory(history);
                    File.Copy(
                        r.verify_assembly,
                        Path.Combine(history, "K01-A-001_GATE04E_P006_SERVICE_VERIFY_" +
                            DateTime.Now.ToString("yyyyMMdd_HHmmss") + ".SLDASM"),
                        true);
                    File.Delete(r.verify_assembly);
                }

                File.Copy(r.source_assembly, r.verify_assembly, true);

                int openErrors = 0, openWarnings = 0;
                ModelDoc2 doc = sw.OpenDoc6(
                    r.verify_assembly,
                    (int)swDocumentTypes_e.swDocASSEMBLY,
                    (int)swOpenDocOptions_e.swOpenDocOptions_Silent,
                    "",
                    ref openErrors,
                    ref openWarnings) as ModelDoc2;

                if (doc == null)
                    throw new Exception("Open verification assembly failed. errors=" + openErrors);

                title = doc.GetTitle();
                AssemblyDoc assy = doc as AssemblyDoc;
                if (assy == null)
                    throw new Exception("Verification document is not an AssemblyDoc.");

                Component2 p006 = FindP006(assy);
                if (p006 == null)
                    throw new Exception("Top-level P006 component was not found in the C2R1 verification assembly.");

                r.replaced_component_before = p006.GetPathName() ?? "";

                doc.ClearSelection2(true);
                if (!p006.Select4(false, null, false))
                    throw new Exception("P006 component selection failed.");

                bool replaced = assy.ReplaceComponents2(
                    r.p006_candidate,
                    "",
                    false,
                    (int)swReplaceComponentsConfiguration_e.swReplaceComponentsConfiguration_MatchName,
                    true);

                if (!replaced)
                    throw new Exception("ReplaceComponents2 returned false.");

                doc.ForceRebuild3(false);

                Component2 newP006 = FindP006(assy);
                if (newP006 == null)
                    throw new Exception("P006 component was not found after replacement.");

                r.replaced_component_after = newP006.GetPathName() ?? "";
                if (!String.Equals(
                    Path.GetFullPath(r.replaced_component_after),
                    Path.GetFullPath(r.p006_candidate),
                    StringComparison.OrdinalIgnoreCase))
                {
                    throw new Exception("Assembly does not reference the expected P006 candidate after replacement.");
                }

                object componentsObject = assy.GetComponents(true);
                object[] components = componentsObject as object[];
                r.top_level_component_count = components == null ? 0 : components.Length;

                int saveErrors = 0, saveWarnings = 0;
                bool saveOk = doc.Save3(
                    (int)swSaveAsOptions_e.swSaveAsOptions_Silent,
                    ref saveErrors,
                    ref saveWarnings);

                if (!saveOk || saveErrors != 0)
                    throw new Exception("Save3 failed. errors=" + saveErrors + " warnings=" + saveWarnings);

                r.status = "PASS_P006_LINKED_IN_FULL_C2R1_ASSEMBLY";
                r.note =
                    "The Gate04E assembly is a copy of the already-passed full C2R1 verification assembly with only P006 replaced by the service candidate. The P006 operation removes material and does not enlarge the external envelope. Existing C2R1 mate/interference evidence remains the geometric baseline; final service-process and release gates remain open.";

                SaveReport();
                Console.WriteLine("STATUS=" + r.status);
                Console.WriteLine("Verify assembly: " + r.verify_assembly);
                Console.WriteLine("P006 before: " + r.replaced_component_before);
                Console.WriteLine("P006 after : " + r.replaced_component_after);
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
            finally
            {
                try { if (!String.IsNullOrWhiteSpace(title)) sw.CloseDoc(title); } catch { }
            }
        }

        static Component2 FindP006(AssemblyDoc assy)
        {
            object componentObject = assy.GetComponents(true);
            object[] components = componentObject as object[];
            if (components == null) return null;

            foreach (object o in components)
            {
                Component2 c = o as Component2;
                if (c == null) continue;
                string path = c.GetPathName() ?? "";
                string name = c.Name2 ?? "";
                string text = (path + " " + name).ToUpperInvariant();

                if (text.Contains("K01-P-006_RETAINING_PLUG"))
                    return c;
            }
            return null;
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

        static void SaveReport()
        {
            File.WriteAllText(reportPath, new JavaScriptSerializer().Serialize(r));
        }
    }
}
