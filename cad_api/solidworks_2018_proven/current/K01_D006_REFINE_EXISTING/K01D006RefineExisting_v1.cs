using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using SolidWorks.Interop.sldworks;
using SolidWorks.Interop.swconst;

public class K01D006RefineExisting
{
    static void Need(bool ok,string msg){if(!ok)throw new Exception(msg);}
    static string Arg(string[] a,string k){for(int i=0;i<a.Length-1;i++)if(a[i]==k)return a[i+1];return null;}
    static double ArgD(string[] a,string k,double d){string s=Arg(a,k);double v;return s!=null&&Double.TryParse(s,System.Globalization.NumberStyles.Float,System.Globalization.CultureInfo.InvariantCulture,out v)?v:d;}
    static string Sha(string p){
        using(FileStream fs=new FileStream(p,FileMode.Open,FileAccess.Read,FileShare.ReadWrite|FileShare.Delete))
        using(SHA256 h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(fs)).Replace("-","").ToLowerInvariant();
    }
    static IEnumerable Items(object o){
        if(o==null)yield break;
        Array a=o as Array;if(a!=null){foreach(object x in a)yield return x;yield break;}
        IEnumerable e=o as IEnumerable;if(e!=null)foreach(object x in e)yield return x;
    }
    class VRec{
        public View v; public string name,orient,refModel; public double[] box; public double aspect; public bool section;
    }
    static string Name(View v){try{return v.GetName2();}catch{return "";}}
    static string Orient(View v){try{return v.GetOrientationName();}catch{return "";}}
    static string RefModel(View v){try{return v.GetReferencedModelName();}catch{return "";}}
    static double[] Outline(View v){
        try{
            object o=v.GetOutline(); Array a=o as Array;
            if(a!=null&&a.Length>=4)return new double[]{Convert.ToDouble(a.GetValue(0)),Convert.ToDouble(a.GetValue(1)),Convert.ToDouble(a.GetValue(2)),Convert.ToDouble(a.GetValue(3))};
        }catch{}
        return new double[]{0,0,0,0};
    }
    static List<VRec> ModelViews(DrawingDoc dr,string partBase){
        var r=new List<VRec>(); View v=dr.GetFirstView() as View; if(v!=null)v=v.GetNextView() as View; // skip sheet
        while(v!=null){
            string rm=RefModel(v);
            if(!String.IsNullOrWhiteSpace(rm) && String.Equals(Path.GetFileName(rm),partBase,StringComparison.OrdinalIgnoreCase)){
                double[] b=Outline(v);double w=Math.Abs(b[2]-b[0]),h=Math.Abs(b[3]-b[1]);
                string n=Name(v),o=Orient(v);
                r.Add(new VRec{v=v,name=n,orient=o,refModel=rm,box=b,aspect=h>1e-9?w/h:999,
                    section=n.ToUpperInvariant().Contains("SECTION")||n.ToUpperInvariant().Contains("A-A")});
            }
            v=v.GetNextView() as View;
        }
        return r;
    }
    static void SetView(View v,double x,double y,double scale){
        try{v.UseSheetScale=0;}catch{}
        try{v.UseParentScale=false;}catch{}
        try{v.ScaleDecimal=scale;}catch{}
        try{v.Position=new double[]{x,y};}catch{}
    }
    static string DxFeatureName(Annotation a){
        try{
            object f=a.GetDimXpertFeature();
            if(f==null)return "";
            SolidWorks.Interop.swdimxpert.DimXpertFeature dx=f as SolidWorks.Interop.swdimxpert.DimXpertFeature;
            if(dx!=null)return dx.Name;
            return "";
        }catch{return "";}
    }
    static string DxName(Annotation a){try{return a.GetDimXpertName();}catch{return "";}}
    static HashSet<string> ExistingDx(DrawingDoc dr){
        var s=new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        View v=dr.GetFirstView() as View;
        while(v!=null){
            foreach(object ao in Items(v.GetAnnotations())){
                Annotation a=ao as Annotation;if(a==null)continue;
                string f=DxFeatureName(a),n=DxName(a);
                if(!String.IsNullOrWhiteSpace(f))s.Add("F:"+f);
                if(!String.IsNullOrWhiteSpace(n))s.Add("N:"+n);
            }
            v=v.GetNextView() as View;
        }
        return s;
    }
    static bool IsDx(Annotation a,out string key){
        key="";string f=DxFeatureName(a),n=DxName(a);
        if(!String.IsNullOrWhiteSpace(f)){key="F:"+f;return true;}
        if(!String.IsNullOrWhiteSpace(n)){key="N:"+n;return true;}
        return false;
    }
    static bool DeleteAnnotation(ModelDoc2 doc,Annotation a){
        try{
            doc.ClearSelection2(true);
            SelectionMgr sm=doc.SelectionManager as SelectionMgr;
            if(sm==null)return false;
            SelectData sd=sm.CreateSelectData() as SelectData;
            if(sd==null)return false;
            if(!a.Select3(false,sd))return false;
            return doc.Extension.DeleteSelection2((int)swDeleteSelectionOptions_e.swDelete_Absorbed);
        }catch{return false;}
    }
    static int ImportOnlyDimXpert(ModelDoc2 doc,DrawingDoc dr,View target,HashSet<string> before,List<string> kept,List<string> removed){
        Need(target!=null,"target view null");
        string activateName=Name(target);
        Need(!String.IsNullOrWhiteSpace(activateName),"target drawing view has no name");
        doc.ClearSelection2(true);
        Need(dr.ActivateView(activateName),"cannot activate target drawing view: "+activateName);

        // IView.SelectEntity selects a model entity *inside* a drawing view; it does not
        // select the drawing view itself.  InsertModelAnnotations3(AllViews=false)
        // requires the drawing view to be selected, so use the SW2018-proven
        // ModelDocExtension.SelectByID2(..., "DRAWINGVIEW", ...) path.
        string selectName=activateName;
        try{
            string uniqueName=target.GetUniqueName();
            if(!String.IsNullOrWhiteSpace(uniqueName))selectName=uniqueName;
        }catch{}
        bool selected=false;
        try{selected=doc.Extension.SelectByID2(selectName,"DRAWINGVIEW",0,0,0,false,0,null,0);}catch{}
        if(!selected&&!String.Equals(selectName,activateName,StringComparison.OrdinalIgnoreCase)){
            try{selected=doc.Extension.SelectByID2(activateName,"DRAWINGVIEW",0,0,0,false,0,null,0);}catch{}
        }
        Need(selected,"cannot select target drawing view: activate="+activateName+" select="+selectName);
        int types=(int)swInsertAnnotation_e.swInsertDimensions |
                  (int)swInsertAnnotation_e.swInsertTolerancedDims |
                  (int)swInsertAnnotation_e.swInsertDatums |
                  (int)swInsertAnnotation_e.swInsertGTols;
        object raw=dr.InsertModelAnnotations3((int)swImportModelItemsSource_e.swImportModelItemsFromEntireModel,types,false,false,false,false);
        int keptCount=0;
        foreach(object x in Items(raw)){
            Annotation a=x as Annotation;if(a==null)continue;
            string key="";
            if(!IsDx(a,out key)){
                if(DeleteAnnotation(doc,a))removed.Add("NON_DX");
                continue;
            }
            if(before.Contains(key)){
                if(DeleteAnnotation(doc,a))removed.Add("DUP:"+key);
                continue;
            }
            before.Add(key);kept.Add(key);keptCount++;
        }
        doc.ClearSelection2(true);
        return keptCount;
    }
    static bool SaveAs(ModelDoc2 d,string p){
        int e=0,w=0;
        bool ok=d.Extension.SaveAs(p,(int)swSaveAsVersion_e.swSaveAsCurrentVersion,(int)swSaveAsOptions_e.swSaveAsOptions_Silent,null,ref e,ref w);
        if(!ok||e!=0)throw new Exception("SaveAs failed e="+e+" w="+w);
        return true;
    }
    static int Main(string[] args){
        string drawing=Arg(args,"--drawing"), part=Arg(args,"--part"), outdir=Arg(args,"--outdir"), report=Arg(args,"--report");
        double sectionScale=ArgD(args,"--section-scale",5.0), endScale=ArgD(args,"--end-scale",5.0), sideScale=ArgD(args,"--side-scale",2.0);
        if(String.IsNullOrWhiteSpace(drawing)||String.IsNullOrWhiteSpace(part)||String.IsNullOrWhiteSpace(outdir)||String.IsNullOrWhiteSpace(report)){Console.Error.WriteLine("missing args");return 2;}
        try{
            Need(File.Exists(drawing),"drawing missing");
            Need(File.Exists(part),"part missing");
            string drawingSha=Sha(drawing),partSha=Sha(part);
            Directory.CreateDirectory(outdir);
            string dst=Path.Combine(outdir,"K01-D-006_Hermetic_Magnetic_Can_REFINED_CANDIDATE.SLDDRW");
            File.Copy(drawing,dst,false);

            SldWorks sw=null;try{sw=Marshal.GetActiveObject("SldWorks.Application") as SldWorks;}catch{}
            if(sw==null){Type t=Type.GetTypeFromProgID("SldWorks.Application");Need(t!=null,"SW ProgID missing");sw=Activator.CreateInstance(t) as SldWorks;Need(sw!=null,"SW activate failed");sw.Visible=true;}
            Need(typeof(SldWorks).Assembly.GetName().Version.Major==26,"requires SW2018 interop major 26");
            int er=0,wr=0;
            ModelDoc2 doc=sw.OpenDoc6(dst,(int)swDocumentTypes_e.swDocDRAWING,(int)swOpenDocOptions_e.swOpenDocOptions_Silent,"",ref er,ref wr) as ModelDoc2;
            Need(doc!=null,"open drawing failed e="+er+" w="+wr);
            DrawingDoc dr=doc as DrawingDoc;Need(dr!=null,"not drawing");
            List<VRec> views=ModelViews(dr,Path.GetFileName(part));
            Need(views.Count>=3,"expected >=3 P007 model views; got "+views.Count);

            VRec section=null,end=null,side=null;
            foreach(VRec v in views)if(v.section&&section==null)section=v;
            foreach(VRec v in views)if(!v.section&&v.aspect>0.80&&v.aspect<1.25&&end==null)end=v;
            foreach(VRec v in views)if(!v.section&&v!=end&&(v.aspect>=1.25||v.aspect<=0.80)&&side==null)side=v;
            if(section==null)section=views[views.Count-1];
            if(end==null)foreach(VRec v in views)if(v!=section){end=v;break;}
            if(side==null)foreach(VRec v in views)if(v!=section&&v!=end){side=v;break;}

            // A3 landscape target. Scale values are supplied by the controlled ISO 5455 profile.
            // Keep the parent side view because the section may depend on it.
            if(side!=null)SetView(side.v,0.100,0.225,sideScale);
            if(end!=null)SetView(end.v,0.315,0.215,endScale);
            if(section!=null)SetView(section.v,0.145,0.105,sectionScale);
            doc.EditRebuild3();

            HashSet<string> dx=ExistingDx(dr);
            var kept=new List<string>();var removed=new List<string>();
            // Import into likely end and longitudinal/section views. Filter returned annotations to DimXpert only.
            if(end!=null)ImportOnlyDimXpert(doc,dr,end.v,dx,kept,removed);
            if(side!=null)ImportOnlyDimXpert(doc,dr,side.v,dx,kept,removed);
            if(section!=null)ImportOnlyDimXpert(doc,dr,section.v,dx,kept,removed);
            doc.EditRebuild3();

            int finalDx=ExistingDx(dr).Count;
            SaveAs(doc,dst);

            string pdf=Path.ChangeExtension(dst,"PDF"),bmp=Path.ChangeExtension(dst,"BMP");
            int pe=0,pw=0;bool pdfOk=doc.Extension.SaveAs(pdf,(int)swSaveAsVersion_e.swSaveAsCurrentVersion,(int)swSaveAsOptions_e.swSaveAsOptions_Silent,null,ref pe,ref pw);
            doc.ViewZoomtofit2();bool bmpOk=doc.SaveBMP(bmp,1800,1273);
            sw.CloseDoc(doc.GetTitle());

            Need(Sha(drawing)==drawingSha,"source drawing changed");
            Need(Sha(part)==partSha,"source part changed");
            Need(File.Exists(dst)&&new FileInfo(dst).Length>4096,"refined drawing missing/small");
            Need(pdfOk&&File.Exists(pdf),"PDF export failed");

            var sb=new StringBuilder();
            sb.AppendLine("STATUS=PASS_D006_EXISTING_DRAWING_REFINED_CANDIDATE");
            sb.AppendLine("SOURCE_DRAWING="+drawing);
            sb.AppendLine("SOURCE_DRAWING_SHA="+drawingSha);
            sb.AppendLine("SOURCE_PART="+part);
            sb.AppendLine("SOURCE_PART_SHA="+partSha);
            sb.AppendLine("OUTPUT_DRAWING="+dst);
            sb.AppendLine("OUTPUT_PDF="+pdf);
            sb.AppendLine("OUTPUT_BMP="+bmp);
            sb.AppendLine("P007_VIEW_COUNT="+views.Count);
            sb.AppendLine("SECTION_VIEW="+(section==null?"":section.name));
            sb.AppendLine("END_VIEW="+(end==null?"":end.name));
            sb.AppendLine("SIDE_VIEW="+(side==null?"":side.name));
            sb.AppendLine("SECTION_SCALE="+sectionScale.ToString(System.Globalization.CultureInfo.InvariantCulture)+":1");
            sb.AppendLine("END_SCALE="+endScale.ToString(System.Globalization.CultureInfo.InvariantCulture)+":1");
            sb.AppendLine("SIDE_SCALE="+sideScale.ToString(System.Globalization.CultureInfo.InvariantCulture)+":1");
            sb.AppendLine("DIMXPERT_EXISTING_OR_IMPORTED_COUNT="+finalDx);
            sb.AppendLine("DIMXPERT_NEW="+String.Join(",",kept.ToArray()));
            sb.AppendLine("FILTERED_IMPORTED_ANNOTATIONS="+removed.Count);
            sb.AppendLine("SOURCE_DRAWING_INVARIANT=True");
            sb.AppendLine("SOURCE_PART_INVARIANT=True");
            File.WriteAllText(report,sb.ToString(),Encoding.UTF8);

            Console.WriteLine("STATUS: PASS_D006_EXISTING_DRAWING_REFINED_CANDIDATE");
            Console.WriteLine("OUTPUT: "+dst);
            Console.WriteLine("PDF: "+pdf);
            Console.WriteLine("BMP: "+bmp);
            Console.WriteLine("VIEWS: "+views.Count+" section="+(section==null?"":section.name)+" end="+(end==null?"":end.name)+" side="+(side==null?"":side.name));
            Console.WriteLine("DIMXPERT COUNT: "+finalDx+" new="+String.Join(",",kept.ToArray()));
            return 0;
        }catch(Exception ex){
            try{File.WriteAllText(report,"STATUS=HOLD\nERROR="+ex.ToString()+"\n",Encoding.UTF8);}catch{}
            Console.Error.WriteLine(ex.ToString());return 2;
        }
    }
}
