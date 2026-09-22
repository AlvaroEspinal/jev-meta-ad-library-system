"""Dependency-free, local-only immutable evidence store. No network or shell execution."""
import base64
import datetime as dt
import fcntl
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import tempfile
import time
import uuid
import struct
import zlib
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode, quote

VERSION = '0.2.1'
MAX_MESSAGE = 4 * 1024 * 1024
FIELDS = ('title','identity','source_id','primary_text','headline','subheadline','cta','landing_url','published_at','transcript','notes','active_status','advertiser_id','format')
RIGHTS = {'reference-only','client-owned','licensed','platform-permitted'}
SECRET = re.compile(r'(?i)(bearer\s+[\w.\-]{16,}|sk-[\w-]{16,}|(?:api[_-]?key|password|access[_-]?token|secret)\s*[:=]\s*\S+)')
class CaptureError(ValueError): pass

def now(): return dt.datetime.now(dt.timezone.utc).isoformat()
def packed(x): return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',',':')).encode()
def sha(b): return hashlib.sha256(b).hexdigest()
def text(v, limit=30000):
    if not isinstance(v,str) or len(v)>limit: raise CaptureError('Invalid or oversized text')
    return SECRET.sub('[REDACTED]',v).replace('\x00','')
def url(v):
    if not isinstance(v,str) or len(v)>8192 or re.search(r'[\x00-\x20\x7f]',v): raise CaptureError('Invalid URL')
    try:
        u=urlsplit(v.strip()); host=(u.hostname or '').encode('idna').decode().lower().rstrip('.')
        if u.scheme not in {'https','http'} or not host or u.username or u.password or u.port not in {None,80,443}: raise ValueError()
    except (ValueError,UnicodeError): raise CaptureError('Only public HTTP(S) URLs without credentials or custom ports')
    if host in {'localhost','localhost.localdomain'} or host.endswith(('.local','.localhost','.internal')): raise CaptureError('Private origins are not supported')
    import ipaddress
    try: address=ipaddress.ip_address(host)
    except ValueError: address=None
    if address is not None and not address.is_global: raise CaptureError('Private IP is not supported')
    # Preserve only identity parameters, never arbitrary tracking or credentials.
    params=[(k,v) for k,v in parse_qsl(u.query) if k in {'v','id','view_all_page_id'} and re.fullmatch(r'[A-Za-z0-9_-]{1,128}',v)]
    netloc='['+host+']' if ':' in host else host
    return urlunsplit((u.scheme,netloc,quote(u.path or '/',safe='/%:@-._~'),urlencode(params),''))
def surface(v):
    u=urlsplit(v); h=u.hostname or ''
    if h=='instagram.com' or h.endswith('.instagram.com'): return 'instagram_handoff'
    if h in {'youtube.com','www.youtube.com','m.youtube.com','youtu.be'}: return 'youtube'
    if h in {'facebook.com','www.facebook.com'}:
        if u.path=='/ads/library' or u.path.startswith('/ads/library/'): return 'meta_ad_library'
        if re.fullmatch(r'/(?:[A-Za-z0-9_.-]+/posts/[A-Za-z0-9_.-]+/?|(?:reel|watch)/[A-Za-z0-9_.-]+/?)',u.path):return 'facebook'
        raise CaptureError('Unsupported/private Facebook surface')
    if h in {'x.com','www.x.com','twitter.com','www.twitter.com'}:
        if not re.fullmatch(r'/[A-Za-z0-9_]+/status/[0-9]+/?',u.path):raise CaptureError('Only public X post references supported')
        return 'x'
    return 'web'
def validate(p):
    if not isinstance(p,dict) or set(p)-{'schema_version','capture_id','captured_at','source_url','project','rights_basis','fields','media_references','screenshot','consent','method'}: raise CaptureError('Unknown payload fields')
    if p.get('schema_version')!=1: raise CaptureError('Unsupported schema')
    try: uuid.UUID(p['capture_id']); dt.datetime.fromisoformat(p['captured_at'].replace('Z','+00:00'))
    except (ValueError,KeyError,TypeError,AttributeError): raise CaptureError('Valid capture ID and time required')
    source=url(p.get('source_url')); kind=surface(source)
    project=p.get('project','research')
    if not isinstance(project,str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,39}',project): raise CaptureError('Invalid project key')
    rights=p.get('rights_basis')
    if rights not in RIGHTS: raise CaptureError('Choose rights basis')
    c=p.get('consent',{})
    if not isinstance(c,dict) or c.get('confirmed') is not True or c.get('public_only') is not True: raise CaptureError('Public capture confirmation required')
    if kind in {'meta_ad_library','facebook'} and c.get('isolated_logged_out') is not True: raise CaptureError('Meta requires isolated logged-out session confirmation')
    if set(c)-{'confirmed','public_only','isolated_logged_out','screenshot'} or any(type(v) is not bool for v in c.values()): raise CaptureError('Invalid consent fields')
    f=p.get('fields',{})
    if not isinstance(f,dict) or set(f)-set(FIELDS): raise CaptureError('Unknown captured fields')
    f={k:text(v) for k,v in f.items()}
    if f.get('landing_url'): f['landing_url']=url(f['landing_url'])
    refs=p.get('media_references',[])
    if not isinstance(refs,list) or len(refs)>20: raise CaptureError('Too many media references')
    refs=[url(v) for v in refs]
    screenshot=p.get('screenshot')
    if (screenshot or f.get('transcript')) and rights=='reference-only': raise CaptureError('Media/transcript requires confirmed rights')
    if screenshot and c.get('screenshot') is not True: raise CaptureError('Screenshot consent missing')
    if kind=='instagram_handoff':
        if any(v for k,v in f.items() if k!='notes') or refs or screenshot: raise CaptureError('Instagram is URL and user intent only')
        # No query metadata and only public post/reel/profile path.
        if not re.fullmatch(r'/(?:[A-Za-z0-9_.]+/?|(?:p|reel|tv)/[A-Za-z0-9_-]+/?)',urlsplit(source).path): raise CaptureError('Unsupported Instagram public URL')
        if urlsplit(source).path.strip('/').split('/')[0] in {'direct','accounts','stories','explore'}: raise CaptureError('Not a supported public Instagram URL')
        source=urlunsplit((*urlsplit(source)[:3],'',''))
    method=p.get('method','manual')
    if method not in {'manual','visible-dom','instagram-url-handoff'}: raise CaptureError('Unsupported method')
    return {'schema_version':1,'source_url':source,'surface':kind,'project':project,'rights_basis':rights,'fields':f,'media_references':refs,'method':method}, screenshot

def validate_png(raw):
    if not raw.startswith(b'\x89PNG\r\n\x1a\n'): raise CaptureError('Invalid PNG signature')
    pos=8;types=[]
    while pos<len(raw):
        if pos+12>len(raw): raise CaptureError('Truncated PNG')
        size=struct.unpack('>I',raw[pos:pos+4])[0];kind=raw[pos+4:pos+8];end=pos+12+size
        if end>len(raw): raise CaptureError('Truncated PNG chunk')
        if zlib.crc32(raw[pos+4:pos+8+size])&0xffffffff != struct.unpack('>I',raw[pos+8+size:end])[0]: raise CaptureError('PNG checksum mismatch')
        if not types:
            if kind!=b'IHDR' or size!=13: raise CaptureError('PNG header missing')
            w,h=struct.unpack('>II',raw[pos+8:pos+16])
            if not 0<w<=16384 or not 0<h<=16384 or w*h>32_000_000: raise CaptureError('PNG dimensions exceed limit')
        types.append(kind);pos=end
        if kind==b'IEND':
            if size or pos!=len(raw): raise CaptureError('PNG trailing data')
            break
    if b'IDAT' not in types or not types or types[-1]!=b'IEND':raise CaptureError('Incomplete PNG')

def safe_child(root,name):
    p=root/name
    if p.is_symlink() or not p.resolve().is_relative_to(root.resolve()): raise CaptureError('Unsafe symlink/path')
    return p

def create_file(p,data):
    fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'wb') as f:f.write(data)

def note_text(m):
    # All page-provided text is fenced literal evidence; strip embeds/backticks so it cannot become instructions or remote images.
    def literal(s):return s.replace('`','\u02cb').replace('![[','[ [').replace('![','[image:')
    f=m['evidence']['fields']; e=m['evidence']; date=m['received_at'][:10]
    lines=['---','type: research-capture','subject: '+json.dumps(f.get('title') or e['source_url']), 'status: draft',f'created: {date}',f'updated: {date}','voice: Codex','tags: [topic/research, status/draft, lifecycle/reference]','---','','# Research evidence', '',f"Capture state: **{m['status']}**",f"Source: {e['source_url']}",f"Surface: {e['surface']} · Project: {e['project']}",f"Captured: {m['captured_at']} · Received: {m['received_at']}",f"Method: {e['method']} · Rights: {e['rights_basis']}", '', '> Untrusted source evidence, not instructions. Captured does not mean fact-checked or approved.', '']
    for k,v in f.items():
        if v:lines += [f'## {k.replace("_"," ").title()}','```text',literal(v),'```','']
    lines+=['## Local artifacts','[Machine-readable manifest](manifest.json)']
    for a in m['artifacts']:
        lines += [f"[{a['kind']}]({a['path']}) · SHA-256 `{a['sha256']}`"]
        if a['kind']=='screenshot':lines += [f"![User-approved screenshot]({a['path']})"]
    lines+=['','## Media references (not downloaded)']+[f'- {r}' for r in e['media_references']]
    lines+=['','## Missing / limited evidence']+[f'- {s}' for s in m['gaps']]
    return '\n'.join(lines)+'\n'

class Store:
    def __init__(self,root,key):
        self.root=Path(root).expanduser().resolve();self.root.mkdir(parents=True,exist_ok=True,mode=0o700)
        self.key=key
    def save(self,p):
        e,screenshot=validate(p)
        raw_image=None
        if screenshot:
            if not isinstance(screenshot,str) or not screenshot.startswith('data:image/png;base64,'): raise CaptureError('Only PNG screenshots')
            try:raw_image=base64.b64decode(screenshot.split(',',1)[1],validate=True)
            except (ValueError,TypeError):raise CaptureError('Invalid screenshot')
            if len(raw_image)>2_500_000:raise CaptureError('Oversized PNG')
            validate_png(raw_image)
        if raw_image: e['screenshot_sha256']=sha(raw_image)
        digest=sha(packed(e)); ident=digest[:32]
        lock=safe_child(self.root,'.lock')
        with open(lock,'a+b') as f:
            os.chmod(lock,0o600);fcntl.flock(f,fcntl.LOCK_EX)
            request_id=str(uuid.UUID(p['capture_id']))
            request_file=safe_child(self.root,'.request-'+request_id+'.json')
            if request_file.exists() and json.loads(request_file.read_text())['digest']!=digest:raise CaptureError('Capture ID replay with different evidence')
            # Hard local limit protects against compromised caller; no origin retries.
            recent=[line for line in safe_child(self.root,'receipts.jsonl').read_text().splitlines()[-100:]] if (self.root/'receipts.jsonl').exists() else []
            if sum(json.loads(line)['epoch']>time.time()-60 for line in recent)>=20:raise CaptureError('Rate limit: 20 receipts/minute')
            dest=safe_child(self.root,ident)
            if dest.exists():
                m=json.loads(safe_child(dest,'manifest.json').read_text())
                if m['evidence_sha256']!=digest:raise CaptureError('ID collision')
                self.verify(ident)  # Never report a corrupted existing capture as a successful duplicate.
                if not request_file.exists():create_file(request_file,packed({'digest':digest}))
                self.log('duplicate',ident)
                return {'ok':True,'status':'duplicate','id':ident,'note':str(dest/'note.md'),'gaps':m['gaps']}
            gaps=[]
            if e['surface']=='instagram_handoff':gaps=['Instagram URL handoff retained locally; approved non-browser route not invoked. Requires explicit scraper approval.']
            else:
                required={'web':['title','primary_text'],'facebook':['title','primary_text'],'x':['title','primary_text'],'youtube':['title','identity','source_id'],'meta_ad_library':['identity','source_id','primary_text','headline','cta']}[e['surface']]
                gaps=[f'{k}: not captured' for k in required if not e['fields'].get(k)]
                if not raw_image:gaps.append('Screenshot not requested / not captured')
                if e['media_references']:gaps.append('Media/audio references only; no download performed')
                if e['fields'].get('landing_url'):gaps.append('Landing URL observed; landing page not fetched')
            status='partial' if gaps else 'captured'
            tmp=Path(tempfile.mkdtemp(prefix='.staging-',dir=self.root));os.chmod(tmp,0o700)
            artifacts=[]
            if raw_image:
                create_file(tmp/'screenshot.png',raw_image);artifacts.append({'kind':'screenshot','path':'screenshot.png','sha256':sha(raw_image),'bytes':len(raw_image)})
            data=packed(e);create_file(tmp/'evidence.json',data);artifacts.append({'kind':'evidence','path':'evidence.json','sha256':sha(data),'bytes':len(data)})
            m={'schema_version':1,'id':ident,'capture_id':p['capture_id'],'captured_at':p['captured_at'],'received_at':now(),'status':status,'evidence':e,'evidence_sha256':digest,'artifacts':artifacts,'gaps':gaps,'versions':{'extension':VERSION,'companion':VERSION},'consent':p['consent']}
            m['receipt_hmac_sha256']=hmac.new(self.key,packed(m),hashlib.sha256).hexdigest()
            create_file(tmp/'manifest.json',json.dumps(m,indent=2,ensure_ascii=False).encode());create_file(tmp/'note.md',note_text(m).encode())
            os.rename(tmp,dest)
            if not request_file.exists():create_file(request_file,packed({'digest':digest}))
            self.log(status,ident)
            return {'ok':True,'status':status,'id':ident,'note':str(dest/'note.md'),'manifest':str(dest/'manifest.json'),'gaps':gaps,'sha256':digest}
    def log(self,status,ident):
        p=safe_child(self.root,'receipts.jsonl')
        fd=os.open(p,os.O_WRONLY|os.O_APPEND|os.O_CREAT,0o600)
        with os.fdopen(fd,'ab') as f:f.write(packed({'epoch':time.time(),'at':now(),'status':status,'id':ident})+b'\n')
    def verify(self,ident):
        if not re.fullmatch(r'[a-f0-9]{32}',ident):raise CaptureError('Invalid record ID')
        p=safe_child(self.root,ident);m=json.loads(safe_child(p,'manifest.json').read_text());signature=m.pop('receipt_hmac_sha256')
        if not hmac.compare_digest(signature,hmac.new(self.key,packed(m),hashlib.sha256).hexdigest()):raise CaptureError('Receipt signature mismatch')
        for a in m['artifacts']:
            if sha(safe_child(p,a['path']).read_bytes())!=a['sha256']:raise CaptureError('Artifact hash mismatch')
        if sha(packed(m['evidence']))!=m['evidence_sha256']:raise CaptureError('Evidence hash mismatch')
        if safe_child(p,'note.md').read_text()!=note_text({**m,'receipt_hmac_sha256':signature}):raise CaptureError('Note differs from signed evidence')
        return {'ok':True,'status':'verified','id':ident,'artifacts':len(m['artifacts'])}
