# ClaimPromoteBench submission metadata

This file is the copy-ready metadata source for ICLR and arXiv. It does not authorize an upload.
The author must compare every field with the final server-built preview.

No OpenReview submission ID, arXiv ID, DOI, or archival identifier exists yet.

## ICLR 2027 title

```text
ClaimPromoteBench: Source-Traceable Regression Tests for Model Services under Policy Revision
```

## ICLR 2027 abstract

```text
Executable policy revisions can change the required action for an unchanged input, yet model-service tests rarely isolate policy version. We introduce ClaimPromoteBench, which enumerates action-changing differences between two deterministic evaluators and converts them into paired route tests. It reports changed-rule and action-transition coverage, a cardinality-minimum structural suite, parser provenance, and failure-inclusive item and pair accuracy. We trace six revisions from five public projects and evaluate hosted routes on two Gatekeeper revisions. Across 144 calls, Qwen and DeepSeek Flash complete 0/36 and 21/36 raw-strict pairs. All 63 extracted actions agree with the Open Policy Agent oracle, locating the observed failures at the service or output interface. On an imbalanced evidence-state suite, Qwen reaches 113/150 pairs end to end and 113/123 conditional. An action-balanced challenge yields 48/90 and 13/90 full-contract pairs end to end for Qwen and Flash, versus 48/64 and 13/61 conditional, with DEMOTE recall of 4/30 and 0/30. Complete confusion matrices retain terminal failures. These results support source-traceable regression testing under finite executable policy changes. The study measures a synthetic model-service boundary; deployment frequency and naturalistic policy interpretation require field evidence.
```

The ICLR upload must use the anonymous PDF and anonymous supplementary ZIP. Author identity,
institution, public repository URLs, workflow identifiers, and searchable private provenance must
stay out of both files.

## arXiv title

```text
ClaimPromoteBench: Source-Traceable Regression Tests for Model Services under Policy Revision
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

- Two exact Gatekeeper revisions yield 12 source-traceable pairs covering 2/2 changed rules and
  2/2 observed action edges; a two-pair suite is jointly complete for the committed grammar.
- Three repetitions per hosted route yield 53/72 raw-strict actions and 21/36 pairs for DeepSeek
  Flash, versus 10/72 and 0/36 for Qwen. All 63 raw-strict actions are correct. Terminal failures are
  12 read timeouts and 69 serialization or output-envelope failures. Both model IDs use the same
  provider/API configuration; provider-side serving internals are opaque.
- Trivy reproduces a real inverted policy predicate on four upstream cases. Cosign reproduces four
  verifier-interface fault modes on six cases. Cosign remains a separate evidence class.
- A frozen public-source audit screens 465 repository seeds and reviews 11 candidates at source
  level. Microsoft Agent Governance Toolkit reproduces an agent-policy verdict gap (11/15 parent
  versus 15/15 fixed upstream tests), and agentgateway passes 33/33 offline tests at the exact
  Bedrock guardrail-adapter fix. The audit validates boundary faults, not prevalence or
  naturalistic model interpretation.
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

- [ ] OpenReview profile, conflicts, author list, and institutional domains are current.
- [ ] Title and abstract match the final anonymous PDF.
- [ ] Venue topics match the paper's bounded scope.
- [ ] Ethics and AI-use acknowledgements are complete.
- [ ] Anonymous PDF and supplementary previews contain no identity or provenance leak.
- [ ] The server-built PDF is downloaded and inspected page by page.
- [ ] arXiv author, affiliation, title, abstract, categories, and source archive are verified.
- [ ] No submission, merge, public release, or ready-for-review transition occurs without explicit
  authorization.
