using System;
using System.Collections.Generic;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Web.Script.Serialization;
using SolidWorks.Interop.sldworks;
using SolidWorks.Interop.swconst;

namespace Marvilon.K01.BOM
{
    public sealed class BomRow
    {
        public string observed_part_no="",identity_source="",description="",revision="",material_property="",solidworks_material="",make_buy="",status="",supplier="",supplier_pn="",qty_unit="",configuration="",path="";
        public int qty=0; public List<string> issues=new List<string>();
    }
    public sealed class Report
    {
        public string schema="k01_automatic_bom_v1",created_utc=DateTime.UtcNow.ToString("o"),status="RUNNING",mode="",assembly="",solidworks_revision="",error="";
        public int included_instances=0,unique_rows=0,excluded_instances=0,suppressed_instances=0,issue_count=0;
        public List<BomRow> rows=new List<BomRow>();public List<string> issues=new List<string>();
    }
    public static class Program
    {
        const string PROD=@"D:\Marvilon\K01\cad\assemblies\K01-A-001_Calibration_Module.SLDASM";
        const string STUDY=@"D:\Marvilon\K01\cad\candidates\gate04d_c2\verification\K01-A-001_GATE04D_C2_VERIFY.SLDASM";
        const string STUDYR1=@"D:\Marvilon\K01\cad\candidates\gate04d_c2r1\verification\K01-A-001_GATE04D_C2R1_VERIFY.SLDASM";
        const string BDIR=@"D:\BreshevEngineering\marvilon-k01\bom";
        const string RDIR=@"D:\BreshevEngineering\marvilon-k01\reports\bom";
        static SldWorks sw;static Report R=new Report();
        public static int Main(string[] args)
        {
            try{
                string mode=(args.Length>0?args[0]:"study").ToLowerInvariant();string path=mode=="production"?PROD:(mode=="r1"?STUDYR1:STUDY);R.mode=mode;R.assembly=path;
                Directory.CreateDirectory(BDIR);Directory.CreateDirectory(RDIR);Connect();Build(path);R.status=R.issue_count==0?"PASS":"HOLD";WriteOutputs();
                Console.WriteLine("BOM "+R.status+" rows="+R.unique_rows+" issues="+R.issue_count);return R.status=="PASS"?0:2;
            }catch(Exception ex){R.status="FAIL";R.error=ex.ToString();try{WriteOutputs();}catch{}Console.WriteLine(ex);return 1;}
        }
        static void Connect(){object a=null;try{a=Marshal.GetActiveObject("SldWorks.Application");}catch{}sw=a!=null?(SldWorks)a:(SldWorks)Activator.CreateInstance(Type.GetTypeFromProgID("SldWorks.Application",true));sw.Visible=true;R.solidworks_revision=sw.RevisionNumber();}
        static void Build(string path)
        {
            if(!File.Exists(path))throw new Exception("Assembly missing: "+path);int e=0,w=0;
            ModelDoc2 doc=sw.OpenDoc6(path,(int)swDocumentTypes_e.swDocASSEMBLY,(int)swOpenDocOptions_e.swOpenDocOptions_Silent|(int)swOpenDocOptions_e.swOpenDocOptions_ReadOnly,"",ref e,ref w) as ModelDoc2;
            if(doc==null)throw new Exception("OpenDoc6 failed e="+e+" w="+w);string title=doc.GetTitle();
            try{
                AssemblyDoc asm=doc as AssemblyDoc;object[] comps=asm.GetComponents(false) as object[];if(comps==null)comps=new object[0];
                Dictionary<string,BomRow> map=new Dictionary<string,BomRow>(StringComparer.OrdinalIgnoreCase);
                foreach(object o in comps){
                    Component2 c=o as Component2;if(c==null)continue;bool supp=false;try{supp=c.IsSuppressed();}catch{}if(supp){R.suppressed_instances++;continue;}
                    bool ex=false;try{ex=c.ExcludeFromBOM;}catch{}if(ex){R.excluded_instances++;continue;}
                    string cp="";try{cp=c.GetPathName()??"";}catch{}if(String.IsNullOrWhiteSpace(cp))continue;string conf="";try{conf=c.ReferencedConfiguration??"";}catch{}
                    string key=cp.ToLowerInvariant()+"|"+conf.ToLowerInvariant();BomRow row;if(!map.TryGetValue(key,out row)){row=ReadRow(c,cp,conf);map[key]=row;}row.qty++;R.included_instances++;
                }
                foreach(BomRow r in map.Values){R.rows.Add(r);R.issue_count+=r.issues.Count;}R.unique_rows=R.rows.Count;
                if(R.issue_count>0)R.issues.Add("HOLD: missing/OPEN identity or material properties exist. Filename fallback is display-only.");
            }finally{try{sw.CloseDoc(title);}catch{}}
        }
        static BomRow ReadRow(Component2 c,string path,string conf)
        {
            BomRow r=new BomRow();r.path=path;r.configuration=conf;ModelDoc2 d=null;try{d=c.GetModelDoc2() as ModelDoc2;}catch{}
            bool opened=false;string openedTitle="";
            if(d==null){int type=path.EndsWith(".SLDASM",StringComparison.OrdinalIgnoreCase)?(int)swDocumentTypes_e.swDocASSEMBLY:(int)swDocumentTypes_e.swDocPART;int e=0,w=0;d=sw.OpenDoc6(path,type,(int)swOpenDocOptions_e.swOpenDocOptions_Silent|(int)swOpenDocOptions_e.swOpenDocOptions_ReadOnly,"",ref e,ref w) as ModelDoc2;if(d!=null){opened=true;openedTitle=d.GetTitle();}}
            try{
                string pno=Prop(d,conf,new[]{"PartNo","Part Number","PartNo."});if(String.IsNullOrWhiteSpace(pno)){r.observed_part_no=Path.GetFileNameWithoutExtension(path);r.identity_source="FILENAME_FALLBACK_NONAUTHORITATIVE";r.issues.Add("Missing PartNo.");}else{r.observed_part_no=pno;r.identity_source="CUSTOM_PROPERTY";}
                r.description=Prop(d,conf,new[]{"Description","DESCRIPTION"});r.revision=Prop(d,conf,new[]{"Revision","REV"});r.material_property=Prop(d,conf,new[]{"Material","MATERIAL"});
                r.make_buy=Prop(d,conf,new[]{"MakeBuy","MAKE_BUY"});r.status=Prop(d,conf,new[]{"Status","STATUS"});r.supplier=Prop(d,conf,new[]{"Supplier","SUPPLIER"});r.supplier_pn=Prop(d,conf,new[]{"SupplierPN","Supplier P/N","SUPPLIER_PN"});r.qty_unit=Prop(d,conf,new[]{"QtyUnit","QTY_UNIT"});
                if(d is PartDoc){string db="";try{r.solidworks_material=((PartDoc)d).GetMaterialPropertyName2(conf,out db)??"";}catch{}}
                if(String.IsNullOrWhiteSpace(r.description))r.issues.Add("Missing Description.");
                if(String.IsNullOrWhiteSpace(r.material_property)&&String.IsNullOrWhiteSpace(r.solidworks_material))r.issues.Add("Missing material.");
                if((r.material_property??"").IndexOf("OPEN",StringComparison.OrdinalIgnoreCase)>=0)r.issues.Add("Material OPEN.");
            }finally{if(opened)try{sw.CloseDoc(openedTitle);}catch{}}
            return r;
        }
        static string Prop(ModelDoc2 d,string conf,string[] names)
        {
            if(d==null)return "";foreach(string n in names){string v=GetOne(d.Extension.get_CustomPropertyManager(conf),n);if(String.IsNullOrWhiteSpace(v))v=GetOne(d.Extension.get_CustomPropertyManager(""),n);if(!String.IsNullOrWhiteSpace(v))return v;}return "";
        }
        static string GetOne(CustomPropertyManager c,string name){if(c==null)return "";string raw="",res="";bool wr=false,link=false;try{c.Get6(name,false,out raw,out res,out wr,out link);}catch{return "";}return !String.IsNullOrWhiteSpace(res)?res:raw;}
        static void WriteOutputs()
        {
            string suffix=R.mode=="production"?"production":(R.mode=="r1"?"study_c2r1":"study_c2");var js=new JavaScriptSerializer();File.WriteAllText(Path.Combine(BDIR,"K01_BOM_"+suffix+".json"),js.Serialize(R));File.WriteAllText(Path.Combine(RDIR,"K01_BOM_AUDIT_"+suffix+".json"),js.Serialize(R));
            StringBuilder sb=new StringBuilder();sb.AppendLine("PartNo,Qty,Unit,Description,Revision,MaterialProperty,SolidWorksMaterial,MakeBuy,Status,Supplier,SupplierPN,Configuration,Path,IdentitySource,Issues");
            foreach(BomRow r in R.rows)sb.AppendLine(Csv(r.observed_part_no)+","+r.qty+","+Csv(r.qty_unit)+","+Csv(r.description)+","+Csv(r.revision)+","+Csv(r.material_property)+","+Csv(r.solidworks_material)+","+Csv(r.make_buy)+","+Csv(r.status)+","+Csv(r.supplier)+","+Csv(r.supplier_pn)+","+Csv(r.configuration)+","+Csv(r.path)+","+Csv(r.identity_source)+","+Csv(String.Join(" | ",r.issues.ToArray())));
            File.WriteAllText(Path.Combine(BDIR,"K01_BOM_"+suffix+".csv"),sb.ToString(),new UTF8Encoding(true));
        }
        static string Csv(string s){s=s??"";return "\""+s.Replace("\"","\"\"")+"\"";}
    }
}
