# Research Capture — Friend Distribution 0.2.1

Start with [the enclosing pack's START-HERE](../START-HERE.md) for prerequisites, safe key entry, generic install/uninstall, destination selection and offline tests. This directory contains the complete extension/companion source derived from capture v0.2.0, with portable macOS installation and a generic native-host namespace.

- [Capabilities](docs/capabilities.md)
- [Architecture](docs/architecture.md)
- [Acceptance boundaries](docs/acceptance.md)
- [Threat model](docs/jev-research-capture-threat-model.md)
- [Marketing and decision kit](../research-kit/README.md)

## Developer offline tests

Run from **this research-capture directory**:

```sh
npm ci --ignore-scripts
python3 -m unittest discover -s tests -v
npm test
python3 scripts/fixture_receipts.py
python3 scripts/verify_artifacts.py artifacts/fixture-vault
python3 scripts/workflow_fixtures.py
python3 scripts/verify_workflow_fixtures.py artifacts/workflow-fixtures
```

These commands do not invoke live model/source services. npm may contact its dependency registry; installation scripts are disabled. Fixture output directories must be new. The enclosing `tools/check-offline.py` performs these commands in a temporary copy rather than polluting your package.

## Explicit workflow CLI

`python3 scripts/workflow.py --config /absolute/reviewed-config.json --message /absolute/reviewed-message.json`

A message uses `command: workflow`, `mode: quick_download` or `save_obsidian`, the reviewed payload schema, and optional `asset_url`, `title`, `convert: original|mp3`, `fetch_landing` boolean. No output path or command string is accepted from the browser. Executable examples are in `tests/test_workflows.py`. Save without asset is note-only; save with asset stores both. Asset+screenshot together is refused; screenshot-only uses explicit evidence capture.

## External non-browser imports (Instagram included)

Configure and authorize the canonical non-browser provider separately. This pack does not launch one. Inspect its actual receipt; an empty result or success exit alone is not capture. A reviewed import envelope contains `transport: canonical-nonbrowser`, `adapter: canonical-instagram-scraper|canonical-apify`, `status: captured`, `browser_used: false`, relative `path`, `mime`, and `sha256`.

Invoke workflow.py with `--adapter-receipt FILE --adapter-root DIR --confirm-reviewed-nonbrowser-import`. For Instagram use `external_import: true`, method `instagram-url-handoff`, and URL+intent only. This imports authorized local bytes; it never visits Instagram. Envelope provenance fields are operator attestations, not cryptographic proof of provider behavior. Failed/private/unsupported sources must stay failed; never use a browser fallback.

`--response FILE` imports a local saved response for typed shadow validation, without making a model call. Receipt request hash must match the current evidence/questions. Review is always required; no imported score authorizes an action.

## Local configuration

Installation defaults: `media_enabled=false`, `landing_enabled=false`, empty exact-host lists and your own Downloads folder. Runtime destinations come from the reviewed local config, not a web page. No wildcard approval, hidden provider fallback, cookies, redirects or signed query capabilities. See the enclosing START-HERE for opt-in boundaries.
