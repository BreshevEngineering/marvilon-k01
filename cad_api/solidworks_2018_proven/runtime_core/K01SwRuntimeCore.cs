using System;
using System.IO;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Threading;
using SolidWorks.Interop.sldworks;
using SolidWorks.Interop.swconst;

namespace K01Sw2018Runtime
{
    public sealed class SwSession : IDisposable
    {
        public SldWorks App { get; private set; }
        public bool OwnsInstance { get; private set; }
        public string Revision { get; private set; }

        private SwSession() {}

        public static SwSession ConnectOrStart(bool visible)
        {
            SwSession s = new SwSession();
            try
            {
                object active = Marshal.GetActiveObject("SldWorks.Application");
                s.App = active as SldWorks;
                s.OwnsInstance = false;
            }
            catch
            {
                s.App = Activator.CreateInstance(Type.GetTypeFromProgID("SldWorks.Application", true)) as SldWorks;
                s.OwnsInstance = true;
            }

            if (s.App == null) throw new Exception("Cannot connect to or start SOLIDWORKS.");
            s.App.Visible = visible;
            s.Revision = s.App.RevisionNumber();
            if (String.IsNullOrWhiteSpace(s.Revision) || !s.Revision.StartsWith("26."))
                throw new Exception("Expected SOLIDWORKS 2018 / revision 26; got " + s.Revision);
            return s;
        }

        public ModelDoc2 GetOpenDocument(string fullPath)
        {
            if (String.IsNullOrWhiteSpace(fullPath)) return null;
            ModelDoc2 d = null;
            try { d = App.GetOpenDocumentByName(fullPath) as ModelDoc2; } catch {}
            if (d != null) return d;

            try
            {
                string file = Path.GetFileName(fullPath);
                d = App.GetOpenDocumentByName(file) as ModelDoc2;
            }
            catch {}
            return d;
        }

        public void RequireTargetClosed(string fullPath, string role)
        {
            ModelDoc2 d = GetOpenDocument(fullPath);
            if (d != null)
                throw new Exception("TARGET_DOCUMENT_OPEN: " + role + " :: " + fullPath +
                    ". Close only this target document; unrelated SOLIDWORKS documents may remain open.");
        }

        public void Dispose()
        {
            if (App == null) return;
            if (OwnsInstance)
            {
                try { App.ExitApp(); } catch {}
            }
            try { Marshal.FinalReleaseComObject(App); } catch {}
            App = null;
        }

        public static string Sha256File(string path)
        {
            using (SHA256 h = SHA256.Create())
            using (FileStream f = File.Open(path, FileMode.Open, FileAccess.Read,
                FileShare.ReadWrite | FileShare.Delete))
                return BitConverter.ToString(h.ComputeHash(f)).Replace("-", "").ToLowerInvariant();
        }

        public static string Sha256AfterClose(string path)
        {
            Exception last = null;
            for (int i=0; i<20; i++)
            {
                try { return Sha256File(path); }
                catch (IOException ex) { last = ex; Thread.Sleep(100); }
            }
            throw new IOException("File remained unavailable after CloseDoc: " + path, last);
        }
    }
}
