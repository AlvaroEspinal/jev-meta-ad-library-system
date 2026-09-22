#!/usr/bin/env python3
"""Submit a clearly labeled synthetic 10-worker fixture to a local cockpit."""
import argparse
import json
import os
from datetime import datetime, timezone
from urllib.request import Request, urlopen


def post(url, token, event):
    request = Request(url, data=json.dumps(event).encode(), method="POST", headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
    with urlopen(request, timeout=5) as response:
        if response.status not in (200, 202): raise RuntimeError(f"cockpit returned {response.status}")


def main():
    parser = argparse.ArgumentParser(description="Synthetic cockpit fixture; never browses or scrapes.")
    parser.add_argument("--url", default="http://127.0.0.1:8877/api/events")
    parser.add_argument("--token", default=os.environ.get("JEV_COCKPIT_TOKEN"))
    parser.add_argument("--run-id", default="synthetic-10-worker-demo")
    args = parser.parse_args()
    if not args.token: parser.error("set JEV_COCKPIT_TOKEN or pass --token")
    stamp = datetime.now(timezone.utc).isoformat()
    base = {"run_id": args.run_id, "timestamp": stamp, "detail": {"fixture": True, "message": "Synthetic demo receipt; no browser was run."}}
    post(args.url, args.token, {**base, "worker_id": "coordinator", "seq": 1, "type": "run_started"})
    for number in range(1, 11):
        worker = f"worker-{number:02d}"
        post(args.url, args.token, {**base, "worker_id": worker, "seq": 1, "type": "worker_started", "company": f"Synthetic Company {number}"})
        post(args.url, args.token, {**base, "worker_id": worker, "seq": 2, "type": "observation", "company": f"Synthetic Company {number}", "ads": number % 4, "detail": {"fixture": True, "message": "Synthetic observation; no browser was run."}})
        post(args.url, args.token, {**base, "worker_id": worker, "seq": 3, "type": "worker_complete", "ads": number % 4})
    post(args.url, args.token, {**base, "worker_id": "coordinator", "seq": 2, "type": "run_complete"})

if __name__ == "__main__": main()
