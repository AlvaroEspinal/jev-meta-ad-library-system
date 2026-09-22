# Capabilities v0.2.0 — explicit, bounded support

| Source / operation | Safe implementation present | Remaining gate / limit |
|---|---|---|
| Public web | Explicit visible text/selection, editable fields, approved screenshot, reference media | Exact origin allowlist; real-page live checks pending |
| YouTube | Visible title/channel/ID/description and user-opened transcript | Does not fetch hidden captions, DRM or streaming manifests; video requires approved direct asset or external import |
| Meta Ad Library | Isolated single-ad evidence; ID/advertiser/copy/headline/subheadline/CTA/status/start-date/page-ID/format when observed | Real DOM fixture heuristics are not universal; logged-out isolation confirmation required; never mixes multiple cards |
| Public Facebook post/reel | Narrow public URL shapes, manual/explicit visible evidence | No private feeds, groups, messages or session reuse; no built-in platform video resolver |
| Public X/Twitter post | Public status URL references and explicit/manual visible evidence | DOM origin must be locally approved; generic adapter may need manual copy; no built-in video resolver |
| Quick Download | One authorized direct asset to configured Downloads; human-readable collision-safe name; SHA-256 readback | Network off by default; exact host approval; unsigned HTTPS only, 50 MB; private/DRM/pages rejected |
| Save to Obsidian | Note-only or asset+record, source folders, immutable JSON/Markdown/HTML, manifest/HMAC/hash verification and dedupe | Missing fields/media/landing/model failure stay partial; does not publish |
| MP3 conversion | Local ffprobe/ffmpeg, audio/duration check, file/pipe only, capped subprocesses | Tools must be installed; not a hardened codec sandbox |
| Local transcription | Existing explicit media CLI + local Whisper | Separate optional CLI, no automatic model download |
| Instagram | External manually pasted URL-only reference OR reviewed artifact import from approved canonical non-browser route | No active-tab URL autofill, DOM/UI/screenshots/cookies/network observation or browser fallback. Provider dispatch is intentionally **not** implemented here; use canonical scraper separately with approval. Unsupported/private/expired/failed source stops |
| Landing-page evidence | Explicit bounded allowlisted HTTPS HTML fetch; heading/structure/CTA candidates, raw evidence pointers | No JS, redirects, forms, automatic link following; offer/proof/claims not inferred. Their reviewed extraction is not yet automated |
| Jev analysis | Canonical questions for category, awareness, dominant angle, funnel, hook/offer/proof/authority/fear/benefit/comparison/objection presence, format, LP match; strict validator; off and shadow-import | One-call CLI transport implemented, dry-run default and dedicated credential only; no browser model command or active routing. Live calls require separate approval; imported identity remains unverified beyond receipt binding |
| Research display | Full escaped evidence/fields/decision HTML for every saved record | Existing running cockpit is not modified or automatically fed; canonical field compatibility is a data contract, not installed integration |

Source support means only the stated operation, not universal media-download support or legal permission. Platform media acquisition and automatic cockpit ingestion remain real scope gaps, not just installation gates. Workstream 1 is advanced but **not acceptance-complete**.
