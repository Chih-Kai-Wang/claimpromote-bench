# ClaimPromoteBench submission metadata

This file is the copy-ready metadata source for ICLR and arXiv. It does not authorize an upload.
The author must compare every field with the final server-built preview.

The ICLR 2027 OpenReview submission was created on 2026-08-25 with note ID
`8JTLEHqGRl` and submission number `4338`. No arXiv ID, DOI, or other archival identifier exists
yet. See `docs/submissions/2026-08-25-iclr2027-openreview.md` for the private submission receipt.

## ICLR 2027 title

```text
ClaimPromoteBench: Paired Regression Tests for Versioned Agent Policies
```

## ICLR 2027 abstract

```text
Repository policies are versioned inputs to coding agents, yet evaluations usually score versions independently. We present ClaimPromoteBench, a paired regression protocol that binds two policy versions, an unchanged case, and a target action relation. For finite executable policies, it enumerates action-changing contexts and derives cardinality-minimum suites with relative rule and transition coverage. For prose policies, targets are declared author mappings, not policy-owner ground truth. Route records retain transport, syntax, schema, and semantic failures in end-to-end denominators. Eight public histories illustrate the supported fault classes. On ten author-mapped pairs from two AGENTS.md revisions, eight hosted routes yield 128/160 item agreements and 52/80 pair agreements. In a prespecified non-ALLOW extension, every valid item agrees with its author target; incomplete outputs leave 50/54 stable pairs but only 6/18 changed pairs complete. On selected routes, a same-item request-cap comparison changes complete target-agreeing pairs from 0/15 to 7/15 and 0/15 to 9/15, with one call per cell. The protocol supports auditable frozen-case regression tests. The executable studies also retain exact action confusion matrices and source-bound verification receipts. Deployment validity and model-family effects remain unmeasured.
```

The ICLR upload must use the anonymous PDF and anonymous supplementary ZIP. Author identity,
institution, public repository URLs, workflow identifiers, and searchable private provenance must
stay out of both files.

## arXiv title

```text
ClaimPromoteBench: Paired Regression Tests for Versioned Agent Policies
```

## arXiv abstract

Use the same canonical abstract shown above.

## Author and affiliation

```text
Chih-Kai Wang
Department of Mathematics and Information Education
National Taipei University of Education
```

This identity belongs only in the public arXiv wrapper.

## Suggested categories and topics

- arXiv primary category: `cs.SE`
- possible arXiv cross-list: `cs.AI`
- evaluation and benchmarks
- software testing for AI systems
- trustworthy language-model systems
- structured decision making
- formal or neuro-symbolic methods

## Suggested TL;DR

```text
Joins finite action-changing differences between caller-supplied policy evaluators to source-traceable, failure-inclusive model-service regression tests with explicit parser provenance.
```

## Main empirical findings

- Two public `AGENTS.md` revisions contribute ten author-mapped pairs per replication: six changed
  pairs and four stable controls. Upstream maintainers authored the policy text; the study authors
  constructed the scenarios, precedence rule, action mapping, and labels before inference.
- Eight hosted routes receive 480 scheduled calls over three repetitions with zero client retries.
  The designated first replication yields 132/160 valid decisions, 128/160 author-target action
  agreements, and 52/80 pair agreements. Changed pairs reach 23/48 end to end and 23/26 conditionally; stable controls
  score 29/32 and 29/29.
- Across all three external-policy repetitions, routes produce 399/480 valid decisions, 387/480
  author-target action agreements, and 158/240 pair agreements. The 81 terminal failures comprise 26 server-side
  transport failures, nine length-terminated JSON failures, and 46 action/reason-code conflicts.
- A prespecified, commit-frozen non-`ALLOW` extension contributes eight author-mapped pairs from
  four public source records. Every valid item agrees with its author target. Stable outcomes are
  50 target-agreeing, zero complete-disagreeing, and four incomplete pairs; changed outcomes are
  6, 0, and 12. Always-`ALLOW` scores 0/8 pairs; copy-before scores 6/8.
- A 360-call same-item comparison crosses three selected routes with prompt-only caps of 4096,
  8192, and 12288 tokens and strict JSON schema at 4096. It uses one call per cell. The primary
  4096-to-12288 contrast changes complete target-agreeing pairs from 0/15 to 7/15, 0/15 to 9/15,
  and 7/15 to 7/15. All conditions retain their 30-item
  and 15-pair denominators.
- A content-free transport diagnostic classifies 63 late quota-or-billing rejections, six server
  errors, four timeouts, and three network errors. Each route has the same five quota-rejected item
  IDs in both conditions of the primary contrast. No cell was retried or replaced.
- Two exact Gatekeeper revisions yield 12 source-traceable pairs covering 2/2 changed rules and
  2/2 observed action edges; a two-pair suite is jointly complete for the committed grammar. Three
  repetitions yield 53/72 raw-strict actions and 21/36 pairs for Flash, versus 10/72 and 0/36 for
  Qwen. All 63 extracted actions agree with the executable oracle.
- Trivy reproduces an inverted policy predicate on four upstream cases. Cosign reproduces four
  verifier-interface fault modes on six cases. A frozen public-source audit screens 465 repository
  seeds and reviews 11 candidates. Microsoft Agent Governance Toolkit reproduces an agent-policy
  verdict gap, and agentgateway passes 33/33 selected offline tests at the exact adapter fix.
- The SLSA-inspired rule suite covers 12/12 changed rules and 6/10 reachable action edges; the graph
  suite covers 12/12 and 10/10. A ten-pair structural-coverage suite is jointly minimum for the
  committed candidate pool.
- The policy-aware structured random-forest control reaches 107/120 items and 47/60 pairs; the
  profile-blind control reaches 57/120 items and 0/60 pairs.
- An offline audit of 1,320 prior route items separates raw-strict, registered-parser, and
  full-contract endpoints. Raw-strict parsing finds 69 actions outside the full contract, including
  49 correct actions and 40 correct pairs. The registered challenge parser accepts six fenced Qwen
  objects, so raw-strict Qwen scores are 128/180 items and 46/90 pairs versus full-contract scores
  of 132/180 and 48/90.
- The imbalanced suite's Qwen route returns 272/300 valid decisions and scores 258/300 items and 113/150 pairs end to end,
  versus 258/272 and 113/123 conditional. Its `DEMOTE` support is 8/300 and recall is 0/8.
- The public balanced challenge contains 90 pairs, 180 items, 15 factors, 90 `ALLOW` members, and 30
  members for each remaining action. Qwen and Flash score 48/90 and 13/90 pairs end to end versus
  48/64 and 13/61 conditional; `DEMOTE` recall is 4/30 and 0/30.
- The historical Flash interface for the imbalanced suite returns HTTP 401 before model output on all 300 calls. Later
  Flash paths establish only their own executability because the service stacks differ.
- The deterministic executor is the definitional policy ceiling. Naive Bayes is a weak sanity
  control, reaching 184/300 items and 34/150 pairs on the imbalanced suite.

## Data and code availability

### Anonymous conference version

```text
An anonymized supplementary bundle contains the finite policy-difference enumerator and suite reducer, exact source-validation inputs and receipts, frozen paired datasets, prompt packets, content-free terminal records, parser provenance, analysis code, complete confusion matrices, and privacy receipts needed for deterministic source and score replay. It does not reissue hosted calls. Its manifest derives file counts from the generated tree. It excludes raw failed responses, free-form errors, provider response identifiers, hidden reasoning, account identity, author-identifying provenance, private construction seeds, and generated caches.
```

Replay begins with released parsed decisions and content-free terminal records. Raw response text
and raw-response hashes are absent, so an external reviewer cannot independently re-adjudicate the
raw-output-to-parser transformation or provider error messages.

### Public preprint version

```text
A history-free public export will retain the necessary code, licensed source excerpts, frozen datasets, content-free empirical records, validators, and reproducibility receipts. Private construction material, raw provider text, hidden reasoning, and account metadata will remain excluded. Repository and archival identifiers will be added only after they exist and disclosure is authorized.
```

## Reproducibility statement

```text
The artifact binds exact upstream source bytes and commits, licenses, executable policies, finite grammars, prompts, frozen zero-retry schedules, content-free terminal outcome classes, parser source, and analysis code. Validators perform deterministic source and score replay for source behavior, coverage, minimum suites, endpoint metrics, parser provenance, action recalls, and confusion matrices; they do not reproduce hosted inference. Reviewer derivatives preserve every scheduled denominator while removing response content and identifying metadata.
```

## Ethics and AI-use scope

The study contains no human-subject experiment or human annotation study. Synthetic reviewer and
provenance fields are policy state. The manuscript reports no annotator agreement, IRB approval,
exemption, or informed consent.

Use the complete AI Assistance Disclosure from the manuscript in venue forms.

## Account-side checklist

- [x] OpenReview profile, author list, and institutional domain were confirmed at submission time.
  Conflict information remains an account-side responsibility throughout review.
- [x] Title and abstract match the final anonymous PDF.
- [x] The primary area and keywords match the paper's bounded scope.
- [x] Ethics and AI-use acknowledgements are complete.
- [x] The locally validated anonymous PDF and supplementary bundle were uploaded; OpenReview
  exposed both attachment links and rendered the PDF. The authenticated server bytes were not
  independently rehashed after upload.
- [ ] The server-built PDF is downloaded and inspected page by page.
- [ ] arXiv author, affiliation, title, abstract, categories, and source archive are verified.
- [ ] No submission, merge, public release, or ready-for-review transition occurs without explicit
  authorization.
