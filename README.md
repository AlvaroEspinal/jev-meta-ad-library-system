# Jev Research System — friend edition

This repository brings together three **separate** local components:

1. `browser_runner/` — an opt-in Browser Use cloud observer for recipient-supplied public advertiser targets, with optional bounded Jev evidence review. It sends observed progress to the cockpit automatically.
2. `cockpit/` — a loopback-only, authenticated live view for up to ten worker lanes and durable run history.
3. `research-pack/` — the separately verified Research Capture extension and portable marketing/decision kit. Start at [`research-pack/START-HERE.md`](research-pack/START-HERE.md).

The cockpit receives structured events from the runner; it does **not** control a browser or claim that visible ads are a complete Meta Ad Library census. This is a research prototype and demonstration framework, not a production scraper, local Jev model, ad publisher, or access to the sender's accounts. The capture extension is a separate reviewed workflow, not a background collector. Read [`SECURITY.md`](SECURITY.md) before any live use.

## First-time setup

Hand [`SETUP-FOR-YOUR-AGENT.md`](SETUP-FOR-YOUR-AGENT.md) to your own coding agent. It tells the agent how to inspect, install and verify this repository **on your computer**, and where to ask you for your own credentials, browser access, vault and public targets. Never send secrets into a chat or commit them to this repo.

**Offline acceptance first:** `research-pack` ships its own strict hash and cold-fixture verification tools. The cockpit and runner also provide synthetic ten-worker tests; run them before connecting to a live source. The runner uses **fresh Browser Use Cloud sessions only**, never local Chrome. Live cloud access, provider availability and paid usage require separate approval and readback. Installing the optional Research Capture extension/native host is a different approval and is not needed for the runner-to-cockpit connection.

From a clean clone, run the no-account acceptance check:

```sh
python3 tools/check_distribution.py
```

It starts a temporary loopback cockpit, replays ten **synthetic** worker receipts, checks the blocked and zero-ad lanes, restarts the cockpit to verify retained history, and verifies the pinned research pack. It makes no browser or paid-model calls. To view the synthetic dashboard yourself, keep the same terminal open:

```sh
export JEV_COCKPIT_TOKEN="$(python3 cockpit/server.py --print-token)"
python3 cockpit/server.py --port 8877 &
COCKPIT_PID=$!
sleep 1
python3 -m browser_runner.replay --cockpit-port 8877
```

Open `http://127.0.0.1:8877`. The replay is conspicuously labeled synthetic and is excluded from real cumulative totals. When finished, run `kill "$COCKPIT_PID"` in that same terminal to stop only the cockpit process started above. For real setup, follow [`browser_runner/README.md`](browser_runner/README.md) and [`cockpit/README.md`](cockpit/README.md); nothing in this quick start authenticates a provider or visits Meta.

## Boundaries

- No sender credentials, client datasets, historical ad results, browser profiles or private vault are shipped.
- The browser runner and cockpit connect over authenticated `127.0.0.1` HTTP. Do not expose or tunnel that port.
- Instagram browser/UI/DOM/cookies/session/screenshot automation is prohibited. Use an approved non-browser source route if separately configured; otherwise stop.
- Public Meta Ad Library observation is read-only and may be blocked or incomplete. Keep `zero_ads`, `source_blocked`, unresolved identity and unobserved targets distinct.
- No paid API or browser session is invoked by default. Live use requires the recipient's own accounts and explicit opt-in.
- Jev judgments are bounded suggestions. Decisions, records and receipts require validation and human review; model output is not verified ground truth.

## Provenance

The browser-use/Jev approach builds on the MIT-licensed [Browser Use Jev Ultrafast](https://github.com/browser-use/jev-ultrafast) project; retain its copyright notice for any copied source. The pack's exact pinned source versions and verification receipt are in [`research-pack/VERSION.json`](research-pack/VERSION.json) and [`research-pack/VERIFICATION-RECEIPT.json`](research-pack/VERIFICATION-RECEIPT.json). See [`THIRD-PARTY-NOTICES.md`](THIRD-PARTY-NOTICES.md) for attribution and dependency boundaries.

Original code in this private repository is offered to invited collaborators or direct owner-provided copy recipients under [`LICENSE`](LICENSE); Browser Use-derived files retain their separate MIT notice. This is not a public/open-source release unless the owner chooses to relicense it.
