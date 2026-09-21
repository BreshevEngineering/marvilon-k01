using System;
using System.IO;
using System.Runtime.InteropServices;
using System.Threading;
using System.Web.Script.Serialization;
using SolidWorks.Interop.sldworks;
using SolidWorks.Interop.swconst;

namespace Marvilon.K01.MEDTAS
{
    public sealed class DocumentState
    {
        public string title="";
        public string path="";
        public string document_type="";
        public int document_type_code=0;
        public string configuration="";
        public bool dirty=false;
        public int feature_count=0;
        public int top_level_component_count=0;
        public string artifact_class="UNCLASSIFIED";
    }

    public sealed class LiveState
    {
        public string schema="k01_solidworks_live_state_v1";
        public string created_utc="";
        public string status="DISCONNECTED";
        public bool connected=false;
        public string solidworks_revision="";
        public string bridge_mode="";
        public DocumentState active_document=null;
        public string error="";
    }

    public static class Program
    {
        static string OutputPath=@"D:\BreshevEngineering\marvilon-k01\reports\cad\live\K01_SOLIDWORKS_LIVE_STATE.json";

        public static int Main(string[] args)
        {
            bool watch=false;
            int intervalMs=2000;
            for(int i=0;i<args.Length;i++)
            {
                if(String.Equals(args[i],"--watch",StringComparison.OrdinalIgnoreCase)) watch=true;
                else if(String.Equals(args[i],"--once",StringComparison.OrdinalIgnoreCase)) watch=false;
                else if(String.Equals(args[i],"--output",StringComparison.OrdinalIgnoreCase) && i+1<args.Length) OutputPath=args[++i];
                else if(String.Equals(args[i],"--interval-ms",StringComparison.OrdinalIgnoreCase) && i+1<args.Length)
                {
                    int v=0;if(Int32.TryParse(args[++i],out v) && v>=500) intervalMs=v;
                }
            }
            Directory.CreateDirectory(Path.GetDirectoryName(OutputPath));
            if(!watch){ WriteSnapshot("ONCE"); return 0; }
            Console.WriteLine("MEDTAS SOLIDWORKS LIVE BRIDGE v1");
            Console.WriteLine("Read-only polling bridge. Close this window to stop.");
            Console.WriteLine("Output: "+OutputPath);
            while(true){ WriteSnapshot("WATCH"); Thread.Sleep(intervalMs); }
        }

        static void WriteSnapshot(string mode)
        {
            LiveState s=new LiveState();
            s.created_utc=DateTime.UtcNow.ToString("o");
            s.bridge_mode=mode;
            try
            {
                object appObj=null;
                try{ appObj=Marshal.GetActiveObject("SldWorks.Application"); }catch{ appObj=null; }
                if(appObj==null){ s.status="SOLIDWORKS_NOT_RUNNING"; Save(s); return; }
                SldWorks sw=(SldWorks)appObj;
                s.connected=true; s.solidworks_revision=sw.RevisionNumber(); s.status="CONNECTED";
                object ad=sw.ActiveDoc;
                if(ad==null){ s.status="CONNECTED_NO_ACTIVE_DOCUMENT"; Save(s); return; }
                ModelDoc2 doc=ad as ModelDoc2;
                if(doc==null){ s.status="CONNECTED_ACTIVE_DOCUMENT_CAST_FAILED"; Save(s); return; }
                DocumentState d=new DocumentState();
                d.title=doc.GetTitle() ?? "";
                d.path=doc.GetPathName() ?? "";
                d.document_type_code=doc.GetType();
                d.document_type=DocTypeName(d.document_type_code);
                try
                {
                    ConfigurationManager cm=doc.ConfigurationManager;
                    if(cm!=null){ Configuration cfg=cm.ActiveConfiguration; if(cfg!=null)d.configuration=cfg.Name ?? ""; }
                }catch{}
                try{d.dirty=doc.GetSaveFlag();}catch{}
                try{d.feature_count=doc.GetFeatureCount();}catch{}
                if(d.document_type_code==(int)swDocumentTypes_e.swDocASSEMBLY)
                {
                    try
                    {
                        AssemblyDoc a=doc as AssemblyDoc;
                        if(a!=null){ object co=a.GetComponents(true); Array ar=co as Array; d.top_level_component_count=ar!=null?ar.Length:0; }
                    }catch{}
                }
                d.artifact_class=Classify(d.path,d.title);
                s.active_document=d;
                Save(s);
            }
            catch(Exception ex){ s.status="BRIDGE_ERROR"; s.error=ex.ToString(); try{Save(s);}catch{} }
        }

        static string DocTypeName(int t)
        {
            if(t==(int)swDocumentTypes_e.swDocPART)return "PART";
            if(t==(int)swDocumentTypes_e.swDocASSEMBLY)return "ASSEMBLY";
            if(t==(int)swDocumentTypes_e.swDocDRAWING)return "DRAWING";
            return "UNKNOWN";
        }

        static string Classify(string path,string title)
        {
            string x=((path??"")+" "+(title??"")).ToUpperInvariant();
            if(x.Contains("GATE04D_C2R1")||x.Contains("GATE04E"))return "CONTROLLED_CANDIDATE_OR_VERIFY";
            if(x.Contains("K01-A-001_CALIBRATION_MODULE"))return "PRODUCTION_ASSEMBLY";
            if(x.Contains("K01-P-"))return "K01_PART";
            if(x.Contains("K01-D-"))return "K01_DRAWING";
            return "OTHER";
        }

        static void Save(LiveState s)
        {
            string tmp=OutputPath+".tmp";
            File.WriteAllText(tmp,new JavaScriptSerializer().Serialize(s));
            if(File.Exists(OutputPath))File.Delete(OutputPath);
            File.Move(tmp,OutputPath);
        }
    }
}
