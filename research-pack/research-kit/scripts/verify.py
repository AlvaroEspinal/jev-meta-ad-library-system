"""Independent manifest, local-link and sensitive-pattern scan. No application imports."""
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def verify():
    manifest=json.loads((ROOT/'MANIFEST.json').read_text());errors=[]
    patterns=[r'/Users/[A-Za-z0-9_./-]+',r'/home/[A-Za-z0-9_./-]+',r'(?i)sk-[a-z0-9_-]{20,}',r'-----BEGIN [A-Z ]*PRIVATE KEY-----',r'(?i)[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}',r'(?i)(?:access_token|api_key|password)\s*[:=]\s*["\']?[a-z0-9_-]{16,}']
    for name,digest in manifest['files'].items():
        p=ROOT/name
        if p.is_symlink() or not p.resolve().is_relative_to(ROOT) or not p.is_file():errors.append(name+': missing/unsafe');continue
        data=p.read_bytes()
        if hashlib.sha256(data).hexdigest()!=digest:errors.append(name+': hash mismatch')
        text=data.decode('utf-8')
        for pattern in patterns:
            if re.search(pattern,text):errors.append(name+': sensitive/path pattern')
        if p.suffix=='.md':
            for dest in re.findall(r'\]\(([^)]+)\)',text):
                if '://' not in dest and not (p.parent/dest.split('#')[0]).exists():errors.append(name+': broken link '+dest)
    result={'ok':not errors,'files_checked':len(manifest['files']),'checks':['sha256','symlink/path containment','secret/PII patterns','relative Markdown links'],'errors':errors,'network_calls':0}
    print(json.dumps(result,indent=2));return not errors
if __name__=='__main__':raise SystemExit(0 if verify() else 1)
