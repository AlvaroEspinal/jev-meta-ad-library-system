#!/usr/bin/env python3
"""Explicit local utility. External non-browser import only; never starts a scraper/browser."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'companion'))
from workflows import Workflows,approved_import
from core import CaptureError
p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--message',required=True);p.add_argument('--adapter-receipt');p.add_argument('--adapter-root');p.add_argument('--confirm-reviewed-nonbrowser-import',action='store_true');p.add_argument('--response',help='Explicit local shadow-response JSON; never invokes a provider');args=p.parse_args()
try:
 c=json.loads(Path(args.config).read_text());m=json.loads(Path(args.message).read_text());asset=None
 if args.adapter_receipt:
  if not args.adapter_root or not args.confirm_reviewed_nonbrowser_import:raise CaptureError('Review the configured non-browser adapter provenance, rights and artifact before import; explicit confirmation and root required')
  asset=approved_import(args.adapter_receipt,args.adapter_root)
 response=json.loads(Path(args.response).read_text()) if args.response else None
 r=Workflows(c).run(m,imported=asset,response=response)
 print(json.dumps(r,indent=2));raise SystemExit(0 if r['ok'] else 1)
except Exception as e:
 print(json.dumps({'ok':False,'status':'failed','error':str(e) if isinstance(e,CaptureError) else 'Local workflow failed; no success claimed'}));raise SystemExit(1)
