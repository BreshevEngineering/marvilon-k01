using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using System.Web.Script.Serialization;
using SolidWorks.Interop.sldworks;
using SolidWorks.Interop.swconst;
using K01Sw2018Runtime;

namespace K01DrawingRefineApi
{
    public class Signature
    {
        public Nullable<double> nominal_mm;
        public Nullable<double> tol_min_mm;
        public Nullable<double> tol_max_mm;
        public string view_contains;
    }

    public class Target
    {
        public string annotation_name;
        public Signature signature;
    }

    public class Operation
    {
        public string id;
        public string op;
        public Target target;
        public Nullable<double> tol_min_mm;
        public Nullable<double> tol_max_mm;
        public Nullable<int> precision;
        public Nullable<bool> visible;
        public string text;
        public string hole_fit;
        public string shaft_fit;
        public string prefix;
        public string suffix;
        public double[] position_m;
    }

    public class Job
    {
        public string schema;
        public string drawing_id;
        public string source_drawing;
        public string source_model;
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
        public string schema="k01.drawing_refine_api.report.v1";
        public string status="HOLD";
        public string sw_revision="";
        public bool attached_to_existing_sw=false;
        public string drawing_id="";
        public string source_drawing="";
        public string source_model="";
        public string candidate_drawing="";
        public string output_pdf="";
        public string output_dxf="";
        public string source_drawing_sha_before="";
        public string source_drawing_sha_after="";
        public string source_model_sha_before="";
        public string source_model_sha_after="";
        public string candidate_sha="";
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
            Report R=new Report();

            try
            {
                Job job=Load<Job>(jobPath);
                ValidateJob(job);
                R.drawing_id=job.drawing_id;
                R.source_drawing=job.source_drawing;
                R.source_model=job.source_model;
                R.operations_requested=job.operations.Count;

                R.source_drawing_sha_before=SwSession.Sha256File(job.source_drawing);
                R.source_model_sha_before=SwSession.Sha256File(job.source_model);

                string stamp=DateTime.Now.ToString("yyyyMMdd_HHmmss");
                string candDir=Path.Combine(job.candidate_root,stamp);
                Directory.CreateDirectory(candDir);
                string candidate=Path.Combine(candDir,
                    Path.GetFileNameWithoutExtension(job.source_drawing)+"_REFINED_CANDIDATE.SLDDRW");
                R.candidate_drawing=candidate;
                R.output_pdf=Path.ChangeExtension(candidate,"PDF");
                R.output_dxf=Path.ChangeExtension(candidate,"DXF");

                using(SwSession ses=SwSession.ConnectOrStart(true))
                {
                    R.sw_revision=ses.Revision;
                    R.attached_to_existing_sw=!ses.OwnsInstance;

                    ses.RequireTargetClosed(job.source_drawing,"SOURCE_DRAWING");
                    File.Copy(job.source_drawing,candidate,false);

                    int e=0,w=0;
                    ModelDoc2 doc=ses.App.OpenDoc6(candidate,(int)swDocumentTypes_e.swDocDRAWING,
                        (int)swOpenDocOptions_e.swOpenDocOptions_Silent,"",ref e,ref w) as ModelDoc2;
                    if(doc==null) throw new Exception("Candidate open failed e="+e+" w="+w);
                    DrawingDoc dr=doc as DrawingDoc;
                    if(dr==null) throw new Exception("Candidate is not DrawingDoc.");

                    try
                    {
                        Dictionary<string,List<Tuple<Annotation,string>>> byName;
                        List<Tuple<Annotation,string>> anns=InventoryAnnotations(dr,out byName);
                        R.annotations_inventory=anns.Count;

                        List<Resolved> rr=new List<Resolved>();
                        foreach(Operation op in job.operations)
                            rr.Add(Resolve(op,anns,byName));
                        R.operations_resolved=rr.Count;
                        Console.WriteLine("PREFLIGHT_TARGETS_RESOLVED="+R.operations_resolved);

                        foreach(Resolved x in rr)
                        {
                            Apply(x,R);
                            R.operations_applied++;
                        }

                        doc.EditRebuild3();
                        doc.GraphicsRedraw2();

                        int se=0,swarn=0;
                        bool saved=doc.Save3((int)swSaveAsOptions_e.swSaveAsOptions_Silent,ref se,ref swarn);
                        if(!saved || se!=0) throw new Exception("Candidate Save3 failed errors="+se+" warnings="+swarn);
                        Console.WriteLine("CANDIDATE_SAVE=PASS warnings="+swarn);

                        SaveAs(doc,R.output_pdf);
                        SaveAs(doc,R.output_dxf);
                        Console.WriteLine("EXPORT_PDF=PASS path="+R.output_pdf);
                        Console.WriteLine("EXPORT_DXF=PASS path="+R.output_dxf);
                    }
                    finally
                    {
                        string title=doc.GetTitle();
                        ses.App.CloseDoc(title);
                    }
                }

                R.candidate_sha=SwSession.Sha256AfterClose(R.candidate_drawing);
                R.source_drawing_sha_after=SwSession.Sha256AfterClose(job.source_drawing);
                R.source_model_sha_after=SwSession.Sha256AfterClose(job.source_model);

                if(R.source_drawing_sha_before!=R.source_drawing_sha_after)
                    throw new Exception("SOURCE_DRAWING_INVARIANCE_FAILED");
                if(R.source_model_sha_before!=R.source_model_sha_after)
                    throw new Exception("SOURCE_MODEL_INVARIANCE_FAILED");

                R.status="PASS_DRAWING_REFINE_EXECUTION__SEMANTIC_QA_REQUIRED";
                SaveReport(reportDir,R);
                Console.WriteLine("STATUS="+R.status);
                Console.WriteLine("SOURCE_DRAWING_INVARIANCE=PASS");
                Console.WriteLine("SOURCE_MODEL_INVARIANCE=PASS");
                Console.WriteLine("CANDIDATE="+R.candidate_drawing);
                Console.WriteLine("PDF="+R.output_pdf);
                Console.WriteLine("DXF="+R.output_dxf);
                Console.WriteLine("CANDIDATE_SHA="+R.candidate_sha);
                return 0;
            }
            catch(Exception ex)
            {
                R.status="HOLD_DRAWING_REFINE_API";
                R.error=ex.ToString();
                try { SaveReport(reportDir,R); } catch {}
                Console.WriteLine("STATUS="+R.status);
                Console.WriteLine("ERROR="+ex.Message);
                return 2;
            }
        }

        static void ValidateJob(Job j)
        {
            if(j==null) throw new Exception("JOB_NULL");
            if(String.IsNullOrWhiteSpace(j.source_drawing) || !File.Exists(j.source_drawing))
                throw new Exception("SOURCE_DRAWING_MISSING");
            if(String.IsNullOrWhiteSpace(j.source_model) || !File.Exists(j.source_model))
                throw new Exception("SOURCE_MODEL_MISSING");
            if(String.IsNullOrWhiteSpace(j.candidate_root))
                throw new Exception("CANDIDATE_ROOT_MISSING");
            if(j.operations==null || j.operations.Count==0)
                throw new Exception("NO_OPERATIONS");
        }

        static T Load<T>(string p)
        {
            JavaScriptSerializer js=new JavaScriptSerializer(); js.MaxJsonLength=Int32.MaxValue;
            return js.Deserialize<T>(File.ReadAllText(p));
        }

        static List<Tuple<Annotation,string>> InventoryAnnotations(
            DrawingDoc dr,out Dictionary<string,List<Tuple<Annotation,string>>> byName)
        {
            List<Tuple<Annotation,string>> all=new List<Tuple<Annotation,string>>();
            byName=new Dictionary<string,List<Tuple<Annotation,string>>>(StringComparer.OrdinalIgnoreCase);

            View v=dr.GetFirstView() as View; int vg=0;
            while(v!=null && vg++<500)
            {
                string vn=""; try { vn=v.Name??""; } catch {}
                Annotation a=null;
                try { a=v.GetFirstAnnotation3() as Annotation; } catch { a=null; }
                int ag=0;
                while(a!=null && ag++<10000)
                {
                    var t=Tuple.Create(a,vn); all.Add(t);
                    string n=AnnName(a);
                    if(!String.IsNullOrWhiteSpace(n))
                    {
                        if(!byName.ContainsKey(n)) byName[n]=new List<Tuple<Annotation,string>>();
                        byName[n].Add(t);
                    }
                    try { a=a.GetNext3() as Annotation; } catch { a=null; }
                }
                v=v.GetNextView() as View;
            }
            return all;
        }

        static Resolved Resolve(Operation op,
            List<Tuple<Annotation,string>> all,
            Dictionary<string,List<Tuple<Annotation,string>>> byName)
        {
            if(op==null || String.IsNullOrWhiteSpace(op.id) || String.IsNullOrWhiteSpace(op.op))
                throw new Exception("Invalid operation record.");
            if(op.target==null) throw new Exception(op.id+": target missing.");

            List<Tuple<Annotation,string>> hits=new List<Tuple<Annotation,string>>();

            if(!String.IsNullOrWhiteSpace(op.target.annotation_name))
            {
                List<Tuple<Annotation,string>> named;
                if(byName.TryGetValue(op.target.annotation_name,out named)) hits.AddRange(named);
            }
            else if(op.target.signature!=null)
            {
                Signature s=op.target.signature;
                foreach(var t in all)
                {
                    Annotation a=t.Item1;
                    if(!String.IsNullOrWhiteSpace(s.view_contains) &&
                       (t.Item2??"").IndexOf(s.view_contains,StringComparison.OrdinalIgnoreCase)<0) continue;
                    DisplayDimension dd=a.GetSpecificAnnotation() as DisplayDimension;
                    if(dd==null) continue;
                    Dimension d=dd.GetDimension2(0) as Dimension; if(d==null) continue;

                    if(s.nominal_mm.HasValue &&
                       Math.Abs(d.SystemValue/MM-s.nominal_mm.Value)>0.003) continue;

                    if(s.tol_min_mm.HasValue || s.tol_max_mm.HasValue)
                    {
                        DimensionTolerance tol=d.Tolerance; if(tol==null) continue;
                        double mn=0,mx=0; int sm=-999,sx=-999;
                        try { sm=tol.GetMinValue2(out mn); } catch {}
                        try { sx=tol.GetMaxValue2(out mx); } catch {}
                        if(sm!=0 || sx!=0) continue;
                        if(s.tol_min_mm.HasValue && Math.Abs(mn/MM-s.tol_min_mm.Value)>0.002) continue;
                        if(s.tol_max_mm.HasValue && Math.Abs(mx/MM-s.tol_max_mm.Value)>0.002) continue;
                    }
                    hits.Add(t);
                }
            }

            if(hits.Count!=1)
                throw new Exception(op.id+": target resolution count="+hits.Count+"; expected exactly 1.");

            Annotation ann=hits[0].Item1;
            object sp=ann.GetSpecificAnnotation();
            Resolved r=new Resolved{op=op,ann=ann,view=hits[0].Item2};
            r.dd=sp as DisplayDimension;
            r.note=sp as Note;
            if(r.dd!=null) r.dim=r.dd.GetDimension2(0) as Dimension;

            string code=(op.op??"").ToUpperInvariant();
            if((code=="SET_TOLERANCE" || code=="CLEAR_TOLERANCE" || code=="SET_PRECISION" ||
                code=="SET_FIT" || code=="SET_ASYM_PRESENTATION" || code=="SET_DIM_TEXT") &&
               (r.dd==null || r.dim==null))
                throw new Exception(op.id+": operation requires DisplayDimension.");
            if(code=="SET_NOTE" && r.note==null)
                throw new Exception(op.id+": SET_NOTE requires Note.");

            return r;
        }

        static void Apply(Resolved r,Report R)
        {
            string code=(r.op.op??"").ToUpperInvariant();
            string target=!String.IsNullOrWhiteSpace(r.op.target.annotation_name)
                ? r.op.target.annotation_name : ("signature@"+r.view);

            if(code=="SET_TOLERANCE")
            {
                if(!r.op.tol_min_mm.HasValue || !r.op.tol_max_mm.HasValue)
                    throw new Exception(r.op.id+": tolerance values missing.");
                DimensionTolerance t=r.dim.Tolerance;
                if(t==null) throw new Exception(r.op.id+": tolerance object missing.");
                string before=TolText(r.dim);
                t.Type=(int)swTolType_e.swTolBILAT;
                bool ok=t.SetValues2(r.op.tol_min_mm.Value*MM,r.op.tol_max_mm.Value*MM,
                    r.op.precision.HasValue?r.op.precision.Value:2,null);
                if(!ok) throw new Exception(r.op.id+": SetValues2 failed.");
                if(r.op.precision.HasValue)
                {
                    int rc=r.dd.SetPrecision2(r.op.precision.Value,-1,r.op.precision.Value,-1);
                    if(rc<0) throw new Exception(r.op.id+": SetPrecision2 failed rc="+rc);
                }
                Add(R,r.op.id,code,target,before,TolText(r.dim));
            }
            else if(code=="CLEAR_TOLERANCE")
            {
                DimensionTolerance t=r.dim.Tolerance;
                if(t==null) throw new Exception(r.op.id+": tolerance object missing.");
                string before=TolText(r.dim);
                t.Type=(int)swTolType_e.swTolNONE;
                if(r.op.precision.HasValue)
                {
                    int rc=r.dd.SetPrecision2(r.op.precision.Value,-1,r.op.precision.Value,-1);
                    if(rc<0) throw new Exception(r.op.id+": SetPrecision2 failed rc="+rc);
                }
                Add(R,r.op.id,code,target,before,TolText(r.dim));
            }
            else if(code=="SET_FIT")
            {
                if(String.IsNullOrWhiteSpace(r.op.hole_fit) && String.IsNullOrWhiteSpace(r.op.shaft_fit))
                    throw new Exception(r.op.id+": fit designation missing.");
                string before=TolText(r.dim);
                DimensionTolerance t=r.dim.Tolerance;
                if(t==null) throw new Exception(r.op.id+": tolerance object missing.");
                t.Type=(int)swTolType_e.swTolFIT;
                bool ok=t.SetFitValues(r.op.hole_fit??"",r.op.shaft_fit??"");
                if(!ok) throw new Exception(r.op.id+": SetFitValues failed.");
                if(r.op.precision.HasValue) SetDimPrecision(r.dd,r.op.precision.Value,r.op.id);
                Add(R,r.op.id,code,target,before,TolText(r.dim));
            }
            else if(code=="SET_ASYM_PRESENTATION")
            {
                if(!r.op.tol_min_mm.HasValue || !r.op.tol_max_mm.HasValue)
                    throw new Exception(r.op.id+": tolerance values missing.");
                string before=DimText(r.dd);
                try
                {
                    DimensionTolerance t=r.dim.Tolerance;
                    if(t!=null) t.Type=(int)swTolType_e.swTolNONE;
                }
                catch {}
                string suffix=" +"+F(r.op.tol_max_mm.Value)+"/"+F(r.op.tol_min_mm.Value)+(r.op.suffix??"");
                r.dd.SetText((int)swDimensionTextParts_e.swDimensionTextSuffix,suffix);
                if(!String.IsNullOrWhiteSpace(r.op.prefix))
                    r.dd.SetText((int)swDimensionTextParts_e.swDimensionTextPrefix,r.op.prefix);
                if(r.op.precision.HasValue) SetDimPrecision(r.dd,r.op.precision.Value,r.op.id);
                Add(R,r.op.id,code,target,before,DimText(r.dd));
            }
            else if(code=="SET_DIM_TEXT")
            {
                string before=DimText(r.dd);
                if(r.op.prefix!=null)
                    r.dd.SetText((int)swDimensionTextParts_e.swDimensionTextPrefix,r.op.prefix);
                if(r.op.suffix!=null)
                    r.dd.SetText((int)swDimensionTextParts_e.swDimensionTextSuffix,r.op.suffix);
                if(r.op.precision.HasValue) SetDimPrecision(r.dd,r.op.precision.Value,r.op.id);
                Add(R,r.op.id,code,target,before,DimText(r.dd));
            }
            else if(code=="SET_PRECISION")
            {
                if(!r.op.precision.HasValue) throw new Exception(r.op.id+": precision missing.");
                int before=-999; try { before=r.dd.GetPrimaryPrecision2(); } catch {}
                SetDimPrecision(r.dd,r.op.precision.Value,r.op.id);
                Add(R,r.op.id,code,target,before.ToString(),r.op.precision.Value.ToString());
            }
            else if(code=="SET_VISIBLE")
            {
                if(!r.op.visible.HasValue) throw new Exception(r.op.id+": visible missing.");
                int before=r.ann.Visible;
                r.ann.Visible=r.op.visible.Value
                    ? (int)swAnnotationVisibilityState_e.swAnnotationVisible
                    : (int)swAnnotationVisibilityState_e.swAnnotationHidden;
                Add(R,r.op.id,code,target,before.ToString(),r.ann.Visible.ToString());
            }
            else if(code=="SET_NOTE")
            {
                string before=r.note.GetText()??"";
                if(r.op.text!=null)
                {
                    bool ok=r.note.SetText(r.op.text);
                    if(!ok) throw new Exception(r.op.id+": Note.SetText failed.");
                }
                if(r.op.visible.HasValue)
                    r.ann.Visible=r.op.visible.Value
                        ? (int)swAnnotationVisibilityState_e.swAnnotationVisible
                        : (int)swAnnotationVisibilityState_e.swAnnotationHidden;
                if(r.op.position_m!=null && r.op.position_m.Length>=2)
                {
                    double z=r.op.position_m.Length>2?r.op.position_m[2]:0.0;
                    bool ok=r.ann.SetPosition(r.op.position_m[0],r.op.position_m[1],z);
                    if(!ok) throw new Exception(r.op.id+": Annotation.SetPosition failed.");
                }
                Add(R,r.op.id,code,target,One(before),One(r.note.GetText()??""));
            }
            else
                throw new Exception(r.op.id+": unsupported operation "+r.op.op);
        }

        static void SetDimPrecision(DisplayDimension dd,int p,string id)
        {
            int rc=dd.SetPrecision2(p,-1,p,-1);
            if(rc<0) throw new Exception(id+": SetPrecision2 failed rc="+rc);
        }

        static string DimText(DisplayDimension dd)
        {
            if(dd==null) return "";
            string p="",s="";
            try { p=dd.GetText((int)swDimensionTextParts_e.swDimensionTextPrefix)??""; } catch {}
            try { s=dd.GetText((int)swDimensionTextParts_e.swDimensionTextSuffix)??""; } catch {}
            return "prefix="+One(p)+" suffix="+One(s);
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

        static void Add(Report R,string id,string op,string target,string before,string after)
        {
            R.changes.Add(new Change{id=id,op=op,target=target,before=before,after=after,status="PASS"});
            Console.WriteLine("CHANGE "+id+" "+op+" target="+target);
        }

        static string TolText(Dimension d)
        {
            if(d==null) return "";
            DimensionTolerance t=d.Tolerance;
            if(t==null) return F(d.SystemValue/MM)+" tol=null";
            double mn=0,mx=0; int sm=-999,sx=-999;
            try { sm=t.GetMinValue2(out mn); } catch {}
            try { sx=t.GetMaxValue2(out mx); } catch {}
            return F(d.SystemValue/MM)+" type="+t.Type+" min="+F(mn/MM)+" max="+F(mx/MM)+
                " status="+sm+"/"+sx;
        }

        static object[] ToObjects(object v)
        {
            if(v==null) return new object[0];
            object[] a=v as object[]; if(a!=null) return a;
            Array ar=v as Array; if(ar==null) return new object[0];
            object[] r=new object[ar.Length];
            for(int i=0;i<ar.Length;i++) r[i]=ar.GetValue(i);
            return r;
        }

        static string AnnName(Annotation a)
        {
            try { return a.GetName()??""; } catch { return ""; }
        }

        static void SaveReport(string dir,Report r)
        {
            Directory.CreateDirectory(dir);
            JavaScriptSerializer js=new JavaScriptSerializer(); js.MaxJsonLength=Int32.MaxValue;
            File.WriteAllText(Path.Combine(dir,"K01_DRAWING_REFINE_API_CURRENT.json"),
                js.Serialize(r),new UTF8Encoding(true));

            StringBuilder b=new StringBuilder();
            b.AppendLine("STATUS="+r.status);
            b.AppendLine("SW_REVISION="+r.sw_revision);
            b.AppendLine("ATTACHED_TO_EXISTING_SW="+r.attached_to_existing_sw);
            b.AppendLine("DRAWING_ID="+r.drawing_id);
            b.AppendLine("SOURCE_DRAWING="+r.source_drawing);
            b.AppendLine("CANDIDATE_DRAWING="+r.candidate_drawing);
            b.AppendLine("OUTPUT_PDF="+r.output_pdf);
            b.AppendLine("OUTPUT_DXF="+r.output_dxf);
            b.AppendLine("ANNOTATIONS_INVENTORY="+r.annotations_inventory);
            b.AppendLine("OPERATIONS_REQUESTED="+r.operations_requested);
            b.AppendLine("OPERATIONS_RESOLVED="+r.operations_resolved);
            b.AppendLine("OPERATIONS_APPLIED="+r.operations_applied);
            foreach(Change c in r.changes)
                b.AppendLine("CHANGE="+c.id+"|"+c.op+"|"+c.target+"|"+One(c.before)+"|"+One(c.after));
            if(!String.IsNullOrWhiteSpace(r.error)) b.AppendLine("ERROR="+One(r.error));
            File.WriteAllText(Path.Combine(dir,"K01_DRAWING_REFINE_API_CURRENT.txt"),
                b.ToString(),new UTF8Encoding(true));
        }

        static string One(string s){return (s??"").Replace("\r"," ").Replace("\n"," ");}
        static string F(double x){return x.ToString("0.######",CultureInfo.InvariantCulture);}
    }
}
