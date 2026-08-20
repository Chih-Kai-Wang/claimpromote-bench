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
AI research agents may have valid evidence and still assign a claim status beyond the registered support. We study whether a requested status change satisfies a fixed policy given a claim, its evidence, and its current status. We introduce ClaimPromoteBench, a controlled benchmark with 200 pairs over 20 policy factors, including a preregistered 150-pair hidden test. Numerical and formal cases connect to executable artifacts, and the hidden set and exact prompts were committed before scored inference. The primary study contains 7,200 hidden decisions from two Qwen3 models, four intervention arms, and three seeds. Among these outputs, 5,327 (73.99%) receive FORMAT_ERROR, while all 1,873 parseable raw decisions select ALLOW. A post-v1 public pilot compares free and JSON-schema-constrained decoding under identical prompts. Constraints raise coverage from 75% to 100% for Qwen3-0.6B and from 0% to 95% for Qwen3-1.7B; all 78 constrained parseable decisions select ALLOW, and raw pair accuracy and flip rate remain zero over 38 complete pairs. A deterministic gate applies the benchmark policy to covered cases and blocks false promotion. We report structured-output coverage, raw evidence sensitivity, and deterministic policy execution as separate quantities.
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
Schema constraints restore usable outputs for two small Qwen3 models but not evidence-sensitive decisions: every parseable action remains ALLOW, while a separate deterministic gate enforces the fixed benchmark policy on covered cases.
```

## Main empirical findings

- frozen v1 hidden study: 24 runs and 7,200 decisions;
- v1 format errors: 5,327 / 7,200 (73.99%);
- v1 parseable raw decisions: 1,873, all `ALLOW`;
- post-v1 public pilot: 160 decisions, two models, one seed;
- constrained parseable decisions: 78 / 80;
- constrained complete pairs: 38 / 40;
- constrained raw pair accuracy: 0;
- constrained raw flip rate: 0;
- deterministic post-gate correctness measures execution of the fixed benchmark policy.

## Data and code availability

### Anonymous conference version

```text
An anonymized supplementary bundle contains the public controlled benchmark, validation code, compact v1 and v2 result summaries, and public formal artifacts. It excludes the private hidden seed and data, author-identifying provenance, generated caches, and unused human-review workflow files. Public repository and archival identifiers will be released when double-blind review permits disclosure.
```

### Public preprint version

```text
Code, public benchmark data, compact v1 and v2 result summaries, validation workflows, and public formal artifacts are available in the project repository. The private hidden seed is not released. Exact workflow and artifact identities are recorded in the manuscript and repository. A long-term archival identifier will be added only after it exists.
```

## Reproducibility statement

```text
The public benchmark is deterministically rebuildable and checked for schema, oracle, pair-contract, shortcut, metamorphic-invariance, executable-artifact, and pinned-Lean consistency. The v1 hidden set and exact prompts were committed before scored inference. V1 recovery reused the original 24 source artifacts without re-querying the models and reclassified only 27 cross-field-invalid structured outputs as FORMAT_ERROR. The post-v1 public pilot retained raw responses, verified identical prompts across decoding conditions, and was recomputed twice from four immutable source runs with byte-identical aggregate output. Paper-facing values are checked against machine-readable v1 and v2 summaries in CI.
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

## Official ICLR 2027 dates verified on 2026-08-20

- Genuine abstract and final author list deadline: **2026-09-18 AOE**.
- Full paper and supplementary-material deadline: **2026-09-25 AOE**.
- Official guide: `https://iclr.cc/Conferences/2027/AuthorGuidelines`

## OpenReview account-side checklist

- [ ] OpenReview profile exists, is current, and has a verified email.
- [ ] Conflicts and institutional domains are accurate.
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
