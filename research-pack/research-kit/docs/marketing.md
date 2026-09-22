# Marketing framework and canonical taxonomy

This is an original operational explanation, not a reproduction of a marketing book. The five awareness stages are conventionally attributed to Eugene Schwartz; see the bibliography. Stage judgments describe the **intended prospect knowledge at encountering an ad**, not knowledge of an identified person.

## Awareness stages
### Unaware
The prospect is not consciously thinking about the problem yet. The ad uses story, surprise, news, a dramatic claim, or a pattern interrupt to create problem awareness and does not lead with the advertiser's product.

### Problem Aware
The prospect already feels or recognizes the problem but does not yet know a solution. The ad leads with vivid pain, empathy, a question, or a threat and then teases that a solution exists.

### Solution Aware
The prospect knows solution categories exist and is comparing approaches. The ad leads with a category benefit, method, differentiation, or comparison to alternatives.

### Product Aware
The prospect knows this advertiser or offering but needs proof, a product-specific reason, an objection handled, a testimonial, or a reason to choose it now.

### Most Aware
The prospect already wants the specific offering and mainly needs price, an offer, urgency, availability, a promotion, or a direct low-friction action.

### Review
Captured evidence is insufficient or genuinely ambiguous; do not guess.

Do not assign product-aware merely because a logo appears, most-aware merely because a CTA exists, or unaware merely because a video opens with a story. Read the dominant promise, assumed prior knowledge, explanation and ask together. Missing material is `review`, never an invented label.

## Every canonical angle
The keys and descriptions below are extracted from the existing cockpit classifier, not a new competing taxonomy.

| Key | Label | Boundary |
|---|---|---|
| `offer_promo` | Offer / promo | Price, discount, promotion, financing, bonus, or special offer is the dominant appeal. |
| `problem_pain` | Problem / pain | The prospect's current problem, frustration, or pain is the dominant appeal. |
| `fear_risk` | Fear / risk | Risk, loss, a costly mistake, danger, or a negative consequence is the dominant appeal. |
| `benefit_umbrella` | Benefit umbrella | A broad desirable outcome or bundle of benefits is the dominant appeal. |
| `project_showcase` | Project showcase | A completed design, room, or project reveal is the dominant appeal. |
| `before_after_transformation` | Before / after transformation | A before-and-after transformation is the dominant appeal. |
| `material_product_feature` | Material / product feature | A material, named product, construction detail, or feature is dominant. |
| `process_mechanism` | Process / mechanism | How the service, design process, or mechanism works is the dominant appeal. |
| `authority_expertise` | Authority / expertise | Credentials, experience, technical expertise, or authority is dominant. |
| `social_proof` | Social proof | A testimonial, review, customer result, or peer proof is dominant. |
| `comparison` | Comparison | A comparison between choices, alternatives, providers, or paths is dominant. |
| `status_lifestyle_design` | Status / lifestyle / design | Taste, identity, status, aesthetics, aspiration, or lifestyle is dominant. |
| `local_convenience` | Local / convenience | Local relevance, proximity, service area, speed, or convenience is dominant. |
| `other` | Other | There is a clear dominant persuasive angle outside this taxonomy. |
| `review` | Review required | Captured evidence is insufficient or genuinely ambiguous; do not guess. |

## Dominant versus multiple angles
`primary_angle` selects one dominant persuasive appeal (or review). It drives the comparable matrix. Optional secondary-angle annotations use the **same keys**, each with an evidence ID and review status. They are not summed as additional ads. A testimonial can contain both social proof and process explanation: decide what principally carries the persuasion rather than counting keywords. `other` means enough evidence for an angle outside this map; `review` means insufficient/ambiguous evidence.

## Awareness is not funnel
Top/middle/bottom funnel is a campaign objective or placement in a customer journey. Awareness is assumed knowledge. An unaware prospect can see a conversion campaign; a product-aware prospect can see educational content. Never infer one from the other. The legacy cockpit field `journey_stage` maps to **awareness**, despite historical UI wording such as 'angles x funnel'. Keep `funnel_stage` separately as top/middle/bottom/review, with its own evidence; campaign configuration is stronger evidence than copy alone. The funnel keys are a documented extension, not a claim they existed in the original taxonomy.

## Anatomy to capture and judge
- **Hook:** attention entry point, commonly the first line or video opening. Preserve exact observed text and timing when available; a title alone is not a video hook.
- **Offer:** what is exchanged and on what terms. Separate a product benefit from a price/discount/consultation offer. No terms invented.
- **Proof:** observed review, demonstration, result, measurement or testimonial. 'They claim X' is not verification of X.
- **Authority:** claimed credentials, years, expertise or associations. Record source; validate important claims separately.
- **Objection:** concern the message explicitly addresses (risk, disruption, price, uncertainty). Do not attribute unstated objections to a person.
- **Benefit:** desired outcome. A feature is a property; a benefit is its consequence for the customer.
- **Fear/risk:** articulated adverse outcome. Keep it separate from existing pain and never add unsupported threats.
- **Comparison:** explicit alternative, baseline or method contrast; record what is compared, not just 'best'.
- **CTA:** exact button/text and destination. A platform CTA and an in-copy CTA may differ; retain both when observed.
- **Format:** observable static image, carousel, video, text or unknown; absence of video perception means visual claims remain unchecked.
- **Company/category:** observed advertiser identity versus separately reviewed business-category label. Similar names do not verify identity.

## Matrix and whitespace workflow
1. Deduplicate by platform ad ID plus versioned content hash; retain repeated observations, timestamps and changed creative versions.
2. Count only evidence-backed, reviewed classifications in angle x awareness. Report review/missing counts and denominators; do not mix IDs-only discoveries with analyzed creatives.
3. Build a distinct angle x funnel view only for records with funnel evidence. Keep single dominant-angle and multi-angle views explicitly separate.
4. An empty cell in the sampled corpus is **unobserved**, not necessarily a market opportunity. It can mean sampling bias, missing creatives, unavailable ads or a poor strategic fit.
5. Combine whitespace hypotheses with first-party conversion data, product truth, audience research and operational constraints. Never equate ad longevity with profitability, spend or conversions.
6. A generative worker drafts a few differentiated briefs. Jev performs bounded rubric checks; humans confirm brand/claims/rights.
7. Test real campaigns with an explicit hypothesis, audience, creative, landing page, budget approval, primary outcome, stopping rule and sufficient data. Validate lift or decision value against a baseline; use real qualified leads/sales where possible.

## Landing-page match
Compare the captured ad promise, offer/terms, audience, CTA and proof to timestamped page evidence. Return matched/mismatch/review with evidence IDs; inaccessible pages remain not_checked. A coherent message is not proof of higher CVR. Draft changes in preview and validate with analytics/experiments before publishing. Never submit forms while collecting evidence.

## Safe feedback to ad platforms
Only authorized, accurate first-party lifecycle events belong in measurement/optimization integrations, subject to consent, platform rules and legal review. A model's simulated interest or inferred quality score is not a purchase or qualified lead event. Never fabricate conversions or upload scraped personal profiles as customer data.
