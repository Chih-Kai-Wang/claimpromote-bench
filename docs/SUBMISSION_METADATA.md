# ClaimPromoteBench submission metadata

This is the copy-ready metadata source for the ICLR 2027 and arXiv upload forms. The title and
abstract below match the canonical manuscript. Recheck every field against the final server-built
preview before the author performs either submission.

No OpenReview submission ID, arXiv ID, DOI, or archival identifier exists yet. Add one only after
the corresponding service has issued it and the author has verified it.

## ICLR 2027 title

```text
ClaimPromoteBench: Synthetic, Policy-Constrained Evaluation of Evidence-State Transitions
```

## ICLR 2027 abstract

```text
Producing evidence and deciding what status that evidence licenses are different tasks. We frame the latter as synthetic policy conformance, rather than a broad test of research-agent ability. ClaimPromoteBench presents a claim, typed evidence, a current state, and a requested transition under a fixed author-defined policy. In a preregistered 300-item hidden study, a Qwen3.7-Max service configuration returned 272 valid decisions (decision coverage .9067) and 123 complete pairs (pair coverage .8200). End-to-end item and pair accuracy were .8600 and .7533; conditional accuracy among valid decisions and complete pairs was .9485 and .9187. End-to-end recall was .9533/ALLOW, .8209/HOLD, 0/DEMOTE, and .6250/ESCALATE. A weak public-development text Naive Bayes comparator reached .6133 item and .2267 pair accuracy. A separately precommitted public robustness challenge balanced 90 ALLOW members against 30 each of HOLD, DEMOTE, and ESCALATE over 90 pairs and 15 factors. Qwen produced 148/180 valid decisions, with .7333/.5333 end-to-end and .8919/.7500 conditional item/pair accuracy; a Flash route produced 146/180 valid decisions, with .5000/.1444 end-to-end and .6164/.2131 conditional accuracy. Factor-level end-to-end pair accuracy spans .000--1.000 in both Qwen regimes and .000--.833 for Flash, exposing heterogeneity hidden by aggregates. Every service, syntax, schema, and semantic failure remains incorrect in the end-to-end denominator. The earlier Flash lane's 300 HTTP 401 responses diagnose its frozen service interface; the later route establishes executability only. Different service stacks preclude a strict causal model ablation. A deterministic policy executor is a definitional policy ceiling, not a learned baseline.
```

The ICLR upload must use the anonymous PDF and anonymous supplementary ZIP. Author identity,
institution, public repository URLs, workflow IDs, and searchable public artifact hashes must stay
out of both files.

## arXiv title

```text
ClaimPromoteBench: Synthetic, Policy-Constrained Evaluation of Evidence-State Transitions
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

- AI evaluation
- synthetic benchmarks
- policy conformance
- evidence-state transitions
- behavioral testing
- structured decision making
- trustworthy AI
- formal verification / verification-aware systems

Choose only topics actually offered by OpenReview. Likely higher-level matches are evaluation and
benchmarks, language-model agents, trustworthy or reliable machine learning, reasoning and
decision making, AI for science, and formal or neuro-symbolic methods.

## Suggested TL;DR

```text
A hidden 300-item evaluation and a separately precommitted 180-item action-balanced public challenge expose coverage and DEMOTE failures in service configurations applying a fixed synthetic evidence-transition policy; all unusable responses remain incorrect, and cross-stack differences are descriptive rather than causal.
```

## Main empirical findings

- fresh confirmatory realization: 150 controlled pairs / 300 items, 600 frozen requests, and all
  600 terminal cells C2-sealed before gold loading or analysis;
- Qwen3.7-Max: 272 / 300 valid decisions, 258 / 300 correct actions, and 113 / 150 correct pairs;
- Qwen3.7-Max decision / pair coverage: 0.907 and 0.820; E2E item / pair accuracy: 0.860 and
  0.753; conditional item / pair accuracy: 0.949 and 0.919;
- frozen public-development text Naive Bayes baseline: 184 / 300 correct actions and 34 / 150
  correct pairs;
- Qwen3.7-Max versus baseline: 74 additional correct actions, 84 pair-block wins, 10 losses,
  one-sided exact `p=5.16e-16`, and two-hypothesis Holm-adjusted `p=1.03e-15`;
- Qwen3.7-Max per-action correct counts: 143 / 150 `ALLOW`, 110 / 134 `HOLD`, 5 / 8
  `ESCALATE`, and 0 / 8 `DEMOTE`;
- Qwen3.7-Max service failures: 14 HTTP 500 responses, one HTTP 503 response, ten timeouts, and
  three semantic-invalid outputs, all incorrect with zero retries;
- registered Flash lane: 300 HTTP 401 responses and no model output; scheduled service-configuration
  E2E scores are 0 / 300 items and 0 / 150 pairs, while conditional correctness and model efficacy
  are non-evaluable and dual-model confirmation is unsupported;
- balanced public challenge: 90 pairs / 180 items / 15 factors, with 90 `ALLOW` and 30 each of
  `HOLD`, `DEMOTE`, and `ESCALATE`;
- challenge Qwen: 148 / 180 valid decisions, 0.733 / 0.533 E2E item / pair accuracy, and
  0.892 / 0.750 conditional item / pair accuracy;
- challenge Flash: 146 / 180 valid decisions, 0.500 / 0.144 E2E item / pair accuracy, and
  0.616 / 0.213 conditional item / pair accuracy;
- factor-level E2E pair accuracy ranges from 0 to 1.0 in r6 Qwen and challenge Qwen, and from 0
  to 0.833 in challenge Flash; every configuration has zero-accuracy factors;
- challenge Qwen action recall (`ALLOW` / `HOLD` / `DEMOTE` / `ESCALATE`):
  0.878 / 0.867 / 0.133 / 0.767; Flash: 0.756 / 0.300 / 0.000 / 0.433;
- the later Flash route establishes service-path executability only; differing service stacks
  preclude a strict causal model ablation;
- permanent fresh-study reviewer evidence uses a dynamically counted manifest with a reasoning-free
  post-C2 derivative and byte-identical scientific analysis payload;
- frozen v1 hidden study: 24 runs and 7,200 decisions;
- v1 format errors: 5,327 / 7,200 (73.99%);
- v1 parseable raw decisions: 1,873, all `ALLOW`;
- capable-model extension: 14 adaptive pilot attempts, two fresh 300-instance full passes, and a
  post-hoc 288-instance / 144-pair pilot-excluded sensitivity;
- Qwen3.7-Max pilot-excluded E2E action / pair accuracy: 270 / 288 and 126 / 144;
- DeepSeek-V4-Flash pilot-excluded E2E action / pair accuracy: 181 / 288 and 37 / 144;
- both completed lanes: 0 / 8 on pilot-excluded `DEMOTE` cases;
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
- deterministic policy execution is a definitional policy ceiling, not a learned baseline; the
  public-development text Naive Bayes comparator remains weak.

## Data and code availability

### Anonymous conference version

```text
An anonymized supplementary bundle contains the public controlled benchmark, balanced public challenge, reviewer-release hidden datasets and oracle labels, exact prompt packets, projected C2 records, item-level empirical records, recomputation code, privacy/redaction/correction receipts, and executable and formal replay inputs. Its manifest records the generated tree's current file count. It excludes private construction seeds, provider hidden-thinking content, provider response identifiers, author-identifying provenance, generated caches, and unused human-review workflow files. Public repository and archival identifiers will be released when double-blind review permits disclosure.
```

### Public preprint version

```text
Code, public benchmark and balanced-challenge data, reviewer-release hidden datasets, item-level empirical records, validation workflows, privacy/redaction/scientific-equivalence receipts, and executable and formal replay inputs are available in the project repository. Private construction seeds and provider hidden-thinking content are not released. Exact workflow and artifact identities are recorded in repository evidence manifests. A long-term archival identifier will be added only after it exists.
```

## Reproducibility statement

```text
The public benchmark is deterministically rebuildable and checked for schema, oracle, pair-contract, shortcut, metamorphic-invariance, executable-artifact, and pinned-Lean consistency. The v1 hidden set and exact prompts were committed before scored inference. V1 recovery reused the original 24 source artifacts without re-querying the models and reclassified only 27 cross-field-invalid structured outputs as FORMAT_ERROR. The fresh study binds public C0 and salt commitments, a future randomness beacon, C1 construction, a frozen request schedule, and all 600 pre-gold C2 terminal cells. A post-C2 text-only allowlist derivative removes provider hidden-thinking blocks and verifies source-to-derived row hashes and byte-identical scientific analysis. The public balanced challenge freezes its data, prompts, adapters, statistics, and zero-retry schedule before inference; its receipt validates 360 records and privacy scans. Paper-facing values are recomputed from released item records and checked against machine-readable summaries in CI.
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
