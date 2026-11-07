"""Full static source inventory; no supplied application code is imported or run."""
import argparse,hashlib,json,subprocess,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts.build_subway_code_ontology import ARCHIVES
from scripts.integration_config import private_write

# These are infrastructure/security stores, not missing business ontology concepts.
EXCLUDED={'api-log','audit-log','auditlog','bcApiLog','token','user','client-secret','api-client','mail','master-id-counter','otp','notification','user-id-counter','user-properties','store-id-tracker','notice-id-tracker','store-update-tracker','sample'}
def inventory():
 result={'archives':{},'files':[]};inputs=[]
 for app,filename in ARCHIVES.items():
  path=ROOT/filename;result['archives'][app]={'name':filename,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
  with zipfile.ZipFile(path) as z:
   for info in z.infolist():
    if info.is_dir() or '/src/' not in info.filename or not info.filename.endswith('.js'):continue
    relative=info.filename.split('/src/',1)[1]
    if not relative.startswith(('models/','services/')):continue
    raw=z.read(info);key=app+'|'+relative;inputs.append({'key':key,'text':raw.decode('utf8')})
    result['files'].append({'key':key,'application':app,'member':info.filename,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)})
 scans=json.loads(subprocess.check_output(['node',str(ROOT/'scripts/subway_coverage_scan.mjs')],input=json.dumps({'sources':inputs}),text=True))
 for f in result['files']:
  scan=scans[f['key']];f.update(scan)
  stem=Path(f['member']).name.removesuffix('.js').removesuffix('.model')
  f['classification']='service' if '/services/' in f['member'] else 'infrastructure_or_security' if stem in EXCLUDED or '/plugins/' in f['member'] else 'business_model' if scan['models'] else 'schema_or_helper'
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=inventory()
 # Guard bodies are only a discovery index, never automatically policy rules.
 for f in r['files']:
  for guard in f['guards']:guard['quote_sha256']=hashlib.sha256(guard.pop('quote').encode()).hexdigest()
 private_write(a.output,json.dumps(r,indent=2)+'\n')
 print(json.dumps({k:sum(f['classification']==k for f in r['files']) for k in ['business_model','infrastructure_or_security','schema_or_helper','service']}))
