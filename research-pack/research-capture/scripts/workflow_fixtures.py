"""Create synthetic source-separated workflow fixtures without network/model calls."""
import json,sys,uuid,wave
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'companion'))
from workflows import Workflows,approved_import
from core import sha,now
ROOT=Path(__file__).resolve().parents[1];base=ROOT/'artifacts/workflow-fixtures';base.mkdir(parents=True,exist_ok=False)
config={'capture_root':str(base/'vault'),'downloads_root':str(base/'Downloads'),'receipt_key':'aa'*32,'media_enabled':False,'landing_enabled':False};w=Workflows(config)
asset=base/'synthetic.wav'
with wave.open(str(asset),'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000);f.writeframes(b'\x00\x00'*1600)
def msg():return {'command':'workflow','mode':'save_obsidian','payload':{'schema_version':1,'capture_id':str(uuid.uuid4()),'captured_at':now(),'source_url':'https://www.facebook.com/ads/library/?id=123','project':'research','rights_basis':'licensed','fields':{'identity':'Example fixture company','source_id':'123','title':'Synthetic fixture','primary_text':'Review the plan before work starts.','headline':'Know the plan','cta':'Book now','landing_url':'https://example.com/plan'},'media_references':[],'consent':{'confirmed':True,'public_only':True,'isolated_logged_out':True},'method':'manual'}}
results=[]
for case in ['complete','partial','inaccessible_lp','duplicate','changed_creative','jev_failure','model_off']:
 m=msg()
 if case=='partial':del m['payload']['fields']['headline']
 if case=='inaccessible_lp':m['fetch_landing']=True
 if case=='changed_creative':m['payload']['fields']['primary_text']='New version of the fixture creative'
 response={'error':'fixture failure'} if case=='jev_failure' else None
 r=w.run(m,imported=(asset,'audio/wav'),response=response);results.append({'case':case,**r})
# Separate quick route demonstrates no vault mutation, even when a vault exists.
before={str(p.relative_to(base/'vault')):sha(p.read_bytes()) for p in (base/'vault').rglob('*') if p.is_file()}
m=msg();m['mode']='quick_download';r=w.run(m,imported=(asset,'audio/wav'));results.append({'case':'quick_download',**r})
after={str(p.relative_to(base/'vault')):sha(p.read_bytes()) for p in (base/'vault').rglob('*') if p.is_file()};assert before==after
receipt=base/'adapter.json';receipt.write_text(json.dumps({'transport':'canonical-nonbrowser','adapter':'canonical-apify','status':'captured','browser_used':False,'path':'synthetic.wav','mime':'audio/wav','sha256':sha(asset.read_bytes())}))
m=msg();m['external_import']=True;m['payload']['source_url']='https://www.instagram.com/p/fixture123/';m['payload']['fields']={'notes':'Externally supplied synthetic adapter fixture'};m['payload']['method']='instagram-url-handoff';r=w.run(m,imported=approved_import(receipt,base));results.append({'case':'instagram_external_import',**r})
(base/'results.json').write_text(json.dumps({'synthetic':True,'network_calls':0,'model_calls':0,'quick_vault_unchanged':before==after,'results':results},indent=2));print(base)
