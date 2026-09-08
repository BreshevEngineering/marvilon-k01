using System;
using System.IO;
using System.Collections.Generic;
using SolidWorks.Interop.sldworks;
using SolidWorks.Interop.swconst;
using System.Runtime.InteropServices;
using System.Web.Script.Serialization;

public class MedtasPackAndGoPromotion {
  [STAThread]
  public static int Main(string[] args) {
    if(args.Length<3){Console.Error.WriteLine("usage: exe sourceAssembly targetFolder baselineJson"); return 2;}
    string src=Path.GetFullPath(args[0]); string dst=Path.GetFullPath(args[1]);
    try {
      if(!File.Exists(src)) throw new IOException("Source missing: "+src);
      if(Directory.Exists(dst) && Directory.GetFileSystemEntries(dst).Length!=0)
        throw new IOException("Destination must be empty: "+dst);
      var baseline=new JavaScriptSerializer().Deserialize<Dictionary<string,object>>(File.ReadAllText(args[2]));
      var mapping=baseline["identity_renames"] as Dictionary<string,object>;
      if(mapping==null) throw new IOException("identity_renames is missing");
      SldWorks sw=(SldWorks)Marshal.GetActiveObject("SldWorks.Application");
      int err=0,warn=0; ModelDoc2 doc=sw.GetOpenDocumentByName(src) as ModelDoc2;
      if(doc==null) doc=sw.OpenDoc6(src,(int)swDocumentTypes_e.swDocASSEMBLY,(int)swOpenDocOptions_e.swOpenDocOptions_Silent,"",ref err,ref warn);
      if(doc==null){Console.Error.WriteLine("Cannot open source assembly err="+err); return 3;}
      Directory.CreateDirectory(dst);
      PackAndGo pg=doc.Extension.GetPackAndGo();
      pg.IncludeDrawings=false; pg.IncludeSimulationResults=false; pg.FlattenToSingleFolder=true;
      object namesObj;
      if(!pg.GetDocumentNames(out namesObj)) throw new IOException("GetDocumentNames failed");
      object[] names=namesObj as object[];
      if(names==null || names.Length==0) throw new IOException("PackAndGo returned no documents");
      string[] newNames=new string[names.Length];
      var rename=new Dictionary<string,string>(StringComparer.OrdinalIgnoreCase);
      foreach(var item in mapping) rename.Add(item.Key,Convert.ToString(item.Value));
      var destinations=new HashSet<string>(StringComparer.OrdinalIgnoreCase);
      for(int i=0;i<names.Length;i++){
        string old=Convert.ToString(names[i]); string fn=Path.GetFileName(old); string nn=rename.ContainsKey(fn)?rename[fn]:fn; if(!File.Exists(old)) throw new IOException("Dependency missing: "+old);
        if(nn!=Path.GetFileName(nn) || String.IsNullOrWhiteSpace(nn)) throw new IOException("Invalid rename target");
        newNames[i]=Path.Combine(dst,nn);
        if(!destinations.Add(newNames[i])) throw new IOException("Flattening name collision: "+nn);
      }
      bool ok=pg.SetDocumentSaveToNames(newNames); if(!ok){Console.Error.WriteLine("SetDocumentSaveToNames failed");return 4;}
      object statusObj=doc.Extension.SavePackAndGo(pg); int[] status=statusObj as int[];
      if(status==null || status.Length!=names.Length) throw new IOException("Invalid PackAndGo status array");
      int bad=0; for(int i=0;i<status.Length;i++){ Console.WriteLine(newNames[i]+" status="+status[i]); if(status[i]!=0) bad++; }
      return bad==0?0:5;
    } catch(Exception ex){Console.Error.WriteLine(ex.ToString()); return 10;}
  }
}
