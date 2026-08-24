# ClaimPromoteBench submission metadata

This file is the copy-ready metadata source for ICLR and arXiv. It does not authorize an upload.
The author must compare every field with the final server-built preview.

No OpenReview submission ID, arXiv ID, DOI, or archival identifier exists yet.

## ICLR 2027 title

```text
ClaimPromoteBench: Compiling Executable Policy Revisions into Paired Model-Service Regression Tests
```

## ICLR 2027 abstract

```text
Policy revisions can change prescribed actions for fixed evidence, creating regression risk in structured decisions routed through language-model services. ClaimPromoteBench is a synthetic, policy-constrained evaluation that compiles two executable policy versions and a finite grammar into paired tests that hold context fixed and change only policy. It certifies changed-rule and action-transition coverage and selects a minimum joint suite. Two source-traceable Gatekeeper revisions yield 12 pairs covering two rules and both transitions; two pairs suffice. Across three frozen repetitions per hosted route, strict end-to-end action/pair scores are 53/72 and 21/36 for DeepSeek Flash and 10/72 and 0/36 for Qwen. Every extracted action is correct; failures are 12 timeouts and 69 output-envelope violations. A 1,320-item audit recovers 49 correct actions and 40 correct pairs outside the full contract. R6 Qwen scores 258/300 items and 113/150 pairs end to end versus 258/272 and 113/123 conditional. On a public balanced challenge, Qwen and Flash score 132/180, 48/90 and 90/180, 13/90 end to end versus 132/148, 48/64 and 90/146, 13/61 conditional; DEMOTE recall is 4/30 and 0/30. Results support regression testing of finite authored policy surfaces and model-service interfaces.
```

The ICLR upload must use the anonymous PDF and anonymous supplementary ZIP. Author identity,
institution, public repository URLs, workflow identifiers, and searchable private provenance must
stay out of both files.

## arXiv title

```text
ClaimPromoteBench: Compiling Executable Policy Revisions into Paired Model-Service Regression Tests
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
Compiles action-changing differences between executable policy versions into minimum coverage-certified paired regression tests, then scores complete model-service routes at action and structured-contract endpoints.
```

## Main empirical findings

- Two exact Gatekeeper revisions yield 12 source-traceable pairs covering 2/2 changed rules and
  2/2 observed action edges; a two-pair suite is jointly complete for the committed grammar.
- Three repetitions per hosted route yield 53/72 strict actions and 21/36 pairs for DeepSeek Flash,
  versus 10/72 and 0/36 for Qwen. Every safely extracted action is correct. Terminal failures are
  12 read timeouts and 69 output-envelope failures.
- Trivy reproduces a real inverted policy predicate on four upstream cases. Cosign reproduces four
  verifier-interface fault modes on six cases. Cosign remains a separate evidence class.
- The authored SLSA rule suite covers 12/12 changed rules and 6/10 reachable action edges; the graph
  suite covers 12/12 and 10/10. A ten-pair suite is jointly minimum for the committed candidate pool.
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
  control.

## Data and code availability

### Anonymous conference version

```text
An anonymized supplementary bundle contains the policy-difference compiler, exact source-validation inputs and receipts, frozen paired datasets, prompt packets, content-free terminal records, analysis code, complete confusion matrices, and privacy receipts needed to recompute the paper. Its manifest derives file counts from the generated tree. It excludes raw failed responses, free-form errors, provider response identifiers, hidden reasoning, account identity, author-identifying provenance, private construction seeds, and generated caches.
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
