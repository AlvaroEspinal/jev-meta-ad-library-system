# Give this prompt to your own setup agent

> Clone this repository into a new folder on **my** computer. Read `README.md`, `SECURITY.md`, the browser runner and cockpit READMEs, and `research-pack/START-HERE.md` before running installers or live collection. Do not use any sender-specific path, account, browser profile, API key, company list, client data or archived output. First run only the repo's offline tests, synthetic ten-worker demo, and strict pack verification. Show me the test results and proposed local paths.
>
> Then ask **me locally** whether I want the optional Obsidian capture extension; for the browser runner, ask for my own Browser Use Cloud access, provider credentials and budget, and the public advertiser page IDs I want to inspect. The runner must never use local Chrome or an existing profile. Keep secrets out of chat, logs, screenshots, Git and command arguments. Configure the cockpit only on `127.0.0.1`, create a unique local bearer token with owner-only permissions, and connect the runner to that endpoint. Verify that each real worker event appears in the correct lane and that cumulative history survives a restart; verify `zero_ads`, `source_blocked` and failed runs stay distinct. Run browser-harness diagnostics before any source visit. Do not use Instagram in a browser or UI or bypass access controls.
>
> Stop before any paid Jev/model call, cloud-browser allocation or live scrape. If I separately request the Research Capture extension, stop before its Chrome native-host installation too; it is not part of browser-runner setup. Give me an exact plan, expected costs, targets, permissions and rollback, and wait for my explicit approval. After approval, test one authorized target first. Compare the browser result to the visible source, inspect cleanup, event receipts and saved evidence, then decide whether the ten-worker run is justified. Never call a blocked or incomplete source a successful zero-ad result.

This prompt is intentionally portable. It supplies **instructions**, not access. If any tool or dependency is unavailable on your machine, report that gap rather than substituting a private sender connection.

## Concrete offline checklist for the agent

Run these from the clone root before asking for any credential:

```sh
python3 tools/check_publication.py
python3 tools/check_distribution.py
python3 tools/check_scheduler_protocol.py
python3 -m browser_runner.runner --companies browser_runner/examples/companies.example.json --workers 10
```

The publication guard needs a Git clone with an index. All other commands above use synthetic data only. For development tests, create a new virtual environment and install the pinned Browser Harness requirement from `browser_runner/requirements.txt`; run the Python tests in `tests/`. Do not interpret an offline pass as live-source or paid-provider acceptance.

After the owner agrees to local setup, start the cockpit as its README describes on port **8877**. Configure the *same* `JEV_COCKPIT_TOKEN` environment variable for the runner's shell; never pass it in a chat, Git commit or command argument. Use `browser-harness auth status` and `browser-harness --doctor` for diagnostics **before** an approved cloud run. The browser runner's dry-run plan is safe; `--execute --approve-live-collection` is not an offline check. Optional `--approve-paid-jev` requires a separate decision and an owner-supplied, budget-limited dedicated key.

The `research-pack/` folder is independently versioned. If the owner wants the Chrome capture extension, follow its dry-run installer with **their** existing vault and isolated profile; do not infer that extension installation is needed for the browser-runner→cockpit connection.
