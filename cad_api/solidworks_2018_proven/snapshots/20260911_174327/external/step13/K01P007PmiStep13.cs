using System;
using System.IO;
using System.Linq;
using System.Text;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using SolidWorks.Interop.sldworks;
using SolidWorks.Interop.swconst;
using SolidWorks.Interop.swdimxpert;

namespace K01P007PmiStep9BV3
{
    class InsertEvidence
    {
        public string Id;
        public bool ApiReturn;
        public int FeatureBefore;
        public int FeatureAfter;
        public int AnnotationBefore;
        public int AnnotationAfter;
        public string AnnotationName;
        public string AnnotationType;
        public string FeatureName;
        public string FeatureType;
        public int FeatureFaceCount;
        public bool IsDimensionTolerance;
        public double NominalM;
        public string DimensionType;
        public bool NominalMatches;
        public bool SemanticPass;
        public string Diagnostic;
    }

    class Program
    {
        static string Esc(string s)
        {
            if(s==null)return "null";StringBuilder b=new StringBuilder("\"");
            foreach(char c in s){if(c=='\\')b.Append("\\\\");else if(c=='"')b.Append("\\\"");else if(c=='\n')b.Append("\\n");else if(c=='\r')b.Append("\\r");else if(c=='\t')b.Append("\\t");else b.Append(c);}
            b.Append("\"");return b.ToString();
        }
        static string R(double x){return x.ToString("R",System.Globalization.CultureInfo.InvariantCulture);}
        static double[] D(object o){Array a=o as Array;if(a==null)return null;double[] r=new double[a.Length];for(int i=0;i<a.Length;i++)r[i]=Convert.ToDouble(a.GetValue(i));return r;}

        static string GeometryFingerprint(ModelDoc2 doc)
        {
            PartDoc pd=(PartDoc)doc;Array bodies=pd.GetBodies2((int)swBodyType_e.swSolidBody,true) as Array;List<string> recs=new List<string>();
            if(bodies!=null)foreach(object bo in bodies){Body2 body=bo as Body2;if(body==null)continue;Array fs=body.GetFaces() as Array;if(fs==null)continue;
                foreach(object fo in fs){Face2 f=fo as Face2;if(f==null)continue;double area=0;try{area=f.GetArea();}catch{}double[] box=D(f.GetBox());Surface s=(Surface)f.GetSurface();string typ="other";double[] par=null;
                    try{if(s.IsCylinder()){typ="cyl";par=D(s.CylinderParams);}else if(s.IsPlane()){typ="plane";par=D(s.PlaneParams);}else if(s.IsCone()){typ="cone";par=D(s.ConeParams);}else if(s.IsSphere()){typ="sphere";par=D(s.SphereParams);}}catch{}
                    StringBuilder x=new StringBuilder();x.Append(typ+"|"+R(area)+"|");if(box!=null)foreach(double v in box)x.Append(R(v)+",");x.Append("|");if(par!=null)foreach(double v in par)x.Append(R(v)+",");recs.Add(x.ToString());}}
            recs.Sort(StringComparer.Ordinal);string raw=String.Join("\n",recs.ToArray());SHA256 sha=SHA256.Create();byte[] h=sha.ComputeHash(Encoding.UTF8.GetBytes(raw));return BitConverter.ToString(h).Replace("-","").ToLowerInvariant();
        }

        static Dictionary<string,string> Manifest(string p)
        {Dictionary<string,string>d=new Dictionary<string,string>(StringComparer.OrdinalIgnoreCase);foreach(string line in File.ReadAllLines(p)){if(String.IsNullOrWhiteSpace(line)||line.TrimStart().StartsWith("#"))continue;int k=line.IndexOf('=');if(k>0)d[line.Substring(0,k).Trim()]=line.Substring(k+1).Trim();}return d;}
        static object Resolve(IModelDocExtension ext,string b64,out int err){return ext.GetObjectByPersistReference3(Convert.FromBase64String(b64),out err);}
        static HashSet<string> AnnotationNames(DimXpertPart dx)
        {
            HashSet<string> s=new HashSet<string>(StringComparer.OrdinalIgnoreCase);Array a=dx.GetAnnotations() as Array;if(a!=null)foreach(object o in a){DimXpertAnnotation an=o as DimXpertAnnotation;if(an!=null&&an.Name!=null)s.Add(an.Name);}return s;
        }

        static InsertEvidence InsertAndRead(DimXpertPart dx,ModelDoc2 doc,object face,string id,double expectedM,double[] pos)
        {
            InsertEvidence ev=new InsertEvidence();ev.Id=id;ev.NominalM=Double.NaN;ev.Diagnostic="";
            HashSet<string> beforeNames=AnnotationNames(dx);ev.FeatureBefore=dx.GetFeatureCount();ev.AnnotationBefore=dx.GetAnnotationCount();
            doc.ClearSelection2(true);Entity ent=face as Entity;if(ent==null){ev.Diagnostic="entity cast failed";return ev;}
            bool sel=ent.Select4(false,null);SelectionMgr sm=(SelectionMgr)doc.SelectionManager;int sc=sm.GetSelectedObjectCount2(-1);int st=sc>0?sm.GetSelectedObjectType3(1,-1):-1;
            DimXpertDimensionOption opt=dx.GetDimOption();opt.TextPosition=pos;opt.FeatureSelectorOptions=new int[]{(int)swDimXpertFeatureSelectorOption_e.swDimXpertFeatureSelectorOption_Cylinder};
            ev.ApiReturn=dx.InsertSizeDimension(opt);
            ev.FeatureAfter=dx.GetFeatureCount();ev.AnnotationAfter=dx.GetAnnotationCount();
            ev.Diagnostic="select="+sel+" selection_count="+sc+" selection_type="+st+" api_return="+ev.ApiReturn;

            Array anns=dx.GetAnnotations() as Array;List<DimXpertAnnotation> news=new List<DimXpertAnnotation>();
            if(anns!=null)foreach(object o in anns){DimXpertAnnotation an=o as DimXpertAnnotation;if(an!=null&&!beforeNames.Contains(an.Name))news.Add(an);}
            if(news.Count==1)
            {
                DimXpertAnnotation an=news[0];ev.AnnotationName=an.Name;ev.AnnotationType=an.Type.ToString();
                try{DimXpertFeature f=an.Feature;if(f!=null){ev.FeatureName=f.Name;ev.FeatureType=f.Type.ToString();ev.FeatureFaceCount=f.GetFaceCount();}}catch(Exception ex){ev.Diagnostic+=" feature_read="+ex.Message;}
                IDimXpertDimensionTolerance dt=an as IDimXpertDimensionTolerance;
                ev.IsDimensionTolerance=(dt!=null);
                if(dt!=null)
                {
                    try{ev.NominalM=dt.GetNominalValue();ev.DimensionType=dt.DimensionType.ToString();ev.NominalMatches=Math.Abs(ev.NominalM-expectedM)<=1e-6;}catch(Exception ex){ev.Diagnostic+=" dim_read="+ex.Message;}
                }
            }
            else ev.Diagnostic+=" new_annotation_count="+news.Count;

            ev.SemanticPass=(ev.FeatureAfter==ev.FeatureBefore+1 &&
                             ev.AnnotationAfter==ev.AnnotationBefore+1 &&
                             news.Count==1 &&
                             ev.IsDimensionTolerance &&
                             ev.NominalMatches);
            doc.ClearSelection2(true);return ev;
        }

        static string EvidenceJson(InsertEvidence e)
        {
            return "{"+
                "\"id\":"+Esc(e.Id)+","+
                "\"api_return\":"+(e.ApiReturn?"true":"false")+","+
                "\"feature_before\":"+e.FeatureBefore+",\"feature_after\":"+e.FeatureAfter+","+
                "\"annotation_before\":"+e.AnnotationBefore+",\"annotation_after\":"+e.AnnotationAfter+","+
                "\"annotation_name\":"+Esc(e.AnnotationName)+",\"annotation_type\":"+Esc(e.AnnotationType)+","+
                "\"feature_name\":"+Esc(e.FeatureName)+",\"feature_type\":"+Esc(e.FeatureType)+",\"feature_face_count\":"+e.FeatureFaceCount+","+
                "\"is_dimension_tolerance\":"+(e.IsDimensionTolerance?"true":"false")+","+
                "\"nominal_m\":"+(Double.IsNaN(e.NominalM)?"null":R(e.NominalM))+","+
                "\"dimension_type\":"+Esc(e.DimensionType)+","+
                "\"nominal_matches_expected\":"+(e.NominalMatches?"true":"false")+","+
                "\"semantic_pass\":"+(e.SemanticPass?"true":"false")+","+
                "\"diagnostic\":"+Esc(e.Diagnostic)+"}";
        }

        static void Main(string[] args)
        {
            string part=null,manifest=null,output=null;
            for(int i=0;i<args.Length;i++){if(args[i]=="--part"&&i+1<args.Length)part=args[++i];else if(args[i]=="--manifest"&&i+1<args.Length)manifest=args[++i];else if(args[i]=="--output"&&i+1<args.Length)output=args[++i];}
            if(part==null||manifest==null||output==null)System.Environment.Exit(2);

            SldWorks sw=null;bool started=false;ModelDoc2 doc=null;
            try
            {
                try{sw=(SldWorks)Marshal.GetActiveObject("SldWorks.Application");}catch{Type t=Type.GetTypeFromProgID("SldWorks.Application");sw=(SldWorks)Activator.CreateInstance(t);sw.Visible=false;started=true;}
                int oe=0,ow=0;doc=(ModelDoc2)sw.OpenDoc6(part,(int)swDocumentTypes_e.swDocPART,(int)swOpenDocOptions_e.swOpenDocOptions_Silent,"",ref oe,ref ow);
                if(doc==null)throw new Exception("Open failed errors="+oe+" warnings="+ow);
                int ae=0;doc=(ModelDoc2)sw.ActivateDoc3(doc.GetTitle(),false,(int)swRebuildOnActivation_e.swDontRebuildActiveDoc,ref ae);if(doc==null||ae!=0)throw new Exception("ActivateDoc3 error="+ae);
                string active=((ModelDoc2)sw.ActiveDoc).GetPathName();

                Dictionary<string,string> m=Manifest(manifest);IModelDocExtension ext=doc.Extension;int e02=0,e05=0;object f02=Resolve(ext,m["C02_REF"],out e02);object f05=Resolve(ext,m["C05_REF"],out e05);
                if(f02==null||e02!=(int)swPersistReferencedObjectStates_e.swPersistReferencedObject_Ok)throw new Exception("C02 persist ref state="+e02);
                if(f05==null||e05!=(int)swPersistReferencedObjectStates_e.swPersistReferencedObject_Ok)throw new Exception("C05 persist ref state="+e05);

                string geomBefore=GeometryFingerprint(doc);string cfg=doc.IGetActiveConfiguration().Name;DimXpertManager mgr=doc.Extension.get_DimXpertManager(cfg,true);DimXpertPart dx=(DimXpertPart)mgr.DimXpertPart;
                InsertEvidence c02=InsertAndRead(dx,doc,f02,"C02",14.10,new double[]{0.020,0.020,0.020});
                InsertEvidence c05=InsertAndRead(dx,doc,f05,"C05",33.00,new double[]{0.025,-0.020,0.020});
                string geomAfterInsert=GeometryFingerprint(doc);bool geomInsert=(geomBefore==geomAfterInsert);

                bool semantic=(c02.SemanticPass&&c05.SemanticPass&&geomInsert);
                bool apiAnomaly=semantic&&(!c02.ApiReturn||!c05.ApiReturn);
                bool saved=false;int se=0,swarn=0;
                if(semantic)
                {
                    saved=doc.Save3((int)swSaveAsOptions_e.swSaveAsOptions_Silent,ref se,ref swarn);
                    if(!saved||se!=0)semantic=false;
                }
                string geomAfterSave=GeometryFingerprint(doc);
                bool geomSave=(geomBefore==geomAfterSave);
                if(!geomSave)semantic=false;

                int featPersist=dx.GetFeatureCount();
                int annPersist=dx.GetAnnotationCount();

                bool reopenPass=false;
                string geomAfterReopen="";
                int featReopen=-1,annReopen=-1;
                int reopenC02Count=0,reopenC05Count=0;
                int re02=-999,re05=-999;
                if(semantic)
                {
                    string title=doc.GetTitle();
                    sw.CloseDoc(title);
                    doc=null;
                    int roe=0,row=0;
                    doc=(ModelDoc2)sw.OpenDoc6(part,(int)swDocumentTypes_e.swDocPART,
                        (int)swOpenDocOptions_e.swOpenDocOptions_Silent,"",ref roe,ref row);
                    if(doc==null)throw new Exception("Reopen after PMI save failed errors="+roe+" warnings="+row);
                    int rae=0;
                    doc=(ModelDoc2)sw.ActivateDoc3(doc.GetTitle(),false,(int)swRebuildOnActivation_e.swDontRebuildActiveDoc,ref rae);
                    if(doc==null||rae!=0)throw new Exception("Activate after reopen failed error="+rae);

                    geomAfterReopen=GeometryFingerprint(doc);
                    string rcfg=doc.IGetActiveConfiguration().Name;
                    DimXpertManager rmgr=doc.Extension.get_DimXpertManager(rcfg,true);
                    DimXpertPart rdx=(DimXpertPart)rmgr.DimXpertPart;
                    featReopen=rdx.GetFeatureCount();
                    annReopen=rdx.GetAnnotationCount();

                    Array ranns=rdx.GetAnnotations() as Array;
                    if(ranns!=null)foreach(object oo in ranns)
                    {
                        IDimXpertDimensionTolerance dtt=oo as IDimXpertDimensionTolerance;
                        if(dtt!=null)
                        {
                            double nv=dtt.GetNominalValue();
                            if(Math.Abs(nv-14.10)<=1e-6)reopenC02Count++;
                            if(Math.Abs(nv-33.00)<=1e-6)reopenC05Count++;
                        }
                    }

                    object rf02=Resolve(doc.Extension,m["C02_REF"],out re02);
                    object rf05=Resolve(doc.Extension,m["C05_REF"],out re05);
                    reopenPass=(geomAfterReopen==geomBefore &&
                                featReopen>=2 && annReopen>=2 &&
                                reopenC02Count>=1 && reopenC05Count>=1 &&
                                rf02!=null && re02==(int)swPersistReferencedObjectStates_e.swPersistReferencedObject_Ok &&
                                rf05!=null && re05==(int)swPersistReferencedObjectStates_e.swPersistReferencedObject_Ok);
                    semantic=semantic&&reopenPass;
                }

                string status=semantic?
                    (apiAnomaly?"PASS_PMI_SAVE_REOPEN_WITH_API_RETURN_ANOMALY":"PASS_PMI_SAVE_REOPEN"):
                    "HOLD_PMI_SAVE_REOPEN";

                StringBuilder j=new StringBuilder();j.Append("{\n");
                j.Append("\"schema\":\"k01.p007.pmi_step9b_v3.v1\",\n");
                j.Append("\"status\":"+Esc(status)+",\n");
                j.Append("\"candidate_part\":"+Esc(part)+",\n");
                j.Append("\"active_document\":"+Esc(active)+",\n");
                j.Append("\"persistent_reference_states\":{\"C02\":"+e02+",\"C05\":"+e05+"},\n");
                j.Append("\"C02\":"+EvidenceJson(c02)+",\n");
                j.Append("\"C05\":"+EvidenceJson(c05)+",\n");
                j.Append("\"geometry_fingerprint_before\":"+Esc(geomBefore)+",\n");
                j.Append("\"geometry_fingerprint_after_insert\":"+Esc(geomAfterInsert)+",\n");
                j.Append("\"geometry_fingerprint_after_save\":"+Esc(geomAfterSave)+",\n");
                j.Append("\"geometry_invariant\":"+((geomInsert&&geomSave)?"true":"false")+",\n");
                j.Append("\"saved\":"+(saved?"true":"false")+",\"save_error\":"+se+",\"save_warning\":"+swarn+",\n");
                j.Append("\"dimxpert_readback\":{\"feature_count\":"+featPersist+",\"annotation_count\":"+annPersist+"},\n");
                j.Append("\"reopen_readback\":{\"pass\":"+(reopenPass?"true":"false")+
                    ",\"geometry_fingerprint\":"+Esc(geomAfterReopen)+
                    ",\"feature_count\":"+featReopen+
                    ",\"annotation_count\":"+annReopen+
                    ",\"C02_nominal_match_count\":"+reopenC02Count+
                    ",\"C05_nominal_match_count\":"+reopenC05Count+
                    ",\"C02_persist_state\":"+re02+
                    ",\"C05_persist_state\":"+re05+"},\n");
                j.Append("\"api_return_anomaly\":"+(apiAnomaly?"true":"false")+",\n");
                j.Append("\"release_scope\":\"NOT_RELEASED_PMI_PILOT_NOMINAL_SIZE_ONLY\",\n");
                j.Append("\"policy\":{\"Gate04E_source_not_modified\":true,\"candidate_copy_only\":true,\"false_API_return_is_not_accepted_without_semantic_object_readback\":true}\n");
                j.Append("}\n");
                Directory.CreateDirectory(Path.GetDirectoryName(output));File.WriteAllText(output,j.ToString(),new UTF8Encoding(false));

                Console.WriteLine("active_document: "+active);
                Console.WriteLine("C02 api_return="+c02.ApiReturn+" semantic_pass="+c02.SemanticPass+" ann="+c02.AnnotationName+" annType="+c02.AnnotationType+" feature="+c02.FeatureName+" featureType="+c02.FeatureType+" nominal_m="+(Double.IsNaN(c02.NominalM)?"OPEN":c02.NominalM.ToString("R"))+" dimType="+c02.DimensionType);
                Console.WriteLine("C05 api_return="+c05.ApiReturn+" semantic_pass="+c05.SemanticPass+" ann="+c05.AnnotationName+" annType="+c05.AnnotationType+" feature="+c05.FeatureName+" featureType="+c05.FeatureType+" nominal_m="+(Double.IsNaN(c05.NominalM)?"OPEN":c05.NominalM.ToString("R"))+" dimType="+c05.DimensionType);
                Console.WriteLine("geometry_invariant: "+(geomInsert&&geomSave));
                Console.WriteLine("saved: "+saved+" save_error="+se+" save_warning="+swarn);
                Console.WriteLine("DimXpert readback features="+featPersist+" annotations="+annPersist);
                Console.WriteLine("reopen_readback: "+reopenPass+" features="+featReopen+" annotations="+annReopen+" C02matches="+reopenC02Count+" C05matches="+reopenC05Count+" persist="+re02+"/"+re05);
                Console.WriteLine("api_return_anomaly: "+apiAnomaly);
                Console.WriteLine("status: "+status);
                Console.WriteLine("report: "+output);
                if(!semantic)System.Environment.Exit(3);
            }
            catch(Exception ex){Console.Error.WriteLine("HOLD: "+ex.Message);Console.Error.WriteLine(ex.ToString());System.Environment.Exit(2);}
            finally{try{if(sw!=null&&doc!=null)sw.CloseDoc(doc.GetTitle());if(started&&sw!=null)sw.ExitApp();}catch{}}
        }
    }
}
