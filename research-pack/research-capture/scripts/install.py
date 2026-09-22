#!/usr/bin/env python3
"""macOS user-only native host. Inspection is default; no live service calls."""
import argparse,base64,hashlib,json,os,secrets,shlex,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
HOST='com.jev.research_capture'
def no_symlinks(p):
 p=Path(p).expanduser().absolute()
 # macOS exposes root-owned system aliases; normalize only these known aliases.
 for alias,target in [('/var','/private/var'),('/tmp','/private/tmp')]:
  if p.is_relative_to(alias) and Path(alias).is_symlink() and Path(alias).resolve()==Path(target):p=Path(target)/p.relative_to(alias)
 if any(x.is_symlink() for x in [p,*p.parents]):raise ValueError('Symlink installation targets are not allowed')
 return p

def plan(vault,home,profile=None,capture_subdir='Research Capture'):
 vault=no_symlinks(vault).resolve();home=no_symlinks(home).resolve()
 if not vault.is_dir():raise ValueError('Vault must already exist')
 sub=Path(capture_subdir)
 if not capture_subdir.strip() or sub.is_absolute() or '..' in sub.parts or sub==Path('.'):raise ValueError('Capture subdirectory must be a nonempty relative path inside the vault')
 capture=no_symlinks(vault/sub)
 dest=no_symlinks(home/'Library/Application Support/JevResearchCapture')
 chrome=no_symlinks(profile) if profile else no_symlinks(home/'Library/Application Support/Google/Chrome')
 manifest=json.loads((ROOT/'extension/manifest.json').read_text());pub=base64.b64decode(manifest['key'])
 ident=''.join(chr(97+int(c,16)) for c in hashlib.sha256(pub).hexdigest()[:32])
 return {'install_root':str(dest),'native_manifest':str(chrome/'NativeMessagingHosts'/f'{HOST}.json'),'origin':f'chrome-extension://{ident}/','capture_root':str(capture),'extension':str(ROOT/'extension'),'downloads_root':str(home/'Downloads')}

def install(p):
 dest=no_symlinks(p['install_root']);nm=no_symlinks(p['native_manifest']);capture=no_symlinks(p['capture_root'])
 if dest.exists() or nm.exists():raise ValueError('Existing installation/registration: uninstall recoverably first; no overwrite')
 for f in ['core.py','host.py','media.py','workflows.py','research.py','landing.py','jev_contract.py','jev_client.py','data/taxonomy.json']:
  if not (ROOT/'companion'/f).is_file():raise ValueError('Incomplete source package')
 os.umask(0o077);dest.mkdir(parents=True,mode=0o700)
 for f in ['core.py','host.py','media.py','workflows.py','research.py','landing.py','jev_contract.py','jev_client.py']:
  shutil.copyfile(ROOT/'companion'/f,dest/f)
 (dest/'data').mkdir();shutil.copyfile(ROOT/'companion/data/taxonomy.json',dest/'data/taxonomy.json')
 config={'origin':p['origin'],'capture_root':p['capture_root'],'receipt_key':secrets.token_hex(32),'downloads_root':p['downloads_root'],'media_enabled':False,'landing_enabled':False,'allowed_media_hosts':[],'allowed_landing_hosts':[]}
 (dest/'config.json').write_text(json.dumps(config,indent=2));(dest/'config.json').chmod(0o600)
 launch=dest/'launch';launch.write_text('#!/bin/sh\nexec '+shlex.quote(sys.executable)+' '+shlex.quote(str(dest/'host.py'))+' "$@"\n');launch.chmod(0o700)
 nm.parent.mkdir(parents=True,exist_ok=True)
 with nm.open('x') as out:json.dump({'name':HOST,'description':'Local reviewed evidence; optional exact-host downloads','path':str(launch),'type':'stdio','allowed_origins':[p['origin']]},out,indent=2)
 nm.chmod(0o600);capture.mkdir(parents=True,exist_ok=True,mode=0o700)
 return p
if __name__=='__main__':
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--vault',required=True);a.add_argument('--home',default=str(Path.home()));a.add_argument('--chrome-profile-root');a.add_argument('--capture-subdir',default='Research Capture');a.add_argument('--execute',action='store_true');args=a.parse_args()
 p=plan(args.vault,args.home,args.chrome_profile_root,args.capture_subdir)
 if args.execute:install(p)
 print(json.dumps({'status':'installed' if args.execute else 'planned',**p},indent=2))
