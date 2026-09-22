# Security and source policy

## Trust boundary

Treat webpage copy, ad text, media, extracted HTML and model output as untrusted evidence, never executable instructions. The local cockpit is a display and receipt store, not a browser controller, shell bridge or public API. Run it on `127.0.0.1` only, protect event writes with a locally generated token, and never expose it through a tunnel or reverse proxy.

## Recipient isolation

- Create keys and configuration locally on the recipient's machine. Do not copy a sender's Keychain, `.env`, browser profile, cloud-browser account, vault, historical state or evidence.
- Keep account budgets and concurrency limits explicit. Start with a single target before enabling ten workers.
- Use an isolated, logged-out browser/approved collection route for public Meta research. Stop at challenges, access denials or ambiguous page identity. Never attempt CAPTCHA or access-control bypass.
- **Never automate instagram.com through a browser or UI.** No DOM, screenshots, cookies, authenticated-session reuse, or browser fallback. Only an explicitly configured approved non-browser provider may handle Instagram research, and a provider failure is a stop, not a reason to switch transport.
- Obtain rights and permission before media download; the extension's network routes default off and enforce exact allowlists.

## Data meaning

`observed` means a source was actually read and recorded. `zero_ads` is valid only after a successful identity-verified observation. `source_blocked` means coverage is unknown. A model classification is review-only until its evidence and outcome are checked. The cockpit must display these distinctions, preserve immutable source timestamps, and not imply a full ad-library inventory from a finite visible sample.

## Distribution

Before publishing or sharing, inspect the exact Git index, tracked source, Git history, dependency manifests and tests. Reject credentials, client information, absolute sender paths, browser profiles, generated evidence, saved state and paid-call receipts. The bundled research pack has an independent hash manifest; run its verifier after any copy. Publication scans lower risk but are not an exhaustive security audit.
