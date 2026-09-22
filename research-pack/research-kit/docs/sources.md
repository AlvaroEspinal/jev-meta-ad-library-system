# Sources, attribution and evidence boundaries

This bundle contains original summaries and local application-contract snapshots. Links below are references, not assertions that provider offerings/prices are current. No linked page, book chapter, private client file, downloaded ad asset, full tweet thread or video transcript is bundled.

- TypeSafe, System One/Jev introduction: https://typesafe.ai/blog/introducing-system-one-models-and-jev
- TypeSafe model documentation: https://docs.typesafe.ai/models
- Typed primitives: https://docs.typesafe.ai/primitives/choice ; https://docs.typesafe.ai/primitives/score ; https://docs.typesafe.ai/primitives/noul
- Model limitations reference: https://docs.typesafe.ai/model-jaggedness/jev-1.13
- Browser Use upstream project: https://github.com/browser-use/jev-ultrafast (upstream license applies to any separately obtained code; full runtime not distributed here).
- Candidate local model project, not audited or installed by this kit: https://github.com/mizorewww/laya-mlx
- Provider reference: https://openrouter.ai/labs/jev/compile
- Eugene M. Schwartz, *Breakthrough Advertising* (1966): conceptual attribution for five awareness stages; no copyrighted book content included.
- User-supplied four-page AVIDLIVE 'How to master Jev / Jev Engineering' diagrams: ideas summarized here include responsibility split, bounded types, relevant evidence, independent batching, action gates, readback, retrieval shortlists, shadow rollout, hold-out evaluation and whole-task economics. No screenshot or verbatim sheet reproduction included; sheets explicitly describe illustrative designs, not benchmark results.
- User-supplied X demo screenshots: reported ideas from Gregor Zunic (browser use), Max Blade (games), Elvis (news relevance), Yum (marketing screening), Dmitry Korzhov (ad research workflow), Matthew Berman (ad categorization/persona simulation), and Laya posts. Claims are reported/demo-scoped, not verified performance evidence; media not redistributed.

## Code/data provenance
`schemas/taxonomy.json` records a SHA-256 of the local canonical classifier source and AST extraction method. The pure contract validator is the local shared Jev skill's dependency-free validator, not third-party model code. All fixture company names, IDs, copy and pages were newly created for this kit. Examples do not identify real clients or people. No canonical private dataset or absolute source-machine path is included.

Redistribution scope: original handoff prose and synthetic fixtures are intended for the requested private share. This does not grant rights to linked third-party software, media or books. Review licenses before distributing added upstream code or model weights.
