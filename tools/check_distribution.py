#!/usr/bin/env python3
"""Cold, offline integration check for the shareable cockpit and research pack.

Uses only synthetic runner receipts and a temporary loopback server/state directory.
Never starts a browser, calls a model, or reads an account credential.
"""
from __future__ import annotations

import json
import os
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def get_json(url: str, *, host: str | None = None) -> dict:
    request = Request(url, headers={"Host": host} if host else {})
    with urlopen(request, timeout=2) as response:
        return json.load(response)


def wait_ready(url: str, process: subprocess.Popen) -> dict:
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"cockpit exited early: {process.returncode}")
        try:
            return get_json(url)
        except (URLError, TimeoutError):
            time.sleep(0.05)
    raise RuntimeError("cockpit did not become ready")


def start(port: int, data: Path, token: str) -> subprocess.Popen:
    env = {**os.environ, "JEV_COCKPIT_TOKEN": token}
    return subprocess.Popen(
        [sys.executable, "cockpit/server.py", "--port", str(port), "--data", str(data)],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )


def stop(process: subprocess.Popen) -> None:
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=3)
    if process.stderr:
        process.stderr.close()


def run() -> dict:
    with tempfile.TemporaryDirectory(prefix="jev-friend-cold-") as temporary:
        state_dir = Path(temporary)
        data = state_dir / "history.json"
        token = secrets.token_urlsafe(32)
        port = free_port()
        url = f"http://127.0.0.1:{port}/api/state"
        process = start(port, data, token)
        try:
            initial = wait_ready(url, process)
            assert initial["totals"].get("runs", 0) == 0, initial["totals"]

            unauthorized = Request(
                f"http://127.0.0.1:{port}/api/events",
                data=b"{}",
                method="POST",
                headers={"Content-Type": "application/json"},
            )
            try:
                urlopen(unauthorized, timeout=2)
                raise AssertionError("unauthorized event write succeeded")
            except HTTPError as exc:
                assert exc.code == 401, exc.code

            try:
                get_json(url, host="attacker.example")
                raise AssertionError("foreign Host was accepted")
            except HTTPError as exc:
                assert exc.code == 403, exc.code

            subprocess.run(
                [sys.executable, "-m", "browser_runner.replay", "--cockpit-port", str(port),
                 "--cockpit-token", token, "--delay-ms", "0"],
                cwd=ROOT,
                check=True,
                timeout=20,
                capture_output=True,
                text=True,
            )
            live = get_json(url)
            assert live["active_run"]["synthetic"] is True
            assert len([w for w in live["active_run"]["workers"] if w["worker_id"].startswith("worker-")]) == 10
            assert live["active_run"]["summary"]["workers"] == 10
            assert live["active_run"]["summary"].get("blocked", 0) == 1
            assert live["active_run"]["summary"].get("zero_ads", 0) == 1
            assert live["active_run"]["summary"]["observed_ads"] == 38
            revision = live["revision"]
        finally:
            stop(process)

        assert data.is_file(), "history was not saved"
        assert data.stat().st_mode & 0o077 == 0, "history is not owner-only"
        port = free_port()
        process = start(port, data, token)
        try:
            restored = wait_ready(f"http://127.0.0.1:{port}/api/state", process)
            assert restored["revision"] == revision
            assert restored["active_run"]["summary"]["observed_ads"] == 38
            assert restored["active_run"]["summary"].get("blocked", 0) == 1
        finally:
            stop(process)

    # Verify a cold distribution copy rather than a developer's source folder,
    # which may legitimately contain Python caches from previous tests.
    source_pack = ROOT / "research-pack"
    manifest = json.loads((source_pack / "MANIFEST.json").read_text())
    with tempfile.TemporaryDirectory(prefix="jev-friend-pack-cold-") as temporary:
        pack = Path(temporary) / "research-pack"
        for relative in [*manifest["files"], "MANIFEST.json", "SHA256SUMS"]:
            source = source_pack / relative
            target = pack / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        result = subprocess.run(
            [sys.executable, "tools/verify.py", "--strict"], cwd=pack, check=True,
            capture_output=True, text=True, timeout=20,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
    pack_receipt = json.loads(result.stdout)
    assert pack_receipt["ok"] is True and pack_receipt["files_checked"] == 75
    return {
        "ok": True,
        "synthetic_workers": 10,
        "synthetic_observed_ads": 38,
        "blocked_workers": 1,
        "zero_ad_workers": 1,
        "restart_preserved_revision": revision,
        "pack_files_verified": 75,
        "paid_calls": 0,
        "browser_sessions": 0,
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
