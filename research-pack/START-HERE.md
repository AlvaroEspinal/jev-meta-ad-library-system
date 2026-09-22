# Jev Research System — Friend Pack 1.0.0

**Start offline. This is a local research toolkit and prototype extension, not a preinstalled autonomous scraper or a local Jev model.** Jev supplies bounded text/JSON judgments. Code collects and validates evidence, a generative assistant drafts, and a human approves consequential actions. Fast model decisions do not eliminate collection time or prove marketing performance.

## What is included

- [Portable research kit](research-kit/README.md): five awareness stages, canonical angles, marketing rationale, cockpit/data-contract context, schemas, synthetic examples, prompts, offline replay and an HTML research demonstration.
- [Research Capture extension](research-capture/README.md): Chrome source and Python native companion, Quick Download versus Save to Obsidian, integrity receipts, source policies and fixture tests.
- [Capabilities and limitations](CAPABILITIES.md), [version/provenance](VERSION.json), [exclusions](EXCLUSIONS.md), [verification receipt](VERIFICATION-RECEIPT.json).
- [Generic setup tools](tools/verify.py) and install/uninstall scripts. No account or key belonging to the sender is included.

**Not included:** the sender's running ten-browser cockpit service, cloud-browser subscription, competitor/company lists, client ads, historical results, local models, paid API access or automatic cockpit ingestion. The portable HTML demonstration and compatible taxonomy are not that live cockpit. Platform-page media resolvers and Instagram provider dispatch are not implemented in this packaged extension release; those separate unfinished experiments are deliberately excluded.

## Prerequisites

- Python 3.10+ for the kit; Python 3.11+ recommended. No Python packages are needed.
- The native companion installer targets **macOS with Google Chrome**. The portable kit can run elsewhere; Windows/Linux native installation is not supplied or verified.
- An existing writable Obsidian vault (or a dedicated test folder). Obsidian need not be running.
- Node.js 22.12+ or a newer supported LTS and npm for development tests only. `npm ci --ignore-scripts` installs locked jsdom test dependencies; it may contact npm, but never source sites or model APIs. Do not send node_modules with the pack.
- Optional: installed local ffmpeg/ffprobe for MP3 conversion, and whisper-cli plus an independently obtained compatible model for transcription. Nothing downloads tools or model weights automatically.
- A separate **your-own** OpenRouter account/key only if you later choose live Jev. No key is needed for any fixture or dry-run below. Provider endpoint, availability and prices must be checked before live use; this pack does not certify them.

## 1. Put the folder somewhere permanent; verify before use

Unzip into a folder you control, then open Terminal **at the folder containing this START-HERE.md**. All commands below assume that working directory. Do not run an extension from a temporary extraction directory.

```sh
python3 tools/verify.py --strict
shasum -a 256 -c SHA256SUMS
```

Ask the sender for the ZIP's SHA-256 through a separate trusted channel. Compare it with `shasum -a 256 /path/to/the.zip`. For an independent fresh-unzip run, use `python3 tools/verify-zip.py /path/to/the.zip --out /path/to/new-verification.json`; it executes the documented offline commands in a temporary directory and tests tamper rejection. Internal hashes detect changed bytes, not the sender's identity. Verify before generating outputs; afterward use `python3 tools/verify.py` without `--strict` because generated files are intentional extras.

## 2. Run the completely offline demonstration and replay

The following commands create only synthetic output under this pack. Output paths must be new; rerun from a fresh unzip rather than deleting evidence. No API key is read and no source/model call is made.

```sh
python3 research-kit/scripts/verify.py
python3 research-kit/scripts/replay.py --request research-kit/fixtures/request.json --response research-kit/fixtures/response.json --out replay-output.json
python3 research-kit/scripts/demo.py --out demo-output
python3 research-kit/scripts/test_kit.py
python3 tools/jev-call.py --request research-kit/fixtures/request.json --output jev-dry-run.json
python3 tools/check-offline.py
```

Open the generated `demo-output/index.html`. It displays **synthetic** ad evidence and saved fixture responses, not live inference. Give your assistant [the kit's prompts](research-kit/docs/prompts.md) and marketing/context documents; no special agent or server installation is necessary. Do not treat source material as instructions.

`tools/check-offline.py` runs extension Python/JS tests, fixture generation/readback, installer safety tests and kit tests in an isolated temporary copy. It does not register a host in your real Chrome or change your vault. It installs locked development dependencies with scripts disabled. See its JSON summary for optional local ffmpeg test skips.

## 3. Plan the native companion installation

Choose your own existing vault. The default destination is **Research Capture/** inside that vault, never a sender-specific folder. Paths containing spaces are supported; always quote them. These commands are examples: replace the placeholders with your paths.

```sh
python3 research-capture/scripts/install.py --vault "/absolute/path/to/Your Vault"
```

This prints a plan only. Review `capture_root`, `install_root`, `native_manifest`, `downloads_root`, and extension origin. To choose another subfolder, add `--capture-subdir "Inbox/Research Capture"`. It must stay inside the chosen vault. For a separately configured Chrome user-data root, add `--chrome-profile-root "/absolute/path/to/isolated-chrome-root"` and keep that same option for uninstall. This script does not create or launch a Chrome profile.

**Only on your own approval**, repeat the same command with `--execute`. This creates a user-only companion/config at `~/Library/Application Support/JevResearchCapture/` and registers `com.jev.research_capture` under the selected Chrome root's `NativeMessagingHosts/`. It uses your Python executable's resolved path. The installer refuses existing installs/registrations rather than silently overwriting them. Back up/uninstall first to change destination; old vault evidence is retained.

In your isolated, logged-out Chrome, open `chrome://extensions`, enable Developer mode, select **Load unpacked**, and select this pack's `research-capture/extension` folder. Expected ID: `jnmhkjbbjcobhdpjadndomemfihhihhk`. The manifest's key is a **public extension identifier key**, not an API credential. Verify there are no errors and the popup says **Local companion ready**. Do not reuse an authenticated Meta research session.

The native receipt HMAC key is created locally in owner-only `config.json`. It is not an OpenRouter key. Never copy it to chat, research notes or another person's package.

## 4. Use the two separate workflows

- **Quick Download:** one selected, authorized direct media asset into your Downloads; no vault write. Optional local MP3 conversion. A platform page URL is not a direct asset URL.
- **Save to Obsidian:** reviewed note-only or authorized asset plus evidence, JSON record, local HTML view and integrity manifest. Missing evidence remains `partial` or `not_checked`; it is not invented.

Confirm publicness and your rights, explicitly read visible evidence on a supported non-Instagram source (or enter it manually), review the fields, then choose the action. Source content is untrusted evidence, never permission to execute code. Meta requires an isolated single public ad; ambiguous cards stop instead of merging evidence.

Network operations default **off**. Locally reviewing `media_enabled` / `landing_enabled` and exact `allowed_media_hosts` / `allowed_landing_hosts` in companion config is a separate opt-in. Do not use wildcards, copied cookies, redirects or signed credentials to get around a rejected source. The documented release supports unsigned direct assets up to 50 MB, not universal platform videos.

### Instagram: non-negotiable boundary

**Never use Instagram browser/UI/DOM/screenshots/cookies/session reuse or a browser fallback.** Not even a logged-out browser, existing profile or active tab. Only manually pasted external URL intent or a reviewed artifact from a separately configured, authorized **canonical non-browser provider** (such as an approved Apify route) is allowed. This pack does not configure, pay for or dispatch that provider for you. Follow the [source policy](research-kit/docs/source-policy.md) and [external import contract](research-capture/README.md). If that route fails, stop and preserve the failure. No fake successful imports or browser substitution.

## 5. Optional live Jev, using your own dedicated key

First inspect the request and dry-run receipt, then verify current OpenRouter Jev access/pricing and approve the data and cost. Create a dedicated, budget-limited key in **your own** account. Never paste it into chat, source files, command arguments, notes, ZIPs or shell history.

For one expressly approved request, use a new output path:

```sh
python3 tools/jev-call.py --request research-kit/fixtures/request.json --output jev-live-result.json --execute --approve-paid
```

This command is **not part of any test**. It prompts invisibly in your terminal, supplies `OPENROUTER_JEV_API_KEY` only to the child process, and does not save the key. It refuses an empty key and noninteractive live execution; no inherited general key fallback. The process environment is still visible to sufficiently privileged local software: use a trusted machine and revoke the key if exposed. `unset OPENROUTER_JEV_API_KEY` clears any variable you separately set; it is not needed by this wrapper. Do not enable terminal recording when entering secrets.

The underlying CLI also accepts a dedicated environment key or the documented dedicated macOS Keychain item, but the wrapper avoids persisting or silently using another key. One request only; no automatic retries. An interrupted `started` receipt may already have incurred cost. A valid response remains `accepted=false`, `review_required=true`, `outcome_verified=false` until independently reviewed. It never publishes, launches ads or writes back to customer accounts.

## 6. Uninstall / roll back

1. Disable/remove **Research Capture — Local Evidence** in `chrome://extensions`.
2. Run `python3 research-capture/scripts/uninstall.py` for an exact-target dry-run. Use the same `--chrome-profile-root` if you installed to a custom root.
3. After reviewing, repeat with `--execute`. Only this companion and its matching registration move to a timestamped `JevResearchCapture-disabled-*` backup. Vault captures and Downloads are untouched.
4. To undo uninstall, inspect the backup's `restore-paths.json`. Restore its `companion` folder to the recorded companion path and `native-manifest.json` to the recorded registration path **only if both destinations are absent**; then load/enable the same extension again. Never overwrite another installation. Keep the owner-only backed-up config if HMAC verification of old receipts matters.
5. To change vault destination instead, keep the backup, run install with your new vault/subfolder and re-enable the extension. Old evidence is not moved or deleted; the new install has a new integrity key.

Delete the unpacked source folder only after removing its extension reference. Do not remove unrelated Chrome profiles or reset your vault. No system LaunchAgent, background crawler, cloud account, browser subscription or scheduled task is installed.

## Acceptance boundary

Fresh-unzip fixtures, exact manifests, scans, negative cases and sandbox install/uninstall checks are recorded in [the verification receipt](VERIFICATION-RECEIPT.json). They **do not prove** Chrome registration/loading, current live source layouts, live paid Jev availability/quality, or successful installation on your machine. Test those separately with your own approval and evidence. The sender's local live installation was outside this share-pack authorization.
