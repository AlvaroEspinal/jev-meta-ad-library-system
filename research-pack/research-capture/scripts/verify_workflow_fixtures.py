"""Independent v2 package verifier; no companion/extension imports."""
import hashlib,json,sys
from pathlib import Path
root=Path(sys.argv[1]).resolve();results=json.loads((root/'results.json').read_text());errors=[];count=0
assert results['synthetic'] is True and results['network_calls']==0 and results['quick_vault_unchanged']
for p in root.rglob('manifest.json'):
 m=json.loads(p.read_text());count+=1
 assert m['schema_version']==2
 for name,digest in m['files'].items():
  f=p.parent/name
  if f.is_symlink() or not f.resolve().is_relative_to(p.parent) or hashlib.sha256(f.read_bytes()).hexdigest()!=digest:errors.append(str(f))
 record=json.loads((p.parent/'record.json').read_text());decision=record['classification']
 assert decision['accepted'] is False and decision['review_required'] is True and decision['outcome_verified'] is False
 assert decision['network_calls']==0
 if decision['mode']=='off':assert decision['cost']==0
 if record['surface']=='instagram_handoff':
  assert 'instagram_handoff' in p.parts
  assert all(e['id']=='ad.notes' for e in record['evidence'])
 assert 'Content-Security-Policy' in (p.parent/'index.html').read_text()
 assert 'voice: Codex' in (p.parent/'note.md').read_text()
cases={r['case']:r for r in results['results']}
assert cases['complete']['status']=='captured'
for key in ['partial','inaccessible_lp','jev_failure']:assert cases[key]['status']=='partial'
assert cases['duplicate']['status']=='duplicate'
assert cases['changed_creative']['id']!=cases['complete']['id']
a=Path(cases['quick_download']['path']);assert a.is_relative_to(root/'Downloads');assert hashlib.sha256(a.read_bytes()).hexdigest()==cases['quick_download']['sha256'];assert cases['quick_download']['vault_written'] is False
report={'ok':not errors,'unique_packages_checked':count,'cases_checked':len(cases),'errors':errors,'checks':['file hashes','path containment','source separation','statuses','off-mode cost','review flags','quick download readback'],'limits':'Synthetic receipt/hash checks, not source truth, Chrome execution or provider inference'}
print(json.dumps(report,indent=2));raise SystemExit(0 if not errors else 1)
