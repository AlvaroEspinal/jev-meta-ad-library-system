#!/usr/bin/env python3
"""Offline plan by default. Opt-in one-call wrapper with an unrecorded hidden key prompt."""
import argparse,getpass,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--request',required=True);p.add_argument('--output',required=True);p.add_argument('--execute',action='store_true');p.add_argument('--approve-paid',action='store_true');a=p.parse_args()
cmd=[sys.executable,str(ROOT/'research-capture/companion/jev_client.py'),'--input',a.request,'--out',a.output,'--task-class','friend-research','--question-set-version','reviewed-v1']
env=os.environ.copy();env.pop('OPENROUTER_API_KEY',None);env.pop('OPENROUTER_JEV_API_KEY',None)
if a.execute:
 if not a.approve_paid:raise SystemExit('Separate --approve-paid consent required; inspect request and current provider costs first')
 if not sys.stdin.isatty():raise SystemExit('Live mode requires an interactive hidden-key prompt')
 key=getpass.getpass('Your OWN dedicated Jev OpenRouter key (not stored): ').strip()
 if not key:raise SystemExit('No key supplied; no call made')
 env['OPENROUTER_JEV_API_KEY']=key;cmd.append('--execute')
result=subprocess.run(cmd,env=env);env.pop('OPENROUTER_JEV_API_KEY',None)
raise SystemExit(result.returncode)
