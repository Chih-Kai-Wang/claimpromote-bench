# ClaimPromoteBench submission metadata

This is the copy-ready metadata source for the ICLR 2027 and arXiv upload forms. The title and
abstract below match the canonical manuscript. Recheck every field against the final server-built
preview before the author performs either submission.

No OpenReview submission ID, arXiv ID, DOI, or archival identifier exists yet. Add one only after
the corresponding service has issued it and the author has verified it.

## ICLR 2027 title

```text
ClaimPromoteBench: Failure-Aware Paired Tests of Model Routes under Executable Policy Revisions
```

## ICLR 2027 abstract

```text
Policy revisions can leave model-mediated structured decisions valid-looking but stale; valid-only scoring also hides interface failure. We introduce ClaimPromoteBench, a synthetic protocol that holds typed context fixed across executable policies and scores paired action conformance after output-contract validation. Every scheduled service, syntax, schema, and semantic failure remains incorrect end to end. In one authored BLUE-to-AMBER migration, rule-complete tests cover 6/10 action edges, graph-complete tests cover all ten reachable edges, and a 10-pair gate covers all 12 changed rules. Two pinned local routes, evaluated once without independent replication, score 10/60 and 2/60 pairs and fail the gate. Auxiliary r6 Qwen coverage is 272/300; item/pair accuracy is 258/300 and 113/150 end to end versus 258/272 and 113/123 conditional. In a balanced challenge, Qwen and Flash coverage is 148/180 and 146/180; end-to-end item/pair scores are 132/180,48/90 and 90/180,13/90, versus 132/148,48/64 and 90/146,13/61 conditional; DEMOTE recall is 4/30 and 0/30. A post-hoc route, frozen before its first call, returns 13/20 valid action-correct decisions and 6/10 pairs but fails the strict gate. The executor defines labels, not a learned baseline. Results support regression testing of finite authored decision surfaces, not model-family ranking, naturalistic validity, or causal comparison.
```

The ICLR upload must use the anonymous PDF and anonymous supplementary ZIP. Author identity,
institution, public repository URLs, workflow IDs, and searchable public artifact hashes must stay
out of both files.

## arXiv title

```text
ClaimPromoteBench: Failure-Aware Paired Tests of Model Routes under Executable Policy Revisions
```

## arXiv abstract

Use the same canonical abstract shown above so the preprint metadata, PDF, README, and citation
record describe the same study.

## Author and affiliation

```text
Chih-Kai Wang
Department of Mathematics and Information Education
National Taipei University of Education
```

The public arXiv PDF contains this identity. The anonymous ICLR PDF and supplementary bundle do
not.

## arXiv categories

- Suggested primary category: `cs.SE`
- Possible cross-list: `cs.AI`

The author must choose the final category and cross-list in arXiv after inspecting the available
account-side choices and any endorsement requirement.

## ICLR suggested keywords and topics

- AI evaluation
- synthetic benchmarks
- policy conformance
- evidence-state transitions
- behavioral testing
- software testing
- policy migration
- structured decision making
- trustworthy AI
- formal verification / verification-aware systems

Choose only topics actually offered by OpenReview. Likely higher-level matches are evaluation and
benchmarks, trustworthy or reliable machine learning, reasoning and decision making,
language-model systems, and formal or neuro-symbolic methods.

## Suggested TL;DR

```text
Compiles behavioral differences between executable policy versions into minimum rule- and action-transition-complete regression tests, then scores model-service routes with failures end to end.
```

## Main empirical findings

- Central migration: the rule-stratified 60-pair suite covers all 12 changed rules but 6 / 10
  reachable action edges; the 60-pair graph suite covers all ten edges and all 12 rules.
- Graph routes: Mistral produces 71 / 120 valid decisions, 40 / 120 correct items, 10 / 60 correct
  pairs, and 10 / 31 conditional pair accuracy; Phi-4 produces 43 / 120, 27 / 120, 2 / 60, and
  2 / 8. Both have 0 / 24 end-to-end `DEMOTE` recall.
- Minimum gate: ten pairs retain all ten edges and all 12 rules. Mistral produces 14 / 20 valid
  decisions, 9 / 20 correct items, and 2 / 10 correct pairs; Phi-4 produces 6 / 20, 5 / 20, and
  0 / 10. Both fail the fixed gate. The gate reuses graph records and is not an independent sample.
- Auxiliary r6 Qwen route: 272 / 300 valid decisions, 258 / 300 correct actions, and 113 / 150
  correct pairs; conditional item and pair scores are 258 / 272 and 113 / 123. Its action recalls
  are 143 / 150 `ALLOW`, 110 / 134 `HOLD`, 0 / 8 `DEMOTE`, and 5 / 8 `ESCALATE`.
- Historical r6 Flash interface: all 300 requests return HTTP 401 before model output. It is an
  interface failure described in prose, not a model-result row; a later route on a different stack
  cannot establish a causal model or provider effect.
- Auxiliary balanced challenge: 90 pairs, 180 items, and 15 factors, with 90 `ALLOW` items and 30
  for each other action. Qwen coverage is 148 / 180, with 132 / 180 item and 48 / 90 pair accuracy
  end to end versus 132 / 148 and 48 / 64 conditional. Flash coverage is 146 / 180, with 90 / 180
  and 13 / 90 end to end versus 90 / 146 and 13 / 61 conditional.
- Challenge action recall (`ALLOW` / `HOLD` / `DEMOTE` / `ESCALATE`) is 0.878 / 0.867 / 0.133 /
  0.767 for Qwen and 0.756 / 0.300 / 0.000 / 0.433 for Flash. Full confusion matrices retain a
  no-valid-decision column.
- Ox minimum-route replay: 13 / 20 valid and action-correct decisions, six complete and correct
  pairs, conditional item/pair accuracy 1.0 / 1.0, and end-to-end accuracy .65 / .60. Three HTTP
  503, three cross-field semantic, and one length-terminated JSON failure cause the strict gate to
  fail. This is a post-hoc route selection with a pre-call-frozen schedule and an undisclosed stealth
  model identity.
- The deterministic executor is the label definition, not a learned baseline. Naive Bayes is a
  weak sanity control; Random Forest profile-aware and profile-blind rows are construction and
  shortcut controls.
- The quota-confounded seven-route supplement is excluded in full. Permanent reviewer evidence
  uses dynamically counted manifests and reasoning-free derivatives.

## Data and code availability

### Anonymous conference version

```text
An anonymized supplementary bundle contains the public controlled benchmark, pair-balanced public challenge, reviewer-release hidden datasets and policy labels, exact prompt packets, projected C2 records, item-level empirical scoring records, the 20-row Ox minimum-route action/failure derivative, recomputation code, privacy and correction receipts, and executable and formal replay inputs. Its manifest records the generated tree's current file count. It excludes private construction seeds, raw final-response text, free-form errors, provider hidden-thinking content, provider response identifiers, author-identifying provenance, and generated caches. Structured decisions or action-only projections plus parse and failure classes preserve every scheduled denominator. Public repository and archival identifiers will be released when double-blind review permits disclosure.
```

### Public preprint version

```text
Code, public benchmark and challenge data, reviewer-release hidden datasets, item-level empirical records, validation workflows, privacy receipts, and executable and formal replay inputs will be released through a history-free public export after licensing review. Private construction seeds, raw provider text, and provider hidden-thinking content will remain excluded. A long-term archival identifier will be added only after it exists.
```

## Reproducibility statement

```text
The public benchmark is deterministically rebuildable and checked for schema, label generation, pair contracts, shortcuts, metamorphic invariance, executable artifacts, and pinned-Lean consistency. The fresh hidden study freezes its construction and 600-request schedule before inference and seals every terminal cell before gold loading. The public challenge freezes its data, prompts, adapters, statistics, and zero-retry schedule before inference. The local policy-transition graph seals 240 zero-retry terminal records, and its prospectively selected minimum-gate analysis makes no additional calls. Reviewer derivatives remove credentials, provider and account identifiers, author provenance, hidden reasoning, raw final-response text, and free-form errors while preserving structured decisions, parse and failure classes, and all scheduled denominators. Paper-facing values are replayed from released item records and checked against machine-readable summaries.
```

## AI-use disclosure summary

```text
Generative AI tools assisted literature search, research planning and methodological discussion, synthetic benchmark-template and code drafting and debugging, analysis checks and result interpretation, and parts of manuscript drafting and editing. The author chose the research question, defined the benchmark policy and experimental protocol, made the final study and analysis decisions, checked the generated benchmark through deterministic validators, checked the quantitative results and references, and is responsible for the manuscript and submission. AI systems are not authors.
```

Use the detailed disclosure in the manuscript when the venue requests the full statement.

## Ethics scope

The submission contains no human-subject experiment, human annotation study, or human-review
result. Synthetic `review_status` and reviewer-provenance fields are benchmark policy state, not
records collected from people. The author must read and acknowledge the ICLR Code of Ethics in
OpenReview. The paper claims no IRB approval, exemption, institutional review, or informed
consent.

## Official ICLR 2027 dates verified on 2026-08-21

- Genuine abstract and final author list deadline: **2026-09-18 AOE**.
- Full paper and supplementary-material deadline: **2026-09-25 AOE**.
- Official guide: `https://iclr.cc/Conferences/2027/AuthorGuidelines`

## OpenReview account-side checklist

- [ ] OpenReview profile exists, is current, and has a verified email.
- [ ] Conflicts and institutional domains are accurate.
- [ ] Any reciprocal-reviewer registration notice sent after the abstract deadline is completed.
- [ ] The final author list is entered before 2026-09-18 AOE.
- [ ] The genuine title and abstract are entered before 2026-09-18 AOE.
- [ ] Title and abstract still match the final PDF before 2026-09-25 AOE.
- [ ] Topics match the actual paper.
- [ ] The ICLR Code of Ethics acknowledgement is completed.
- [ ] The detailed AI-use disclosure is supplied in the form and remains in the PDF.
- [ ] Anonymous PDF and supplementary previews contain no author or public-provenance leak.
- [ ] The server-displayed PDF is downloaded and inspected before final submission.
- [ ] A valid OpenReview submission record is visible before describing the paper as submitted.

## arXiv account-side checklist

- [ ] Author name and affiliation match the public PDF.
- [ ] Title and abstract match the public PDF exactly.
- [ ] The prepared source ZIP is uploaded; `arxiv.tex` and `references.bib` are present at the
  archive root and the top-level TeX file is detected correctly.
- [ ] Server compilation succeeds without missing files.
- [ ] The server-generated PDF is compared page by page with the locally verified public PDF.
- [ ] `cs.AI` and any `cs.LG` cross-list are confirmed against the final scope.
- [ ] Comments do not claim conference acceptance or a submission status that does not exist.
- [ ] Any endorsement requirement is completed.
- [ ] An arXiv identifier is recorded only after arXiv issues it.

## Status language

Before either account-side submission, use:

```text
Scientific release candidate ready; OpenReview and arXiv account-side submission pending.
```

Use “submitted” only after the corresponding service displays a valid submission record. Use
“accepted” or “published” only after those states actually exist.
