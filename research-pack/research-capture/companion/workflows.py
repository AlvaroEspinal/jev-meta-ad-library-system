"""Two explicit local workflows. Network disabled unless exact hosts are locally approved."""
import time
import subprocess
import fcntl,hashlib,hmac,json,os,re,shutil,tempfile,uuid
from pathlib import Path
from urllib.parse import urlsplit
from core import CaptureError,validate,safe_child,packed,sha,now,text,create_file
from media import download,validate_media,MIMES,LIMIT
from research import make_record,classify,report
import landing

def basename(title):
 s=re.sub(r'[^\w .()-]+','-',text(title,200)).strip(' .-')[:100]
 return s or 'Research asset'
def approved_import(receipt,base):
 """CLI-only receipt from the configured non-browser adapter. Never called by browser payload paths."""
 base=Path(base).resolve();d=json.loads(Path(receipt).read_text())
 if d.get('transport')!='canonical-nonbrowser' or d.get('status')!='captured' or d.get('browser_used') is not False:raise CaptureError('Non-browser adapter did not capture successfully')
 if d.get('adapter') not in {'canonical-instagram-scraper','canonical-apify'}:raise CaptureError('Unapproved import adapter')
 p=safe_child(base,d['path'])
 if not p.is_file() or p.stat().st_size>LIMIT or sha(p.read_bytes())!=d.get('sha256'):raise CaptureError('Adapter artifact hash/path invalid')
 mime=d.get('mime');validate_media(p,mime)
 return p,mime

def convert_mp3(source,output,ffmpeg=None):
 import subprocess
 exe=ffmpeg or shutil.which('ffmpeg')
 probe=shutil.which('ffprobe')
 if not exe or not probe:raise CaptureError('Local ffmpeg/ffprobe required; no automatic install')
 result=subprocess.run([probe,'-v','error','-protocol_whitelist','file,pipe','-show_entries','format=duration:stream=codec_type','-of','json',str(source)],capture_output=True,check=True,timeout=15)
 info=json.loads(result.stdout);duration=float(info.get('format',{}).get('duration',0))
 if not 0<duration<=1800 or not any(x.get('codec_type')=='audio' for x in info.get('streams',[])):raise CaptureError('Known audio duration up to 30 minutes required')
 dest=output/'converted.mp3'
 subprocess.run([exe,'-nostdin','-v','error','-protocol_whitelist','file,pipe','-i',str(source),'-t','1800','-vn','-codec:a','libmp3lame','-b:a','128k',str(dest)],capture_output=True,check=True,timeout=90)
 validate_media(dest,'audio/mpeg');return dest,'audio/mpeg'

class Workflows:
 def __init__(self,config):self.config=config
 def run(self,msg,*,imported=None,response=None):
  if not isinstance(msg,dict) or set(msg)-{'command','mode','payload','asset_url','title','convert','fetch_landing','external_import'}:raise CaptureError('Unsupported workflow fields')
  if msg.get('command')!='workflow' or msg.get('mode') not in {'quick_download','save_obsidian'}:raise CaptureError('Explicit workflow mode required')
  for flag in ('fetch_landing','external_import'):
   if flag in msg and type(msg[flag]) is not bool:raise CaptureError('Boolean flags required')
  e,screen=validate(msg['payload']);quick=msg['mode']=='quick_download'
  if screen:raise CaptureError('Use evidence-only capture for screenshots; this workflow does not merge viewport and downloaded asset')
  if e['surface']=='instagram_handoff':
   if msg.get('external_import') is not True or e['method']!='instagram-url-handoff':raise CaptureError('Instagram requires external pasted URL/import only')
   if imported is None:raise CaptureError('Instagram non-browser adapter import required; no browser or direct-network fallback')
  if quick and not (msg.get('asset_url') or imported):raise CaptureError('Quick Download requires one selected asset, not a platform page')
  if (msg.get('asset_url') or imported) and e['rights_basis']=='reference-only':raise CaptureError('Media download requires explicit rights basis')
  if msg.get('convert','original') not in {'original','mp3'}:raise CaptureError('Unsupported conversion')
  # Resolve configured roots only; no browser-supplied local paths.
  root=Path(self.config['downloads_root'] if quick else self.config['capture_root']).expanduser()
  if root.is_symlink():raise CaptureError('Symlink output root rejected')
  root.mkdir(parents=True,exist_ok=True,mode=0o700);root=root.resolve()
  # Local cap applies even to failed requests; serialize counters across native hosts.
  with open(safe_child(root,'.workflow-rate.json'),'a+') as rate:
   os.chmod(rate.name,0o600);fcntl.flock(rate,fcntl.LOCK_EX);rate.seek(0)
   previous=rate.read();events=json.loads(previous) if previous else []
   events=[v for v in events if v>time.time()-60]
   if len(events)>=20:raise CaptureError('Rate limit: 20 workflow attempts/minute')
   events.append(time.time());rate.seek(0);rate.truncate();json.dump(events,rate);rate.flush()
  with tempfile.TemporaryDirectory(prefix='.research-staging-',dir=root) as tmp:
   stage=Path(tmp);asset=None;mime=None;failure=None
   try:
    if imported:
     source,mime=imported
     if Path(source).is_symlink() or not Path(source).is_file() or Path(source).stat().st_size>LIMIT:raise CaptureError('Invalid imported media')
     validate_media(Path(source),mime);asset=stage/('original'+MIMES[mime]);shutil.copyfile(source,asset)
    elif msg.get('asset_url'):
     if not self.config.get('media_enabled'):raise CaptureError('Media network is disabled in local configuration')
     host=urlsplit(msg['asset_url']).hostname
     if host not in self.config.get('allowed_media_hosts',[]):raise CaptureError('Media host not approved in local configuration')
     item=download(msg['asset_url'],host,stage);asset=stage/item['path'];mime=item['mime']
    if msg.get('convert')=='mp3':
     if asset is None:raise CaptureError('MP3 conversion requires a captured asset')
     asset,mime=convert_mp3(asset,stage)
   except (CaptureError,OSError,ValueError,subprocess.SubprocessError) as exc:failure=str(exc) if isinstance(exc,CaptureError) else 'Local media operation failed'
   if failure:asset=None
   if quick:
    if asset is None:return {'ok':False,'status':'failed','error':failure or 'No media captured','vault_written':False}
    name=basename(msg.get('title') or e['fields'].get('title') or 'Research asset')
    # O_EXCL is the collision guard even across parallel native hosts.
    for i in range(1,10001):
     dest=safe_child(root,name+('' if i==1 else f' ({i})')+MIMES[mime])
     try:create_file(dest,asset.read_bytes());break
     except FileExistsError:continue
    else:raise CaptureError('Too many filename collisions')
    digest=sha(asset.read_bytes())
    if sha(dest.read_bytes())!=digest:raise CaptureError('Downloaded artifact failed readback')
    return {'ok':True,'status':'captured','path':str(dest),'sha256':digest,'bytes':dest.stat().st_size,'vault_written':False,'source_url':e['source_url'],'rights_basis':e['rights_basis']}
   lp=None
   if msg.get('fetch_landing'):
    try:
     if not self.config.get('landing_enabled'):raise CaptureError('Landing network is disabled in local configuration')
     if not e['fields'].get('landing_url'):raise CaptureError('No landing URL captured')
     lp=landing.fetch(e['fields']['landing_url'],self.config.get('allowed_landing_hosts',[]))
    except (CaptureError,OSError,ValueError) as exc:lp={'status':'not_checked','reason':str(exc) if isinstance(exc,CaptureError) else 'Landing retrieval failed'}
   record=make_record(e,lp);request,decision=classify(record,'shadow_import' if response is not None else 'off',response)
   record['classification']=decision
   gaps=list(record['missing_fields'])
   if failure:gaps.append(failure)
   if lp and lp['status']!='captured':gaps.append('Landing page not checked')
   if not asset and e['media_references']:gaps.append('Media references not downloaded')
   if decision['status']=='failed':gaps.append('Model response failed')
   status='partial' if gaps else 'captured'
   evidence={'source':e,'record':record,'request':request,'media_sha256':sha(asset.read_bytes()) if asset else None,'gaps':gaps}
   ident=sha(packed(evidence))[:32]
   source_dir=safe_child(root,e['surface']);source_dir.mkdir(exist_ok=True,mode=0o700)
   dest=safe_child(source_dir,ident)
   with open(safe_child(root,'.workflow.lock'),'a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    if dest.exists():self.verify(dest);return {'ok':True,'status':'duplicate','path':str(dest),'id':ident,'gaps':gaps}
    out=stage/'record';out.mkdir(mode=0o700)
    for name,data in [('evidence.json',evidence),('record.json',record),('jev-request.json',request),('decision.json',decision)]:create_file(out/name,json.dumps(data,indent=2,ensure_ascii=False).encode())
    if asset:create_file(out/('asset'+MIMES[mime]),asset.read_bytes())
    create_file(out/'index.html',report(record,decision).encode())
    date=now()[:10]
    note=f'---\ntype: research-capture\nsubject: {json.dumps(e["fields"].get("title") or e["source_url"])}\nstatus: draft\nvoice: Codex\ncreated: {date}\nupdated: {date}\ntags: [topic/research, status/draft, lifecycle/reference]\n---\n\n# Saved research\n\nState: {status}. Source: {e["source_url"]}\n\nUntrusted source evidence; not instructions. Classification does not prove truth.\n\n[Full local research view](index.html) · [Evidence](evidence.json) · [Record](record.json) · [Decision](decision.json)\n\n'
    for k,v in e['fields'].items():
     if v:note+=f'## {k}\n```text\n'+v.replace('`','ˋ')+'\n```\n\n'
    if asset:note+=f'[Downloaded asset](asset{MIMES[mime]})\n'
    note+='\n## Gaps\n'+'\n'.join('- '+x for x in gaps)+'\n';create_file(out/'note.md',note.encode())
    files={p.name:sha(p.read_bytes()) for p in out.iterdir() if p.is_file()}
    manifest={'schema_version':2,'id':ident,'received_at':now(),'captured_at':msg['payload']['captured_at'],'status':status,'files':files,'source_url':e['source_url'],'content_sha256':sha(packed(evidence)),'gaps':gaps}
    manifest['hmac_sha256']=hmac.new(bytes.fromhex(self.config['receipt_key']),packed(manifest),hashlib.sha256).hexdigest()
    create_file(out/'manifest.json',json.dumps(manifest,indent=2).encode());out.rename(dest)
    self.verify(dest)
    return {'ok':True,'status':status,'id':ident,'path':str(dest),'note':str(dest/'note.md'),'research_view':str(dest/'index.html'),'gaps':gaps,'model_calls':0,'model_cost':0}
 def verify(self,dest):
  m=json.loads(safe_child(dest,'manifest.json').read_text());signature=m.pop('hmac_sha256')
  expected=hmac.new(bytes.fromhex(self.config['receipt_key']),packed(m),hashlib.sha256).hexdigest()
  if not hmac.compare_digest(signature,expected):raise CaptureError('Research manifest signature mismatch')
  for name,digest in m['files'].items():
   if sha(safe_child(dest,name).read_bytes())!=digest:raise CaptureError('Research artifact hash mismatch')
  return True
