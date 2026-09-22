#!/usr/bin/env python3
"""Cold unzip verification, independent of package builder and runtime implementation."""
import argparse,hashlib,json,os,re,shlex,subprocess,sys,tempfile,zipfile
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('archive',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args();checks=[];payload_hash=None
with tempfile.TemporaryDirectory(prefix='jev-friend-cold-') as tmp:
 temp=Path(tmp)
 with zipfile.ZipFile(a.archive) as z:
  seen=set()
  for member in z.infolist():
   n=Path(member.filename)
   assert not n.is_absolute() and '..' not in n.parts and member.filename not in seen,'unsafe ZIP path'
   assert (member.external_attr>>16)&0o170000!=0o120000,'symlink ZIP entry'
   seen.add(member.filename)
  z.extractall(temp)
 dirs=list(temp.iterdir());assert len(dirs)==1 and dirs[0].is_dir();root=dirs[0]
 m=json.loads((root/'MANIFEST.json').read_text());payload={k:v for k,v in m['files'].items() if k!='VERIFICATION-RECEIPT.json'};payload_hash=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
 env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1';env.pop('OPENROUTER_JEV_API_KEY',None);env.pop('OPENROUTER_API_KEY',None)
 def run(cmd,cwd=root,expected=0):
  r=subprocess.run(cmd,cwd=cwd,env=env,text=True,capture_output=True,timeout=300)
  output=(r.stdout+r.stderr).replace(str(temp),'<TEMP>')
  result={'command':' '.join('python3' if str(x)==sys.executable else str(x).replace(str(temp),'<TEMP>') for x in cmd),'exit_code':r.returncode,'passed':r.returncode==expected,'output_tail':output[-1600:]}
  if cmd[-1:] == ['tools/check-offline.py']:
   report=json.loads(r.stdout);result['offline_checks']=report;result['output_tail']='See offline_checks'
  checks.append(result);assert result['passed'],json.dumps(result);return r
 # Execute actual documented offline shell blocks, never live/placeholder commands.
 start=(root/'START-HERE.md').read_text();blocks=re.findall(r'```sh\n(.*?)```',start,re.S)
 assert len(blocks)==4,'Review changed START-HERE command groups'
 for block in blocks[:2]:
  for line in block.strip().splitlines():
   cmd=shlex.split(line)
   if cmd[0]=='python3':cmd[0]=sys.executable
   run(cmd)
 # Kit README itself is exercised from its own cwd exactly as printed.
 kit=root/'research-kit';block=re.findall(r'```sh\n(.*?)```',(kit/'README.md').read_text(),re.S)[0]
 for line in block.strip().splitlines():
  cmd=shlex.split(line);assert cmd[0]=='python3';cmd[0]=sys.executable;run(cmd,kit)
 # Installer dry-runs use isolated fake home/vault and must create nothing.
 fake=temp/'sandbox';fake.mkdir();vault=fake/'My Vault';vault.mkdir();home=fake/'Home';chrome=fake/'Chrome Root'
 run([sys.executable,'research-capture/scripts/install.py','--vault',str(vault),'--home',str(home),'--chrome-profile-root',str(chrome),'--capture-subdir','Inbox/Research'])
 run([sys.executable,'research-capture/scripts/uninstall.py','--home',str(home),'--chrome-profile-root',str(chrome)])
 assert not home.exists() and not chrome.exists() and not list(vault.iterdir())
 checks.append({'check':'documented generic install/uninstall dry-run produced no registration or vault writes','passed':True})
 assert json.loads((root/'jev-dry-run.json').read_text())['status']=='dry_run'
 assert json.loads((root/'replay-output.json').read_text())['accepted'] is False
 assert json.loads((root/'VERSION.json').read_text())['native_host']=='com.jev.research_capture'
 # Negative tamper tests independently against both manifests; preserve the evidence of failure.
 target=root/'research-kit/fixtures/ad-record.json';target.write_text(target.read_text()+'\n ')
 run([sys.executable,'tools/verify.py'],expected=1)
 run([sys.executable,'scripts/verify.py'],kit,expected=1)
 checks.append({'check':'modified synthetic evidence rejected by both top-level and kit integrity checks','passed':True})
 report={'ok':True,'tested_payload_sha256':payload_hash,'zip_sha256':hashlib.sha256(a.archive.read_bytes()).hexdigest(),'version':json.loads((root/'VERSION.json').read_text()),'checks':checks,'limitations':['Offline/sandbox verification only; no friend-machine or real Chrome acceptance','npm registry/cache used for locked test dependencies; no source/model calls','Pattern scan is not an exhaustive security audit','Live installation, live source capture and paid model smoke remain untested'],'public_upload':False,'paid_api_calls':0,'real_native_registration':False}
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'ok':True,'receipt':str(a.out),'checks':len(checks),'zip_sha256':report['zip_sha256'],'tested_payload_sha256':payload_hash},indent=2))
