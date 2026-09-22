#!/usr/bin/env python3
"""Recoverable exact-target uninstall. Defaults to dry-run; retains all vault evidence."""
import argparse,datetime,json,shutil
from pathlib import Path
from install import no_symlinks,HOST
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--home',default=str(Path.home()));p.add_argument('--chrome-profile-root');p.add_argument('--execute',action='store_true');a=p.parse_args()
home=no_symlinks(a.home).resolve();root=no_symlinks(home/'Library/Application Support/JevResearchCapture');chrome=no_symlinks(a.chrome_profile_root) if a.chrome_profile_root else no_symlinks(home/'Library/Application Support/Google/Chrome');manifest=no_symlinks(chrome/'NativeMessagingHosts'/f'{HOST}.json');backup=home/'Library/Application Support'/('JevResearchCapture-disabled-'+datetime.datetime.now().strftime('%Y%m%dT%H%M%S%f'))
if manifest.exists() and json.loads(manifest.read_text()).get('path')!=str(root/'launch'):raise SystemExit('Registration belongs to another installation; stop')
plan={'companion':str(root),'registration':str(manifest),'backup':str(backup),'vault':'untouched','execute':a.execute};print(json.dumps(plan,indent=2))
if a.execute and (root.exists() or manifest.exists()):
 backup.mkdir(mode=0o700,parents=True,exist_ok=False)
 if manifest.exists():shutil.move(str(manifest),str(backup/'native-manifest.json'))
 if root.exists():shutil.move(str(root),str(backup/'companion'))
 (backup/'restore-paths.json').write_text(json.dumps(plan,indent=2))
