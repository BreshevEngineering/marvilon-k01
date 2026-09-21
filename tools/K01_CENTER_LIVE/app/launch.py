import sys
sys.dont_write_bytecode=True
import json,os,traceback,webbrowser,errno
from pathlib import Path
APP=Path(__file__).resolve().parent
HOME_DIR=APP.parent
class Tee:
 def __init__(self,console,log):self.console=console;self.log=log
 def write(self,s):
  self.log.write(s);self.log.flush()
  try:self.console.write(s);self.console.flush()
  except UnicodeEncodeError:self.console.write(s.encode('ascii','backslashreplace').decode())
 def flush(self):self.console.flush();self.log.flush()
def main():
 runtime=HOME_DIR/'runtime';runtime.mkdir(exist_ok=True)
 with (runtime/'CENTER_STARTUP.log').open('a',encoding='utf-8') as log:
  stdout,stderr=sys.stdout,sys.stderr;sys.stdout=Tee(stdout,log);sys.stderr=Tee(stderr,log)
  try:
   if sys.version_info<(3,10):raise RuntimeError('Python 3.10 or newer is required.')
   config=json.loads((HOME_DIR/'settings.json').read_text(encoding='utf-8-sig'))
   root=Path(config['repo_root']).resolve()
   if not root.is_dir():raise RuntimeError('Project folder does not exist: '+str(root)+'. Edit repo_root in settings.json.')
   from server import Server
   port=int(config.get('port',8792))
   try:s=Server(root,port)
   except OSError as e:
    if e.errno not in (errno.EADDRINUSE,10048):raise
    s=Server(root,0)
   state=s.model.state()
   (runtime/'SOURCE_DIAGNOSTICS.json').write_text(json.dumps(state,indent=2,ensure_ascii=False),encoding='utf-8')
   print('\nK01 CENTER - STANDALONE ENGLISH EDITION')
   print('Application:',HOME_DIR);print('Project:',root)
   for key,src in state['sources'].items():print(key+': '+src['state']+' | '+src['path'])
   print('Open:',s.origin);print('Keep this window open. Press Ctrl+C to stop.')
   webbrowser.open(s.origin)
   try:s.serve_forever()
   except KeyboardInterrupt:print('Center stopped.')
   finally:s.server_close()
   return 0
  except Exception:
   traceback.print_exc();return 2
  finally:sys.stdout,sys.stderr=stdout,stderr
if __name__=='__main__':raise SystemExit(main())
