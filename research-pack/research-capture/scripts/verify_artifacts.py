#!/usr/bin/env python3
"""Cold verifier: independent implementation; no imports from companion or extension."""
import argparse,hashlib,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('root');args=p.parse_args();root=Path(args.root).resolve();fail=[];count=0
for manifest in root.rglob('manifest.json'):
 try:
  m=json.loads(manifest.read_text())
  if m.get('schema_version')!=1 or 'evidence_sha256' not in m:continue
  count+=1;content=json.dumps(m['evidence'],ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
  if hashlib.sha256(content).hexdigest()!=m['evidence_sha256']:fail.append(str(manifest)+': evidence hash')
  for a in m['artifacts']:
   path=manifest.parent/a['path']
   if not path.resolve().is_relative_to(manifest.parent.resolve()) or path.is_symlink():raise ValueError('Unsafe artifact')
   if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=a['sha256']:fail.append(str(path)+': asset hash')
  note=(manifest.parent/'note.md').read_text()
  for required in ['voice: Codex','status: draft','Source: '+m['evidence']['source_url'],'Machine-readable manifest','Untrusted source evidence']:
   if required not in note:fail.append(str(manifest)+': note missing '+required)
  if m['evidence']['surface']=='instagram_handoff':
   e=m['evidence']
   if set(e['fields'])-{'notes'} or e['media_references'] or len(m['artifacts'])!=1:fail.append('Instagram leaked evidence')
 except Exception as e:fail.append(str(manifest)+': '+str(e))
result={'result':'PASS' if count and not fail else 'FAIL','records_checked':count,'failures':fail,'limits':'Hash, containment and note evidence checks; does not independently establish source truth or Chrome execution.'};print(json.dumps(result,indent=2));raise SystemExit(0 if count and not fail else 1)
