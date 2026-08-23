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
Evidence-producing systems must also decide whether recorded evidence permits a claim-state change. We introduce ClaimPromoteBench, a synthetic conformance test for one author-defined evidence-transition policy. Each controlled pair changes one policy-relevant field; scoring retains service, syntax, schema, and semantic failures in the scheduled denominator. In a frozen 300-item hidden realization, one Qwen service configuration returned 272 valid decisions and achieved 258/300 item and 113/150 pair correctness end to end (conditional: 258/272 and 113/123). A separately frozen 180-item public challenge balances its 90 non-ALLOW members across HOLD, DEMOTE, and ESCALATE (30 each). Qwen and Flash configurations achieved end-to-end item correctness of 132/180 and 90/180; pair correctness was 48/90 and 13/90. DEMOTE recall was 4/30 and 0/30. The deterministic executor generates the labels and defines the policy ceiling; the learned Naive Bayes comparator is weak. The artifact supports reproducible diagnosis of policy conformance, not naturalistic scientific validity or a causal model comparison.
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
A hidden diagnostic and pair-balanced public challenge test one synthetic evidence-transition policy with failure-aware item, pair, and action metrics.
```

## Main empirical findings

- fresh confirmatory realization: 150 controlled pairs / 300 items, 600 frozen requests, and all
  600 terminal cells C2-sealed before gold loading or analysis;
- Qwen3.7-Max: 272 / 300 valid decisions, 258 / 300 correct actions, and 113 / 150 correct pairs;
- Qwen3.7-Max decision / pair coverage: 0.907 and 0.820; E2E item / pair accuracy: 0.860 and
  0.753; conditional item / pair accuracy: 0.949 and 0.919;
- frozen public-development four-class multinomial Naive Bayes (`alpha=1`, identifier-normalized
  unigram and bigram prompt counts): 184 / 300 correct actions and 34 / 150 correct pairs; this is
  a weak low-cost comparator, not a representative competitive baseline;
- Qwen3.7-Max per-action correct counts: 143 / 150 `ALLOW`, 110 / 134 `HOLD`, 5 / 8
  `ESCALATE`, and 0 / 8 `DEMOTE`;
- Qwen3.7-Max service failures: 14 HTTP 500 responses, one HTTP 503 response, ten timeouts, and
  three semantic-invalid outputs, all incorrect with zero retries;
- registered Flash lane: 300 HTTP 401 responses and no model output; scheduled service-configuration
  E2E scores are 0 / 300 items and 0 / 150 pairs, while conditional correctness and model efficacy
  are non-evaluable and dual-model confirmation is unsupported;
- pair-balanced public challenge: 90 pairs / 180 items / 15 factors, with 90 `ALLOW` and 30 each of
  `HOLD`, `DEMOTE`, and `ESCALATE`;
- challenge Qwen: 148 / 180 valid decisions, 0.733 / 0.533 E2E item / pair accuracy, and
  0.892 / 0.750 conditional item / pair accuracy;
- challenge Flash: 146 / 180 valid decisions, 0.500 / 0.144 E2E item / pair accuracy, and
  0.616 / 0.213 conditional item / pair accuracy;
- the manuscript reports complete/correct pair counts for all 20 r6 factors and all 15 challenge
  factors; every configuration has zero-accuracy factors;
- challenge Qwen action recall (`ALLOW` / `HOLD` / `DEMOTE` / `ESCALATE`):
  0.878 / 0.867 / 0.133 / 0.767; Flash: 0.756 / 0.300 / 0.000 / 0.433;
- the later Flash route establishes service-path executability only; differing service stacks
  preclude a strict causal model ablation;
- service labels are configuration labels. Model, serving implementation, and adapter differ, so
  the old/new Flash routes do not support a strict causal ablation or model-family ranking;
- permanent reviewer evidence uses dynamically counted manifests and reasoning-free derivatives;
- deterministic policy execution is a definitional policy ceiling, not a learned baseline; the
  public-development text Naive Bayes comparator remains weak.

## Data and code availability

### Anonymous conference version

```text
An anonymized supplementary bundle contains the public controlled benchmark, pair-balanced public challenge, reviewer-release hidden datasets and policy labels, exact prompt packets, projected C2 records, item-level empirical records, recomputation code, privacy and correction receipts, and executable and formal replay inputs. Its manifest records the generated tree's current file count. It excludes private construction seeds, provider hidden-thinking content, provider response identifiers, author-identifying provenance, and generated caches. Model-visible final JSON and sanitized error text retained for parser audit pass the same fail-closed identity and credential scans. Public repository and archival identifiers will be released when double-blind review permits disclosure.
```

### Public preprint version

```text
Code, public benchmark and challenge data, reviewer-release hidden datasets, item-level empirical records, validation workflows, privacy receipts, and executable and formal replay inputs will be released through a history-free public export after licensing review. Private construction seeds, raw provider text, and provider hidden-thinking content will remain excluded. A long-term archival identifier will be added only after it exists.
```

## Reproducibility statement

```text
The public benchmark is deterministically rebuildable and checked for schema, label generation, pair contracts, shortcuts, metamorphic invariance, executable artifacts, and pinned-Lean consistency. The fresh hidden study freezes its construction and 600-request schedule before inference and seals every terminal cell before gold loading. The public challenge freezes its data, prompts, adapters, statistics, and zero-retry schedule before inference. Reviewer derivatives remove credentials, provider and account identifiers, author provenance, and hidden reasoning while preserving scoring fields. The balanced-challenge derivative retains model-visible final JSON and sanitized error text for parser audit. Paper-facing values are replayed from released item records and checked against machine-readable summaries.
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
