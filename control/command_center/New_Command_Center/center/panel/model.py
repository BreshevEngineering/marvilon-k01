"""Presentation adapter. Never evaluates engineering acceptance."""
import hashlib,json,mimetypes,subprocess
from pathlib import Path
from datetime import datetime,timezone

DEFAULTS={'verdict':'evidence/verdict.json','graph':'control/graph.json','ebom':'reports/bom/current/K01_EBOM_A001_CURRENT.json','mbom':'reports/bom/current/K01_MBOM_A001_CURRENT.json','artifacts':'evidence/current/K01_EVIDENCE_INDEX.json','ledger':'evidence/ledger.jsonl','cad_root':None,'commands':{'verdict':['verdict'],'audit':['audit'],'selftest':['selftest']}}

def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()

def records(value):
 if isinstance(value,list):return [v for v in value if isinstance(v,dict)]
 if isinstance(value,dict):return [dict(v,id=v.get('id',k)) for k,v in value.items() if isinstance(v,dict)]
 return []

def reasons(v):
 x=v.get('reasons',v.get('reason',v.get('issues',[])))
 return x if isinstance(x,list) else [x] if x else []

class Model:
 def __init__(self,root):
  self.root=Path(root).resolve();self.cfg=dict(DEFAULTS);p=self.root/'center/panel/config.json'
  if p.exists():self.cfg.update(json.loads(p.read_text(encoding='utf-8-sig')))
  self.files={}
 def resolve(self,raw):
  p=Path(raw);p=(self.root/p).resolve() if not p.is_absolute() else p.resolve()
  roots=[self.root]
  if self.cfg.get('cad_root'):roots.append(Path(self.cfg['cad_root']).resolve())
  if not any(p.is_relative_to(r) for r in roots):raise ValueError('Path outside configured roots')
  return p
 def register(self,p):
  p=self.resolve(str(p));key=hashlib.sha256(str(p).encode()).hexdigest()[:24];self.files[key]=p;return key
 def source(self,key):
  raw=self.cfg[key];info={'path':raw,'state':'MISSING','sha256':None,'file_id':None}
  try:
   p=self.resolve(raw)
   if not p.is_file():return {},info
   data=p.read_bytes();info.update(state='AVAILABLE',sha256=hashlib.sha256(data).hexdigest(),file_id=self.register(p),modified=datetime.fromtimestamp(p.stat().st_mtime,timezone.utc).isoformat())
   d=json.loads(data.decode('utf-8-sig'))
   if not isinstance(d,(dict,list)):raise ValueError('JSON object or array expected')
   return d,info
  except (OSError,ValueError) as e:info.update(state='ERROR',error=str(e));return {},info
 def git_state(self):
  try:
   def call(args):
    r=subprocess.run(["git","-C",str(self.root)]+args,capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=5)
    if r.returncode:raise ValueError(r.stderr.strip())
    return r.stdout.strip()
   branch=call(["branch","--show-current"]);head=call(["rev-parse","HEAD"]);history=call(["log","-12","--format=%h%x09%aI%x09%s"])
   return {"state":"AVAILABLE","branch":branch,"head":head,"commits":[dict(zip(["hash","date","subject"],x.split("\t",2))) for x in history.splitlines()]}
  except (OSError,ValueError,subprocess.TimeoutExpired) as e:return {"state":"UNAVAILABLE","reason":str(e)}
 def state(self):
  self.files={};docs={};sources={}
  for key in ['verdict','graph','ebom','mbom','artifacts']:docs[key],sources[key]=self.source(key)
  v=docs['verdict'];v=v if isinstance(v,dict) else {}
  raw=v.get('overall',v.get('verdict',v.get('status')))
  if isinstance(raw,dict):raw=raw.get('status')
  if sources['verdict']['state']=='AVAILABLE' and not isinstance(raw,str):sources['verdict'].update(state='ERROR',error='No overall/verdict/status string in selected source')
  overall=raw if sources['verdict']['state']=='AVAILABLE' else sources['verdict']['state']
  groups={k:records(v.get(k,[])) for k in ['nodes','requirements','gates','blockers']}
  for rs in groups.values():
   for x in rs:x['reasons']=reasons(x)
  blockers=groups['blockers']
  if not blockers:
   blockers=[dict(x,kind=k) for k in ['nodes','requirements','gates'] for x in groups[k] if x.get('status') not in ('PASS','NOT_APPLICABLE')]
  boms={}
  for k in ['ebom','mbom']:
   d=docs[k];d=d if isinstance(d,dict) else {};boms[k]={'status':d.get('status',sources[k]['state']),'rows':records(d.get('rows',d.get('items',[]))),'reasons':reasons(d),'transformations':d.get('manufacturing_transformations',[])}
  d=docs['artifacts'];ars=records(d if isinstance(d,list) else d.get('artifacts',d.get('entries',d.get('items',[]))))
  for a in ars:
   raw=a.get('path',a.get('file_path'));a['file_id']=None
   if not isinstance(raw,str):a['availability']='NO_PATH';continue
   try:
    p=self.resolve(raw);a['availability']='AVAILABLE' if p.is_file() else 'MISSING'
    if p.is_file():a['file_id']=self.register(p);a['extension']=p.suffix.lower()
   except (ValueError,OSError):a['availability']='OUTSIDE_ROOT'
  history=[];history_errors=[]
  try:
   p=self.resolve(self.cfg['ledger'])
   if p.exists():
    lines=p.read_text(encoding='utf-8-sig').splitlines()
    for i,line in enumerate(lines[-200:],max(1,len(lines)-199)):
     try:history.append(json.loads(line))
     except ValueError:history_errors.append(f'Ledger line {i}: invalid JSON')
  except (ValueError,OSError) as e:history_errors.append(str(e))
  # Input integrity is a transport observation, NOT a replacement engineering verdict.
  checks=[]
  for item in v.get('inputs',[]):
   if not isinstance(item,dict) or not item.get('path'):continue
   expected=item.get('sha256',item.get('physical_sha256'));obs='UNVERIFIED'
   try:
    p=self.resolve(item['path']);obs='MISSING' if not p.is_file() else ('MATCH' if digest(p)==expected else 'CHANGED') if expected else 'UNVERIFIED'
   except (ValueError,OSError):obs='ERROR'
   checks.append({'path':item['path'],'state':obs})
  return {'git':self.git_state(),'schema':'k01.center.view.v1','overall':overall,'generated_utc':v.get('generated_utc',v.get('utc')),'sources':sources,'groups':groups,'blockers':blockers,'boms':boms,'graph':docs['graph'],'artifacts':ars,'history':list(reversed(history)),'history_errors':history_errors,'input_checks':checks,'freshness':v.get('freshness','NOT_DECLARED'),'commands':list(self.cfg['commands']),'repo_root':str(self.root)}
