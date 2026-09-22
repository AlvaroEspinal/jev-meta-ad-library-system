# Measurement and release gates

1. Define the decision, available evidence, answer boundaries, fallback and cost of an error. Label representative examples, including missing/ambiguous/malicious source text and inaccessible pages.
2. Split development and held-out examples before tuning. Freeze a candidate; test without changing labels/prompts. Once a hold-out failure guides tuning it becomes development data, requiring a new hold-out for the next release.
3. Compare deterministic baseline, Jev and optional local alternative on the same evidence. Track wrong routes, critical misses, precision/recall per class, review rate, auto-coverage, calibration, provider errors and actual verified outcomes. Always publish sample size and excluded cases.
4. Measure observation, retrieval, generation, model decision, browser execution, verification, retries and human review separately. Cost per acceptable verified task includes failed attempts and repair, not just successful model tokens. Local inference has hardware/energy/maintenance cost; not 'free' in every sense.
5. Shadow run: same event, two judgments, one execution path. Roll out limited active use only after preset quality/risk thresholds pass; keep off switch and original fallback. Changes in provider, model, language, question wording, candidates or policy require re-evaluation.

Example of timing scope: if decisions were 40% of total time, making just that step 20x faster changes total from 1 to 0.6 + 0.4/20 = 0.62: about 1.61x overall, not 20x. This is arithmetic, not a Jev benchmark.

The supplied tests check contracts/integrity and synthetic failure handling only; there is no measured marketing accuracy, ROI, model benchmark or production readiness claim.
