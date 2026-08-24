# ClaimPromoteBench submission metadata

This file is the copy-ready metadata source for ICLR and arXiv. It does not authorize an upload.
The author must compare every field with the final server-built preview.

No OpenReview submission ID, arXiv ID, DOI, or archival identifier exists yet.

## ICLR 2027 title

```text
ClaimPromoteBench: Compiling Executable Policy Revisions into Failure-Aware Model-Service Tests
```

## ICLR 2027 abstract

```text
Executable policy revisions can change downstream actions for fixed inputs, yet model-service tests rarely isolate policy version. ClaimPromoteBench compiles deterministic policy versions and a finite authored context grammar into pairs whose oracle actions change. It records rule witnesses, action transitions, a minimum structural-coverage suite, and failure-inclusive endpoints. Six revisions across five public projects ground the fault model. Exact offline replay recovers policy or adapter faults in Gatekeeper, Trivy, Cosign, Microsoft Agent Governance Toolkit, and agentgateway; the latter two occur at agent or model boundaries. Two Gatekeeper revisions yield 12 pairs and a two-pair minimum. Across three runs on two hosted routes (144 calls), all 63 parsed actions match OPA; timeouts and envelope violations reduce end-to-end pair scores to 21/36 for DeepSeek Flash and 0/36 for Qwen. An offline endpoint audit recovers 40 correct pairs outside the full object contract. In evidence-state diagnostics, R6 Qwen reaches 113/150 pairs end to end versus 113/123 conditional. On an author-created challenge frozen publicly before calls, Qwen and Flash reach 48/90 and 13/90 pairs end to end versus 48/64 and 13/61 conditional, with DEMOTE recall of 4/30 and 0/30. Complete confusion matrices retain terminal failures. The results support regression testing of exact model-service interfaces under finite authored policy changes. Deployment prevalence and naturalistic model interpretation remain open.
```

The ICLR upload must use the anonymous PDF and anonymous supplementary ZIP. Author identity,
institution, public repository URLs, workflow identifiers, and searchable private provenance must
stay out of both files.

## arXiv title

```text
ClaimPromoteBench: Compiling Executable Policy Revisions into Failure-Aware Model-Service Tests
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
Enumerates finite action-changing differences between caller-supplied policy evaluators, reduces them to a minimum structural-coverage pair suite, and scores complete model-service routes at action and structured-contract endpoints.
```

## Main empirical findings

- Two exact Gatekeeper revisions yield 12 source-traceable pairs covering 2/2 changed rules and
  2/2 observed action edges; a two-pair suite is jointly complete for the committed grammar.
- Three repetitions per hosted route yield 53/72 strict actions and 21/36 pairs for DeepSeek Flash,
  versus 10/72 and 0/36 for Qwen. All 63 strictly parsed actions are correct. Terminal failures are
  12 read timeouts and 69 serialization or output-envelope failures. Both model IDs use the same
  provider/API configuration; provider-side serving internals are opaque.
- Trivy reproduces a real inverted policy predicate on four upstream cases. Cosign reproduces four
  verifier-interface fault modes on six cases. Cosign remains a separate evidence class.
- A frozen public-source audit screens 465 repository seeds and reviews 11 candidates at source
  level. Microsoft Agent Governance Toolkit reproduces an agent-policy verdict gap (11/15 parent
  versus 15/15 fixed upstream tests), and agentgateway passes 33/33 offline tests at the exact
  Bedrock guardrail-adapter fix. The audit validates boundary faults, not prevalence or
  naturalistic model interpretation.
- The authored SLSA rule suite covers 12/12 changed rules and 6/10 reachable action edges; the graph
  suite covers 12/12 and 10/10. A ten-pair structural-coverage suite is jointly minimum for the
  committed candidate pool.
- The policy-aware structured random-forest control reaches 107/120 items and 47/60 pairs; the
  profile-blind control reaches 57/120 items and 0/60 pairs.
- An offline audit of 1,320 prior route items recovers 69 strict actions outside the full contract,
  including 49 correct actions and 40 additional correct pairs.
- R6 Qwen returns 272/300 valid decisions and scores 258/300 items and 113/150 pairs end to end,
  versus 258/272 and 113/123 conditional. Its `DEMOTE` support is 8/300 and recall is 0/8.
- The public balanced challenge contains 90 pairs, 180 items, 15 factors, 90 `ALLOW` members, and 30
  members for each remaining action. Qwen and Flash score 48/90 and 13/90 pairs end to end versus
  48/64 and 13/61 conditional; `DEMOTE` recall is 4/30 and 0/30.
- The historical r6 Flash interface returns HTTP 401 before model output on all 300 calls. Later
  Flash paths establish only their own executability because the service stacks differ.
- The deterministic executor is the definitional policy ceiling. Naive Bayes is a weak sanity
  control, reaching 184/300 items and 34/150 pairs on r6.

## Data and code availability

### Anonymous conference version

```text
An anonymized supplementary bundle contains the finite policy-difference enumerator and suite reducer, exact source-validation inputs and receipts, frozen paired datasets, prompt packets, content-free terminal records, analysis code, complete confusion matrices, and privacy receipts needed to recompute the paper. Its manifest derives file counts from the generated tree. It excludes raw failed responses, free-form errors, provider response identifiers, hidden reasoning, account identity, author-identifying provenance, private construction seeds, and generated caches.
```

### Public preprint version

```text
A history-free public export will retain the necessary code, licensed source excerpts, frozen datasets, content-free empirical records, validators, and reproducibility receipts. Private construction material, raw provider text, hidden reasoning, and account metadata will remain excluded. Repository and archival identifiers will be added only after they exist and disclosure is authorized.
```

## Reproducibility statement

```text
The artifact binds exact upstream source bytes and commits, licenses, executable policies, finite grammars, prompts, frozen zero-retry schedules, content-free terminal outcome classes, and analysis code. Validators recompute source behavior, coverage, minimum suites, endpoint metrics, action recalls, and confusion matrices. Reviewer derivatives preserve every scheduled denominator while removing response content and identifying metadata.
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
