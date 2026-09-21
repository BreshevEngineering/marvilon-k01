using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Windows.Automation;
using SolidWorks.Interop.sldworks;
using SolidWorks.Interop.swconst;
using SolidWorks.Interop.swdimxpert;

public class K01D006AutomatedNativePmiV6
{
    [DllImport("user32.dll")] static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] static extern bool ShowWindow(IntPtr hWnd,int nCmdShow);
    const int SW_RESTORE=9;

    static void Need(bool ok,string msg){if(!ok)throw new Exception(msg);}
    static string Arg(string[] a,string k){for(int i=0;i<a.Length-1;i++)if(a[i]==k)return a[i+1];return null;}
    static IEnumerable Items(object o){
        if(o==null)yield break; Array a=o as Array;if(a!=null){foreach(object x in a)yield return x;yield break;}
        IEnumerable e=o as IEnumerable;if(e!=null)foreach(object x in e)yield return x;
    }
    static bool Eq(string a,string b){return String.Equals(a??"",b??"",StringComparison.OrdinalIgnoreCase);}
    static string Sha(string p){using(FileStream fs=new FileStream(p,FileMode.Open,FileAccess.Read,FileShare.ReadWrite|FileShare.Delete))using(SHA256 h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(fs)).Replace("-","").ToLowerInvariant();}
    static string ViewName(View v){try{return v.GetName2()??"";}catch{return "";}}
    static string RefModel(View v){try{return v.GetReferencedModelName()??"";}catch{return "";}}
    static string DxFeatureName(Annotation a){try{object f=a.GetDimXpertFeature();DimXpertFeature dx=f as DimXpertFeature;return dx==null?"":dx.Name;}catch{return "";}}
    static string DxName(Annotation a){try{return a.GetDimXpertName()??"";}catch{return "";}}
    static bool IsC02(Annotation a){return Eq(DxFeatureName(a),"Cylinder1")&&Eq(DxName(a),"Diameter2");}
    static bool IsC05(Annotation a){return Eq(DxFeatureName(a),"Cylinder2")&&Eq(DxName(a),"Diameter4");}

    static double[] Dbl(object o){var x=new List<double>();foreach(object q in Items(o)){try{x.Add(Convert.ToDouble(q,CultureInfo.InvariantCulture));}catch{}}return x.ToArray();}
    static string GeometryFingerprint(ModelDoc2 m){
        var sig=new List<string>();PartDoc p=m as PartDoc;Need(p!=null,"not part for geometry fingerprint");
        foreach(object bo in Items(p.GetBodies2((int)swBodyType_e.swSolidBody,true))){Body2 b=bo as Body2;if(b==null)continue;
            foreach(object fo in Items(b.GetFaces())){Face2 f=fo as Face2;if(f==null)continue;string s="unknown";double area=0;try{area=Convert.ToDouble(f.GetArea(),CultureInfo.InvariantCulture);}catch{}
                try{Surface su=f.IGetSurface();if(su.IsPlane()){s="plane|"+String.Join(",",Array.ConvertAll(Dbl(su.PlaneParams),z=>z.ToString("G17",CultureInfo.InvariantCulture)));}
                    else if(su.IsCylinder()){s="cyl|"+String.Join(",",Array.ConvertAll(Dbl(su.CylinderParams),z=>z.ToString("G17",CultureInfo.InvariantCulture)));}
                    else if(su.IsCone())s="cone";else if(su.IsSphere())s="sphere";else s="other";}catch{}
                sig.Add(s+"|A="+area.ToString("G17",CultureInfo.InvariantCulture));
            }
        }
        sig.Sort(StringComparer.Ordinal);byte[] raw=Encoding.UTF8.GetBytes(String.Join("\n",sig.ToArray()));using(SHA256 h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(raw)).Replace("-","").ToLowerInvariant();
    }

    static Annotation FindDxAnnotation(ModelDoc2 m,string feat,string name){
        foreach(object ao in Items(m.Extension.GetAnnotations())){Annotation a=ao as Annotation;if(a==null)continue;if(Eq(DxFeatureName(a),feat)&&Eq(DxName(a),name))return a;}return null;
    }
    static DimensionTolerance TolFrom(Annotation a){
        Need(a!=null,"DimXpert annotation missing");object sp=a.GetSpecificAnnotation();DisplayDimension dd=sp as DisplayDimension;Need(dd!=null,"DimXpert annotation is not DisplayDimension: "+DxName(a));
        Dimension d=dd.GetDimension2(0);Need(d!=null,"GetDimension2 failed: "+DxName(a));DimensionTolerance t=d.Tolerance as DimensionTolerance;Need(t!=null,"DimensionTolerance missing: "+DxName(a));return t;
    }
    class Semantics{public bool c02,c05;public string c02Type="",c02Hole="",c02Shaft="",c05Type="";}
    static Semantics ReadSemantics(ModelDoc2 m){
        Semantics s=new Semantics();Annotation a02=FindDxAnnotation(m,"Cylinder1","Diameter2"),a05=FindDxAnnotation(m,"Cylinder2","Diameter4");
        if(a02!=null){DimensionTolerance t=TolFrom(a02);s.c02Type=((swTolType_e)t.Type).ToString();try{s.c02Hole=t.GetHoleFitValue()??"";}catch{}try{s.c02Shaft=t.GetShaftFitValue()??"";}catch{}s.c02=(t.Type==(int)swTolType_e.swTolFIT && Eq(s.c02Hole,"H7") && String.IsNullOrWhiteSpace(s.c02Shaft));}
        if(a05!=null){DimensionTolerance t=TolFrom(a05);s.c05Type=((swTolType_e)t.Type).ToString();s.c05=t.Type==(int)swTolType_e.swTolNONE;}
        return s;
    }
    static void AuthorSemantics(ModelDoc2 m,List<string> log){
        Annotation a02=FindDxAnnotation(m,"Cylinder1","Diameter2"),a05=FindDxAnnotation(m,"Cylinder2","Diameter4");Need(a02!=null,"C02 Cylinder1/Diameter2 missing in source PMI");Need(a05!=null,"C05 Cylinder2/Diameter4 missing in source PMI");
        DimensionTolerance t02=TolFrom(a02);t02.Type=(int)swTolType_e.swTolFIT;bool fitOk=t02.SetFitValues("H7","");log.Add("PMI_C02_SET type=swTolFIT hole=H7 shaft=<empty> setFitReturn="+fitOk);
        DimensionTolerance t05=TolFrom(a05);t05.Type=(int)swTolType_e.swTolNONE;log.Add("PMI_C05_SET type=swTolNONE");
        try{m.GraphicsRedraw2();}catch{}
    }
    static void SavePart(ModelDoc2 m){int e=0,w=0;bool ok=m.Save3((int)swSaveAsOptions_e.swSaveAsOptions_Silent,ref e,ref w);Need(ok&&e==0,"part Save3 failed e="+e+" w="+w);}

    class ScanResult{public int count;public bool c02,c05,c02Sem,c05Sem;public string c02Type="",c02Hole="",c05Type="";public List<string> rows=new List<string>();}
    static ScanResult Scan(DrawingDoc dr,string partBase){
        ScanResult r=new ScanResult();View v=dr.GetFirstView() as View;
        while(v!=null){string rm=RefModel(v);bool p007=!String.IsNullOrWhiteSpace(rm)&&Eq(Path.GetFileName(rm),partBase);if(p007){
            foreach(object ao in Items(v.GetAnnotations())){Annotation a=ao as Annotation;if(a==null)continue;string f=DxFeatureName(a),n=DxName(a);if(String.IsNullOrWhiteSpace(f)&&String.IsNullOrWhiteSpace(n))continue;r.count++;string extra="";
                try{DimensionTolerance t=TolFrom(a);extra=";T="+((swTolType_e)t.Type).ToString();if(IsC02(a)){string h="",sh="";try{h=t.GetHoleFitValue()??"";}catch{}try{sh=t.GetShaftFitValue()??"";}catch{}r.c02=true;r.c02Type=((swTolType_e)t.Type).ToString();r.c02Hole=h;r.c02Sem=t.Type==(int)swTolType_e.swTolFIT&&Eq(h,"H7")&&String.IsNullOrWhiteSpace(sh);extra+=";H="+h+";S="+sh;}if(IsC05(a)){r.c05=true;r.c05Type=((swTolType_e)t.Type).ToString();r.c05Sem=t.Type==(int)swTolType_e.swTolNONE;}}
                catch(Exception ex){extra=";SEMERR="+ex.GetType().Name;}
                r.rows.Add("VIEW="+ViewName(v)+";F="+f+";N="+n+extra);
            }}v=v.GetNextView() as View;}
        return r;
    }

    static AutomationElement SwWindow(){Process[] ps=Process.GetProcessesByName("SLDWORKS");if(ps==null||ps.Length==0)return null;Process best=ps[0];for(int i=0;i<ps.Length;i++)if(ps[i].MainWindowHandle!=IntPtr.Zero){best=ps[i];break;}if(best.MainWindowHandle==IntPtr.Zero)return null;try{ShowWindow(best.MainWindowHandle,SW_RESTORE);SetForegroundWindow(best.MainWindowHandle);}catch{}try{return AutomationElement.FromHandle(best.MainWindowHandle);}catch{return null;}}
    static List<AutomationElement> Desc(AutomationElement root,ControlType type){var r=new List<AutomationElement>();if(root==null)return r;try{Condition c=new PropertyCondition(AutomationElement.ControlTypeProperty,type);AutomationElementCollection xs=root.FindAll(TreeScope.Descendants,c);foreach(AutomationElement x in xs)r.Add(x);}catch{}return r;}
    static List<AutomationElement> DescAll(AutomationElement root){var r=new List<AutomationElement>();if(root==null)return r;try{AutomationElementCollection xs=root.FindAll(TreeScope.Descendants,Condition.TrueCondition);foreach(AutomationElement x in xs)r.Add(x);}catch{}return r;}
    static string AName(AutomationElement e){try{return(e.Current.Name??"").Trim();}catch{return"";}} static string AId(AutomationElement e){try{return(e.Current.AutomationId??"").Trim();}catch{return"";}}
    static string AType(AutomationElement e){try{return e.Current.ControlType==null?"":e.Current.ControlType.ProgrammaticName;}catch{return"";}}
    static bool ContainsI(string s,string q){return(s??"").IndexOf(q,StringComparison.OrdinalIgnoreCase)>=0;}
    static bool HasToggle(AutomationElement e){try{return e.GetCurrentPattern(TogglePattern.Pattern) is TogglePattern;}catch{return false;}}
    static void DumpUi(AutomationElement root,List<string> log){int n=0;foreach(AutomationElement e in DescAll(root)){string name=AName(e),id=AId(e);if(String.IsNullOrWhiteSpace(name)&&String.IsNullOrWhiteSpace(id))continue;log.Add("UI_ELEM type="+AType(e)+" toggle="+HasToggle(e)+" name="+name+" id="+id);if(++n>=180){log.Add("UI_ELEM_TRUNCATED=180");break;}}}
    static AutomationElement FindToggle(AutomationElement root,string kind){foreach(AutomationElement e in DescAll(root)){if(!HasToggle(e))continue;string s=AName(e)+" "+AId(e);if(kind=="dimxpert"&&ContainsI(s,"dimxpert"))return e;if(kind=="design"&&ContainsI(s,"design")&&ContainsI(s,"annotation"))return e;if(kind=="import"&&ContainsI(s,"import")&&ContainsI(s,"annotation")&&!ContainsI(s,"design")&&!ContainsI(s,"dimxpert"))return e;}return null;}
    static bool SetCheck(AutomationElement e,bool want,List<string> log,string label){if(e==null){log.Add("UI_SET "+label+"=MISSING");return false;}try{TogglePattern t=e.GetCurrentPattern(TogglePattern.Pattern) as TogglePattern;if(t==null){log.Add("UI_SET "+label+"=NO_TOGGLE_PATTERN");return false;}bool on=t.Current.ToggleState==ToggleState.On;if(on!=want)t.Toggle();Thread.Sleep(250);bool after=t.Current.ToggleState==ToggleState.On;log.Add("UI_SET "+label+"="+after+" target="+want+" name="+AName(e)+" id="+AId(e));return after==want;}catch(Exception ex){log.Add("UI_SET "+label+"=ERROR "+ex.GetType().Name+":"+ex.Message);return false;}}
    static bool AcceptPropertyManager(AutomationElement root,List<string> log){foreach(AutomationElement e in Desc(root,ControlType.Button)){string n=AName(e),id=AId(e),s=n+" "+id;if(Eq(n,"OK")||Eq(n,"Accept")||ContainsI(s,"accept")||ContainsI(s,"green check")){try{InvokePattern ip=e.GetCurrentPattern(InvokePattern.Pattern) as InvokePattern;if(ip!=null){ip.Invoke();log.Add("UI_ACCEPT button="+n+" id="+id);Thread.Sleep(700);return true;}}catch{}}}try{System.Windows.Forms.SendKeys.SendWait("{ENTER}");log.Add("UI_ACCEPT fallback=ENTER");Thread.Sleep(700);return true;}catch(Exception ex){log.Add("UI_ACCEPT ERROR "+ex.Message);return false;}}
    static bool SelectView(ModelDoc2 doc,DrawingDoc dr,View v,List<string> log){string n=ViewName(v);if(String.IsNullOrWhiteSpace(n))return false;doc.ClearSelection2(true);bool a=false,s=false;try{a=dr.ActivateView(n);}catch{}string unique=n;try{string u=v.GetUniqueName();if(!String.IsNullOrWhiteSpace(u))unique=u;}catch{}try{s=doc.Extension.SelectByID2(unique,"DRAWINGVIEW",0,0,0,false,0,null,0);}catch{}if(!s&&!Eq(unique,n))try{s=doc.Extension.SelectByID2(n,"DRAWINGVIEW",0,0,0,false,0,null,0);}catch{}log.Add("VIEW_SELECT name="+n+" unique="+unique+" activate="+a+" select="+s);return a&&s;}
    static AutomationElement OpenViewPropertyManager(SldWorks sw,ModelDoc2 doc,List<string> log){
        // Stable SOLIDWORKS command IDs: Drawing_Feat_Edit=2693 (drawing-view RMB > Edit Feature);
        // Display_Property_Dve=1884 is a legacy drawing-view PropertyManager display fallback.
        int[] cmds=new int[]{2693,1884};
        for(int i=0;i<cmds.Length;i++){bool enabled=false,ran=false;try{enabled=sw.IsCommandEnabled(cmds[i]);}catch{}try{ran=doc.Extension.RunCommand(cmds[i],"K01 D006 Drawing View");}catch(Exception ex){log.Add("UI_PM_CMD id="+cmds[i]+" enabled="+enabled+" ERROR="+ex.GetType().Name+":"+ex.Message);}
            log.Add("UI_PM_CMD id="+cmds[i]+" enabled="+enabled+" ran="+ran);Thread.Sleep(1100);AutomationElement root=SwWindow();if(root==null)continue;int toggles=0;foreach(AutomationElement e in DescAll(root))if(HasToggle(e))toggles++;log.Add("UI_PM_SCAN id="+cmds[i]+" toggles="+toggles);if(toggles>0)return root;}
        return SwWindow();
    }
    static List<View> P007Views(DrawingDoc dr,string partBase){var r=new List<View>();View v=dr.GetFirstView() as View;if(v!=null)v=v.GetNextView() as View;while(v!=null){string rm=RefModel(v);if(!String.IsNullOrWhiteSpace(rm)&&Eq(Path.GetFileName(rm),partBase))r.Add(v);v=v.GetNextView() as View;}return r;}

    static string FindP007Reference(SldWorks sw,string drawing,List<string> log){
        object dep=null;try{dep=sw.GetDocumentDependencies2(drawing,false,true,false);}catch(Exception ex){log.Add("DEPENDENCIES_ERROR="+ex.Message);}
        var xs=new List<string>();foreach(object x in Items(dep))xs.Add(Convert.ToString(x)??"");for(int i=0;i+1<xs.Count;i+=2){string p=xs[i+1];log.Add("DEPENDENCY name="+xs[i]+" path="+p);if(Path.GetFileName(p).StartsWith("K01-P-007_Hermetic_Magnetic_Can",StringComparison.OrdinalIgnoreCase)&&p.EndsWith(".SLDPRT",StringComparison.OrdinalIgnoreCase))return p;}return "";
    }

    public static int Main(string[] args){
        string drawing=Arg(args,"--drawing"),sourcePart=Arg(args,"--part"),outDrawingRoot=Arg(args,"--drawing-out-root"),outPartRoot=Arg(args,"--part-out-root"),report=Arg(args,"--report");
        if(String.IsNullOrWhiteSpace(drawing)||String.IsNullOrWhiteSpace(sourcePart)||String.IsNullOrWhiteSpace(outDrawingRoot)||String.IsNullOrWhiteSpace(outPartRoot)||String.IsNullOrWhiteSpace(report)){Console.Error.WriteLine("missing args");return 2;}
        SldWorks sw=null;ModelDoc2 doc=null;bool created=false;var log=new List<string>();
        try{
            Need(File.Exists(drawing),"drawing missing");Need(File.Exists(sourcePart),"source PMI part missing");string sourceDrawingSha=Sha(drawing),sourcePartSha=Sha(sourcePart),stamp=DateTime.Now.ToString("yyyyMMdd_HHmmss");
            string partDir=Path.Combine(outPartRoot,"native_semantics_"+stamp);Directory.CreateDirectory(partDir);string partCandidate=Path.Combine(partDir,"K01-P-007_Hermetic_Magnetic_Can_DRAWING_SOURCE_CANDIDATE.SLDPRT");File.Copy(sourcePart,partCandidate,false);
            string drawDir=Path.Combine(outDrawingRoot,"automated_native_pmi_"+stamp);Directory.CreateDirectory(drawDir);string dst=Path.Combine(drawDir,"K01-D-006_Hermetic_Magnetic_Can_AUTOMATED_NATIVE_PMI_CANDIDATE.SLDDRW");File.Copy(drawing,dst,false);
            try{sw=Marshal.GetActiveObject("SldWorks.Application") as SldWorks;}catch{}if(sw==null){Type t=Type.GetTypeFromProgID("SldWorks.Application");Need(t!=null,"SW ProgID missing");sw=Activator.CreateInstance(t) as SldWorks;Need(sw!=null,"SW activate failed");created=true;}sw.Visible=true;Need(typeof(SldWorks).Assembly.GetName().Version.Major==26,"requires SW2018 interop major 26");

            // 1) Create a separate drawing-authoring PMI source; never mutate proven evidence source.
            int er=0,wr=0;doc=sw.OpenDoc6(partCandidate,(int)swDocumentTypes_e.swDocPART,(int)swOpenDocOptions_e.swOpenDocOptions_Silent,"",ref er,ref wr) as ModelDoc2;Need(doc!=null,"open PMI source candidate failed e="+er+" w="+wr);
            string geomBefore=GeometryFingerprint(doc);Semantics semBefore=ReadSemantics(doc);log.Add("PMI_BEFORE C02="+semBefore.c02+" type="+semBefore.c02Type+" hole="+semBefore.c02Hole+" C05="+semBefore.c05+" type="+semBefore.c05Type);
            AuthorSemantics(doc,log);SavePart(doc);string pt=doc.GetTitle();sw.CloseDoc(pt);doc=null;
            int er2=0,wr2=0;doc=sw.OpenDoc6(partCandidate,(int)swDocumentTypes_e.swDocPART,(int)(swOpenDocOptions_e.swOpenDocOptions_Silent|swOpenDocOptions_e.swOpenDocOptions_ReadOnly),"",ref er2,ref wr2) as ModelDoc2;Need(doc!=null,"reopen semantics candidate failed e="+er2+" w="+wr2);
            string geomAfter=GeometryFingerprint(doc);Semantics semAfter=ReadSemantics(doc);log.Add("PMI_AFTER C02="+semAfter.c02+" type="+semAfter.c02Type+" hole="+semAfter.c02Hole+" C05="+semAfter.c05+" type="+semAfter.c05Type);Need(geomBefore==geomAfter,"PMI semantics write changed solid geometry");Need(semAfter.c02,"C02 semantics not Ø14.10 H7 / swTolFIT after reopen");Need(semAfter.c05,"C05 tolerance type is not NONE after reopen");sw.CloseDoc(doc.GetTitle());doc=null;

            // 2) Reference-safe migration of only the timestamped drawing copy to the semantics-correct copied part.
            string oldRef=FindP007Reference(sw,dst,log);Need(!String.IsNullOrWhiteSpace(oldRef),"cannot resolve P007 reference in drawing copy");bool repl=sw.ReplaceReferencedDocument(dst,oldRef,partCandidate);log.Add("RELINK old="+oldRef+" new="+partCandidate+" return="+repl);Need(repl,"ReplaceReferencedDocument failed");

            // 3) Open existing linked drawing copy and automate only the native SW2018 DimXpert-import UI gap.
            int de=0,dw=0;doc=sw.OpenDoc6(dst,(int)swDocumentTypes_e.swDocDRAWING,(int)swOpenDocOptions_e.swOpenDocOptions_Silent,"",ref de,ref dw) as ModelDoc2;Need(doc!=null,"open drawing copy failed e="+de+" w="+dw);DrawingDoc dr=doc as DrawingDoc;Need(dr!=null,"not drawing");string partBase=Path.GetFileName(partCandidate);
            List<View> views=P007Views(dr,partBase);Need(views.Count>0,"no P007 views after reference-safe migration");ScanResult before=Scan(dr,partBase);log.Add("DRAWING_BEFORE count="+before.count+" C02="+before.c02+" C05="+before.c05);
            if(!(before.c02&&before.c05&&before.c02Sem&&before.c05Sem)){
                for(int i=0;i<views.Count;i++){View v=views[i];if(!SelectView(doc,dr,v,log))continue;Thread.Sleep(350);AutomationElement root=OpenViewPropertyManager(sw,doc,log);if(root==null){log.Add("UI_ROOT=MISSING");continue;}DumpUi(root,log);AutomationElement cbImport=FindToggle(root,"import"),cbDim=FindToggle(root,"dimxpert"),cbDesign=FindToggle(root,"design");bool importOk=SetCheck(cbImport,true,log,"IMPORT_ANNOTATIONS"),dimOk=SetCheck(cbDim,true,log,"DIMXPERT_ANNOTATIONS");SetCheck(cbDesign,false,log,"DESIGN_ANNOTATIONS");if(importOk&&dimOk){AcceptPropertyManager(root,log);try{doc.EditRebuild3();}catch{}Thread.Sleep(900);}ScanResult now=Scan(dr,partBase);log.Add("AFTER_VIEW name="+ViewName(v)+" count="+now.count+" C02="+now.c02+" C05="+now.c05+" C02SEM="+now.c02Sem+" C05SEM="+now.c05Sem);if(now.c02&&now.c05&&now.c02Sem&&now.c05Sem)break;}
            }
            ScanResult final=Scan(dr,partBase);bool pass=final.c02&&final.c05&&final.c02Sem&&final.c05Sem;string pdf=Path.ChangeExtension(dst,"PDF"),bmp=Path.ChangeExtension(dst,"BMP");bool saved=false,pdfOk=false,bmpOk=false;
            if(pass){int se=0,swarn=0;saved=doc.Extension.SaveAs(dst,(int)swSaveAsVersion_e.swSaveAsCurrentVersion,(int)swSaveAsOptions_e.swSaveAsOptions_Silent,null,ref se,ref swarn);Need(saved&&se==0,"save candidate failed e="+se+" w="+swarn);int pe=0,pw=0;pdfOk=doc.Extension.SaveAs(pdf,(int)swSaveAsVersion_e.swSaveAsCurrentVersion,(int)swSaveAsOptions_e.swSaveAsOptions_Silent,null,ref pe,ref pw);doc.ViewZoomtofit2();bmpOk=doc.SaveBMP(bmp,1800,1273);}
            sw.CloseDoc(doc.GetTitle());doc=null;Need(Sha(drawing)==sourceDrawingSha,"source drawing changed");Need(Sha(sourcePart)==sourcePartSha,"proven PMI evidence source changed");
            string status=pass?"PASS_D006_NATIVE_DIMXPERT_C02_H7_C05_OPEN_AUTOMATED":"HOLD_D006_AUTOMATED_NATIVE_PMI_NOT_IMPORTED_OR_SEMANTICS";
            var sb=new StringBuilder();sb.AppendLine("STATUS="+status);sb.AppendLine("SOURCE_DRAWING="+drawing);sb.AppendLine("SOURCE_DRAWING_SHA256="+sourceDrawingSha);sb.AppendLine("PROVEN_PMI_SOURCE="+sourcePart);sb.AppendLine("PROVEN_PMI_SOURCE_SHA256="+sourcePartSha);sb.AppendLine("DRAWING_SOURCE_PART="+partCandidate);sb.AppendLine("DRAWING_SOURCE_GEOMETRY_INVARIANT=True");sb.AppendLine("OUTPUT_DRAWING="+(pass?dst:""));sb.AppendLine("OUTPUT_PDF="+(pass?pdf:""));sb.AppendLine("OUTPUT_BMP="+(pass?bmp:""));sb.AppendLine("P007_VIEW_COUNT="+views.Count);sb.AppendLine("DIMXPERT_COUNT="+final.count);sb.AppendLine("C02="+final.c02);sb.AppendLine("C02_SEMANTICS_H7="+final.c02Sem);sb.AppendLine("C02_TOLTYPE="+final.c02Type);sb.AppendLine("C02_HOLE_FIT="+final.c02Hole);sb.AppendLine("C05="+final.c05);sb.AppendLine("C05_SEMANTICS_NONE="+final.c05Sem);sb.AppendLine("C05_TOLTYPE="+final.c05Type);sb.AppendLine("SAVED="+saved);sb.AppendLine("PDF_OK="+pdfOk);sb.AppendLine("BMP_OK="+bmpOk);sb.AppendLine("SOURCE_DRAWING_INVARIANT=True");sb.AppendLine("PROVEN_PMI_SOURCE_INVARIANT=True");for(int i=0;i<final.rows.Count;i++)sb.AppendLine("DX_"+(i+1)+"="+final.rows[i]);for(int i=0;i<log.Count;i++)sb.AppendLine("LOG_"+(i+1)+"="+log[i].Replace("\r"," ").Replace("\n"," "));File.WriteAllText(report,sb.ToString(),Encoding.UTF8);
            Console.WriteLine("STATUS: "+status);Console.WriteLine("DRAWING SOURCE PMI: "+partCandidate);Console.WriteLine("DIMXPERT COUNT: "+final.count);Console.WriteLine("C02: "+final.c02+" H7="+final.c02Sem+" type="+final.c02Type+" hole="+final.c02Hole);Console.WriteLine("C05: "+final.c05+" NONE="+final.c05Sem+" type="+final.c05Type);Console.WriteLine("P007 VIEWS: "+views.Count);Console.WriteLine("OUTPUT: "+(pass?dst:"NOT_SAVED_AS_VALID_CANDIDATE"));Console.WriteLine("PDF: "+(pass?pdf:""));Console.WriteLine("BMP: "+(pass?bmp:""));Console.WriteLine("REPORT: "+report);
            if(!pass){int shown=0;for(int i=0;i<log.Count&&shown<32;i++)if(log[i].StartsWith("PMI_")||log[i].StartsWith("UI_")||log[i].StartsWith("VIEW_")||log[i].StartsWith("AFTER_")||log[i].StartsWith("RELINK")||log[i].StartsWith("DEPENDENCY")){Console.WriteLine(log[i]);shown++;}}
            return pass?0:3;
        }catch(Exception ex){try{File.WriteAllText(report,"STATUS=HOLD_D006_AUTOMATED_NATIVE_PMI_ERROR\nERROR="+ex.ToString()+"\n",Encoding.UTF8);}catch{}Console.Error.WriteLine(ex.ToString());return 2;}
        finally{try{if(doc!=null&&sw!=null)sw.CloseDoc(doc.GetTitle());}catch{}try{if(created&&sw!=null)sw.ExitApp();}catch{}}
    }
}
