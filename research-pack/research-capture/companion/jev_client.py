#!/usr/bin/env python3
"""One-call OpenRouter evaluator; validates proposals, never accepts or executes them."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPRedirectHandler, ProxyHandler

from jev_contract import (CONTRACT_VERSION, MAX_RESPONSE_BYTES, ContractError,
                          canonical, safe_usage, strict_json, validate_request,
                          validate_response)

ENDPOINT = "https://openrouter.ai/api/alpha/decisions"
DEFAULT_MODEL = "~typesafe/jev-latest"


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise HTTPError(req.full_url, code, "Redirect refused", headers, fp)

def urlopen(request, timeout):
    return build_opener(ProxyHandler({}), NoRedirect()).open(request, timeout=timeout)


def fail(message, code=2):
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(code)


def get_key():
    # Dedicated credential only; no silent fallback to another project/general key.
    key = os.environ.get("OPENROUTER_JEV_API_KEY", "").strip()
    if key:
        return key
    if sys.platform == "darwin":
        proc = subprocess.run(["/usr/bin/security", "find-generic-password", "-s", "openrouter", "-a", "jev-api-key", "-w"], text=True, capture_output=True, check=False)
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
    raise RuntimeError("credential_unavailable")


def write_receipt(path, record, *, reserve=False):
    """Exclusive reservation BEFORE credential/network access; atomic owned updates."""
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(record, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if reserve:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as out:
            out.write(encoded)
            out.flush()
            os.fsync(out.fileno())
    else:
        temp = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as out:
                temp = Path(out.name)
                out.write(encoded)
                out.flush()
                os.fsync(out.fileno())
            temp.replace(path)
        finally:
            if temp is not None and temp.exists():
                temp.unlink()  # Only our own new temporary file, never prior user evidence.


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--expected-model", help="Optional exact resolved-version gate")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--task-class", default="unqualified")
    parser.add_argument("--question-set-version", default="unversioned")
    args = parser.parse_args(argv)
    out = Path(args.out).expanduser()
    if out.exists() or out.is_symlink():
        fail("output already exists; use a new result path, not the dry-run plan path")
    try:
        raw = sys.stdin.read() if args.input == "-" else Path(args.input).expanduser().read_text()
        payload = validate_request(strict_json(raw), args.model)
        request_bytes = canonical(payload)
    except (OSError, UnicodeError, ContractError):
        fail("invalid request; check the local request contract (no call attempted)")
    record = {
        "schema_version": CONTRACT_VERSION,
        "status": "started" if args.execute else "dry_run",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "endpoint": ENDPOINT, "provider": "openrouter",
        "requested_model": args.model, "resolved_model": None, "response_id": None,
        "expected_model": args.expected_model,
        "request_sha256": hashlib.sha256(request_bytes).hexdigest(),
        "state_sha256": hashlib.sha256(canonical(payload["state"])).hexdigest(),
        "questions_sha256": hashlib.sha256(canonical(payload["questions"])).hexdigest(),
        "request_bytes": len(request_bytes), "question_names": list(payload["questions"]),
        "task_class": args.task_class, "question_set_version": args.question_set_version,
        "policy_version": "review-only/v1", "disposition": "not_checked",
        "validated": False, "accepted": False, "review_required": True,
        "attempt_count": 0, "http_status": None, "latency_ms": None,
        "answers": None, "usage": None, "cost_usd": None,
        "usage_status": "unknown", "outcome_verified": False,
    }
    try:
        write_receipt(out, record, reserve=True)
    except OSError:
        fail("cannot reserve output receipt; no call attempted")
    if not args.execute:
        print(json.dumps(record, indent=2))
        return
    started = time.monotonic()
    error = None
    try:
        key = get_key()
        req = Request(ENDPOINT, data=request_bytes,
                      headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                      method="POST")
        record["attempt_count"] = 1
        # Persist dispatch intent: an interrupted process is not proof no call occurred.
        write_receipt(out, record)
        with urlopen(req, timeout=20) as response:
            record["http_status"] = response.status
            raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise ContractError("response too large")
        if record["http_status"] != 200:
            error = "http_error"
        else:
            response_json = strict_json(raw)
            if isinstance(response_json, dict):
                record["usage"] = safe_usage(response_json.get("usage"))
                if record["usage"]:
                    record["usage_status"] = "provider_reported"
                    record["cost_usd"] = record["usage"].get("cost", record["usage"].get("total_cost"))
                if isinstance(response_json.get("id"), str):
                    record["response_id"] = response_json["id"][:256]
                if isinstance(response_json.get("model"), str):
                    record["resolved_model"] = response_json["model"][:256]
            record["answers"] = validate_response(response_json, payload["questions"], args.expected_model)
            record.update(status="completed", validated=True, disposition="review_required")
    except HTTPError as exc:
        record["http_status"] = exc.code
        error = "http_error"  # Never print or persist provider error bodies.
    except (URLError, TimeoutError):
        error = "transport_error"
    except ContractError as exc:
        record["validation_error"] = str(exc)  # Contract messages contain no provider values.
        error = "invalid_response"
    except (RuntimeError, OSError):
        error = "credential_or_local_error"
    except Exception:
        error = "unexpected_client_error"  # Sanitized; preserve a failure receipt.
    record["latency_ms"] = round((time.monotonic() - started) * 1000)
    if error:
        record.update(status="failed", error_class=error, disposition="not_checked", answers=None)
    try:
        write_receipt(out, record)
    except OSError:
        fail("final receipt persistence failed; inspect started receipt before considering any retry", 1)
    print(json.dumps(record, indent=2, ensure_ascii=False))
    if error:
        fail(f"{error}; failure receipt saved; no automatic retry", 1)


if __name__ == "__main__":
    main()
