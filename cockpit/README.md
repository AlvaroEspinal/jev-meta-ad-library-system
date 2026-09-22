# Jev Friend Cockpit

A local, loopback-only observer for receipts sent by the included browser runner. It shows up to ten concurrent workers, updates in real time through SSE (then polling fallback), and retains cumulative history in a local JSON file. The cumulative visible-ID observation total can include the same ad again when a later run observes it; it is not a de-duplicated industry inventory. It **does not scrape, navigate, control a browser, call Jev, or assert that observed ads are effective**.

## Start it

```bash
export JEV_COCKPIT_TOKEN="$(python3 cockpit/server.py --print-token)"
python3 cockpit/server.py --port 8766
```

Open `http://127.0.0.1:8766`. Keep the token private. The server binds only to `127.0.0.1`; it rejects requests whose Host header is not the exact local address and port.

Set `JEV_COCKPIT_DATA` to choose another local history path. History is atomic and retained across restarts; delete the JSON file yourself only if you intentionally want to erase it.

## Runner contract

Configure your browser-runner agent with:

```text
Cockpit URL: http://127.0.0.1:8766/api/events
Authorization: Bearer <JEV_COCKPIT_TOKEN>
```

Send one JSON receipt per observed runner transition (max 32 KB):

```json
{"run_id":"demo-2026-09-22","worker_id":"worker-01","seq":1,"type":"observation","timestamp":"2026-09-22T18:00:00Z","company":"Example Builder","url":"https://example.com","ads":3,"detail":{"message":"Observed listing count"}}
```

Allowed `type` values: `run_started`, `worker_started`, `observation`, `zero_ads`, `source_blocked`, `worker_complete`, `worker_failed`, `run_complete`.

`seq` must strictly increase per `{run_id, worker_id}`. Duplicate/out-of-order receipts are acknowledged but do not mutate history. `ads` is rendered only as the latest **observed visible-ID count** supplied by the runner, never an estimate. Cumulative totals intentionally retain repeated observations across runs; they do not claim unique ads unless a runner supplies independent de-duplication evidence. A `zero_ads` receipt is distinct from `source_blocked`. Set `detail.fixture: true` for synthetic test events; the UI labels that data as synthetic.

## Safe agent connection prompt

> Configure the browser runner to send only schema-valid, observed status receipts to the local Jev Friend Cockpit. Read `JEV_COCKPIT_TOKEN` only from its process environment; never store, log, or send it anywhere else. POST only to `http://127.0.0.1:8766/api/events` with `Authorization: Bearer <token>`. Do not use the cockpit to issue browser actions. For each worker, send increasing `seq` values and distinguish `zero_ads`, `source_blocked`, and `worker_failed`. Mark synthetic fixtures with `detail.fixture: true`.

## Test

```bash
python3 -m unittest discover -s tests -p 'test_cockpit*.py' -v
```

## Clearly labeled offline fixture

This exercises the automatic receipt path without opening a browser or making any network request beyond your own loopback cockpit:

```bash
python3 cockpit/fixture_events.py
```

It creates ten **Synthetic Company** worker cards and marks the run as synthetic in the UI. It is only a wiring check, not a demonstration of research performance.
