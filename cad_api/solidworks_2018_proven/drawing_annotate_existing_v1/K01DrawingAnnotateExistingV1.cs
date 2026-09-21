using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using System.Threading;
using System.Web.Script.Serialization;
using System.Runtime.InteropServices;
using SolidWorks.Interop.sldworks;
using SolidWorks.Interop.swconst;
using K01Sw2018Runtime;

namespace K01DrawingAnnotateExistingV1
{
    public class Target
    {
        public string annotation_name;
    }

    public class Operation
    {
        public string id;
        public string op;
        public Target target;

        public string hole_fit;
        public string shaft_fit;

        public Nullable<double> lower_tol_mm;
        public Nullable<double> upper_tol_mm;
        public Nullable<double> sym_tol_mm;
        public Nullable<int> precision;

        public string prefix;
        public string suffix;
        public string text;

        public string property_name;
        public string property_value;

        public Nullable<double> x_m;
        public Nullable<double> y_m;
    }

    public class Job
    {
        public string schema;
        public string drawing_id;
        public string source_drawing;
        public string candidate_root;
        public List<Operation> operations;
    }

    public class Resolved
    {
        public Operation op;
        public Annotation ann;
        public DisplayDimension dd;
        public Dimension dim;
        public Note note;
        public string view;
    }

    public class Change
    {
        public string id;
        public string op;
        public string target;
        public string before;
        public string after;
        public string status;
    }

    public class Report
    {
        public string schema="k01.drawing_annotate_existing.report.v1";
        public string status="HOLD";
        public string drawing_id="";
        public string source_drawing="";
        public string candidate_drawing="";
        public string output_pdf="";
        public string output_dxf="";
        public string output_bmp="";
        public string source_sha_before="";
        public string source_sha_after="";
        public string candidate_sha="";
        public string sw_revision="";
        public int attempts=0;
        public int annotations_inventory=0;
        public int operations_requested=0;
        public int operations_resolved=0;
        public int operations_applied=0;
        public List<Change> changes=new List<Change>();
        public string error="";
    }

    public static class Program
    {
        const double MM=0.001;

        public static int Main(string[] args)
        {
            if(args.Length==1 && args[0]=="--runtime-probe")
            {
                Console.WriteLine("RUNTIME_PROBE=PASS");
                Console.WriteLine("SLDWORKS_ASSEMBLY="+typeof(SldWorks).Assembly.FullName);
                Console.WriteLine("SWCONST_ASSEMBLY="+typeof(swDocumentTypes_e).Assembly.FullName);
                return 0;
            }

            if(args.Length<2)
            {
                Console.WriteLine("Usage: exe <job.json> <report_dir>");
                return 2;
            }

            string jobPath=args[0], reportDir=args[1];
            Directory.CreateDirectory(reportDir);
            Job job=null;
            Report R=new Report();

            try
            {
                job=Load<Job>(jobPath);
                ValidateJob(job);

                R.drawing_id=job.drawing_id;
                R.source_drawing=Path.GetFullPath(job.source_drawing);
                R.operations_requested=job.operations.Count;
                R.source_sha_before=SwSession.Sha256File(R.source_drawing);

                string stamp=DateTime.Now.ToString("yyyyMMdd_HHmmss");
                string candDir=Path.Combine(job.candidate_root,stamp);
                Directory.CreateDirectory(candDir);

                string candidate=Path.Combine(candDir,
                    Path.GetFileNameWithoutExtension(job.source_drawing)+"_ANNOTATED.SLDDRW");
                string pdf=Path.ChangeExtension(candidate,"PDF");
                string dxf=Path.ChangeExtension(candidate,"DXF");
                string bmp=Path.ChangeExtension(candidate,"BMP");

                R.candidate_drawing=candidate;
                R.output_pdf=pdf;
                R.output_dxf=dxf;
                R.output_bmp=bmp;

                Exception last=null;
                for(int attempt=1; attempt<=3; attempt++)
                {
                    R.attempts=attempt;
                    try
                    {
                        File.Copy(R.source_drawing,candidate,true);
                        ExecuteAttempt(job,candidate,pdf,dxf,bmp,R);
                        last=null;
                        break;
                    }
                    catch(COMException ex)
                    {
                        last=ex;
                        Console.WriteLine("ATTEMPT="+attempt+" COM_HOLD="+One(ex.Message));
                        Thread.Sleep(1500);
                    }
                    catch(Exception ex)
                    {
                        last=ex;
                        Console.WriteLine("ATTEMPT="+attempt+" HOLD="+One(ex.Message));
                        // Retry only infrastructure/open/save failures. Semantic target errors should not be hidden.
                        if(IsSemanticFailure(ex.Message)) break;
                        Thread.Sleep(1000);
                    }
                }

                if(last!=null) throw last;

                R.candidate_sha=SwSession.Sha256AfterClose(candidate);
                R.source_sha_after=SwSession.Sha256AfterClose(R.source_drawing);
                if(R.source_sha_before!=R.source_sha_after)
                    throw new Exception("SOURCE_DRAWING_INVARIANCE_FAILED");

                R.status="PASS_DRAWING_ANNOTATE_EXISTING_V1__MANUAL_FINISH_READY";
                SaveReport(reportDir,R);

                Console.WriteLine("STATUS="+R.status);
                Console.WriteLine("ATTEMPTS="+R.attempts);
                Console.WriteLine("OPERATIONS="+R.operations_applied+"/"+R.operations_requested);
                Console.WriteLine("SOURCE_DRAWING_INVARIANCE=PASS");
                Console.WriteLine("CANDIDATE="+candidate);
                Console.WriteLine("PDF="+pdf);
                Console.WriteLine("DXF="+dxf);
                Console.WriteLine("BMP="+bmp);
                Console.WriteLine("REPORT="+Path.Combine(reportDir,"K01_DRAWING_ANNOTATE_EXISTING_CURRENT.json"));
                return 0;
            }
            catch(Exception ex)
            {
                R.status="HOLD_DRAWING_ANNOTATE_EXISTING_V1";
                R.error=ex.ToString();
                try { SaveReport(reportDir,R); } catch {}
                Console.WriteLine("STATUS="+R.status);
                Console.WriteLine("ERROR="+ex.Message);
                return 3;
            }
        }

        static bool IsSemanticFailure(string s)
        {
            s=s??"";
            return s.IndexOf("TARGET_",StringComparison.OrdinalIgnoreCase)>=0 ||
                   s.IndexOf("ANNOTATION_",StringComparison.OrdinalIgnoreCase)>=0 ||
                   s.IndexOf("requires DisplayDimension",StringComparison.OrdinalIgnoreCase)>=0 ||
                   s.IndexOf("requires Note",StringComparison.OrdinalIgnoreCase)>=0 ||
                   s.IndexOf("unsupported operation",StringComparison.OrdinalIgnoreCase)>=0;
        }

        static void ExecuteAttempt(Job job,string candidate,string pdf,string dxf,string bmp,Report R)
        {
            using(SwSession ses=SwSession.ConnectOrStart(true))
            {
                R.sw_revision=ses.Revision;
                ses.RequireTargetClosed(candidate,"CANDIDATE_DRAWING");

                int e=0,w=0;
                ModelDoc2 doc=ses.App.OpenDoc6(candidate,(int)swDocumentTypes_e.swDocDRAWING,
                    (int)swOpenDocOptions_e.swOpenDocOptions_Silent,"",ref e,ref w) as ModelDoc2;
                if(doc==null) throw new Exception("CANDIDATE_OPEN_FAILED e="+e+" w="+w);

                try
                {
                    DrawingDoc dr=doc as DrawingDoc;
                    if(dr==null) throw new Exception("CANDIDATE_NOT_DRAWING");

                    Dictionary<string,List<Tuple<Annotation,string>>> byName;
                    List<Tuple<Annotation,string>> anns=InventoryAnnotations(dr,out byName);
                    R.annotations_inventory=anns.Count;

                    List<Resolved> rr=new List<Resolved>();
                    foreach(Operation op in job.operations)
                    {
                        string code=(op.op??"").ToUpperInvariant();
                        if(code=="SET_PROPERTY" || code=="ADD_NOTE")
                            rr.Add(new Resolved{op=op});
                        else
                            rr.Add(Resolve(op,byName));
                    }
                    R.operations_resolved=rr.Count;

                    foreach(Resolved x in rr)
                    {
                        Apply(doc,x,R);
                        R.operations_applied++;
                    }

                    doc.EditRebuild3();
                    doc.GraphicsRedraw2();

                    int se=0,swarn=0;
                    bool ok=doc.Save3((int)swSaveAsOptions_e.swSaveAsOptions_Silent,ref se,ref swarn);
                    if(!ok || se!=0) throw new Exception("CANDIDATE_SAVE_FAILED e="+se+" w="+swarn);

                    SaveAs(doc,pdf);
                    SaveAs(doc,dxf);
                    doc.ViewZoomtofit2();
                    bool bmpOk=doc.SaveBMP(bmp,1800,1273);
                    if(!bmpOk) Console.WriteLine("BMP_SAVE=HOLD_NONBLOCKING");
                }
                finally
                {
                    try { ses.App.CloseDoc(doc.GetTitle()); } catch {}
                }
            }
        }

        static void ValidateJob(Job j)
        {
            if(j==null) throw new Exception("JOB_NULL");
            if(j.schema!="k01.drawing_annotate_existing.job.v1")
                throw new Exception("JOB_SCHEMA_INVALID");
            if(String.IsNullOrWhiteSpace(j.source_drawing) || !File.Exists(j.source_drawing))
                throw new Exception("SOURCE_DRAWING_MISSING");
            if(String.IsNullOrWhiteSpace(j.candidate_root))
                throw new Exception("CANDIDATE_ROOT_MISSING");
            if(j.operations==null || j.operations.Count==0)
                throw new Exception("NO_OPERATIONS");
        }

        static T Load<T>(string p)
        {
            JavaScriptSerializer js=new JavaScriptSerializer();
            js.MaxJsonLength=Int32.MaxValue;
            return js.Deserialize<T>(File.ReadAllText(p));
        }

        static List<Tuple<Annotation,string>> InventoryAnnotations(
            DrawingDoc dr,out Dictionary<string,List<Tuple<Annotation,string>>> byName)
        {
            List<Tuple<Annotation,string>> all=new List<Tuple<Annotation,string>>();
            byName=new Dictionary<string,List<Tuple<Annotation,string>>>(StringComparer.OrdinalIgnoreCase);

            View v=dr.GetFirstView() as View;
            int vg=0;
            while(v!=null && vg++<500)
            {
                string vn=""; try { vn=v.Name??""; } catch {}
                Annotation a=null; try { a=v.GetFirstAnnotation3() as Annotation; } catch {}
                int ag=0;
                while(a!=null && ag++<10000)
                {
                    var t=Tuple.Create(a,vn);
                    all.Add(t);
                    string n=AnnName(a);
                    if(!String.IsNullOrWhiteSpace(n))
                    {
                        if(!byName.ContainsKey(n))
                            byName[n]=new List<Tuple<Annotation,string>>();
                        byName[n].Add(t);
                    }
                    try { a=a.GetNext3() as Annotation; } catch { a=null; }
                }
                v=v.GetNextView() as View;
            }
            return all;
        }

        static Resolved Resolve(Operation op,Dictionary<string,List<Tuple<Annotation,string>>> byName)
        {
            if(op==null || String.IsNullOrWhiteSpace(op.id) || String.IsNullOrWhiteSpace(op.op))
                throw new Exception("Invalid operation record.");
            if(op.target==null || String.IsNullOrWhiteSpace(op.target.annotation_name))
                throw new Exception(op.id+": TARGET_ANNOTATION_NAME_MISSING");

            List<Tuple<Annotation,string>> hits;
            if(!byName.TryGetValue(op.target.annotation_name,out hits))
                throw new Exception(op.id+": ANNOTATION_NOT_FOUND "+op.target.annotation_name);
            if(hits.Count!=1)
                throw new Exception(op.id+": ANNOTATION_MATCH_COUNT="+hits.Count);

            Annotation ann=hits[0].Item1;
            object sp=ann.GetSpecificAnnotation();
            Resolved r=new Resolved{op=op,ann=ann,view=hits[0].Item2};
            r.dd=sp as DisplayDimension;
            r.note=sp as Note;
            if(r.dd!=null) r.dim=r.dd.GetDimension2(0) as Dimension;

            string code=(op.op??"").ToUpperInvariant();
            if((code=="SET_FIT" || code=="SET_SYM_TOL" || code=="SET_ASYM_TEXT" ||
                code=="SET_DIM_TEXT" || code=="SET_PRECISION") &&
               (r.dd==null || r.dim==null))
                throw new Exception(op.id+": operation requires DisplayDimension.");

            if(code=="SET_NOTE" && r.note==null)
                throw new Exception(op.id+": operation requires Note.");

            return r;
        }

        static void Apply(ModelDoc2 doc,Resolved r,Report R)
        {
            Operation op=r.op;
            string code=(op.op??"").ToUpperInvariant();

            if(code=="SET_FIT")
            {
                string before=TolText(r.dim);
                DimensionTolerance t=r.dim.Tolerance;
                if(t==null) throw new Exception(op.id+": tolerance object missing.");
                t.Type=(int)swTolType_e.swTolFIT;
                bool ok=t.SetFitValues(op.hole_fit??"",op.shaft_fit??"");
                if(!ok) throw new Exception(op.id+": SetFitValues failed.");
                if(op.precision.HasValue) SetPrecision(r.dd,op.precision.Value,op.id);
                Add(R,op.id,code,op.target.annotation_name,before,TolText(r.dim));
            }
            else if(code=="SET_SYM_TOL")
            {
                if(!op.sym_tol_mm.HasValue) throw new Exception(op.id+": sym_tol_mm missing.");
                string before=TolText(r.dim);
                DimensionTolerance t=r.dim.Tolerance;
                if(t==null) throw new Exception(op.id+": tolerance object missing.");
                double v=op.sym_tol_mm.Value*MM;
                t.Type=(int)swTolType_e.swTolSYMMETRIC;
                bool ok=t.SetValues2(-v,v,
                    (int)swSetValueInConfiguration_e.swSetValue_InThisConfiguration,null);
                if(!ok)
                    ok=t.SetValues2(-v,v,
                        (int)swSetValueInConfiguration_e.swSetValue_InAllConfigurations,null);
                if(!ok) throw new Exception(op.id+": SetValues2 failed.");
                if(op.precision.HasValue) SetPrecision(r.dd,op.precision.Value,op.id);
                Add(R,op.id,code,op.target.annotation_name,before,TolText(r.dim));
            }
            else if(code=="SET_ASYM_TEXT")
            {
                if(!op.lower_tol_mm.HasValue || !op.upper_tol_mm.HasValue)
                    throw new Exception(op.id+": asymmetric tolerance missing.");
                string before=DimText(r.dd);
                try { r.dim.Tolerance.Type=(int)swTolType_e.swTolNONE; } catch {}
                string suffix=" +"+F(op.upper_tol_mm.Value)+"/"+F(op.lower_tol_mm.Value)+(op.suffix??"");
                r.dd.SetText((int)swDimensionTextParts_e.swDimensionTextSuffix,suffix);
                if(!String.IsNullOrWhiteSpace(op.prefix))
                    r.dd.SetText((int)swDimensionTextParts_e.swDimensionTextPrefix,op.prefix);
                if(op.precision.HasValue) SetPrecision(r.dd,op.precision.Value,op.id);
                Add(R,op.id,code,op.target.annotation_name,before,DimText(r.dd));
            }
            else if(code=="SET_DIM_TEXT")
            {
                string before=DimText(r.dd);
                if(op.prefix!=null)
                    r.dd.SetText((int)swDimensionTextParts_e.swDimensionTextPrefix,op.prefix);
                if(op.suffix!=null)
                    r.dd.SetText((int)swDimensionTextParts_e.swDimensionTextSuffix,op.suffix);
                if(op.precision.HasValue) SetPrecision(r.dd,op.precision.Value,op.id);
                Add(R,op.id,code,op.target.annotation_name,before,DimText(r.dd));
            }
            else if(code=="SET_PRECISION")
            {
                if(!op.precision.HasValue) throw new Exception(op.id+": precision missing.");
                int before=-999; try { before=r.dd.GetPrimaryPrecision2(); } catch {}
                SetPrecision(r.dd,op.precision.Value,op.id);
                Add(R,op.id,code,op.target.annotation_name,before.ToString(),op.precision.Value.ToString());
            }
            else if(code=="SET_NOTE")
            {
                string before=r.note.GetText()??"";
                bool ok=r.note.SetText(op.text??"");
                if(!ok) throw new Exception(op.id+": Note.SetText failed.");
                if(op.x_m.HasValue && op.y_m.HasValue)
                    r.ann.SetPosition(op.x_m.Value,op.y_m.Value,0);
                Add(R,op.id,code,op.target.annotation_name,One(before),One(r.note.GetText()??""));
            }
            else if(code=="ADD_NOTE")
            {
                Note n=doc.InsertNote(op.text??"") as Note;
                if(n==null) throw new Exception(op.id+": InsertNote failed.");
                Annotation a=n.GetAnnotation() as Annotation;
                if(a!=null)
                {
                    if(op.x_m.HasValue && op.y_m.HasValue)
                        a.SetPosition(op.x_m.Value,op.y_m.Value,0);
                    try { a.SetName("K01AE_"+op.id); } catch {}
                }
                try { n.SetName("K01AE_"+op.id); } catch {}
                Add(R,op.id,code,"<new>","",One(op.text??""));
            }
            else if(code=="SET_PROPERTY")
            {
                if(String.IsNullOrWhiteSpace(op.property_name))
                    throw new Exception(op.id+": property_name missing.");
                CustomPropertyManager c=doc.Extension.get_CustomPropertyManager("");
                string before="";
                try { string rv="",ev=""; bool was=false; c.Get5(op.property_name,false,out rv,out ev,out was); before=rv??""; } catch {}
                try { c.Delete2(op.property_name); } catch {}
                int rc=c.Add(op.property_name,"Text",op.property_value??"");
                if(rc==0) try { c.Set2(op.property_name,op.property_value??""); } catch {}
                Add(R,op.id,code,op.property_name,One(before),One(op.property_value??""));
            }
            else
            {
                throw new Exception(op.id+": unsupported operation "+op.op);
            }
        }

        static void SetPrecision(DisplayDimension dd,int p,string id)
        {
            int rc=dd.SetPrecision2(p,-1,p,-1);
            if(rc<0) throw new Exception(id+": SetPrecision2 failed rc="+rc);
        }

        static void SaveAs(ModelDoc2 doc,string path)
        {
            int e=0,w=0;
            bool ok=doc.Extension.SaveAs(path,
                (int)swSaveAsVersion_e.swSaveAsCurrentVersion,
                (int)swSaveAsOptions_e.swSaveAsOptions_Silent,
                null,ref e,ref w);
            if(!ok || e!=0) throw new Exception("SAVE_AS_FAILED "+path+" e="+e+" w="+w);
        }

        static string TolText(Dimension d)
        {
            if(d==null) return "";
            DimensionTolerance t=d.Tolerance;
            if(t==null) return F(d.SystemValue/MM)+" tol=null";
            double mn=0,mx=0; int sm=-999,sx=-999;
            try { sm=t.GetMinValue2(out mn); } catch {}
            try { sx=t.GetMaxValue2(out mx); } catch {}
            return F(d.SystemValue/MM)+" type="+t.Type+" min="+F(mn/MM)+" max="+F(mx/MM)+" status="+sm+"/"+sx;
        }

        static string DimText(DisplayDimension dd)
        {
            if(dd==null) return "";
            string p="",s="";
            try { p=dd.GetText((int)swDimensionTextParts_e.swDimensionTextPrefix)??""; } catch {}
            try { s=dd.GetText((int)swDimensionTextParts_e.swDimensionTextSuffix)??""; } catch {}
            return "prefix="+One(p)+" suffix="+One(s);
        }

        static string AnnName(Annotation a)
        {
            try { return a.GetName()??""; } catch { return ""; }
        }

        static T Load<T>(string p)
        {
            JavaScriptSerializer js=new JavaScriptSerializer();
            js.MaxJsonLength=Int32.MaxValue;
            return js.Deserialize<T>(File.ReadAllText(p));
        }

        static void Add(Report R,string id,string op,string target,string before,string after)
        {
            R.changes.Add(new Change{id=id,op=op,target=target,before=before,after=after,status="PASS"});
            Console.WriteLine("CHANGE "+id+" "+op+" target="+target);
        }

        static void SaveReport(string dir,Report r)
        {
            JavaScriptSerializer js=new JavaScriptSerializer();
            js.MaxJsonLength=Int32.MaxValue;
            File.WriteAllText(Path.Combine(dir,"K01_DRAWING_ANNOTATE_EXISTING_CURRENT.json"),
                js.Serialize(r),new UTF8Encoding(true));

            StringBuilder b=new StringBuilder();
            b.AppendLine("STATUS="+r.status);
            b.AppendLine("DRAWING_ID="+r.drawing_id);
            b.AppendLine("ATTEMPTS="+r.attempts);
            b.AppendLine("SOURCE_DRAWING="+r.source_drawing);
            b.AppendLine("CANDIDATE="+r.candidate_drawing);
            b.AppendLine("PDF="+r.output_pdf);
            b.AppendLine("DXF="+r.output_dxf);
            b.AppendLine("OPERATIONS="+r.operations_applied+"/"+r.operations_requested);
            foreach(Change c in r.changes)
                b.AppendLine("CHANGE="+c.id+"|"+c.op+"|"+c.target+"|"+One(c.before)+"|"+One(c.after));
            if(!String.IsNullOrWhiteSpace(r.error)) b.AppendLine("ERROR="+One(r.error));
            File.WriteAllText(Path.Combine(dir,"K01_DRAWING_ANNOTATE_EXISTING_CURRENT.txt"),
                b.ToString(),new UTF8Encoding(true));
        }

        static string One(string s){return (s??"").Replace("\r"," ").Replace("\n"," ");}
        static string F(double x){return x.ToString("0.###",CultureInfo.InvariantCulture);}
    }
}
