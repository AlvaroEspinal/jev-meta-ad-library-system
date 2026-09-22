# Architecture v0.2.0

## Decision and alternatives
Retain the minimal activeTab extension plus native companion rather than add a broad background crawler or local HTTP API. The native host now accepts an explicit typed `workflow` command for two modes. Default network is **off**, credentials never enter the extension, and downloaded bytes are never treated as executable instructions. This extends the prior local-writer-only design; its new network/codec risks are documented in the threat-model addendum.

1. **Quick Download:** user selects one authorized direct asset and rights basis. Native configuration owns Downloads root, exact allowed host and whether downloads are enabled. Download to a private temporary directory, validate bytes/MIME, optionally convert to MP3, allocate a readable name with exclusive creation and collision suffix, verify SHA-256 readback. No vault/Obsidian constructor is invoked.
2. **Save to Obsidian:** user reviews fields and optionally an asset/landing page. Host validates evidence, downloads selected media only if locally enabled, builds a canonical bounded Jev request in off mode, stores source-specific Markdown/JSON/HTML and checksums. `captured` is capture completeness, not an accepted model answer or verified source truth. A failed asset/LP/model operation remains partial with visible gaps.
3. **External import:** CLI only; reviewed receipt from configured canonical non-browser scraper/Apify, local root containment, content hash, MIME, status and `browser_used=false`. User explicitly confirms provenance. This attestation is not cryptographic proof of how the upstream scraper ran. The utility never invokes or falls back to a browser. Provider dispatch remains outside this prototype.

## Records and trust
`capture_root/<surface>/<content-digest>/` contains note.md, evidence.json, record.json, jev-request.json, decision.json, index.html, optional asset and manifest.json. Per-record files are immutable; exact repeats verify then return duplicate, changed copy/assets create a new version. HMAC binds local file hashes and metadata; independent verification detects tampering relative to recorded hashes but does not prove source truth. No existing vault note is overwritten.

The legacy screenshot/reference `capture` path is retained. It uses its existing v1 immutable store, while two-mode packages use schema v2. Screenshot+download combination is explicitly rejected rather than silently dropping an asset. Quick Download failure never claims a file saved; note mode can preserve partial evidence when media fails. Unsupported input is rejected without storing secrets.

## Semantic layer and cockpit
The taxonomy is AST-extracted from the existing cockpit classifier, with source hash in `companion/data/taxonomy.json`. `journey_stage` is five-stage awareness, NOT top/middle/bottom funnel. The separate funnel extension has an explicit review state. Evidence IDs, model requested/resolved, review/acceptance/verification flags and missing telemetry are retained. Off mode has zero calls/cost; shadow-import validates local saved responses only; no model is invoked. All results remain review-only. The per-record local HTML renders full evidence and typed answers; the running cockpit is not automatically modified.

## Permissions and configuration
Permissions remain activeTab, scripting, nativeMessaging, storage. No host_permissions, content_scripts, background worker, cookies, debugger, external messaging or extension network access. Exact caller origin and 4 MB stdio frame limit. Exact DOM origins and media/landing hosts configured locally, not granted by a page. Media/landing network defaults disabled. Fixed roots, containment/symlink checks, 20 attempts/minute, file/byte/time limits, no shell/network proxy endpoints.

No live registration, host installation, real browser source capture, paid provider or account operation was performed during v0.2 fixture work. See capabilities.md for actual remaining feature gaps.
