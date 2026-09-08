using System;
using System.Collections.Generic;
using System.IO;
using System.Runtime.InteropServices;
using System.Text.RegularExpressions;
using System.Web.Script.Serialization;
using SolidWorks.Interop.sldworks;
using SolidWorks.Interop.swconst;

namespace Marvilon.K01.Gate04D_C2.InterferenceDelta
{
    public sealed class Hit
    {
        public string pair="";
        public List<string> components=new List<string>();
        public double volume_mm3=0;
    }
    public sealed class PairResult
    {
        public string pair="";
        public double stable_volume_mm3=0;
        public double c2_volume_mm3=0;
        public double delta_mm3=0;
        public double relative_delta=0;
        public string disposition="";
        public string rationale="";
    }
    public sealed class Report
    {
        public string schema="k01_gate04d_c2_interference_delta_v1";
        public string created_utc=DateTime.UtcNow.ToString("o");
        public string status="RUNNING";
        public string solidworks_revision="";
        public string stable_assembly="";
        public string c2_assembly="";
        public List<Hit> stable_hits=new List<Hit>();
        public List<Hit> c2_hits=new List<Hit>();
        public List<PairResult> pairs=new List<PairResult>();
        public int blocking_pair_count=0;
        public List<string> checks=new List<string>();
        public string error="";
    }

    public static class Program
    {
        const string STABLE=@"D:\Marvilon\K01\cad\assemblies\K01-A-001_Calibration_Module.SLDASM";
        const string C2=@"D:\Marvilon\K01\cad\candidates\gate04d_c2\verification\K01-A-001_GATE04D_C2_VERIFY.SLDASM";
        const string RDIR=@"D:\BreshevEngineering\marvilon-k01\reports\cad\current";
        static readonly HashSet<string> DeclaredFunctional = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
        {
            "K01-P-003|K01-P-006"
        };
        static readonly HashSet<string> KnownLegacy = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
        {
            "K01-P-001|K01-P-008",
            "K01-P-003|K01-P-009"
        };
        static SldWorks sw; static Report R=new Report(); static string logPath,jsonPath;

        public static int Main()
        {
            try
            {
                Directory.CreateDirectory(RDIR); string stamp=DateTime.Now.ToString("yyyyMMdd_HHmmss");
                logPath=Path.Combine(RDIR,"K01_GATE04D_C2_INTERFERENCE_DELTA_"+stamp+".log");
                jsonPath=Path.Combine(RDIR,"K01_GATE04D_C2_INTERFERENCE_DELTA.json");
                File.WriteAllText(logPath,"K01 Gate04D-C2 interference DELTA QA\r\n");
                Connect(); R.stable_assembly=STABLE; R.c2_assembly=C2;
                R.stable_hits=Scan(STABLE,"STABLE");
                R.c2_hits=Scan(C2,"C2");
                Compare();
                R.status=R.blocking_pair_count==0?"PASS":"HOLD";
                Save(); Log("STATUS="+R.status); return R.status=="PASS"?0:2;
            }
            catch(Exception ex){R.status="FAIL";R.error=ex.ToString();try{Save();}catch{}try{Log("STATUS=FAIL\r\n"+ex);}catch{}return 1;}
        }

        static void Connect()
        {
            object a=null;try{a=Marshal.GetActiveObject("SldWorks.Application");}catch{}
            sw=a!=null?(SldWorks)a:(SldWorks)Activator.CreateInstance(Type.GetTypeFromProgID("SldWorks.Application",true));
            sw.Visible=true;R.solidworks_revision=sw.RevisionNumber();Log("Connected "+R.solidworks_revision);
        }

        static List<Hit> Scan(string path,string label)
        {
            if(!File.Exists(path))throw new Exception(label+" assembly missing: "+path);
            int e=0,w=0;ModelDoc2 doc=sw.OpenDoc6(path,(int)swDocumentTypes_e.swDocASSEMBLY,
                (int)swOpenDocOptions_e.swOpenDocOptions_Silent|(int)swOpenDocOptions_e.swOpenDocOptions_ReadOnly,"",ref e,ref w) as ModelDoc2;
            if(doc==null)throw new Exception(label+" OpenDoc6 failed e="+e+" w="+w);
            string title=doc.GetTitle();List<Hit> list=new List<Hit>();
            try
            {
                AssemblyDoc asm=doc as AssemblyDoc;InterferenceDetectionMgr mgr=asm.InterferenceDetectionManager;
                mgr.TreatCoincidenceAsInterference=false;mgr.TreatSubAssembliesAsComponents=false;mgr.IncludeMultibodyPartInterferences=true;
                mgr.MakeInterferingPartsTransparent=false;mgr.CreateFastenersFolder=false;mgr.IgnoreHiddenBodies=false;mgr.ShowIgnoredInterferences=false;mgr.UseTransform=false;
                object[] ints=mgr.GetInterferences() as object[];int count=mgr.GetInterferenceCount();Log(label+" count="+count);
                if(ints!=null)foreach(object o in ints)
                {
                    IInterference it=o as IInterference;if(it==null)continue;Hit h=new Hit();h.volume_mm3=it.Volume*1e9;
                    object[] comps=it.Components as object[];List<string> ids=new List<string>();
                    if(comps!=null)foreach(object co in comps){Component2 c=co as Component2;if(c==null)continue;string id=BaseId(c.Name2??"");h.components.Add(c.Name2??"");if(!String.IsNullOrWhiteSpace(id))ids.Add(id);}
                    ids.Sort(StringComparer.OrdinalIgnoreCase);h.pair=String.Join("|",ids.ToArray());list.Add(h);
                    Log(label+" "+h.pair+" V="+h.volume_mm3.ToString("0.######")+" mm^3");
                }
                try{mgr.Done();}catch{}
            }
            finally{try{sw.CloseDoc(title);}catch{}}
            return list;
        }

        static string BaseId(string name)
        {
            Match m=Regex.Match(name,@"K01-(?:P|B|A)-\d{3}",RegexOptions.IgnoreCase);
            return m.Success?m.Value.ToUpperInvariant():"";
        }

        static Dictionary<string,double> Collapse(List<Hit> hits)
        {
            Dictionary<string,double> d=new Dictionary<string,double>(StringComparer.OrdinalIgnoreCase);
            foreach(Hit h in hits){if(String.IsNullOrWhiteSpace(h.pair))continue;if(!d.ContainsKey(h.pair))d[h.pair]=0;d[h.pair]+=h.volume_mm3;}
            return d;
        }

        static void Compare()
        {
            Dictionary<string,double> a=Collapse(R.stable_hits),b=Collapse(R.c2_hits);
            HashSet<string> all=new HashSet<string>(a.Keys,StringComparer.OrdinalIgnoreCase);foreach(string k in b.Keys)all.Add(k);
            foreach(string pair in all)
            {
                double va=a.ContainsKey(pair)?a[pair]:0, vb=b.ContainsKey(pair)?b[pair]:0;
                PairResult p=new PairResult();p.pair=pair;p.stable_volume_mm3=va;p.c2_volume_mm3=vb;p.delta_mm3=vb-va;
                p.relative_delta=Math.Abs(va)>1e-9?Math.Abs(p.delta_mm3)/Math.Abs(va):(vb==0?0:999);
                bool unchanged=Math.Abs(p.delta_mm3)<=0.25 || p.relative_delta<=0.02;

                if(DeclaredFunctional.Contains(pair) && va>0 && vb>0 && unchanged)
                {
                    p.disposition="PASS_FUNCTIONAL_ENGAGEMENT_UNCHANGED";
                    p.rationale="P003/P006 is the controlled M12x1-6H/6g retaining-plug engagement. C2 did not materially change its interference signature.";
                }
                else if(KnownLegacy.Contains(pair) && va>0 && vb>0 && unchanged)
                {
                    p.disposition="PASS_KNOWN_LEGACY_UNCHANGED";
                    p.rationale="Existing controlled legacy contact/interference is unchanged by C2; track in its own CI/EDR.";
                }
                else if(vb==0 && va>0)
                {
                    p.disposition="PASS_REMOVED";
                    p.rationale="Stable interference not present in C2.";
                }
                else if(vb>0 && va==0)
                {
                    p.disposition="HOLD_NEW_PAIR";
                    p.rationale="C2 introduced an interference pair absent from stable A001.";R.blocking_pair_count++;
                }
                else if(vb>0 && !unchanged)
                {
                    p.disposition="HOLD_CHANGED_PAIR";
                    p.rationale="Existing pair changed beyond delta tolerance; engineering disposition required.";R.blocking_pair_count++;
                }
                else
                {
                    p.disposition="PASS_NO_C2_BLOCKER";
                    p.rationale="No blocking C2 interference delta.";
                }
                R.pairs.Add(p);Log(pair+" stable="+va.ToString("0.######")+" c2="+vb.ToString("0.######")+" delta="+p.delta_mm3.ToString("0.######")+" "+p.disposition);
            }
            if(R.blocking_pair_count==0)R.checks.Add("PASS: Gate04D-C2 introduces no new/materially changed hard interference relative to stable A001.");
            else R.checks.Add("HOLD: one or more C2 interference deltas require engineering disposition.");
            R.checks.Add("P003/P006 is accepted only when the stable M12x1 engagement has the same interference signature; it is not blindly whitelisted.");
        }

        static void Log(string s){string l="["+DateTime.Now.ToString("s")+"] "+s;Console.WriteLine(l);File.AppendAllText(logPath,l+global::System.Environment.NewLine);}
        static void Save(){File.WriteAllText(jsonPath,new JavaScriptSerializer().Serialize(R));}
    }
}
