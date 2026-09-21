using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using System.Web.Script.Serialization;
using SolidWorks.Interop.sldworks;
using SolidWorks.Interop.swconst;
using K01Sw2018Runtime;

namespace K01DrawingNativeAttachmentQaV1
{
    public class ObservedEntity
    {
        public int attached_type;
        public string attached_type_name="";
        public bool object_present=false;
        public List<double> cylinder_diameters_mm=new List<double>();
        public List<double> cylinder_center_x_mm=new List<double>();
        public string error="";
    }

    public class AnnotationRecord
    {
        public string view_name="";
        public string referenced_model_path="";
        public string annotation_name="";
        public int attachment_count=0;
        public bool dangling=false;
        public List<ObservedEntity> entities=new List<ObservedEntity>();
    }

    public class InventoryReport
    {
        public string schema="k01.drawing_native_attachment_inventory.v1";
        public string status="HOLD";
        public string drawing_path="";
        public string drawing_sha_before="";
        public string drawing_sha_after="";
        public string sw_revision="";
        public bool attached_to_existing_sw=false;
        public int view_count=0;
        public int annotation_count=0;
        public int named_annotation_count=0;
        public int attached_annotation_count=0;
        public int dangling_annotation_count=0;
        public List<AnnotationRecord> annotations=new List<AnnotationRecord>();
        public string error="";
    }

    public class ExpectedSignature
    {
        public string kind;
        public Nullable<double> diameter_mm;
        public Nullable<double> diameter_tolerance_mm;
        public Nullable<double> center_x_mm;
        public Nullable<double> center_x_tolerance_mm;
    }

    public class Check
    {
        public string id;
        public string annotation_name;
        public string expected_view;
        public string expected_model_path;
        public bool required=true;
        public ExpectedSignature expected_signature;
    }

    public class VerifyJob
    {
        public string schema;
        public string drawing_id;
        public string source_drawing;
        public List<Check> checks;
    }

    public class CheckResult
    {
        public string id="";
        public string annotation_name="";
        public bool required=false;
        public string status="HOLD";
        public string view_name="";
        public string referenced_model_path="";
        public string error="";
        public AnnotationRecord observed;
    }

    public class VerifyReport
    {
        public string schema="k01.drawing_native_attachment_verify.v1";
        public string status="HOLD_NATIVE_ATTACHMENT_QA";
        public string drawing_id="";
        public string source_drawing="";
        public string source_drawing_sha_before="";
        public string source_drawing_sha_after="";
        public int required_checks=0;
        public int required_passed=0;
        public List<CheckResult> checks=new List<CheckResult>();
        public string error="";
    }

    public static class Program
    {
        public static int Main(string[] args)
        {
            if(args.Length==1 && args[0]=="--runtime-probe")
            {
                Console.WriteLine("RUNTIME_PROBE=PASS");
                Console.WriteLine("SLDWORKS_ASSEMBLY="+typeof(SldWorks).Assembly.FullName);
                Console.WriteLine("SWCONST_ASSEMBLY="+typeof(swDocumentTypes_e).Assembly.FullName);
                return 0;
            }

            if(args.Length>=1 && args[0]=="--inventory")
            {
                if(args.Length<3)
                {
                    Console.WriteLine("Usage: exe --inventory <drawing.slddrw> <report_dir>");
                    return 2;
                }
                return RunInventory(args[1],args[2]);
            }

            if(args.Length>=1 && args[0]=="--verify")
            {
                if(args.Length<3)
                {
                    Console.WriteLine("Usage: exe --verify <job.json> <report_dir>");
                    return 2;
                }
                return RunVerify(args[1],args[2]);
            }

            Console.WriteLine("Usage:");
            Console.WriteLine("  exe --runtime-probe");
            Console.WriteLine("  exe --inventory <drawing.slddrw> <report_dir>");
            Console.WriteLine("  exe --verify <job.json> <report_dir>");
            return 2;
        }

        static int RunInventory(string drawingPath,string reportDir)
        {
            Directory.CreateDirectory(reportDir);
            InventoryReport R=new InventoryReport();
            R.drawing_path=Path.GetFullPath(drawingPath);
            SwSession ses=null;
            ModelDoc2 drawing=null;
            bool opened=false;

            try
            {
                Need(File.Exists(R.drawing_path),"DRAWING_MISSING: "+R.drawing_path);
                R.drawing_sha_before=SwSession.Sha256File(R.drawing_path);

                ses=SwSession.ConnectOrStart(false);
                R.sw_revision=ses.Revision;
                R.attached_to_existing_sw=!ses.OwnsInstance;
                ses.RequireTargetClosed(R.drawing_path,"SOURCE_DRAWING");

                int err=0,warn=0;
                drawing=ses.App.OpenDoc6(
                    R.drawing_path,
                    (int)swDocumentTypes_e.swDocDRAWING,
                    (int)(swOpenDocOptions_e.swOpenDocOptions_Silent|swOpenDocOptions_e.swOpenDocOptions_ReadOnly),
                    "",ref err,ref warn) as ModelDoc2;
                Need(drawing!=null,"DRAWING_OPEN_FAILED e="+err+" w="+warn);
                opened=true;

                DrawingDoc dr=drawing as DrawingDoc;
                Need(dr!=null,"NOT_A_DRAWING");

                View v=dr.GetFirstView() as View;
                int vg=0;
                while(v!=null && vg++<500)
                {
                    R.view_count++;
                    string viewName=SafeViewName(v);
                    string refPath=ReferencedModelPath(v);

                    Annotation a=null;
                    try { a=v.GetFirstAnnotation3() as Annotation; } catch {}
                    int ag=0;
                    while(a!=null && ag++<10000)
                    {
                        AnnotationRecord ar=InspectAnnotation(a,viewName,refPath);
                        R.annotations.Add(ar);
                        R.annotation_count++;
                        if(!String.IsNullOrWhiteSpace(ar.annotation_name)) R.named_annotation_count++;
                        if(ar.attachment_count>0) R.attached_annotation_count++;
                        if(ar.dangling) R.dangling_annotation_count++;
                        try { a=a.GetNext3() as Annotation; } catch { a=null; }
                    }

                    v=v.GetNextView() as View;
                }

                if(opened && drawing!=null)
                {
                    string title=drawing.GetTitle();
                    ses.App.CloseDoc(title);
                    drawing=null;
                    opened=false;
                }

                R.drawing_sha_after=SwSession.Sha256AfterClose(R.drawing_path);
                Need(R.drawing_sha_before==R.drawing_sha_after,"DRAWING_INVARIANCE_FAILED");

                R.status="PASS_NATIVE_ATTACHMENT_INVENTORY_V1";
                Save(reportDir,"K01_DRAWING_NATIVE_ATTACHMENT_INVENTORY_CURRENT.json",R);

                Console.WriteLine("STATUS="+R.status);
                Console.WriteLine("DRAWING="+R.drawing_path);
                Console.WriteLine("VIEWS="+R.view_count);
                Console.WriteLine("ANNOTATIONS="+R.annotation_count);
                Console.WriteLine("NAMED_ANNOTATIONS="+R.named_annotation_count);
                Console.WriteLine("ATTACHED_ANNOTATIONS="+R.attached_annotation_count);
                Console.WriteLine("DANGLING_ANNOTATIONS="+R.dangling_annotation_count);
                Console.WriteLine("SOURCE_DRAWING_INVARIANCE=PASS");
                Console.WriteLine("REPORT="+Path.Combine(reportDir,"K01_DRAWING_NATIVE_ATTACHMENT_INVENTORY_CURRENT.json"));
                return 0;
            }
            catch(Exception ex)
            {
                R.status="HOLD_NATIVE_ATTACHMENT_INVENTORY_V1";
                R.error=ex.ToString();
                try { Save(reportDir,"K01_DRAWING_NATIVE_ATTACHMENT_INVENTORY_CURRENT.json",R); } catch {}
                Console.WriteLine("STATUS="+R.status);
                Console.WriteLine("ERROR="+ex.Message);
                return 3;
            }
            finally
            {
                if(ses!=null)
                {
                    try { if(opened && drawing!=null) ses.App.CloseDoc(drawing.GetTitle()); } catch {}
                    ses.Dispose();
                }
            }
        }

        static int RunVerify(string jobPath,string reportDir)
        {
            Directory.CreateDirectory(reportDir);
            VerifyReport R=new VerifyReport();
            SwSession ses=null;
            ModelDoc2 drawing=null;
            bool opened=false;

            try
            {
                VerifyJob job=Load<VerifyJob>(jobPath);
                Need(job!=null && job.schema=="k01.drawing_native_attachment_verify.job.v1","JOB_SCHEMA_INVALID");
                Need(!String.IsNullOrWhiteSpace(job.source_drawing) && File.Exists(job.source_drawing),"SOURCE_DRAWING_MISSING");
                Need(job.checks!=null && job.checks.Count>0,"NO_CHECKS");

                R.drawing_id=job.drawing_id??"";
                R.source_drawing=Path.GetFullPath(job.source_drawing);
                R.source_drawing_sha_before=SwSession.Sha256File(R.source_drawing);

                ses=SwSession.ConnectOrStart(false);
                ses.RequireTargetClosed(R.source_drawing,"SOURCE_DRAWING");

                int err=0,warn=0;
                drawing=ses.App.OpenDoc6(
                    R.source_drawing,
                    (int)swDocumentTypes_e.swDocDRAWING,
                    (int)(swOpenDocOptions_e.swOpenDocOptions_Silent|swOpenDocOptions_e.swOpenDocOptions_ReadOnly),
                    "",ref err,ref warn) as ModelDoc2;
                Need(drawing!=null,"DRAWING_OPEN_FAILED e="+err+" w="+warn);
                opened=true;

                DrawingDoc dr=drawing as DrawingDoc;
                Need(dr!=null,"NOT_A_DRAWING");
                List<AnnotationRecord> inv=Inventory(dr);

                foreach(Check c in job.checks)
                {
                    CheckResult cr=EvaluateCheck(c,inv);
                    R.checks.Add(cr);
                    if(c.required)
                    {
                        R.required_checks++;
                        if(cr.status=="PASS") R.required_passed++;
                    }
                }

                if(opened && drawing!=null)
                {
                    string title=drawing.GetTitle();
                    ses.App.CloseDoc(title);
                    drawing=null;
                    opened=false;
                }

                R.source_drawing_sha_after=SwSession.Sha256AfterClose(R.source_drawing);
                Need(R.source_drawing_sha_before==R.source_drawing_sha_after,"DRAWING_INVARIANCE_FAILED");

                R.status=(R.required_passed==R.required_checks)
                    ?"PASS_NATIVE_ATTACHMENT_QA_REQUIRED_CHECKS"
                    :"HOLD_NATIVE_ATTACHMENT_QA_REQUIRED_CHECKS";
                Save(reportDir,"K01_DRAWING_NATIVE_ATTACHMENT_QA_CURRENT.json",R);

                Console.WriteLine("STATUS="+R.status);
                Console.WriteLine("REQUIRED_CHECKS="+R.required_passed+"/"+R.required_checks);
                Console.WriteLine("SOURCE_DRAWING_INVARIANCE=PASS");
                Console.WriteLine("REPORT="+Path.Combine(reportDir,"K01_DRAWING_NATIVE_ATTACHMENT_QA_CURRENT.json"));
                return (R.required_passed==R.required_checks)?0:3;
            }
            catch(Exception ex)
            {
                R.status="HOLD_NATIVE_ATTACHMENT_QA";
                R.error=ex.ToString();
                try { Save(reportDir,"K01_DRAWING_NATIVE_ATTACHMENT_QA_CURRENT.json",R); } catch {}
                Console.WriteLine("STATUS="+R.status);
                Console.WriteLine("ERROR="+ex.Message);
                return 3;
            }
            finally
            {
                if(ses!=null)
                {
                    try { if(opened && drawing!=null) ses.App.CloseDoc(drawing.GetTitle()); } catch {}
                    ses.Dispose();
                }
            }
        }

        static CheckResult EvaluateCheck(Check c,List<AnnotationRecord> inv)
        {
            CheckResult r=new CheckResult();
            r.id=c.id??"";
            r.annotation_name=c.annotation_name??"";
            r.required=c.required;

            List<AnnotationRecord> hits=new List<AnnotationRecord>();
            foreach(AnnotationRecord a in inv)
                if(String.Equals(a.annotation_name,c.annotation_name,StringComparison.OrdinalIgnoreCase))
                    hits.Add(a);

            if(hits.Count!=1)
            {
                r.error="ANNOTATION_MATCH_COUNT="+hits.Count;
                return r;
            }

            AnnotationRecord ar=hits[0];
            r.observed=ar;
            r.view_name=ar.view_name;
            r.referenced_model_path=ar.referenced_model_path;

            if(!String.IsNullOrWhiteSpace(c.expected_view) &&
               !String.Equals(c.expected_view,ar.view_name,StringComparison.OrdinalIgnoreCase))
            {
                r.error="WRONG_VIEW expected="+c.expected_view+" observed="+ar.view_name;
                return r;
            }

            if(!String.IsNullOrWhiteSpace(c.expected_model_path))
            {
                string exp=Path.GetFullPath(c.expected_model_path).TrimEnd('\\');
                string obs=String.IsNullOrWhiteSpace(ar.referenced_model_path)?"":Path.GetFullPath(ar.referenced_model_path).TrimEnd('\\');
                if(!String.Equals(exp,obs,StringComparison.OrdinalIgnoreCase))
                {
                    r.error="WRONG_REFERENCED_MODEL expected="+exp+" observed="+obs;
                    return r;
                }
            }

            if(ar.attachment_count<1 || ar.dangling)
            {
                r.error="ATTACHMENT_MISSING_OR_DANGLING";
                return r;
            }

            ExpectedSignature s=c.expected_signature;
            Need(s!=null && !String.IsNullOrWhiteSpace(s.kind),c.id+": EXPECTED_SIGNATURE_MISSING");

            if(String.Equals(s.kind,"ATTACHMENT_PRESENT",StringComparison.OrdinalIgnoreCase))
            {
                r.status="PASS";
                return r;
            }

            if(String.Equals(s.kind,"CYLINDER_DIAMETER",StringComparison.OrdinalIgnoreCase))
            {
                Need(s.diameter_mm.HasValue,c.id+": diameter_mm missing");
                double diaTol=s.diameter_tolerance_mm.HasValue?s.diameter_tolerance_mm.Value:0.03;
                double xTol=s.center_x_tolerance_mm.HasValue?s.center_x_tolerance_mm.Value:0.05;

                foreach(ObservedEntity e in ar.entities)
                {
                    for(int i=0;i<e.cylinder_diameters_mm.Count;i++)
                    {
                        double d=e.cylinder_diameters_mm[i];
                        if(Math.Abs(d-s.diameter_mm.Value)>diaTol) continue;

                        if(s.center_x_mm.HasValue)
                        {
                            if(i>=e.cylinder_center_x_mm.Count) continue;
                            if(Math.Abs(e.cylinder_center_x_mm[i]-s.center_x_mm.Value)>xTol) continue;
                        }

                        r.status="PASS";
                        return r;
                    }
                }

                r.error="CYLINDER_SIGNATURE_MISMATCH expected_dia_mm="+F(s.diameter_mm.Value);
                return r;
            }

            r.error="UNSUPPORTED_SIGNATURE_KIND="+s.kind;
            return r;
        }

        static List<AnnotationRecord> Inventory(DrawingDoc dr)
        {
            List<AnnotationRecord> outp=new List<AnnotationRecord>();
            View v=dr.GetFirstView() as View;
            int vg=0;
            while(v!=null && vg++<500)
            {
                string vn=SafeViewName(v);
                string rp=ReferencedModelPath(v);
                Annotation a=null;
                try { a=v.GetFirstAnnotation3() as Annotation; } catch {}
                int ag=0;
                while(a!=null && ag++<10000)
                {
                    outp.Add(InspectAnnotation(a,vn,rp));
                    try { a=a.GetNext3() as Annotation; } catch { a=null; }
                }
                v=v.GetNextView() as View;
            }
            return outp;
        }

        static AnnotationRecord InspectAnnotation(Annotation a,string viewName,string refPath)
        {
            AnnotationRecord r=new AnnotationRecord();
            r.view_name=viewName??"";
            r.referenced_model_path=refPath??"";
            try { r.annotation_name=a.GetName()??""; } catch {}

            object eo=null,to=null;
            try { eo=a.GetAttachedEntities2(); } catch(Exception ex) { r.entities.Add(new ObservedEntity{error="GetAttachedEntities2: "+ex.Message}); return r; }
            try { to=a.GetAttachedEntityTypes(); } catch(Exception ex) { r.entities.Add(new ObservedEntity{error="GetAttachedEntityTypes: "+ex.Message}); return r; }

            object[] ents=AsObjects(eo);
            int[] types=AsInts(to);
            r.attachment_count=ents.Length;

            int n=Math.Max(ents.Length,types.Length);
            for(int i=0;i<n;i++)
            {
                object obj=i<ents.Length?ents[i]:null;
                int t=i<types.Length?types[i]:(int)swSelectType_e.swSelNOTHING;
                ObservedEntity oe=InspectEntity(obj,t);
                r.entities.Add(oe);
                if(obj==null || t==(int)swSelectType_e.swSelNOTHING) r.dangling=true;
            }
            return r;
        }

        static ObservedEntity InspectEntity(object obj,int type)
        {
            ObservedEntity r=new ObservedEntity();
            r.attached_type=type;
            r.attached_type_name=SelectTypeName(type);
            r.object_present=obj!=null;

            if(obj==null || type==(int)swSelectType_e.swSelNOTHING)
            {
                r.error="DANGLING_OR_UNSUPPORTED";
                return r;
            }

            Face2 f=obj as Face2;
            if(f!=null) AddCylinderFromFace(r,f);

            Edge e=obj as Edge;
            if(e!=null)
            {
                try
                {
                    foreach(object q in AsObjects(e.GetTwoAdjacentFaces2()))
                    {
                        Face2 af=q as Face2;
                        if(af!=null) AddCylinderFromFace(r,af);
                    }
                }
                catch(Exception ex){ r.error="EDGE_ADJACENT_FACE_READ_FAILED: "+ex.Message; }
            }

            return r;
        }

        static void AddCylinderFromFace(ObservedEntity r,Face2 f)
        {
            try
            {
                Surface s=f.IGetSurface();
                if(s==null || !s.IsCylinder()) return;
                double[] p=AsDoubles(s.CylinderParams);
                if(p.Length<7) return;
                double d=Math.Abs(p[6])*2000.0;
                double cx=CenterXmm(f);
                AddCylinderUnique(r,d,cx);
            }
            catch {}
        }

        static double CenterXmm(Face2 f)
        {
            try
            {
                double[] b=AsDoubles(f.GetBox());
                if(b.Length>=6) return (b[0]+b[3])*500.0;
            }
            catch {}
            return Double.NaN;
        }

        static void AddCylinderUnique(ObservedEntity r,double d,double cx)
        {
            for(int i=0;i<r.cylinder_diameters_mm.Count;i++)
                if(Math.Abs(r.cylinder_diameters_mm[i]-d)<=0.0005) return;
            r.cylinder_diameters_mm.Add(d);
            r.cylinder_center_x_mm.Add(cx);
        }

        static string ReferencedModelPath(View v)
        {
            try
            {
                ModelDoc2 rd=v.ReferencedDocument as ModelDoc2;
                if(rd!=null)
                {
                    string p=rd.GetPathName();
                    if(!String.IsNullOrWhiteSpace(p)) return Path.GetFullPath(p);
                }
            }
            catch {}
            return "";
        }

        static string SafeViewName(View v)
        {
            try { return v.Name??""; } catch { return ""; }
        }

        static object[] AsObjects(object raw)
        {
            if(raw==null) return new object[0];
            Array a=raw as Array;
            if(a==null) return new object[]{raw};
            object[] r=new object[a.Length];
            for(int i=0;i<a.Length;i++) r[i]=a.GetValue(i);
            return r;
        }

        static int[] AsInts(object raw)
        {
            if(raw==null) return new int[0];
            Array a=raw as Array;
            if(a==null) return new int[]{Convert.ToInt32(raw,CultureInfo.InvariantCulture)};
            int[] r=new int[a.Length];
            for(int i=0;i<a.Length;i++) r[i]=Convert.ToInt32(a.GetValue(i),CultureInfo.InvariantCulture);
            return r;
        }

        static double[] AsDoubles(object raw)
        {
            if(raw==null) return new double[0];
            Array a=raw as Array;
            if(a==null) return new double[0];
            double[] r=new double[a.Length];
            for(int i=0;i<a.Length;i++) r[i]=Convert.ToDouble(a.GetValue(i),CultureInfo.InvariantCulture);
            return r;
        }

        static string SelectTypeName(int t)
        {
            if(t==(int)swSelectType_e.swSelFACES) return "swSelFACES";
            if(t==(int)swSelectType_e.swSelEDGES) return "swSelEDGES";
            if(t==(int)swSelectType_e.swSelVERTICES) return "swSelVERTICES";
            if(t==(int)swSelectType_e.swSelSKETCHSEGS) return "swSelSKETCHSEGS";
            if(t==(int)swSelectType_e.swSelSKETCHPOINTS) return "swSelSKETCHPOINTS";
            if(t==(int)swSelectType_e.swSelNOTHING) return "swSelNOTHING";
            return "swSelectType_e="+t;
        }

        static T Load<T>(string p)
        {
            JavaScriptSerializer js=new JavaScriptSerializer();
            js.MaxJsonLength=Int32.MaxValue;
            return js.Deserialize<T>(File.ReadAllText(p));
        }

        static void Save<T>(string dir,string name,T obj)
        {
            JavaScriptSerializer js=new JavaScriptSerializer();
            js.MaxJsonLength=Int32.MaxValue;
            File.WriteAllText(Path.Combine(dir,name),js.Serialize(obj),Encoding.UTF8);
        }

        static void Need(bool ok,string msg)
        {
            if(!ok) throw new Exception(msg);
        }

        static string F(double x)
        {
            if(Double.IsNaN(x)) return "NaN";
            return x.ToString("0.######",CultureInfo.InvariantCulture);
        }
    }
}
