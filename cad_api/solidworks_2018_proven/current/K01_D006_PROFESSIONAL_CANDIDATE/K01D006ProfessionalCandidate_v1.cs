using System;
using System.Collections.Generic;
using System.IO;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using SolidWorks.Interop.sldworks;
using SolidWorks.Interop.swconst;

namespace K01D006ProfessionalCandidate
{
    class Program
    {
        static string Arg(string[] a,string k){for(int i=0;i<a.Length-1;i++)if(a[i]==k)return a[i+1];return null;}
        static string OneLine(string s){return (s??"").Replace("\r"," ").Replace("\n"," ").Replace("=","-");}
        static string Sha256Shared(string p)
        {
            using(FileStream fs=new FileStream(p,FileMode.Open,FileAccess.Read,FileShare.ReadWrite|FileShare.Delete))
            using(SHA256 sha=SHA256.Create())
                return BitConverter.ToString(sha.ComputeHash(fs)).Replace("-","").ToLowerInvariant();
        }
        static void Need(bool ok,string msg){if(!ok)throw new Exception(msg);}
        static void AddNote(ModelDoc2 doc,string text,double x,double y)
        {
            doc.ClearSelection2(true);
            Note n=doc.InsertNote(text) as Note;
            Need(n!=null,"InsertNote failed");
            Annotation a=n.GetAnnotation() as Annotation;
            Need(a!=null,"Note annotation missing");
            Need(a.SetPosition(x,y,0),"Note position failed");
            n.LockPosition=true;
            doc.ClearSelection2(true);
        }
        static string[][] ReadTsv(string p)
        {
            var rows=new List<string[]>();
            foreach(string raw in File.ReadAllLines(p,Encoding.UTF8))
            {
                if(String.IsNullOrWhiteSpace(raw))continue;
                rows.Add(raw.Split('\t'));
            }
            return rows.ToArray();
        }
        static void FillTable(TableAnnotation t,string[][] rows)
        {
            Need(t!=null,"table creation returned null");
            int cols=0;foreach(string[] r in rows)cols=Math.Max(cols,r.Length);
            for(int r=0;r<rows.Length;r++)
                for(int c=0;c<cols;c++)
                    t.set_Text2(r,c,false,c<rows[r].Length?rows[r][c]:"");
        }
        static int CountViewsAndRefs(DrawingDoc dd,string modelBase,out int modelRefs)
        {
            int n=0;modelRefs=0;View v=dd.GetFirstView() as View;
            while(v!=null)
            {
                n++;
                string r="";try{r=v.GetReferencedModelName();}catch{}
                if(!String.IsNullOrWhiteSpace(r)&&String.Equals(Path.GetFileName(r),modelBase,StringComparison.OrdinalIgnoreCase))
                    modelRefs++;
                v=v.GetNextView() as View;
            }
            return n;
        }
        static bool SaveNative(ModelDoc2 doc,string p,out int er,out int wr)
        {
            er=0;wr=0;return doc.Extension.SaveAs(p,(int)swSaveAsVersion_e.swSaveAsCurrentVersion,
                (int)swSaveAsOptions_e.swSaveAsOptions_Silent,null,ref er,ref wr);
        }
        static int Main(string[] args)
        {
            string part=Arg(args,"--part"), expected=Arg(args,"--part-sha"), template=Arg(args,"--template");
            string outdir=Arg(args,"--outdir"), table=Arg(args,"--table"), notes=Arg(args,"--notes"), report=Arg(args,"--report");
            if(String.IsNullOrWhiteSpace(part)||String.IsNullOrWhiteSpace(expected)||String.IsNullOrWhiteSpace(template)||
               String.IsNullOrWhiteSpace(outdir)||String.IsNullOrWhiteSpace(table)||String.IsNullOrWhiteSpace(notes)||
               String.IsNullOrWhiteSpace(report)){Console.Error.WriteLine("Missing args");return 2;}
            try
            {
                Need(File.Exists(part),"source part missing");
                Need(File.Exists(template),"controlled drawing template missing");
                Need(File.Exists(table),"characteristic table input missing");
                Need(File.Exists(notes),"note input missing");
                Directory.CreateDirectory(outdir);

                string before=Sha256Shared(part);
                Need(String.Equals(before,expected,StringComparison.OrdinalIgnoreCase),"source part SHA mismatch "+before);

                SldWorks sw=null;
                try{sw=Marshal.GetActiveObject("SldWorks.Application") as SldWorks;}catch{}
                if(sw==null)
                {
                    Type t=Type.GetTypeFromProgID("SldWorks.Application");
                    Need(t!=null,"SOLIDWORKS ProgID unavailable");
                    sw=Activator.CreateInstance(t) as SldWorks;
                    Need(sw!=null,"SOLIDWORKS activation failed");
                    sw.Visible=true;
                }
                int interopMajor=typeof(SldWorks).Assembly.GetName().Version.Major;
                Need(interopMajor==26,"Expected SOLIDWORKS 2018 interop major 26; got "+interopMajor);
                string revision="";try{revision=sw.RevisionNumber();}catch{}

                ModelDoc2 doc=sw.NewDocument(template,0,0,0) as ModelDoc2;
                Need(doc!=null,"NewDocument returned null");
                DrawingDoc dr=doc as DrawingDoc;
                Need(dr!=null,"new document is not DrawingDoc");
                string drawTitle=doc.GetTitle();

                // These drawing operations and call signatures were already proven on this SW2018
                // workstation by K01 Gate04D C2R1 V3: A3 sheet, model views, section view and tables.
                dr.SetupSheet5("Sheet1",(int)swDwgPaperSizes_e.swDwgPaperA3size,
                    (int)swDwgTemplates_e.swDwgTemplateA3size,2,1,true,"",0.420,0.297,"",false);

                View front=dr.CreateDrawViewFromModelView3(part,"*Front",0.112,0.212,0) as View;
                View right=dr.CreateDrawViewFromModelView3(part,"*Right",0.310,0.212,0) as View;
                View iso=dr.CreateDrawViewFromModelView3(part,"*Isometric",0.315,0.108,0) as View;
                Need(front!=null&&right!=null&&iso!=null,"required model views failed");

                bool sectionCreated=false;
                try
                {
                    dr.ActivateView(front.Name);
                    double[] o=front.GetOutline() as double[];
                    Need(o!=null&&o.Length>=4,"front outline unavailable");
                    double cy=(o[1]+o[3])*0.5;
                    doc.ClearSelection2(true);
                    SketchSegment ln=doc.SketchManager.CreateLine(o[0]-0.003,cy,0,o[2]+0.003,cy,0);
                    if(ln!=null)
                    {
                        View sec=dr.CreateSectionViewAt5(0.112,0.108,0,"A",32,null,0) as View;
                        sectionCreated=sec!=null;
                    }
                }catch(Exception ex){Console.WriteLine("section_warning: "+OneLine(ex.Message));}
                Need(sectionCreated,"required section A-A was not created");

                string[][] rows=ReadTsv(table);
                Need(rows.Length>=5,"characteristic table too small");
                int cols=0;foreach(string[] r in rows)cols=Math.Max(cols,r.Length);
                TableAnnotation ct=doc.Extension.InsertGeneralTableAnnotation(false,0.205,0.286,0,"",rows.Length,cols);
                FillTable(ct,rows);

                string[,] tb=new string[,]{
                    {"DRAWING","K01-D-006","PART","K01-P-007"},
                    {"TITLE","HERMETIC MAGNETIC CAN","STATUS","DESIGN REVIEW / NOT RELEASED"},
                    {"UNITS","mm","MATERIAL","AISI 316L / EN 1.4404"},
                    {"SOURCE","CURRENT PROVEN P007 PMI CANDIDATE","REV","CP-P / PMI"},
                    {"CONTROL","OPEN ITEMS EXPLICIT","SHEET","1 / 1"}
                };
                TableAnnotation tt=doc.Extension.InsertGeneralTableAnnotation(false,0.258,0.052,0,"",5,4);
                Need(tt!=null,"title table failed");
                for(int r=0;r<5;r++)for(int c=0;c<4;c++)tt.set_Text2(r,c,false,tb[r,c]);

                string noteText=File.ReadAllText(notes,Encoding.UTF8);
                AddNote(doc,"K01-D-006 | K01-P-007 HERMETIC MAGNETIC CAN",0.015,0.286);
                AddNote(doc,"DESIGN REVIEW CANDIDATE - NOT RELEASED",0.015,0.277);
                AddNote(doc,noteText,0.015,0.060);

                doc.ForceRebuild3(false);
                doc.ViewZoomtofit2();
                doc.WindowRedraw();

                string stamp=DateTime.Now.ToString("yyyyMMdd_HHmmss");
                string drw=Path.Combine(outdir,"K01-D-006_Hermetic_Magnetic_Can_PROFESSIONAL_CANDIDATE_"+stamp+".SLDDRW");
                string pdf=Path.ChangeExtension(drw,"PDF");
                string bmp=Path.ChangeExtension(drw,"BMP");

                int e1=0,w1=0;
                Need(SaveNative(doc,drw,out e1,out w1)&&e1==0,"SLDDRW SaveAs failed e="+e1+" w="+w1);

                string[] snames=dr.GetSheetNames() as string[];
                Need(snames!=null&&snames.Length>0,"sheet name missing");
                dr.ActivateSheet(snames[0]);
                Sheet sheet=dr.GetCurrentSheet() as Sheet;
                Need(sheet!=null,"current sheet missing");
                ExportPdfData pdfData=sw.GetExportFileData((int)swExportDataFileType_e.swExportPdfData) as ExportPdfData;
                Need(pdfData!=null,"PDF export data missing");
                DispatchWrapper[] arr=new DispatchWrapper[]{new DispatchWrapper(sheet)};
                Need(pdfData.SetSheets((int)swExportDataSheetsToExport_e.swExportData_ExportSpecifiedSheets,arr),"PDF SetSheets failed");
                pdfData.ViewPdfAfterSaving=false;
                int e2=0,w2=0;
                bool pdfOk=doc.Extension.SaveAs(pdf,(int)swSaveAsVersion_e.swSaveAsCurrentVersion,
                    (int)swSaveAsOptions_e.swSaveAsOptions_Silent,pdfData,ref e2,ref w2);
                Need(pdfOk&&e2==0,"PDF SaveAs failed e="+e2+" w="+w2);

                doc.ViewZoomtofit2();
                bool bmpOk=doc.SaveBMP(bmp,1800,1273);

                sw.CloseDoc(drawTitle);

                int oe=0,ow=0;
                ModelDoc2 reopened=sw.OpenDoc6(drw,(int)swDocumentTypes_e.swDocDRAWING,
                    (int)swOpenDocOptions_e.swOpenDocOptions_Silent,"",ref oe,ref ow) as ModelDoc2;
                Need(reopened!=null,"reopen drawing failed e="+oe+" w="+ow);
                DrawingDoc rdd=reopened as DrawingDoc;Need(rdd!=null,"reopened doc not drawing");
                int refs=0;int viewCount=CountViewsAndRefs(rdd,Path.GetFileName(part),out refs);
                sw.CloseDoc(reopened.GetTitle());

                string after=Sha256Shared(part);
                bool sourceInvariant=String.Equals(before,after,StringComparison.OrdinalIgnoreCase);
                Need(sourceInvariant,"source P007 candidate changed during drawing authoring");
                Need(refs>=4,"drawing model references <4; got "+refs);
                Need(File.Exists(drw)&&new FileInfo(drw).Length>4096,"SLDDRW missing/small");
                Need(File.Exists(pdf)&&new FileInfo(pdf).Length>4096,"PDF missing/small");

                var sb=new StringBuilder();
                sb.AppendLine("STATUS=PASS_D006_PROFESSIONAL_DESIGN_REVIEW_CANDIDATE");
                sb.AppendLine("WORKSTATION_CONTRACT=SOLIDWORKS 2018 / API revision 26");
                sb.AppendLine("SOLIDWORKS_REVISION="+OneLine(revision));
                sb.AppendLine("INTEROP_MAJOR="+interopMajor);
                sb.AppendLine("TEMPLATE="+OneLine(template));
                sb.AppendLine("SOURCE_PART="+OneLine(part));
                sb.AppendLine("SOURCE_SHA_BEFORE="+before);
                sb.AppendLine("SOURCE_SHA_AFTER="+after);
                sb.AppendLine("SOURCE_HASH_INVARIANT="+sourceInvariant);
                sb.AppendLine("SECTION_CREATED="+sectionCreated);
                sb.AppendLine("CHARACTERISTIC_TABLE_CREATED=True");
                sb.AppendLine("TITLE_TABLE_CREATED=True");
                sb.AppendLine("DRAWING="+OneLine(drw));
                sb.AppendLine("PDF="+OneLine(pdf));
                sb.AppendLine("BMP="+OneLine(bmp));
                sb.AppendLine("DRAWING_BYTES="+new FileInfo(drw).Length);
                sb.AppendLine("PDF_BYTES="+new FileInfo(pdf).Length);
                sb.AppendLine("BMP_CREATED="+bmpOk);
                sb.AppendLine("BMP_BYTES="+(File.Exists(bmp)?new FileInfo(bmp).Length:0));
                sb.AppendLine("VIEW_COUNT_WITH_SHEET="+viewCount);
                sb.AppendLine("P007_MODEL_VIEW_REFERENCES="+refs);
                File.WriteAllText(report,sb.ToString(),Encoding.UTF8);

                Console.WriteLine("STATUS: PASS_D006_PROFESSIONAL_DESIGN_REVIEW_CANDIDATE");
                Console.WriteLine("DRAWING: "+drw);
                Console.WriteLine("PDF: "+pdf);
                Console.WriteLine("BMP: "+bmp);
                Console.WriteLine("SECTION: "+sectionCreated);
                Console.WriteLine("P007 refs: "+refs);
                Console.WriteLine("SOURCE HASH INVARIANT: "+sourceInvariant);
                return 0;
            }
            catch(Exception ex)
            {
                try{File.WriteAllText(report,"STATUS=HOLD\nERROR="+OneLine(ex.ToString())+"\n",Encoding.UTF8);}catch{}
                Console.Error.WriteLine(ex.ToString());
                return 2;
            }
        }
    }
}
