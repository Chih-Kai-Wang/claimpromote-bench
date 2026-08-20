# ClaimPromoteBench submission metadata

This is the copy-ready metadata source for the ICLR 2027 and arXiv upload forms. The title and
abstract below match the canonical manuscript. Recheck every field against the final server-built
preview before the author performs either submission.

No OpenReview submission ID, arXiv ID, DOI, or archival identifier exists yet. Add one only after
the corresponding service has issued it and the author has verified it.

## ICLR 2027 title

```text
ClaimPromoteBench: Evaluating Whether Evidence Justifies Claim-State Transitions in AI Research Agents
```

## ICLR 2027 abstract

```text
AI research agents can possess valid artifacts yet assign a claim status beyond their registered scope. We study whether a requested state transition conforms to a fixed policy given a claim, evidence, and current state. We introduce ClaimPromoteBench, a benchmark with 200 controlled pairs over 20 policy factors, including a preregistered 150-pair hidden test with executable numerical and formal artifacts. In the original 7,200-decision study of two small Qwen3 models, 73.99% of responses failed format validation and all 1,873 parseable decisions chose ALLOW, yielding 13.33% end-to-end item accuracy and zero pair accuracy. We then froze a separate stronger-model protocol on the unchanged hidden split. An accuracy-blind 12-item pilot advanced two of seven service lanes to fresh no-retry full passes. Qwen3.7-Max reached .99 decision coverage, .94 end-to-end action accuracy, and .88 pair accuracy; DeepSeek-V4-Flash reached .913, .627, and .253. Both exceeded the always-ALLOW .50 action baseline in paired exact tests; five other lanes failed formatting qualification. These results distinguish interface reliability from evidence-sensitive policy reasoning. The reviewer artifact contains prompts, item-level outputs, labels, and deterministic recomputation checks; the same-oracle gate is reported only as an implementation check.
```

The ICLR upload must use the anonymous PDF and anonymous supplementary ZIP. Author identity,
institution, public repository URLs, workflow IDs, and searchable public artifact hashes must stay
out of both files.

## arXiv title

```text
ClaimPromoteBench: Evaluating Whether Evidence Justifies Claim-State Transitions in AI Research Agents
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

- Suggested primary category: `cs.AI`
- Possible cross-list: `cs.LG`

The author must choose the final category and cross-list in arXiv after inspecting the available
account-side choices and any endorsement requirement.

## ICLR suggested keywords and topics

- AI agents
- AI evaluation
- scientific reasoning
- research agents
- evidence-aware reasoning
- structured decision making
- trustworthy AI
- formal verification / verification-aware systems

Choose only topics actually offered by OpenReview. Likely higher-level matches are evaluation and
benchmarks, language-model agents, trustworthy or reliable machine learning, reasoning and
decision making, AI for science, and formal or neuro-symbolic methods.

## Suggested TL;DR

```text
On the frozen hidden split, Qwen3.7-Max reaches .94 end-to-end action and .88 pair accuracy while DeepSeek-V4-Flash reaches .627 and .253; five of seven service lanes fail formatting qualification, and same-oracle gate behavior is reported separately.
```

## Main empirical findings

- frozen v1 hidden study: 24 runs and 7,200 decisions;
- v1 format errors: 5,327 / 7,200 (73.99%);
- v1 parseable raw decisions: 1,873, all `ALLOW`;
- capable-model extension: seven accuracy-blind pilots and two fresh 300-instance full passes;
- Qwen3.7-Max hidden E2E action / pair accuracy: 282 / 300 and 132 / 150;
- DeepSeek-V4-Flash hidden E2E action / pair accuracy: 188 / 300 and 38 / 150;
- five capable-model lanes stopped after 0 / 12 valid pilot decisions and have no full score;
- both completed lanes exceed the always-`ALLOW` 150 / 300 action baseline in paired exact tests;
- post-v1 public pilot: 160 decisions, two models, one seed;
- constrained parseable decisions: 78 / 80;
- constrained complete pairs: 38 / 40;
- constrained raw pair accuracy: 0;
- constrained raw flip rate: 0;
- post-protocol GPT-5.4 full pass: 99 / 100 parseable decisions and 49 / 50 complete pairs;
- GPT-5.4 covered decision accuracy: 99 / 99;
- GPT-5.4 covered pair accuracy and raw flip rate: 49 / 49 and 1.0;
- GPT-5.4 raw false promotions: 0 / 49;
- deterministic post-gate correctness measures execution of the fixed benchmark policy.

## Data and code availability

### Anonymous conference version

```text
An anonymized supplementary bundle contains the public controlled benchmark, the reviewer-release hidden dataset and oracle labels, exact prompt packets, item-level empirical records, recomputation code, and executable and formal replay inputs. It excludes the private construction seed, author-identifying provenance, generated caches, and unused human-review workflow files. Public repository and archival identifiers will be released when double-blind review permits disclosure.
```

### Public preprint version

```text
Code, public benchmark data, the reviewer-release hidden dataset, item-level empirical records, validation workflows, and executable and formal replay inputs are available in the project repository. The private construction seed is not released. Exact workflow and artifact identities are recorded in the manuscript and repository. A long-term archival identifier will be added only after it exists.
```

## Reproducibility statement

```text
The public benchmark is deterministically rebuildable and checked for schema, oracle, pair-contract, shortcut, metamorphic-invariance, executable-artifact, and pinned-Lean consistency. The v1 hidden set and exact prompts were committed before scored inference. V1 recovery reused the original 24 source artifacts without re-querying the models and reclassified only 27 cross-field-invalid structured outputs as FORMAT_ERROR. The later studies retain frozen prompt packets, item-level raw responses, parser outcomes, oracle labels, and response hashes. Paper-facing values are recomputed from the released records and checked against machine-readable summaries in CI.
```

## AI-use disclosure summary

```text
Generative AI tools assisted literature search, research planning and methodological discussion, early code drafting and debugging, analysis checks and result interpretation, and parts of manuscript drafting and editing. The author chose the research question, defined the benchmark policy and experimental protocol, made the final study and analysis decisions, checked the quantitative results and references, and is responsible for the manuscript and submission. AI systems are not authors.
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
