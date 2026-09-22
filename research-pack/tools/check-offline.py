#!/usr/bin/env python3
"""Run every shipped test family in a disposable copy; npm is the only registry step."""
import hashlib,json,os,re,shutil,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];checks=[]
with tempfile.TemporaryDirectory(prefix='jev-friend-tests-') as temp:
 clean=Path(temp)/'pack';manifest=json.loads((ROOT/'MANIFEST.json').read_text())
 for name in list(manifest['files'])+['MANIFEST.json','SHA256SUMS']:
  src=ROOT/name
  if src.is_symlink() or not src.is_file() or not src.resolve().is_relative_to(ROOT):raise SystemExit('Unsafe source entry')
  if name in manifest['files'] and hashlib.sha256(src.read_bytes()).hexdigest()!=manifest['files'][name]:raise SystemExit('Manifest mismatch before testing')
  dst=clean/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
 # Python tests cannot connect to source/model sites even if a mock is accidentally removed.
 guard=Path(temp)/'network-guard';guard.mkdir();(guard/'sitecustomize.py').write_text("import socket\ndef denied(*a,**k): raise RuntimeError('offline network denied')\nsocket.socket.connect=denied\nsocket.create_connection=denied\nsocket.getaddrinfo=denied\n")
 env=os.environ.copy();env['PYTHONPATH']=str(guard);env['PYTHONDONTWRITEBYTECODE']='1';env.pop('OPENROUTER_JEV_API_KEY',None);env.pop('OPENROUTER_API_KEY',None)
 commands=[('research-capture',['npm','ci','--ignore-scripts','--prefer-offline','--no-audit','--no-fund']),('research-capture',[sys.executable,'-m','unittest','discover','-s','tests','-v']),('research-capture',['npm','test']),('research-capture',[sys.executable,'scripts/fixture_receipts.py']),('research-capture',[sys.executable,'scripts/verify_artifacts.py','artifacts/fixture-vault']),('research-capture',[sys.executable,'scripts/workflow_fixtures.py']),('research-capture',[sys.executable,'scripts/verify_workflow_fixtures.py','artifacts/workflow-fixtures']),('.', [sys.executable,'tools/test_setup.py']),('research-kit',[sys.executable,'scripts/test_kit.py'])]
 for where,cmd in commands:
  r=subprocess.run(cmd,cwd=clean/where,env=env,capture_output=True,text=True,timeout=180)
  output=(r.stdout+r.stderr).replace(str(temp),'<TEMP>');match=re.search(r'Ran (\d+) tests?',output);js=re.search(r'(?:#|ℹ) tests (\d+)',output)
  checks.append({'cwd':where,'command':' '.join('python3' if x==sys.executable else x for x in cmd),'exit_code':r.returncode,'tests':int(match.group(1)) if match else int(js.group(1)) if js else None,'output_tail':output[-2400:]})
  if r.returncode:print(json.dumps({'ok':False,'checks':checks},indent=2));raise SystemExit(1)
print(json.dumps({'ok':True,'checks':checks,'paid_calls':0,'live_source_calls':0,'real_host_registration':False,'python_network_guard':True,'npm_registry_access':'dependency installation only'},indent=2))
