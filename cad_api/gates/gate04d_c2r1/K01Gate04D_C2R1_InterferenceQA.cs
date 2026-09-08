using System;
using System.Collections.Generic;
using System.IO;
using System.Runtime.InteropServices;
using System.Web.Script.Serialization;
using SolidWorks.Interop.sldworks;
using SolidWorks.Interop.swconst;

namespace Marvilon.K01.Gate04D_C2R1.InterferenceQA
{
    public sealed class IntRow { public int index=0; public List<string> components=new List<string>(); public List<string> paths=new List<string>(); public double volume_mm3=0; public string classification=""; }
    public sealed class Report
    {
        public string schema="k01_gate04d_c2r1_interference_v1";
        public string created_utc=DateTime.UtcNow.ToString("o");
        public string status="RUNNING";
        public string solidworks_revision="";
        public string assembly="";
        public int total_count=0;
        public int known_legacy_count=0;
        public int new_or_unclassified_count=0;
        public List<IntRow> interferences=new List<IntRow>();
        public List<string> checks=new List<string>();
        public string error="";
    }
    public static class Program
    {
        const string ASM=@"D:\Marvilon\K01\cad\candidates\gate04d_c2r1\verification\K01-A-001_GATE04D_C2R1_VERIFY.SLDASM";
        const string RDIR=@"D:\BreshevEngineering\marvilon-k01\reports\cad\current";
        static SldWorks sw; static Report R=new Report(); static string logPath,jsonPath;
        public static int Main()
        {
            try{
                Directory.CreateDirectory(RDIR); string stamp=DateTime.Now.ToString("yyyyMMdd_HHmmss");
                logPath=Path.Combine(RDIR,"K01_GATE04D_C2R1_INTERFERENCE_"+stamp+".log");
                jsonPath=Path.Combine(RDIR,"K01_GATE04D_C2R1_INTERFERENCE.json");
                File.WriteAllText(logPath,"K01 Gate04D-C2R1 interference QA\r\n");
                Connect(); Run(); R.status=R.new_or_unclassified_count==0?"PASS":"HOLD"; Save(); Log("STATUS="+R.status); return R.status=="PASS"?0:2;
            }catch(Exception ex){R.status="FAIL";R.error=ex.ToString();try{Save();}catch{}try{Log("STATUS=FAIL\r\n"+ex);}catch{}return 1;}
        }
        static void Connect()
        {
            object a=null;try{a=Marshal.GetActiveObject("SldWorks.Application");}catch{}
            sw=a!=null?(SldWorks)a:(SldWorks)Activator.CreateInstance(Type.GetTypeFromProgID("SldWorks.Application",true));
            sw.Visible=true;R.solidworks_revision=sw.RevisionNumber();Log("Connected "+R.solidworks_revision);
        }
        static void Run()
        {
            if(!File.Exists(ASM))throw new Exception("Verification assembly missing: "+ASM);
            int e=0,w=0;ModelDoc2 doc=sw.OpenDoc6(ASM,(int)swDocumentTypes_e.swDocASSEMBLY,
                (int)swOpenDocOptions_e.swOpenDocOptions_Silent|(int)swOpenDocOptions_e.swOpenDocOptions_ReadOnly,"",ref e,ref w) as ModelDoc2;
            if(doc==null)throw new Exception("OpenDoc6 failed e="+e+" w="+w);
            R.assembly=ASM;string title=doc.GetTitle();
            try{
                AssemblyDoc asm=doc as AssemblyDoc;InterferenceDetectionMgr mgr=asm.InterferenceDetectionManager;
                mgr.TreatCoincidenceAsInterference=false;mgr.TreatSubAssembliesAsComponents=false;mgr.IncludeMultibodyPartInterferences=true;
                mgr.MakeInterferingPartsTransparent=false;mgr.CreateFastenersFolder=false;mgr.IgnoreHiddenBodies=false;mgr.ShowIgnoredInterferences=false;mgr.UseTransform=false;
                object raw=mgr.GetInterferences();object[] ints=raw as object[];R.total_count=mgr.GetInterferenceCount();Log("Interference count="+R.total_count);
                if(ints!=null)for(int i=0;i<ints.Length;i++){
                    IInterference it=ints[i] as IInterference;if(it==null)continue;IntRow row=new IntRow();row.index=i+1;row.volume_mm3=it.Volume*1e9;
                    object[] comps=it.Components as object[];if(comps!=null)foreach(object co in comps){Component2 c=co as Component2;if(c==null)continue;row.components.Add(c.Name2??"");try{row.paths.Add(c.GetPathName()??"");}catch{row.paths.Add("");}}
                    row.classification=Classify(row.components);if(row.classification=="KNOWN_LEGACY")R.known_legacy_count++;else R.new_or_unclassified_count++;
                    R.interferences.Add(row);Log("I"+row.index+" "+String.Join(" | ",row.components.ToArray())+" V="+row.volume_mm3.ToString("0.######")+" mm^3 "+row.classification);
                }
                try{mgr.Done();}catch{}
                if(R.new_or_unclassified_count==0)R.checks.Add("PASS: no new/unclassified hard interference; only controlled known legacy pairs if present.");
                else R.checks.Add("HOLD: new/unclassified interference requires disposition.");
            }finally{try{sw.CloseDoc(title);}catch{}}
        }
        static string Classify(List<string> names)
        {
            string s=String.Join("|",names.ToArray()).ToUpperInvariant();
            if((s.Contains("K01-P-001")&&s.Contains("K01-P-008"))||(s.Contains("K01-P-003")&&s.Contains("K01-P-009")))return "KNOWN_LEGACY";
            return "NEW_OR_UNCLASSIFIED";
        }
        static void Log(string s){string l="["+DateTime.Now.ToString("s")+"] "+s;Console.WriteLine(l);File.AppendAllText(logPath,l+global::System.Environment.NewLine);}
        static void Save(){File.WriteAllText(jsonPath,new JavaScriptSerializer().Serialize(R));}
    }
}
