#!/usr/bin/env python3
"""Explicit native/CLI lawful media acquisition. No cookies, redirects, proxies or extractor bypass."""
import time
import argparse,hashlib,http.client,ipaddress,json,os,shutil,socket,ssl,subprocess,tempfile,uuid
from pathlib import Path
from urllib.parse import urlsplit
from core import CaptureError,url,now,sha,validate_png
LIMIT=50*1024*1024
MIMES={'image/png':'.png','image/jpeg':'.jpg','video/mp4':'.mp4','audio/mpeg':'.mp3','audio/wav':'.wav','audio/x-wav':'.wav','audio/mp4':'.m4a'}
def public_addresses(host):
 ips=sorted({x[4][0] for x in socket.getaddrinfo(host,443,type=socket.SOCK_STREAM)})
 if not ips or any(not ipaddress.ip_address(i).is_global for i in ips):raise CaptureError('Non-public destination rejected')
 return ips
class PinnedHTTPS(http.client.HTTPSConnection):
 def __init__(self,host,ip):super().__init__(host,timeout=15,context=ssl.create_default_context());self.ip=ip
 def connect(self):self.sock=self._context.wrap_socket(socket.create_connection((self.ip,443),timeout=self.timeout),server_hostname=self.host)
def download(source,allowed_host,output):
 clean=url(source);u=urlsplit(clean);original=urlsplit(source)
 if u.scheme!='https' or u.hostname!=allowed_host.lower().rstrip('.') or original.query:raise CaptureError('Download requires exact approved HTTPS host and unsigned URL; query URLs remain references')
 if any(u.hostname==h or u.hostname.endswith('.'+h) for h in ('instagram.com','facebook.com','youtube.com','youtu.be')):raise CaptureError('Platform pages are references, not a lawful direct-media route')
 ip=public_addresses(u.hostname)[0];conn=PinnedHTTPS(u.hostname,ip)
 try:
  deadline=time.monotonic()+120
  conn.request('GET',u.path or '/',headers={'User-Agent':'ResearchCapture/0.1 (authorized-media)','Accept':','.join(MIMES)})
  r=conn.getresponse();mime=r.getheader('Content-Type','').split(';')[0].lower()
  if r.status!=200:raise CaptureError(f'HTTP {r.status}; redirects/challenges not retried')
  if mime not in MIMES:raise CaptureError('Unsupported media MIME')
  length=r.getheader('Content-Length')
  if length and int(length)>LIMIT:raise CaptureError('Media exceeds 50 MB limit')
  target=output/('original'+MIMES[mime]);total=0;digest=hashlib.sha256()
  with target.open('xb') as f:
   while b:=r.read(65536):
    if time.monotonic()>deadline:raise CaptureError('Media transfer deadline exceeded')
    total+=len(b)
    if total>LIMIT:raise CaptureError('Media exceeds 50 MB limit')
    f.write(b);digest.update(b)
  validate_media(target,mime)
  return {'kind':'authorized-media','path':target.name,'sha256':digest.hexdigest(),'bytes':total,'mime':mime,'source_url':clean}
 finally:conn.close()
def validate_media(path,mime):
 data=path.read_bytes()
 valid=False
 if mime=='image/png':validate_png(data);valid=True
 elif mime=='image/jpeg':valid=len(data)>4 and data.startswith(b'\xff\xd8\xff') and data.endswith(b'\xff\xd9')
 elif mime in {'audio/wav','audio/x-wav'}:valid=len(data)>=44 and data[:4]==b'RIFF' and data[8:12]==b'WAVE'
 elif mime in {'video/mp4','audio/mp4'}:valid=len(data)>=12 and data[4:8]==b'ftyp'
 elif mime=='audio/mpeg':valid=len(data)>4 and (data.startswith(b'ID3') or (data[0]==255 and data[1]&224==224))
 if not valid:raise CaptureError('Media bytes do not match supported MIME; retained only as failed evidence')

def transcribe(source,output,model):
 for cmd in ['ffmpeg','ffprobe','whisper-cli']:
  if not shutil.which(cmd):raise CaptureError(f'{cmd} not installed')
 if not Path(model).is_file():raise CaptureError('Local Whisper model required; no automatic download')
 probe=subprocess.run(['ffprobe','-v','error','-protocol_whitelist','file,pipe','-show_entries','format=duration:stream=codec_type','-of','json',str(source)],check=True,timeout=15,capture_output=True)
 info=json.loads(probe.stdout);duration=float(info.get('format',{}).get('duration',0))
 if not 0<duration<=1800 or not any(s.get('codec_type')=='audio' for s in info.get('streams',[])):raise CaptureError('Audio stream required; duration must be known and at most 30 minutes')
 audio=output/'audio.wav'
 subprocess.run(['ffmpeg','-nostdin','-v','error','-protocol_whitelist','file,pipe','-i',str(source),'-t','1800','-vn','-ac','1','-ar','16000',str(audio)],check=True,timeout=90,capture_output=True)
 subprocess.run(['whisper-cli','-m',str(model),'-f',str(audio),'-otxt','-oj','-of',str(output/'transcript')],check=True,timeout=600,capture_output=True)
 return [{'kind':k,'path':p.name,'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size} for k,p in [('audio',audio),('transcript',output/'transcript.txt'),('transcript-timing',output/'transcript.json')]]
def main():
 a=argparse.ArgumentParser();a.add_argument('--source',required=True);a.add_argument('--output',required=True);a.add_argument('--rights',choices=['client-owned','licensed','platform-permitted'],required=True);a.add_argument('--approve-download',action='store_true');a.add_argument('--allow-host');a.add_argument('--transcribe',action='store_true');a.add_argument('--model');args=a.parse_args()
 out=Path(args.output).resolve();out.mkdir(parents=True,exist_ok=False,mode=0o700);os.umask(0o077)
 receipt={'schema_version':1,'source':'unvalidated input omitted','rights_basis':args.rights,'received_at':now(),'status':'failed','artifacts':[]}
 try:
  receipt['source']=url(args.source) if args.source.startswith('http') else str(Path(args.source).resolve())
  if args.source.startswith('http'):
   if not args.approve_download or not args.allow_host:raise CaptureError('Explicit --approve-download and --allow-host required')
   art=download(args.source,args.allow_host,out);receipt['artifacts'].append(art);src=out/art['path']
  else:
   supplied=Path(args.source).expanduser()
   src=supplied.resolve()
   if supplied.is_symlink() or not src.is_file() or src.stat().st_size>LIMIT:raise CaptureError('Invalid or oversized local file')
   if src.suffix.lower() not in set(MIMES.values()):raise CaptureError('Unsupported local media')
   validate_media(src,next(k for k,v in MIMES.items() if v==src.suffix.lower()))
   dest=out/('original'+src.suffix.lower());shutil.copyfile(src,dest);src=dest;receipt['artifacts'].append({'kind':'local-authorized-media','path':src.name,'sha256':sha(src.read_bytes()),'bytes':src.stat().st_size})
  if args.transcribe:
   if not args.model:raise CaptureError('--model required')
   receipt['artifacts']+=transcribe(src,out,args.model)
  receipt['status']='captured'
 except Exception as e:receipt['error']=str(e) if isinstance(e,CaptureError) else type(e).__name__+': local media processing failed'
 (out/'media-manifest.json').write_text(json.dumps(receipt,indent=2));(out/'README.md').write_text('# Authorized media evidence\n\n'+f"State: {receipt['status']}\n\n"+'\n'.join(f"- [{x['kind']}]({x['path']}) SHA-256 `{x['sha256']}`" for x in receipt['artifacts'])+'\n'+receipt.get('error',''))
 print(json.dumps(receipt,indent=2));return 0 if receipt['status']=='captured' else 1
if __name__=='__main__':raise SystemExit(main())
