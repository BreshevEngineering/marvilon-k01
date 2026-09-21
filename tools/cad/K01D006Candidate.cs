using System;
using System.IO;
using System.Text;
using System.Security.Cryptography;
using System.Runtime.InteropServices;
using SolidWorks.Interop.sldworks;
using SolidWorks.Interop.swconst;

namespace K01D006Candidate
{
    class Program
    {
        static string Sha256Shared(string p)
        {
            using(FileStream fs=new FileStream(p,FileMode.Open,FileAccess.Read,
                FileShare.ReadWrite | FileShare.Delete))
            using(SHA256 sha=SHA256.Create())
            {
                byte[] h=sha.ComputeHash(fs);
                return BitConverter.ToString(h).Replace("-","").ToLowerInvariant();
            }
        }

        static string Arg(string[] a,string k)
        {
            for(int i=0;i<a.Length-1;i++) if(a[i]==k) return a[i+1];
            return null;
        }

        static string OneLine(string s)
        {
            if(s==null) return "";
            return s.Replace("\r"," ").Replace("\n"," ").Replace("=","-");
        }

        static void AddNote(ModelDoc2 doc,string text,double x,double y)
        {
            doc.ClearSelection2(true);
            Note n=(Note)doc.InsertNote(text);
            if(n==null) throw new Exception("InsertNote returned null: "+text);
            Annotation a=(Annotation)n.GetAnnotation();
            if(a==null) throw new Exception("Note annotation null");
            bool ok=a.SetPosition(x,y,0);
            if(!ok) throw new Exception("Failed to position note: "+text);
            n.LockPosition=true;
            doc.ClearSelection2(true);
        }

        static int CountViewsAndRefs(DrawingDoc dd,string modelBase,out int modelRefs)
        {
            int count=0; modelRefs=0;
            View v=(View)dd.GetFirstView();
            while(v!=null)
            {
                count++;
                string r="";
                try { r=v.GetReferencedModelName(); } catch {}
                if(!String.IsNullOrWhiteSpace(r))
                {
                    string b=Path.GetFileName(r);
                    if(String.Equals(b,modelBase,StringComparison.OrdinalIgnoreCase)) modelRefs++;
                }
                v=(View)v.GetNextView();
            }
            return count;
        }

        static int Main(string[] args)
        {
            string part=Arg(args,"--part");
            string expected=Arg(args,"--part-sha");
            string outdir=Arg(args,"--outdir");
            string notes=Arg(args,"--notes");
            string report=Arg(args,"--report");

            if(String.IsNullOrWhiteSpace(part)||String.IsNullOrWhiteSpace(expected)||
               String.IsNullOrWhiteSpace(outdir)||String.IsNullOrWhiteSpace(notes)||
               String.IsNullOrWhiteSpace(report))
            {
                Console.Error.WriteLine("Missing args");
                return 2;
            }

            try
            {
                Directory.CreateDirectory(outdir);
                string before=Sha256Shared(part);
                if(!String.Equals(before,expected,StringComparison.OrdinalIgnoreCase))
                    throw new Exception("P007 authority hash mismatch: "+before);

                SldWorks sw=null;
                try { sw=(SldWorks)Marshal.GetActiveObject("SldWorks.Application"); }
                catch
                {
                    Type t=Type.GetTypeFromProgID("SldWorks.Application");
                    if(t==null) throw new Exception("SOLIDWORKS ProgID unavailable");
                    sw=(SldWorks)Activator.CreateInstance(t);
                    sw.Visible=true;
                }

                int interopMajor=typeof(SldWorks).Assembly.GetName().Version.Major;
                if(interopMajor!=26)
                    throw new Exception("Expected SOLIDWORKS 2018 interop major 26; got "+interopMajor);

                string revision="";
                try { revision=sw.RevisionNumber(); } catch {}
                string template=sw.GetUserPreferenceStringValue(
                    (int)swUserPreferenceStringValue_e.swDefaultTemplateDrawing);
                if(String.IsNullOrWhiteSpace(template) || !File.Exists(template))
                    throw new Exception("Default drawing template is not configured or missing: "+template);

                object o=sw.NewDocument(template,(int)swDwgPaperSizes_e.swDwgPaperA3size,0,0);
                ModelDoc2 doc=o as ModelDoc2;
                if(doc==null) throw new Exception("NewDocument returned null");
                DrawingDoc dd=(DrawingDoc)doc;

                string stamp=DateTime.Now.ToString("yyyyMMdd_HHmmss");
                string drw=Path.Combine(outdir,"K01-D-006_Hermetic_Magnetic_Can_CANDIDATE_"+stamp+".SLDDRW");
                string pdf=Path.ChangeExtension(drw,"PDF");
                string bmp=Path.ChangeExtension(drw,"BMP");

                // Views. Coordinates are sheet meters on A3 landscape.
                View front=(View)dd.CreateDrawViewFromModelView3(part,"*Front",0.105,0.195,0);
                View right=(View)dd.CreateDrawViewFromModelView3(part,"*Right",0.285,0.195,0);
                View top=(View)dd.CreateDrawViewFromModelView3(part,"*Top",0.105,0.105,0);
                View iso=(View)dd.CreateDrawViewFromModelView3(part,"*Isometric",0.285,0.105,0);
                if(front==null || right==null || iso==null)
                    throw new Exception("Required drawing view creation failed");

                string noteText=File.ReadAllText(notes,Encoding.UTF8);
                string[] blocks=noteText.Split(new string[]{"\n---BLOCK---\n"},StringSplitOptions.None);

                AddNote(doc,"K01-D-006  |  K01-P-007 HERMETIC MAGNETIC CAN",0.015,0.286);
                AddNote(doc,"CANDIDATE - NOT RELEASED - CHG-K01-D006-CANDIDATE-001",0.015,0.276);
                if(blocks.Length>0) AddNote(doc,blocks[0].Trim(),0.015,0.070);
                if(blocks.Length>1) AddNote(doc,blocks[1].Trim(),0.215,0.070);

                doc.ForceRebuild3(false);
                doc.ViewZoomtofit2();
                doc.WindowRedraw();

                int e1=0,w1=0;
                bool saved=doc.Extension.SaveAs(
                    drw,
                    (int)swSaveAsVersion_e.swSaveAsCurrentVersion,
                    (int)swSaveAsOptions_e.swSaveAsOptions_Silent,
                    null,ref e1,ref w1);
                if(!saved || e1!=0) throw new Exception("SLDDRW SaveAs failed errors="+e1+" warnings="+w1);

                string[] snames=(string[])dd.GetSheetNames();
                if(snames==null || snames.Length<1) throw new Exception("No drawing sheet names");
                dd.ActivateSheet(snames[0]);
                Sheet sheet=(Sheet)dd.GetCurrentSheet();
                ExportPdfData pdfData=(ExportPdfData)sw.GetExportFileData((int)swExportDataFileType_e.swExportPdfData);
                if(pdfData==null) throw new Exception("GetExportFileData PDF returned null");
                DispatchWrapper[] arr=new DispatchWrapper[]{new DispatchWrapper(sheet)};
                bool shok=pdfData.SetSheets((int)swExportDataSheetsToExport_e.swExportData_ExportSpecifiedSheets,arr);
                if(!shok) throw new Exception("PDF SetSheets failed");
                pdfData.ViewPdfAfterSaving=false;
                int e2=0,w2=0;
                bool pdfok=doc.Extension.SaveAs(
                    pdf,
                    (int)swSaveAsVersion_e.swSaveAsCurrentVersion,
                    (int)swSaveAsOptions_e.swSaveAsOptions_Silent,
                    pdfData,ref e2,ref w2);
                if(!pdfok || e2!=0) throw new Exception("PDF SaveAs failed errors="+e2+" warnings="+w2);

                doc.ViewZoomtofit2();
                bool bmpok=doc.SaveBMP(bmp,1800,1273);

                string title=doc.GetTitle();
                sw.CloseDoc(title);

                int oe=0,ow=0;
                ModelDoc2 reopened=(ModelDoc2)sw.OpenDoc6(
                    drw,
                    (int)swDocumentTypes_e.swDocDRAWING,
                    (int)swOpenDocOptions_e.swOpenDocOptions_Silent,
                    "",ref oe,ref ow);
                if(reopened==null) throw new Exception("Reopen drawing failed errors="+oe+" warnings="+ow);
                DrawingDoc rdd=(DrawingDoc)reopened;
                int refs=0;
                int viewCount=CountViewsAndRefs(rdd,Path.GetFileName(part),out refs);
                bool refsOk=refs>=3;
                sw.CloseDoc(reopened.GetTitle());

                string after=Sha256Shared(part);
                bool geomInvariant=String.Equals(before,after,StringComparison.OrdinalIgnoreCase);

                if(!File.Exists(drw) || new FileInfo(drw).Length<4096)
                    throw new Exception("SLDDRW missing or too small");
                if(!File.Exists(pdf) || new FileInfo(pdf).Length<4096)
                    throw new Exception("PDF missing or too small");
                if(!refsOk) throw new Exception("Reopen references did not resolve to P007 in >=3 model views; refs="+refs);
                if(!geomInvariant) throw new Exception("P007 authority hash changed during drawing authoring");

                StringBuilder sb=new StringBuilder();
                sb.AppendLine("STATUS=PASS_AUTOMATED_D006_CANDIDATE_BUILD");
                sb.AppendLine("WORKSTATION_CONTRACT=SOLIDWORKS 2018 / API revision 26");
                sb.AppendLine("SOLIDWORKS_REVISION="+OneLine(revision));
                sb.AppendLine("INTEROP_MAJOR="+interopMajor);
                sb.AppendLine("TEMPLATE="+OneLine(template));
                sb.AppendLine("SOURCE_PART="+OneLine(part));
                sb.AppendLine("SOURCE_SHA_BEFORE="+before);
                sb.AppendLine("SOURCE_SHA_AFTER="+after);
                sb.AppendLine("GEOMETRY_HASH_INVARIANT="+geomInvariant);
                sb.AppendLine("DRAWING="+OneLine(drw));
                sb.AppendLine("PDF="+OneLine(pdf));
                sb.AppendLine("BMP="+OneLine(bmp));
                sb.AppendLine("DRAWING_BYTES="+new FileInfo(drw).Length);
                sb.AppendLine("PDF_BYTES="+new FileInfo(pdf).Length);
                sb.AppendLine("BMP_CREATED="+bmpok);
                sb.AppendLine("BMP_BYTES="+(File.Exists(bmp)?new FileInfo(bmp).Length:0));
                sb.AppendLine("VIEW_COUNT_WITH_SHEET="+viewCount);
                sb.AppendLine("P007_MODEL_VIEW_REFERENCES="+refs);
                sb.AppendLine("REFERENCES_OK="+refsOk);
                File.WriteAllText(report,sb.ToString(),Encoding.UTF8);

                Console.WriteLine("status: PASS_AUTOMATED_D006_CANDIDATE_BUILD");
                Console.WriteLine("drawing: "+drw);
                Console.WriteLine("pdf: "+pdf);
                Console.WriteLine("bmp: "+bmp);
                Console.WriteLine("views: "+viewCount+" P007 refs="+refs);
                Console.WriteLine("source_hash_invariant: "+geomInvariant);
                return 0;
            }
            catch(Exception ex)
            {
                try { File.WriteAllText(report,"STATUS=HOLD\nERROR="+OneLine(ex.ToString())+"\n",Encoding.UTF8); } catch {}
                Console.Error.WriteLine(ex.ToString());
                return 2;
            }
        }
    }
}
