using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Runtime.InteropServices;
using System.Web.Script.Serialization;
using SolidWorks.Interop.sldworks;
using SolidWorks.Interop.swconst;

namespace Marvilon.K01.Gate04D_C2R1.DrawingsV2
{
    public sealed class PathsCfg
    {
        public string candidate_dir { get; set; }
        public string drawing_dir { get; set; }
        public string report_dir { get; set; }
    }
    public sealed class P003Cfg
    {
        public string material { get; set; }
        public double J2_flange_OD_mm { get; set; }
        public double J2_flange_depth_inward_mm { get; set; }
        public double pilot_OD_nominal_mm { get; set; }
        public double pilot_inner_clearance_D_mm { get; set; }
        public string pilot_fit { get; set; }
        public double pilot_L_outward_mm { get; set; }
        public string oring_size { get; set; }
        public string oring_material { get; set; }
        public double gland_ID_mm { get; set; }
        public double gland_OD_nominal_mm { get; set; }
        public double gland_depth_mm { get; set; }
        public string thread { get; set; }
        public double tap_drill_D_mm { get; set; }
        public double tap_depth_mm { get; set; }
    }
    public sealed class P007Cfg
    {
        public string material { get; set; }
        public double overall_L_mm { get; set; }
        public double locator_ID_nominal_mm { get; set; }
        public string locator_fit { get; set; }
        public double thin_OD_mm { get; set; }
        public double thin_ID_mm { get; set; }
        public double J2_flange_OD_mm { get; set; }
        public double J2_flange_depth_inward_mm { get; set; }
        public double clearance_hole_D_mm { get; set; }
    }
    public sealed class J2Cfg
    {
        public int pattern_qty { get; set; }
        public double pattern_PCD_mm { get; set; }
        public double equal_spacing_deg { get; set; }
        public double P006_head_OD_nominal_mm { get; set; }
        public double pilot_nominal_radial_clearance_to_head_mm { get; set; }
        public double pilot_radial_wall_mm { get; set; }
    }
    public sealed class GateCfg
    {
        public PathsCfg paths { get; set; }
        public P003Cfg P003 { get; set; }
        public P007Cfg P007 { get; set; }
        public J2Cfg J2 { get; set; }
    }

    public sealed class DrawingMetrics
    {
        public string drawing_no="";
        public string model="";
        public string slddrw="";
        public string pdf="";
        public int model_view_count=0;
        public bool side_view=false;
        public bool end_view=false;
        public bool iso_view=false;
        public bool section_view=false;
        public int autodim_side_status=-999;
        public int autodim_end_status=-999;
        public int display_dimension_count=0;
        public bool critical_table=false;
        public bool title_table=false;
        public string quality_status="RUNNING";
        public List<string> checks=new List<string>();
        public List<string> warnings=new List<string>();
    }

    public sealed class Report
    {
        public string schema="k01_gate04d_c2r1_typed_drawings_v2";
        public string created_utc=DateTime.UtcNow.ToString("o");
        public string status="RUNNING";
        public string quality_status="RUNNING";
        public string solidworks_revision="";
        public DrawingMetrics p003=new DrawingMetrics();
        public DrawingMetrics p007=new DrawingMetrics();
        public List<string> checks=new List<string>();
        public List<string> warnings=new List<string>();
        public string error="";
    }

    public static class Program
    {
        static SldWorks sw;
        static GateCfg Cfg;
        static Report R=new Report();
        static string Root, LogPath, ReportPath;
        static string P003Candidate, P007Candidate;

        public static int Main()
        {
            Root=ResolvePackageRoot();
            try
            {
                LoadConfig(); Prepare(); Connect();
                Log("K01 Gate04D-C2R1 DRAWINGS V2 — manufacturing-draft quality gate");
                R.p003=GenerateP003();
                R.p007=GenerateP007();
                R.status="PASS";
                R.quality_status=(R.p003.quality_status=="PASS_DRAFT" && R.p007.quality_status=="PASS_DRAFT") ? "PASS_DRAFT" : "HOLD_DRAWING_QUALITY";
                if(R.quality_status=="PASS_DRAFT")
                    R.checks.Add("PASS_DRAFT: both drawings contain required view set, visible dimensions and controlled document tables.");
                else
                    R.warnings.Add("HOLD: drawing files were generated but at least one drawing does not yet satisfy the v2 manufacturing-draft quality gate.");
                SaveReport(); Log("STATUS="+R.status+" QUALITY="+R.quality_status);
                return R.quality_status=="PASS_DRAFT" ? 0 : 2;
            }
            catch(Exception ex)
            {
                R.status="FAIL";R.quality_status="FAIL";R.error=ex.ToString();
                try{SaveReport();}catch{} try{Log("STATUS=FAIL\r\n"+ex);}catch{}
                return 1;
            }
        }

        static void LoadConfig()
        {
            string p=Path.Combine(Root,"K01_GATE04D_C2R1_PARAMS_v1.json");
            if(!File.Exists(p))throw new Exception("Missing parameter file: "+p);
            Cfg=new JavaScriptSerializer().Deserialize<GateCfg>(File.ReadAllText(p));
            if(Cfg==null||Cfg.paths==null)throw new Exception("Invalid C2R1 parameter file.");
            P003Candidate=Path.Combine(Cfg.paths.candidate_dir,"K01-P-003_Cartridge_Body_GATE04D_C2R1_CANDIDATE.SLDPRT");
            P007Candidate=Path.Combine(Cfg.paths.candidate_dir,"K01-P-007_Hermetic_Magnetic_Can_GATE04D_C2R1_CANDIDATE.SLDPRT");
        }

        static void Prepare()
        {
            Directory.CreateDirectory(Cfg.paths.drawing_dir);
            Directory.CreateDirectory(Path.Combine(Cfg.paths.drawing_dir,"history"));
            Directory.CreateDirectory(Cfg.paths.report_dir);
            string stamp=DateTime.Now.ToString("yyyyMMdd_HHmmss");
            LogPath=Path.Combine(Cfg.paths.report_dir,"K01_GATE04D_C2R1_TYPED_DRAWINGS_V2_"+stamp+".log");
            ReportPath=Path.Combine(Cfg.paths.report_dir,"K01_GATE04D_C2R1_TYPED_DRAWINGS_V2.json");
            File.WriteAllText(LogPath,"K01 Gate04D-C2R1 drawing V2\r\n");
        }

        static void Connect()
        {
            object a=null;try{a=Marshal.GetActiveObject("SldWorks.Application");}catch{}
            sw=a!=null?(SldWorks)a:(SldWorks)Activator.CreateInstance(Type.GetTypeFromProgID("SldWorks.Application",true));
            if(sw==null)throw new Exception("Could not connect to SOLIDWORKS.");
            sw.Visible=true;R.solidworks_revision=sw.RevisionNumber();Log("Connected "+R.solidworks_revision);
        }

        static DrawingMetrics GenerateP003()
        {
            string[,] critical=new string[,]
            {
                {"Feature","Controlled specification","Release state"},
                {"Material","AISI 316L / EN 1.4404","CONTROLLED"},
                {"J2 flange","Ø33.00; axial zone 5.00","C2R1"},
                {"Pilot OD","Ø14.10 g6 × 1.50","C2R1"},
                {"Pilot ID","Ø12.00 STUDY","TOLERANCE / TOOL ACCESS OPEN"},
                {"P006 head clearance","0.25 radial nominal vs Ø11.50 head","TOLERANCE OPEN"},
                {"Clamp","3× M2.5×0.45-6H @120°","THREAD RELEASE OPEN"},
                {"Pattern","PCD 26.50","C2R1"},
                {"Tap geometry","Ø2.05 study drill; depth 5.00","THREAD CALLOUT CONTROLS"},
                {"O-ring","16×1.5","COMPOUND OPEN"},
                {"Gland","ID16.00 / OD20.20 / depth1.10","GEOMETRY CONTROLLED"}
            };
            string note=
                "DRAFT FOR ENGINEERING REVIEW — NOT RELEASED\n"+
                "Dimensioning follows controlled C2R1 parameters. Pilot ID12.00 remains STUDY until worst-case clearance and P006 tool access are closed.\n"+
                "Do not derive production torque from this drawing. O-ring compound and required clamp preload remain OPEN.";
            return GenerateDrawing(P003Candidate,"K01-D-003","K01-P-003","Cartridge Body",Cfg.P003.material,critical,note);
        }

        static DrawingMetrics GenerateP007()
        {
            string[,] critical=new string[,]
            {
                {"Feature","Controlled specification","Release state"},
                {"Material","AISI 316L / EN 1.4404","CONTROLLED"},
                {"Overall length","35.00","CONTROLLED"},
                {"J2 flange","Ø33.00 × 3.00 within L35","C2R1"},
                {"Locator","Ø14.10 H7 × 1.70","C2R1"},
                {"Clamp holes","3× Ø2.90 THRU @120°","C2R1"},
                {"Pattern","PCD 26.50","C2R1"},
                {"Thin can OD","Ø10.00","CONTROLLED"},
                {"Thin can ID","Ø9.40","CONTROLLED"},
                {"Containment wall","0.30 nominal radial","STRUCTURAL REFRESH OPEN"}
            };
            string note=
                "DRAFT FOR ENGINEERING REVIEW — NOT RELEASED\n"+
                "P007 OAL35 and thin containment zone are retained. Final static/buckling refresh is required after J2 mechanical preload is frozen.";
            return GenerateDrawing(P007Candidate,"K01-D-006","K01-P-007","Hermetic Magnetic Can",Cfg.P007.material,critical,note);
        }

        static DrawingMetrics GenerateDrawing(string modelPath,string drawingNo,string partNo,string description,string material,string[,] critical,string engineeringNote)
        {
            RequireFile(modelPath);
            DrawingMetrics M=new DrawingMetrics();M.drawing_no=drawingNo;M.model=modelPath;

            int e=0,w=0;
            ModelDoc2 model=sw.OpenDoc6(modelPath,(int)swDocumentTypes_e.swDocPART,(int)swOpenDocOptions_e.swOpenDocOptions_Silent,"",ref e,ref w) as ModelDoc2;
            if(model==null)throw new Exception("Open model failed "+modelPath+" e="+e);
            string modelTitle=model.GetTitle();

            try
            {
                string template=sw.GetUserPreferenceStringValue((int)swUserPreferenceStringValue_e.swDefaultTemplateDrawing);
                if(String.IsNullOrWhiteSpace(template)||!File.Exists(template))
                    throw new Exception("Default drawing template not found: "+template);

                ModelDoc2 dm=sw.NewDocument(template,0,0.0,0.0) as ModelDoc2;
                if(dm==null)throw new Exception("New drawing failed for "+drawingNo);
                string drawTitle=dm.GetTitle();

                try
                {
                    DrawingDoc dr=dm as DrawingDoc;
                    if(dr==null)throw new Exception("Drawing cast failed.");

                    // Force a controlled ISO-A3 landscape sheet; use first-angle projection.
                    bool sheetOk=false;
                    try
                    {
                        sheetOk=dr.SetupSheet5(
                            "Sheet1",
                            (int)swDwgPaperSizes_e.swDwgPaperA3size,
                            (int)swDwgTemplates_e.swDwgTemplateA3size,
                            2.0,1.0,
                            true,
                            "",
                            0.420,0.297,
                            "",
                            false);
                        dm.ForceRebuild3(false);
                    }
                    catch(Exception ex){M.warnings.Add("A3 sheet setup warning: "+ex.Message);}
                    if(sheetOk)M.checks.Add("A3 first-angle sheet setup PASS.");

                    // Explicit view set; avoid duplicate automatic side views.
                    View side=dr.CreateDrawViewFromModelView3(modelPath,"*Front",0.105,0.205,0.0);
                    View end=dr.CreateDrawViewFromModelView3(modelPath,"*Right",0.285,0.205,0.0);
                    View iso=dr.CreateDrawViewFromModelView3(modelPath,"*Isometric",0.325,0.095,0.0);
                    M.side_view=side!=null;M.end_view=end!=null;M.iso_view=iso!=null;
                    if(side==null||end==null)throw new Exception("Required orthographic view creation failed.");

                    // Longitudinal section through the side-view centerline.
                    try
                    {
                        dr.ActivateView(side.Name);
                        double[] o=(double[])side.GetOutline();
                        double cy=(o[1]+o[3])*0.5;
                        double x1=o[0]-0.004, x2=o[2]+0.004;
                        dm.ClearSelection2(true);
                        SketchSegment ln=dm.SketchManager.CreateLine(x1,cy,0.0,x2,cy,0.0);
                        if(ln!=null)
                        {
                            View sec=dr.CreateSectionViewAt5(0.120,0.085,0.0,"A",32,null,0.0);
                            if(sec!=null){M.section_view=true;M.checks.Add("Longitudinal section A-A created.");}
                        }
                    }
                    catch(Exception ex){M.warnings.Add("Section-view warning: "+ex.Message);}

                    // Native drawing dimensions. These are DRAFT dimensions; the controlled table remains the parameter authority.
                    M.autodim_side_status=AutoDim(dm,dr,side,true);
                    M.autodim_end_status=AutoDim(dm,dr,end,false);

                    // Supplement with any model annotations already marked for drawing.
                    try
                    {
                        dr.ActivateView(side.Name);
                        dr.InsertModelAnnotations3(
                            (int)swImportModelItemsSource_e.swImportModelItemsFromEntireModel,
                            (int)swInsertAnnotation_e.swInsertDimensionsMarkedForDrawing,
                            true,false,false,false);
                    }
                    catch(Exception ex){M.warnings.Add("Marked-model-dimension import warning: "+ex.Message);}

                    // Critical controlled-parameter table. This prevents geometry notes from being the only technical specification.
                    try
                    {
                        TableAnnotation tab=dm.Extension.InsertGeneralTableAnnotation(false,0.235,0.285,0,"",critical.GetLength(0),critical.GetLength(1));
                        if(tab!=null)
                        {
                            for(int r=0;r<critical.GetLength(0);r++)
                                for(int c=0;c<critical.GetLength(1);c++)
                                    tab.set_Text2(r,c,false,critical[r,c]);
                            M.critical_table=true;
                        }
                    }
                    catch(Exception ex){M.warnings.Add("Critical table warning: "+ex.Message);}

                    // ISO-7200-like document data block; this is not a substitute for a corporate sheet format.
                    try
                    {
                        string[,] tb=new string[,]
                        {
                            {"DRAWING",drawingNo,"PART",partNo},
                            {"DESCRIPTION",description,"MATERIAL",material},
                            {"STATUS","DRAFT / NOT RELEASED","GATE","Gate04D-C2R1"},
                            {"PROJECTION","FIRST ANGLE","SCALE","2:1 nominal sheet"},
                            {"SOURCE",Path.GetFileName(modelPath),"REV","STUDY"}
                        };
                        TableAnnotation title=dm.Extension.InsertGeneralTableAnnotation(false,0.255,0.055,0,"",tb.GetLength(0),tb.GetLength(1));
                        if(title!=null)
                        {
                            for(int r=0;r<tb.GetLength(0);r++)
                                for(int c=0;c<tb.GetLength(1);c++)
                                    title.set_Text2(r,c,false,tb[r,c]);
                            M.title_table=true;
                        }
                    }
                    catch(Exception ex){M.warnings.Add("Title block table warning: "+ex.Message);}

                    try
                    {
                        Note n=dm.InsertNote(engineeringNote) as Note;
                        if(n!=null)
                        {
                            Annotation a=n.GetAnnotation() as Annotation;
                            if(a!=null)a.SetPosition2(0.018,0.035,0.0);
                        }
                    }
                    catch(Exception ex){M.warnings.Add("Engineering note warning: "+ex.Message);}

                    dm.ForceRebuild3(false);
                    M.model_view_count=CountModelViews(dr);
                    M.display_dimension_count=CountDisplayDimensions(dr);

                    SetProperty(dm,"DrawingNo",drawingNo);
                    SetProperty(dm,"PartNo",partNo);
                    SetProperty(dm,"Description",description);
                    SetProperty(dm,"MaterialSpec",material);
                    SetProperty(dm,"K01_DrawingStatus","DRAFT_C2R1_API_V2");
                    SetProperty(dm,"K01_SourceModel",modelPath);

                    string stem=drawingNo+"_"+Path.GetFileNameWithoutExtension(modelPath)+"_DRAFT_C2R1_API_V2";
                    string slddrw=Path.Combine(Cfg.paths.drawing_dir,stem+".SLDDRW");
                    string pdf=Path.Combine(Cfg.paths.drawing_dir,stem+".PDF");
                    ArchiveIfExists(slddrw);ArchiveIfExists(pdf);
                    SaveAs3Checked(dm,slddrw);SaveAs3Checked(dm,pdf);
                    M.slddrw=slddrw;M.pdf=pdf;

                    // Quality gate: a generated file is not automatically a drawing PASS.
                    bool dimensionsOk=M.display_dimension_count>=3 || M.autodim_side_status==0 || M.autodim_end_status==0;
                    bool viewSetOk=M.side_view && M.end_view && M.iso_view && M.section_view && M.model_view_count>=4;
                    bool documentOk=M.critical_table && M.title_table;
                    M.quality_status=(dimensionsOk && viewSetOk && documentOk) ? "PASS_DRAFT" : "HOLD_DRAWING_QUALITY";
                    M.checks.Add("Model view count="+M.model_view_count);
                    M.checks.Add("Display dimension count="+M.display_dimension_count);
                    M.checks.Add("AutoDim side status="+M.autodim_side_status+"; end status="+M.autodim_end_status);
                    Log(drawingNo+" QUALITY="+M.quality_status+" views="+M.model_view_count+" dims="+M.display_dimension_count);
                    return M;
                }
                finally{try{sw.CloseDoc(drawTitle);}catch{}}
            }
            finally{try{sw.CloseDoc(modelTitle);}catch{}}
        }

        static int AutoDim(ModelDoc2 dm,DrawingDoc dr,View v,bool side)
        {
            if(v==null)return -999;
            try
            {
                dm.ClearSelection2(true);
                dr.ActivateView(v.Name);
                bool sel=dm.Extension.SelectByID2(v.Name,"DRAWINGVIEW",0,0,0,false,0,null,0);
                if(!sel)return -998;
                int ret=dr.AutoDimension(
                    (int)swAutodimEntities_e.swAutodimEntitiesAll,
                    (int)swAutodimScheme_e.swAutodimSchemeBaseline,
                    (int)swAutodimHorizontalPlacement_e.swAutodimHorizontalPlacementAbove,
                    (int)swAutodimScheme_e.swAutodimSchemeBaseline,
                    (int)swAutodimVerticalPlacement_e.swAutodimVerticalPlacementRight);
                dm.ClearSelection2(true);
                return ret;
            }
            catch{return -997;}
        }

        static int CountModelViews(DrawingDoc dr)
        {
            int count=0;
            View v=dr.GetFirstView() as View;
            if(v!=null)v=v.GetNextView() as View; // first object is sheet
            while(v!=null){count++;v=v.GetNextView() as View;}
            return count;
        }

        static int CountDisplayDimensions(DrawingDoc dr)
        {
            int n=0;
            View v=dr.GetFirstView() as View;
            if(v!=null)v=v.GetNextView() as View;
            while(v!=null)
            {
                try{n+=v.GetDisplayDimensionCount();}catch{}
                v=v.GetNextView() as View;
            }
            return n;
        }

        static void SetProperty(ModelDoc2 doc,string key,string value)
        {
            CustomPropertyManager cpm=doc.Extension.get_CustomPropertyManager("");
            try{cpm.Delete2(key);}catch{}
            int r=cpm.Add(key,"Text",value??"");
            if(r==0)try{cpm.Set2(key,value??"");}catch{}
        }

        static void SaveAs3Checked(ModelDoc2 doc,string path)
        {
            Directory.CreateDirectory(Path.GetDirectoryName(path));
            int status=doc.SaveAs3(path,0,0);
            if(status!=0||!File.Exists(path))throw new Exception("SaveAs3 failed status="+status+" path="+path);
        }

        static void ArchiveIfExists(string path)
        {
            if(!File.Exists(path))return;
            string h=Path.Combine(Path.GetDirectoryName(path),"history");Directory.CreateDirectory(h);
            string dst=Path.Combine(h,Path.GetFileNameWithoutExtension(path)+"_"+DateTime.Now.ToString("yyyyMMdd_HHmmss")+Path.GetExtension(path));
            File.Copy(path,dst,true);File.Delete(path);
        }

        static void RequireFile(string p){if(!File.Exists(p))throw new Exception("Required file missing: "+p);}

        static string ResolvePackageRoot()
        {
            string exe=AppDomain.CurrentDomain.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar);
            string cwd=global::System.Environment.CurrentDirectory.TrimEnd(Path.DirectorySeparatorChar);
            string[] cands=new string[]{exe,Directory.GetParent(exe)!=null?Directory.GetParent(exe).FullName:exe,cwd,Directory.GetParent(cwd)!=null?Directory.GetParent(cwd).FullName:cwd};
            foreach(string c in cands)
            {
                if(String.IsNullOrWhiteSpace(c))continue;
                if(File.Exists(Path.Combine(c,"K01_GATE04D_C2R1_PARAMS_v1.json")))return c;
            }
            throw new Exception("Cannot locate K01_GATE04D_C2R1_PARAMS_v1.json.");
        }

        static void Log(string s)
        {
            string l="["+DateTime.Now.ToString("s")+"] "+s;Console.WriteLine(l);
            if(!String.IsNullOrWhiteSpace(LogPath))File.AppendAllText(LogPath,l+global::System.Environment.NewLine);
        }

        static void SaveReport(){File.WriteAllText(ReportPath,new JavaScriptSerializer().Serialize(R));}
    }
}
