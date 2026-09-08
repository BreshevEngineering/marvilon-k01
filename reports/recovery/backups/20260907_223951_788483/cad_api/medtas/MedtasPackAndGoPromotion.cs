using System;
using System.IO;
using System.Collections.Generic;
using SolidWorks.Interop.sldworks;
using SolidWorks.Interop.swconst;
using System.Runtime.InteropServices;

public class MedtasPackAndGoPromotion {
  [STAThread]
  public static int Main(string[] args) {
    if(args.Length<3){Console.Error.WriteLine("usage: exe sourceAssembly targetFolder baselineJson"); return 2;}
    string src=Path.GetFullPath(args[0]); string dst=Path.GetFullPath(args[1]);
    try {
      SldWorks sw=(SldWorks)Marshal.GetActiveObject("SldWorks.Application");
      int err=0,warn=0; ModelDoc2 doc=sw.GetOpenDocumentByName(src) as ModelDoc2;
      if(doc==null) doc=sw.OpenDoc6(src,(int)swDocumentTypes_e.swDocASSEMBLY,(int)swOpenDocOptions_e.swOpenDocOptions_Silent,"",ref err,ref warn);
      if(doc==null){Console.Error.WriteLine("Cannot open source assembly err="+err); return 3;}
      Directory.CreateDirectory(dst);
      PackAndGo pg=doc.Extension.GetPackAndGo();
      pg.IncludeDrawings=false; pg.IncludeSimulationResults=false; pg.FlattenToSingleFolder=true;
      object namesObj=pg.GetDocumentNames(); object[] names=(object[])namesObj;
      string[] newNames=new string[names.Length];
      Dictionary<string,string> rename=new Dictionary<string,string>(StringComparer.OrdinalIgnoreCase){
        {"K01-A-001_GATE04E_P006_SERVICE_VERIFY.SLDASM","K01-A-001_Calibration_Module.SLDASM"},
        {"K01-P-003_Cartridge_Body_GATE04D_C2R1_CANDIDATE.SLDPRT","K01-P-003_Cartridge_Body.SLDPRT"},
        {"K01-P-006_Retaining_Plug_GATE04E_SERVICE_CANDIDATE.SLDPRT","K01-P-006_Retaining_Plug.SLDPRT"},
        {"K01-P-007_Hermetic_Magnetic_Can_GATE04D_C2R1_CANDIDATE.SLDPRT","K01-P-007_Hermetic_Magnetic_Can.SLDPRT"},
        {"K01-B-001_Internal_SmCo_Magnet_D8x8_REFERENCE.SLDPRT","K01-B-001_Internal_SmCo_Magnet.SLDPRT"}
      };
      for(int i=0;i<names.Length;i++){
        string old=Convert.ToString(names[i]); string fn=Path.GetFileName(old); string nn=rename.ContainsKey(fn)?rename[fn]:fn; newNames[i]=Path.Combine(dst,nn);
      }
      bool ok=pg.SetDocumentSaveToNames(newNames); if(!ok){Console.Error.WriteLine("SetDocumentSaveToNames failed");return 4;}
      object statusObj=doc.Extension.SavePackAndGo(pg); int[] status=(int[])statusObj;
      int bad=0; for(int i=0;i<status.Length;i++){ Console.WriteLine(newNames[i]+" status="+status[i]); if(status[i]!=0) bad++; }
      return bad==0?0:5;
    } catch(Exception ex){Console.Error.WriteLine(ex.ToString()); return 10;}
  }
}
