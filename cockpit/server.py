#!/usr/bin/env python3
"""Loopback-only, authenticated cockpit for observed browser-runner receipts.

It never starts browsers or calls a provider. A compatible runner submits bounded
receipts; the UI renders those observations and labels fixture data explicitly.
"""
from __future__ import annotations

import argparse
import copy
import hmac
import json
import os
import secrets
import threading
from collections import Counter
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import urlparse

MAX_BODY = 32 * 1024
MAX_EVENTS_PER_RUN = 250
EVENT_TYPES = {
    "run_started", "worker_started", "observation", "zero_ads", "source_blocked",
    "worker_complete", "worker_failed", "run_complete",
}
WORKER_TERMINAL = {"complete", "failed", "blocked", "zero_ads"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_store() -> Path:
    return Path(os.environ.get("JEV_COCKPIT_DATA", "~/.local/share/jev-friend-cockpit/history.json")).expanduser()


def _trim(value: object, limit: int) -> str:
    if not isinstance(value, str):
        raise ValueError("must be a string")
    value = value.strip()
    if not value or len(value) > limit:
        raise ValueError(f"must be 1–{limit} characters")
    return value


def _safe_detail(detail: object) -> dict:
    if detail is None:
        return {}
    if not isinstance(detail, dict):
        raise ValueError("detail must be an object")
    encoded = json.dumps(detail, separators=(",", ":"), ensure_ascii=False)
    if len(encoded.encode()) > 4096:
        raise ValueError("detail exceeds 4 KB")
    return detail


def validate_event(value: object) -> dict:
    if not isinstance(value, dict):
        raise ValueError("event must be a JSON object")
    event = {
        "run_id": _trim(value.get("run_id"), 128),
        "worker_id": _trim(value.get("worker_id"), 128),
        "type": _trim(value.get("type"), 48),
        "timestamp": _trim(value.get("timestamp"), 64),
    }
    if event["type"] not in EVENT_TYPES:
        raise ValueError("unsupported event type")
    try:
        datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("timestamp must be ISO-8601") from exc
    seq = value.get("seq")
    if not isinstance(seq, int) or isinstance(seq, bool) or not 0 <= seq <= 10_000_000:
        raise ValueError("seq must be a non-negative integer")
    event["seq"] = seq
    for key, limit in (("company", 240), ("url", 2048)):
        if key in value and value[key] is not None:
            event[key] = _trim(value[key], limit)
    if "ads" in value and value["ads"] is not None:
        ads = value["ads"]
        if not isinstance(ads, int) or isinstance(ads, bool) or not 0 <= ads <= 10_000_000:
            raise ValueError("ads must be a non-negative integer")
        event["ads"] = ads
    event["detail"] = _safe_detail(value.get("detail"))
    return event


class Store:
    def __init__(self, path: Path):
        self.path = path
        self.lock = threading.RLock()
        self.changed = threading.Condition(self.lock)
        self.data = self._read()

    def _read(self) -> dict:
        if not self.path.exists():
            return {"schema": 1, "runs": {}, "revision": 0}
        try:
            data = json.loads(self.path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"cockpit history is unreadable: {exc}") from exc
        if not isinstance(data, dict) or not isinstance(data.get("runs"), dict):
            raise RuntimeError("cockpit history has an unsupported schema")
        data.setdefault("schema", 1)
        data.setdefault("revision", 0)
        return data

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.path.parent.chmod(0o700)
        except OSError:
            pass
        with NamedTemporaryFile("w", dir=self.path.parent, delete=False, encoding="utf-8") as tmp:
            json.dump(self.data, tmp, ensure_ascii=False, separators=(",", ":"))
            tmp.write("\n")
            temporary = Path(tmp.name)
        temporary.replace(self.path)

    def add(self, event: dict) -> tuple[dict, bool]:
        with self.changed:
            run = self.data["runs"].setdefault(event["run_id"], {
                "run_id": event["run_id"], "started_at": event["timestamp"], "updated_at": event["timestamp"],
                "status": "received", "workers": {}, "jobs": {}, "events": [], "synthetic": False,
            })
            kind = event["type"]
            worker = None
            if kind in {"run_started", "run_complete"}:
                controls = run.setdefault("control_seq", {})
                if event["seq"] <= controls.get(event["worker_id"], -1):
                    return self.state_locked(), False
                controls[event["worker_id"]] = event["seq"]
            else:
                worker = run["workers"].setdefault(event["worker_id"], {
                    "worker_id": event["worker_id"], "status": "waiting", "last_seq": -1,
                    "company": None, "url": None, "observed_ads": 0, "updated_at": event["timestamp"], "detail": {}, "job_id": None,
                })
                if event["seq"] <= worker["last_seq"]:
                    return self.state_locked(), False
                worker["last_seq"] = event["seq"]
                worker["updated_at"] = event["timestamp"]
            if event.get("detail", {}).get("fixture") is True:
                run["synthetic"] = True
            # A lane can be reused. Each worker_started opens an immutable job receipt;
            # totals derive from jobs, never from the ten visible lane snapshots.
            if kind == "worker_started":
                job_id = f"{event['worker_id']}:{event['seq']}"
                job = {"job_id": job_id, "worker_id": event["worker_id"], "status": "running", "company": event.get("company"), "url": event.get("url"), "observed_ads": 0, "started_at": event["timestamp"], "updated_at": event["timestamp"], "detail": event.get("detail") or {}}
                run["jobs"][job_id] = job
                worker["job_id"] = job_id
                worker["status"] = "running"
                worker["observed_ads"] = 0
            job = run["jobs"].get(worker.get("job_id")) if worker is not None else None
            if worker is not None:
                for key in ("company", "url"):
                    if key in event:
                        worker[key] = event[key]
                        if job is not None: job[key] = event[key]
            if kind == "run_started":
                run["status"] = "running"
            elif kind == "observation":
                worker["status"] = "running"
                if job is not None:
                    job["status"] = "running"; job["updated_at"] = event["timestamp"]
                # Every event's ads count is a fresh observed count, not an estimate.
                if "ads" in event:
                    worker["observed_ads"] = event["ads"]
                    if job is not None: job["observed_ads"] = event["ads"]
            elif kind == "zero_ads":
                worker["status"] = "zero_ads"; worker["observed_ads"] = 0
                if job is not None: job.update({"status": "zero_ads", "observed_ads": 0, "updated_at": event["timestamp"]})
            elif kind == "source_blocked":
                worker["status"] = "blocked"
                if job is not None: job.update({"status": "blocked", "updated_at": event["timestamp"]})
            elif kind == "worker_complete":
                # Completion is transport success, not permission to erase a distinct
                # zero-result or blocked outcome observed earlier in the job.
                prior = job.get("status") if job is not None else worker.get("status")
                terminal = prior if prior in {"zero_ads", "blocked", "failed"} else "complete"
                worker["status"] = terminal
                if "ads" in event and terminal == "complete": worker["observed_ads"] = event["ads"]
                if job is not None:
                    job["status"] = terminal; job["updated_at"] = event["timestamp"]
                    if "ads" in event and terminal == "complete": job["observed_ads"] = event["ads"]
            elif kind == "worker_failed":
                worker["status"] = "failed"
                if job is not None: job.update({"status": "failed", "updated_at": event["timestamp"]})
            elif kind == "run_complete":
                requested = event.get("detail", {}).get("status")
                job_statuses = {item.get("status") for item in run.get("jobs", {}).values()}
                if requested in {"complete", "partial", "blocked", "failed"}:
                    run["status"] = requested
                elif "failed" in job_statuses or "blocked" in job_statuses:
                    run["status"] = "partial"
                else:
                    run["status"] = "complete"
            if worker is not None:
                worker["detail"] = event.get("detail") or worker["detail"]
            if job is not None: job["detail"] = event.get("detail") or job["detail"]
            run["updated_at"] = event["timestamp"]
            run["events"].append(event)
            run["events"] = run["events"][-MAX_EVENTS_PER_RUN:]
            self.data["revision"] += 1
            self._save()
            self.changed.notify_all()
            return self.state_locked(), True

    def state(self) -> dict:
        with self.lock:
            return self.state_locked()

    def state_locked(self) -> dict:
        runs = sorted(self.data["runs"].values(), key=lambda r: (r.get("started_at", ""), r["run_id"]), reverse=True)
        totals = Counter()
        synthetic_totals = Counter()
        output = []
        for run in runs:
            workers = sorted(copy.deepcopy(list(run["workers"].values())), key=lambda w: w["worker_id"])
            jobs = list(run.get("jobs", {}).values())
            # Support only histories written by this schema; missing jobs means no claimed aggregate.
            status = Counter(job["status"] for job in jobs)
            observed = sum(job.get("observed_ads", 0) for job in jobs)
            target = synthetic_totals if run.get("synthetic") else totals
            target["runs"] += 1
            target["workers"] += len(jobs)
            target["observed_ads"] += observed
            target["completed_workers"] += status["complete"]
            target["blocked_workers"] += status["blocked"]
            target["failed_workers"] += status["failed"]
            target["zero_ad_workers"] += status["zero_ads"]
            output.append({
                "run_id": run["run_id"], "started_at": run.get("started_at"), "updated_at": run.get("updated_at"),
                "status": run.get("status"), "synthetic": bool(run.get("synthetic")), "workers": workers,
                "summary": {"workers": len(jobs), "observed_ads": observed, **dict(status)},
            })
        return {
            "schema": 1, "revision": self.data["revision"], "server_time": now(), "history_file": str(self.path),
            # Fixture/replay receipts are deliberately excluded from production totals.
            "totals": dict(totals), "synthetic_totals": dict(synthetic_totals), "runs": output, "active_run": output[0] if output else None,
            "limits": {"max_event_bytes": MAX_BODY, "max_event_log_per_run": MAX_EVENTS_PER_RUN},
        }


class App:
    def __init__(self, store: Store, token: str):
        self.store, self.token = store, token

    def authorized(self, headers) -> bool:
        value = headers.get("Authorization", "")
        return hmac.compare_digest(value, f"Bearer {self.token}")


def make_handler(app: App, assets: Path):
    class Handler(BaseHTTPRequestHandler):
        server_version = "JevFriendCockpit/1.0"
        def log_message(self, fmt, *args):
            return
        def send_bytes(self, status: int, body: bytes, content_type: str = "application/json"):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.end_headers()
            self.wfile.write(body)
        def json(self, status: int, value: object):
            self.send_bytes(status, json.dumps(value, ensure_ascii=False).encode())
        def same_host(self) -> bool:
            return self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}"
        def do_GET(self):
            if not self.same_host(): return self.send_bytes(403, b"Forbidden", "text/plain")
            path = urlparse(self.path).path
            if path == "/api/state": return self.json(200, app.store.state())
            if path == "/api/events/stream":
                self.send_response(200); self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-store"); self.send_header("Connection", "keep-alive"); self.end_headers()
                revision = -1
                try:
                    while True:
                        with app.store.changed:
                            state = app.store.state_locked()
                            if state["revision"] == revision:
                                app.store.changed.wait(timeout=15)
                                state = app.store.state_locked()
                            revision = state["revision"]
                        self.wfile.write(f"event: state\\ndata: {json.dumps(state, ensure_ascii=False)}\\n\\n".encode()); self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError): pass
                return
            route = {"/": ("index.html", "text/html; charset=utf-8"), "/app.js": ("app.js", "text/javascript; charset=utf-8"), "/style.css": ("style.css", "text/css; charset=utf-8")}
            if path not in route: return self.send_bytes(404, b"Not found", "text/plain")
            name, mime = route[path]
            return self.send_bytes(200, (assets / name).read_bytes(), mime)
        def do_POST(self):
            if not self.same_host(): return self.send_bytes(403, b"Forbidden", "text/plain")
            if urlparse(self.path).path != "/api/events": return self.send_bytes(404, b"Not found", "text/plain")
            if not app.authorized(self.headers): return self.json(401, {"error": "Bearer token required"})
            try:
                length = int(self.headers.get("Content-Length", "-1"))
                if not 0 <= length <= MAX_BODY: raise ValueError("request body too large")
                event = validate_event(json.loads(self.rfile.read(length)))
                state, accepted = app.store.add(event)
                self.json(202 if accepted else 200, {"accepted": accepted, "revision": state["revision"]})
            except (ValueError, json.JSONDecodeError) as exc:
                self.json(400, {"error": str(exc)})
    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description="Local Jev runner cockpit (loopback only)")
    parser.add_argument("--port", type=int, default=8877)
    parser.add_argument("--data", type=Path, default=default_store())
    parser.add_argument("--token", default=os.environ.get("JEV_COCKPIT_TOKEN"))
    parser.add_argument("--print-token", action="store_true", help="Print a generated token and exit")
    args = parser.parse_args()
    if args.print_token:
        print(secrets.token_urlsafe(32)); return
    if not args.token or len(args.token) < 24:
        parser.error("set JEV_COCKPIT_TOKEN or pass a token of at least 24 characters")
    store = Store(args.data.expanduser())
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(App(store, args.token), Path(__file__).parent / "static"))
    print(f"Cockpit ready at http://127.0.0.1:{args.port} (loopback only)")
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()

if __name__ == "__main__": main()
