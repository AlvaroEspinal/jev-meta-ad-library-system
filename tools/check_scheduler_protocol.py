#!/usr/bin/env python3
"""Offline 12-job shuffled-completion check against the real local cockpit.

Only the multiprocessing process primitive and source collector are faked. The
actual runner scheduler, CockpitClient HTTP, cockpit validation, and durable
store are exercised. No browser or model call occurs.
"""
from __future__ import annotations

import json
import os
import queue
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from browser_runner import runner  # noqa: E402
from browser_runner.events import CockpitClient  # noqa: E402


class FakeProcess:
    def __init__(self, target, args):
        self.target, self.args = target, args
        self.exitcode = None
        self._thread = None

    def start(self):
        def invoke():
            try:
                self.target(*self.args)
                self.exitcode = 0
            except BaseException:
                self.exitcode = 1
        self._thread = threading.Thread(target=invoke, daemon=True)
        self._thread.start()

    def join(self, timeout=None):
        self._thread.join(timeout)

    def is_alive(self):
        return self._thread.is_alive()

    def terminate(self):
        raise AssertionError("unexpected termination in offline check")


class FakeContext:
    def Queue(self):
        return queue.Queue()

    def Process(self, target, args):
        return FakeProcess(target, args)


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def run():
    with tempfile.TemporaryDirectory(prefix="jev-scheduler-check-") as temporary:
        port = free_port()
        token = "synthetic-offline-token-" + "x" * 32
        data = Path(temporary) / "history.json"
        process = subprocess.Popen(
            [sys.executable, str(ROOT / "cockpit/server.py"), "--port", str(port), "--data", str(data)],
            cwd=ROOT, env={**os.environ, "JEV_COCKPIT_TOKEN": token},
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        )
        original_context = runner.multiprocessing.get_context
        original_collect = runner.upstream_adapter.collect
        try:
            deadline = time.monotonic() + 8
            while True:
                try:
                    with urlopen(f"http://127.0.0.1:{port}/api/state", timeout=1) as response:
                        json.load(response)
                    break
                except Exception:
                    if time.monotonic() > deadline:
                        raise RuntimeError("cockpit did not start")
                    time.sleep(0.05)

            runner.multiprocessing.get_context = lambda _mode: FakeContext()

            def fake_collect(job):
                index = int(job["company"]["page_id"]) - 1000
                time.sleep(((11 - index) % 5) * 0.015)
                return {"outcome": "active_ads", "ads": 1,
                        "detail": {"visible_ad_ids": [str(index)], "fixture": True}}

            runner.upstream_adapter.collect = fake_collect
            companies = [{"name": f"Fixture Company {i}", "page_id": str(1000 + i)} for i in range(12)]
            summary = runner.execute(companies, 10, Path(temporary) / "run", CockpitClient(port, token), worker_timeout=5)
            with urlopen(f"http://127.0.0.1:{port}/api/state", timeout=2) as response:
                state = json.load(response)
            current = state["active_run"]
            assert summary["companies"] == 12 and summary["active_ads"] == 12 and summary["status"] == "complete"
            assert current["summary"]["workers"] == 12
            assert current["summary"]["complete"] == 12
            assert current["summary"]["observed_ads"] == 12
            assert len(current["workers"]) <= 11  # ten browser lanes, optional coordinator receipt
            assert len([w for w in current["workers"] if w["worker_id"].startswith("worker-")]) <= 10
            assert all(w["status"] == "complete" for w in current["workers"] if w["worker_id"].startswith("worker-"))
            return {"ok": True, "jobs": 12, "browser_lanes": 10, "visible_id_observations": 12,
                    "paid_calls": 0, "browser_sessions": 0}
        finally:
            runner.multiprocessing.get_context = original_context
            runner.upstream_adapter.collect = original_collect
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)
            if process.stderr:
                process.stderr.close()


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
