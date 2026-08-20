# ClaimPromoteBench submission metadata draft

This document is a copy-ready draft for arXiv and conference submission forms. The manuscript is
the source of truth. Recheck every field against the final server-generated preview before pressing
the final submit button.

Account-side fields must be copied from the final manuscript and verified in the server-generated preview rather than guessed.

## Canonical title

```text
ClaimPromoteBench: Evaluating Whether Evidence Justifies Claim-State Transitions in AI Research Agents
```

## Short title

```text
ClaimPromoteBench
```

## Author and affiliation for the public preprint

```text
Chih-Kai Wang
Department of Mathematics and Information Education
National Taipei University of Education
Taipei, Taiwan
```

The anonymous conference PDF must not contain this section, the public repository URL, workflow
IDs, or searchable public artifact hashes.

## Canonical abstract

```text
AI research agents may have valid evidence and still make a claim that is too strong. We study a narrower decision problem: given a claim, its evidence, its current status, and a requested status change, should that change be allowed under a fixed policy? We introduce ClaimPromoteBench, a controlled benchmark with 200 pairs over 20 policy factors, including a preregistered 150-pair hidden test. Numerical and formal cases are tied to executable artifacts, and the hidden set and exact prompts were committed before scored inference. The primary study contains 7,200 hidden decisions from two Qwen3 models, four intervention arms, and three seeds. Of these outputs, 5,327 (73.99%) are FORMAT_ERROR, and all 1,873 parseable raw decisions are ALLOW. To separate interface failure from decision failure, we also run a post-v1 public pilot with identical prompts under free and JSON-schema-constrained decoding. Constraints raise coverage from 75% to 100% for Qwen3-0.6B and from 0% to 95% for Qwen3-1.7B, but all 78 constrained parseable decisions remain ALLOW; raw pair accuracy and flip rate remain zero over 38 complete pairs. A deterministic gate blocks false promotion on covered cases, but it applies the same fixed policy as the benchmark oracle. The evidence therefore supports rule enforcement, not improved model reasoning.
```

Before using this in a web form, confirm that percent signs and monospaced action names render as
plain text rather than LaTeX commands.

## Suggested TL;DR

```text
Schema constraints make two small Qwen3 models return usable decisions, but they still choose ALLOW for every parseable case and never change action across controlled evidence pairs; a deterministic gate enforces the fixed policy but does not improve model reasoning.
```

Alternative shorter version:

```text
Fixing the output format restores coverage, not evidence-sensitive decisions: the tested models still collapse to ALLOW, while a separate deterministic gate only enforces the benchmark policy.
```

## Suggested keywords

```text
AI research agents; AI evaluation; scientific evidence; controlled-pair benchmark; counterfactual evaluation; structured output; abstention; deterministic verification; formal methods; reproducibility
```

## Suggested topic areas

Choose only topics actually offered by the submission system. Likely fits include:

- evaluation and benchmarks;
- language-model agents;
- trustworthy or reliable machine learning;
- reasoning and decision making;
- AI for science;
- formal methods or neuro-symbolic systems, where available.

Do not select an area solely to increase reviewer visibility if the paper does not substantively fit
that area.

## Contribution summary

```text
ClaimPromoteBench evaluates whether typed scientific evidence justifies a requested change in research-claim status under a fixed policy. Its main design choices are four explicit actions (ALLOW, HOLD, DEMOTE, ESCALATE), orthogonal research/computation/formal/review state axes, controlled pairs that change one registered prerequisite, executable numerical and pinned Lean evidence, a committed hidden test, and separate reporting of structured-output coverage, raw model decisions, and deterministic enforcement. The hidden v1 study yields a negative result, and a separately labeled public formatting control shows that restoring output coverage does not restore controlled-pair evidence sensitivity for the two tested small models.
```

## Main empirical findings

Use these values only together with their scope:

- frozen v1 hidden study: 24 runs and 7,200 decisions;
- v1 format errors: 5,327 / 7,200 (73.99%);
- v1 parseable raw decisions: 1,873, all `ALLOW`;
- post-v1 public pilot: 160 decisions, two models, one seed;
- constrained parseable decisions: 78 / 80;
- constrained complete pairs: 38 / 40;
- constrained raw pair accuracy: 0;
- constrained raw flip rate: 0;
- deterministic post-gate correctness is fixed-policy enforcement, not model learning;

## Data and code availability statement

### Anonymous conference version

```text
An anonymized supplementary bundle contains the public controlled benchmark, validation code, compact v1 and v2 result summaries, and public formal artifacts. It excludes the private hidden seed and data, author-identifying public provenance, and author-identifying provenance. Exact public repository and archival identifiers will be released after double-blind review permits disclosure.
```

### Public preprint version

```text
Code, public benchmark data, compact v1 and v2 result summaries, validation workflows, and public formal artifacts are available in the project repository. The private hidden seed is not released. Exact workflow and artifact identities are recorded in the manuscript and repository. A long-term archival identifier will be added only after it exists.
```

Do not insert a DOI, arXiv identifier, or archival URL before it has actually been created and
verified.

## Reproducibility statement

```text
The public benchmark is deterministically rebuildable and checked for schema, oracle, shortcut, metamorphic-invariance, executable-artifact, and pinned-Lean consistency. The v1 hidden set and exact prompts were committed before scored inference. V1 recovery used the original 24 source artifacts without re-querying the models and changed only 27 cross-field-invalid structured outputs to FORMAT_ERROR. The post-v1 public pilot retained raw responses, verified identical prompts across decoding conditions, and was recomputed twice from four immutable source runs with byte-identical aggregate output. Paper-facing values are checked against machine-readable v1 and v2 summaries in CI.
```

## Limitations statement

```text
The model experiments use only Qwen3-0.6B and Qwen3-1.7B Q8_0. The hidden primary benchmark is synthetic and author-constructed, and the post-v1 formatting control uses public data and one seed after the v1 interface limitation was known. The labels follow an author-defined versioned policy rather than independently collected human consensus. The deterministic gate applies the same fixed policy used to define benchmark labels, so its covered correctness is not independent prediction accuracy. Naturalistic external validation is prepared but not yet complete.
```

## AI-use disclosure summary

```text
Generative AI tools assisted literature search, research planning and methodological discussion, early code drafting and debugging, analysis checks and result interpretation, and parts of manuscript drafting and editing. The human author chose the research question, defined the benchmark policy and experimental protocol, made the final study and analysis decisions, checked the quantitative results and references, and is responsible for the manuscript and submission. AI systems are not authors.
```

Use the longer disclosure already present in the manuscript when the venue asks for a detailed
statement.


## Ethics scope

The submission contains no human-subject experiment, human annotation study, or human-review result. Synthetic `review_status` and `INDEPENDENT_REVIEWER` fields are benchmark metadata used to test policy rules; they are not records collected from people. The author must still read and acknowledge the ICLR Code of Ethics in the submission form, but no paper-specific human-subject approval or exemption is claimed.

## OpenReview account-side checklist

- [ ] Profile name matches the legal/public author name.
- [ ] Current affiliation is accurate.
- [ ] Email is verified.
- [ ] Conflicts and institutional domains are accurate.
- [ ] Author list and order are final before the author-list deadline.
- [ ] Title and abstract match the final PDF.
- [ ] Topics match the actual paper.
- [ ] ICLR Code of Ethics acknowledgement is completed; no human-subject study is claimed.
- [ ] Detailed AI-use disclosure is supplied where requested.
- [ ] Anonymous PDF preview contains no author or public provenance leak.
- [ ] Anonymous supplementary ZIP is uploaded rather than linked to the public repository.
- [ ] The server-displayed PDF is downloaded and checked once more before final submission.

## arXiv account-side checklist

- [ ] Author name and affiliation match the public PDF.
- [ ] Title and abstract match the public PDF exactly.
- [ ] Source ZIP is uploaded rather than a TeX-generated PDF alone.
- [ ] The top-level TeX file is detected correctly.
- [ ] Server compilation succeeds without missing files.
- [ ] Server-generated PDF is compared page by page with the locally verified public PDF.
- [ ] Category and any cross-list are chosen based on actual scope.
- [ ] Comments field does not claim conference acceptance or submission status that does not exist.
- [ ] Any endorsement requirement is completed.
- [ ] The final submit action is performed only after metadata and preview review.

## Status language

Before account-side submission, safe wording is:

```text
Technical submission package ready; account-side submission and archival release pending.
```

After arXiv submission but before announcement/identifier issuance, use only the exact status shown
by arXiv. After conference submission, “submitted” is appropriate only when OpenReview displays a
valid submission record. Do not write “accepted,” “published,” or add identifiers before those facts
exist.
