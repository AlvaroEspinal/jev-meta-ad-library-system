# Architecture, roles and modes

`authorized capture -> normalized evidence -> deterministic validation -> bounded questions -> typed validation -> coded review policy -> approved handler -> independent readback`

- Capture layer: public/user-authorized inputs only, timestamped source IDs, content hashes, stable fields, missing-field states. No model credentials in a browser.
- State builder: minimal relevant evidence; mark quoted text untrusted. Retrieve wide summaries, then fetch only shortlisted material. Re-evaluate after evidence changes.
- Jev: choose among enumerated answers; cannot grant permission, prove truth or execute arbitrary selectors/code. A separate generative worker writes copy/artifacts.
- Host: validates schema, freshness, allowed targets, risk thresholds and authorization. Numeric work/deduplication remain deterministic.
- Policy: uncertainty/missing/error -> review or existing fallback. Timeout is not 'no', API failure is not a pass. Thresholds must be calibrated per task/risk, not copied from a demo.
- Executor: one authorized execution path, with idempotency and a completion receipt. If an error may follow a side effect, read back before retrying.
- Memory: curated Obsidian Markdown is durable human context. Evidence manifests are immutable provenance; indexes and cockpit views are rebuildable. Keep private client data out of share bundles and model inputs without authorization.

## Off, shadow, active
Off: no model calls/cost. Shadow: same decision-time state, log proposal and compare against the existing path, **no second execution**. Active: only an evaluated and authorized handler runs; preserve rollback/fallback. Synthetic replay is another separate mode; never label it live.

## Independent batch judgments
Batch only questions answerable from the same original state. Awareness and angle can share a captured ad. A question about a landing page cannot precede page retrieval. Parallel workers have independent browser contexts and private worker state; one coordinator owns shared telemetry and history. Do not run competing writers.

## Cockpit compatibility
Five-stage `journey` counts, `angles[].stages` and creative `journey_stage` refer to awareness. The record also retains captured copy, CTA, URLs, confidence, model and provenance. Discovery, enrichment, classification, accepted classifications and verified business outcomes have separate counts. Per-run state does not reset cumulative history. Deduplicate entities; count repeated checks as observations, not additional unique companies/ads.

The ten-browser wall represents the latest step capture for each lane, not continuous live video. Show staleness, failure, timestamps and cleanup status. Missing telemetry stays unknown (`null`), not zero. Provider model cost excludes browser infrastructure unless explicitly reconciled.
