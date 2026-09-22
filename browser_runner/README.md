# Browser Use + Jev runner

A portable **public Meta Ad Library observer** with up to 10 fresh cloud-browser workers (2-minute provider lifetime per job) and automatic, authenticated updates to the local Cockpit. It is not a crawler, complete inventory, performance analyzer, or ad-publishing tool.

The included observer is a minimal, modified MIT-derived subset of [`browser-use/jev-ultrafast`](https://github.com/browser-use/jev-ultrafast): `browser.py` and `snapshot.js`, with the upstream MIT notice in `vendor/LICENSE-JEV-ULTRAFAST.txt`. It runs Browser Harness only in a fresh cloud browser. It never opens local Chrome, uses profile cookies, logs into Meta, or automates Instagram.

## Your setup

1. Start the Cockpit and copy its one-time loopback token into your current shell without printing it:
   ```bash
   read -rs 'Cockpit token (hidden): ' JEV_COCKPIT_TOKEN; echo
   export JEV_COCKPIT_TOKEN
   ```
2. Create and activate your own virtual environment, then install the pinned dependency:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   python3 -m pip install -r browser_runner/requirements.txt
   browser-harness auth login
   ```
   Browser Use Cloud authentication and any related billing are yours to configure and approve.
3. Supply your own verified company/page-ID JSON. Do not add client inputs, credentials, or run artifacts to Git:
   ```json
   {"companies":[{"name":"Example Builder","page_id":"1234567890"}]}
   ```

## Plan first: no browser, model, network, or paid use

```bash
python3 -m browser_runner.runner --companies browser_runner/examples/companies.example.json --workers 10
```

## Approved live observation

```bash
python3 -m browser_runner.runner --companies companies.json --workers 10 --output ./runs/demo-001 \
  --cockpit-port 8877 \
  --execute --approve-live-collection
```

The runner emits authenticated `Authorization: Bearer` events exclusively to `http://127.0.0.1:<port>/api/events`. Each actual worker has a stable lane ID and each company has a distinct `job_id`. A source block, ambiguous identity, coverage error, or cleanup problem stops unscheduled work and marks remaining jobs `unobserved_after_stop`; it is never reported as zero ads.

## Optional Jev evidence review

This optional mode makes **at most one paid, read-only, typed Jev classification per observed company**. It cannot select an element, navigate, fill a field, or otherwise act in the browser. Set your dedicated key only in your own process environment, then use an additional explicit approval:

```bash
read -rs 'JEV decision key (hidden): ' OPENROUTER_JEV_API_KEY; echo
export OPENROUTER_JEV_API_KEY
python3 -m browser_runner.runner --companies companies.json --workers 10 --output ./runs/demo-001 \
  --cockpit-port 8877 \
  --execute --approve-live-collection --approve-paid-jev
```

`JEV_MODEL` is optional. The endpoint is fixed to OpenRouter Decisions and redirects/proxy routing are refused. A malformed, failed, low-confidence, or contradicting Jev reply becomes `identity_unresolved`, stopping new work. A typed response is a review signal, not proof.

## Offline demo and validation

```bash
python3 -m browser_runner.replay --cockpit-port 8877
PYTHONPATH=. python3 -m pytest -q tests/test_browser_runner.py
```

The replay is unique each time and synthesizes 10 jobs: 8 observed (38 visible IDs), 1 explicit zero-ad state, and 1 source-blocked state. It never contacts Meta, Browser Use, Jev, or any model.

## What results mean

`active_ads` requires the exact requested page ID, the exact standalone visible company-name line, and visible active Library IDs. `no_active_ads` requires that same identity plus explicit no-results text. `source_blocked`, `identity_unresolved`, `source_error`, and `unobserved_after_stop` are review/failure states, not zero ads. Nothing here proves an ad inventory, duration, spend, audience, conversion rate, business qualification, or performance.
