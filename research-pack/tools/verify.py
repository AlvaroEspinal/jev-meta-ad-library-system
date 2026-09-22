#!/usr/bin/env python3
"""Offline exact manifest + path/PII/secret/link checks; independent of application code."""
import argparse,hashlib,json,re
from pathlib import Path
from urllib.parse import unquote
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--strict',action='store_true',help='Reject additional files; use before generating test outputs');a=p.parse_args()
m=json.loads((ROOT/'MANIFEST.json').read_text());errors=[]
patterns=[r'(?i)'+'al'+'varo','claude'+'-setup',r'/Users/[A-Za-z0-9_.-]+/',r'/home/[A-Za-z0-9_.-]+/',r'(?i)sk-[a-z0-9_-]{20,}',r'-----BEGIN [A-Z ]*PRIVATE KEY-----',r'(?i)[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}',r'(?i)(?:access_token|api_key|password)\s*[:=]\s*["\']?[a-z0-9_-]{16,}']
for name,digest in m['files'].items():
 path=ROOT/name
 if Path(name).is_absolute() or '..' in Path(name).parts or path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(ROOT):errors.append(name+': unsafe/missing');continue
 data=path.read_bytes()
 if hashlib.sha256(data).hexdigest()!=digest:errors.append(name+': hash mismatch')
 try:text=data.decode('utf-8')
 except UnicodeDecodeError:errors.append(name+': non-text not approved');continue
 # One known synthetic userinfo-negative test, never a whole-file exemption.
 text=text.replace('https://user:secret@example.com','https://synthetic-userinfo.invalid')
 for pattern in patterns:
  if re.search(pattern,text):errors.append(name+': sensitive/path pattern')
 if path.suffix=='.md':
  for dest in re.findall(r'\]\(([^)]+)\)',text):
   if '://' in dest or dest.startswith('#'):continue
   target=path.parent/unquote(dest.split('#')[0])
   if not target.exists() or not target.resolve().is_relative_to(ROOT):errors.append(name+': broken/unsafe relative link '+dest)
actual={str(x.relative_to(ROOT)) for x in ROOT.rglob('*') if x.is_file()}
if a.strict and actual!=set(m['files'])|{'MANIFEST.json','SHA256SUMS'}:errors.append('Unexpected files in strict distribution')
expected=''.join(f'{digest}  {name}\n' for name,digest in sorted(m['files'].items()))
expected+=hashlib.sha256((ROOT/'MANIFEST.json').read_bytes()).hexdigest()+'  MANIFEST.json\n'
if (ROOT/'SHA256SUMS').read_text()!=expected:errors.append('SHA256SUMS inconsistent')
print(json.dumps({'ok':not errors,'files_checked':len(m['files']),'errors':errors,'strict':a.strict,'network_calls':0},indent=2))
raise SystemExit(bool(errors))
