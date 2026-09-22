#!/usr/bin/env python3
"""Agent handoff CLI: local validation/save/verify, no browser or network calls."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'companion'))
from core import Store
from host import dispatch,DEFAULT_ORIGINS
p=argparse.ArgumentParser();p.add_argument('--config',default=str(Path.home()/'Library/Application Support/JevResearchCapture/config.json'));g=p.add_mutually_exclusive_group(required=True);g.add_argument('--payload');g.add_argument('--verify');args=p.parse_args()
try:
 c=json.loads(Path(args.config).read_text());store=Store(c['capture_root'],bytes.fromhex(c['receipt_key']))
 message={'command':'verify','id':args.verify} if args.verify else {'command':'capture','payload':json.loads(Path(args.payload).read_text())}
 r=dispatch(message,store,c.get('allowed_capture_origins',DEFAULT_ORIGINS));print(json.dumps(r,indent=2));raise SystemExit(0 if r['ok'] else 1)
except Exception as e:print(json.dumps({'ok':False,'status':'failed','error':str(e)}));raise SystemExit(1)
