#!/usr/bin/env python3
"""Reject obvious private material from the exact Git index before a push.

This is a targeted guard, not a complete secret scanner or permission audit.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def git(*args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True).stdout


def run() -> dict:
    names = [name.decode() for name in git("ls-files", "-z").split(b"\0") if name]
    errors = []
    path_block = re.compile(
        r"(^|/)(?:\.env(?:\..*)?|node_modules|__pycache__|state|evidence|runs|artifacts|output)(?:/|$)"
        r"|\.(?:pem|p12|key|sqlite3?|db|log)$", re.I
    )
    secret_patterns = [
        re.compile(rb"gh[opsu]_[A-Za-z0-9_]{20,}"),
        re.compile(rb"sk-[A-Za-z0-9_-]{20,}"),
        re.compile(rb"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
        re.compile(rb"/Users/[A-Za-z0-9_.-]+/"),
        re.compile(rb"/home/[A-Za-z0-9_.-]+/"),
        re.compile(rb"@[A-Za-z0-9.-]+\.(?:ai|com|net|org)\b", re.I),
    ]
    # Verifier source intentionally contains *patterns* that reject absolute paths,
    # credentials and email addresses. They are not private data themselves.
    verifier_paths = {
        "research-pack/tools/verify.py",
        "research-pack/research-kit/scripts/verify.py",
        "tools/check_publication.py",  # This guard contains the searched patterns as code.
    }
    synthetic_userinfo_paths = {
        "research-pack/research-capture/tests/policy.test.js",
        "research-pack/research-capture/tests/test_media.py",
    }
    for name in names:
        if path_block.search(name):
            errors.append(f"forbidden filename: {name}")
            continue
        content = git("show", f":{name}")
        if b"\0" in content:
            errors.append(f"binary file requires manual review: {name}")
            continue
        if name in verifier_paths:
            continue
        for pattern in secret_patterns:
            for match in pattern.finditer(content):
                if name in synthetic_userinfo_paths and match.group().endswith(b"@example.com"):
                    continue
                errors.append(f"sensitive pattern in {name}: {pattern.pattern.decode(errors='replace')}")
        for label in (b"DOCA Boston", b"Told by Fire", b"Proteoformist", b"Rovina"):
            if label.lower() in content.lower():
                errors.append(f"client/private label in {name}: {label.decode()}")
    return {"ok": not errors, "indexed_files": len(names), "errors": errors,
            "limits": "Pattern guard only; still inspect source, history, permissions, accounts and license manually."}


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2))
    if not result["ok"]:
        raise SystemExit(1)
