"""Navigation and evidence discovery; no engineering acceptance decisions."""
from pathlib import Path
import re

def collect_paths(data):
 result=[]
 def walk(x):
  if isinstance(x,dict):
   for v in x.values():walk(v)
  elif isinstance(x,list):
   for v in x:walk(v)
  elif isinstance(x,str) and len(x)<600 and re.search(r'\.(json|pdf|csv|xlsx|md|txt|log|step|stp|sldprt|sldasm|slddrw|cmd|py|png)$',x,re.I):result.append(x)
 walk(data)
 return list(dict.fromkeys(result))

def connect(model,docs,artifacts):
 seen={a.get('path') for a in artifacts}
 candidates=collect_paths(docs)
 # Read the actual command catalog without guessing executable arguments.
 catalog=model.root/'control/commands/K01_COMMAND_CATALOG.json'
 commands={}
 if catalog.is_file():
  import json
  try:commands=json.loads(catalog.read_text(encoding='utf-8-sig'))
  except (ValueError,OSError):pass
 candidates+=collect_paths(commands)
 # Supplement an unfamiliar index schema with files in bounded report folders.
 for rel in ['evidence/current','reports/bom/current','reports/cad/current','reports/drawings/current','control/product_definition','control/project']:
  folder=model.root/rel
  if folder.is_dir():
   candidates.extend(str(p) for p in sorted(folder.iterdir()) if p.is_file() and p.suffix.lower() in {'.json','.pdf','.csv','.md','.txt','.png'})
 if catalog.is_file():candidates.append(str(catalog))
 for raw in candidates:
  if raw in seen:continue
  seen.add(raw)
  try:
   p=model.resolve(raw.replace('\\','/'))
   exists=p.is_file()
   artifacts.append({'id':p.name,'path':raw,'availability':'AVAILABLE' if exists else 'MISSING','file_id':model.register(p) if exists else None,'extension':p.suffix.lower(),'source':'Referenced by connected project documents'})
  except (ValueError,OSError):continue
 return commands
