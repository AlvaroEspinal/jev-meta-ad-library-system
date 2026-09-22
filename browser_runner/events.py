"""Cockpit event client: loopback-only, authenticated, no silent failure."""
import json
import urllib.request
import threading
from datetime import datetime, timezone
from urllib.parse import urlparse

class CockpitError(RuntimeError):
    pass

def utc_now():
    return datetime.now(timezone.utc).isoformat()

class CockpitClient:
    def __init__(self, port: int, token: str, opener=None, initial_seq=None):
        if not (1 <= int(port) <= 65535):
            raise ValueError("cockpit port must be 1-65535")
        if not token or len(token) < 24:
            raise ValueError("cockpit token is required and must be at least 24 characters")
        self.url = f"http://127.0.0.1:{int(port)}/api/events"
        self.token = token
        self.opener = opener or urllib.request.urlopen
        self._seq = dict(initial_seq or {})
        self._lock = threading.Lock()

    def emit(self, run_id, worker_id, kind, *, company=None, url=None, ads=None, detail=None):
        with self._lock:
            seq = self._seq.get(worker_id, 0) + 1
            self._seq[worker_id] = seq
        payload = {"run_id": run_id, "worker_id": worker_id, "seq": seq, "type": kind,
                   "timestamp": utc_now()}
        if company is not None: payload["company"] = company
        if url is not None: payload["url"] = url
        if ads is not None:
            if not isinstance(ads, int) or ads < 0: raise ValueError("ads must be a nonnegative integer")
            payload["ads"] = ads
        if detail is not None: payload["detail"] = detail
        request = urllib.request.Request(self.url, data=json.dumps(payload).encode(), method="POST",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.token}"})
        try:
            with self.opener(request, timeout=5) as response:
                if response.status not in range(200, 300): raise CockpitError(f"cockpit returned HTTP {response.status}")
                body=json.loads(response.read() or b"{}")
                if isinstance(body, dict) and body.get("accepted") is False:
                    raise CockpitError("cockpit rejected event")
                return body
        except Exception as exc:
            raise CockpitError(f"cockpit event rejected: {exc}") from exc
