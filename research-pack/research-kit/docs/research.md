# Research synthesis

## Defensible role
Jev is used in the evaluated architecture to answer bounded text/JSON questions: choose a known category, score an ordered rubric, or judge one yes/no proposition. An application supplies observations and finite candidates. Code owns permissions, numeric calculations, routing and execution. A generative model drafts text or artifacts where required. Independent evidence checks the result.

The portable validator is a snapshot of the shared local `jev-decision/2` contract; it is not an SDK or provider compatibility guarantee. This kit ships no model implementation. Provider schemas, model availability, limits, prices and licenses must be checked before a live integration.

## Demo/use-case catalog (reported ideas, not independently reproduced benchmarks)
- Public competitor-ad discovery; extraction of copy, headline, CTA, dates and creative identifiers; dominant-angle and awareness tagging.
- Creative/brief preflight ranking; multi-persona stop/scroll simulation; ad-to-landing-page promise matching. Use for hypotheses, not predicted ROAS or a replacement for customers/focus groups.
- Review and comment triage; sentiment/complaint/objection tagging; social-post relevance and reply prioritization.
- Company/creator/sponsorship fit screening; ICP matching; public buying-signal triage; lead prioritization. Do not infer sensitive traits or build private-person identity dossiers.
- Search-term intent classification and negative-keyword suggestions; creative-fatigue review from actual account metrics; human-approved edits only.
- News relevance/newsjacking and journalist research from authorized feeds; Product Hunt launch screening; SEO/GEO audit routing.
- Browser action selection from observed controls, flight-search demos and game action loops; repeated local decisions can be cheap while browser/network delays dominate.
- Memory retention proposals, retrieval shortlists, citation checks, semantic QA, support routing, tool/model routing and progress checks.

## Limits of promotional comparisons
Screenshots and demo videos report different tasks, hardware, inputs, caches, concurrency and timing boundaries. Neither '50 times faster', '1 GB maximum', '30 times faster marketing', '$0.22 focus group' nor a local Snake result proves quality or end-to-end speed on this workflow. Laya/MLX is a candidate local classifier, not established here as an OpenAI product, a drop-in Jev replacement or security-audited software. No Laya code/weights are redistributed or installed in this kit.

Before comparing alternatives, freeze a representative labeled set, use equivalent input/evidence and outputs, include cold/warm behavior, device and memory measurements, record quality plus latency/cost, and preserve all failures. Inspect model and dependency provenance/licenses and network behavior in a restricted environment. 'No malicious code found' is not a safety proof.

## Recommended insertion point
Begin after capture, at repeated awareness/angle/LP-match judgments. Existing extraction remains authoritative. Add shadow mode and evaluate against held-out human labels before letting classifications route even reversible downstream work. Do not add Jev to arithmetic, dedupe, missing-field detection, or simple exact rules.
