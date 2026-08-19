# ICLR 2027 reviewer-level risk audit

Date: 2026-08-20

This is an internal pre-submission audit. It uses the ICLR 2027 reviewer questions as an adversarial checklist rather than as a prediction of acceptance.

## 1. What specific question does the paper tackle?

**Current answer:** whether a registered body of scientific evidence licenses a requested research claim-state transition under a frozen, machine-checkable policy.

**Risk:** the manuscript can be mistaken for general theorem verification, scientific fact checking, generic policy compliance, or an end-to-end research-agent benchmark.

**Mitigation now in the manuscript:**

- the title asks whether evidence justifies a claim-state transition;
- the first paragraph gives concrete over-promotion examples;
- one explicit research question anchors the introduction;
- the task-definition section states that the oracle is a transition-policy oracle, not a truth oracle;
- the overview figure separates raw model intent from deterministic enforcement;
- the contribution wording now says `typed scientific evidence`, not generic action policy compliance.

**Residual risk:** the task remains narrow and synthetic. This is intentionally disclosed.

## 2. Is the approach well motivated and placed in the literature?

**Current answer:** related work now distinguishes claim verification, reproducibility, research-agent evaluation, policy-aware action benchmarks, counterfactual evaluation, evidence-state maintenance, abstention, and formal-verification evaluation from scientific claim-state transition admissibility.

**High-priority novelty collision:** SteerBench-Work (August 2026) is methodologically close. It evaluates proceed/hold decisions at workplace action boundaries and includes evidence-reversed incident mirrors. ST-WebAgentBench (ICLR 2026) already evaluates task completion under explicit policies. CofCA (ICLR 2025) establishes counterfactual evidence manipulation as evaluation methodology, and MEDSYN (ACL Findings 2026) already uses the phrase `Evidence Sensitivity`.

**Mitigation:**

- the paper directly cites these close neighbors rather than hiding them;
- it does **not** claim invention of counterfactual pairs, evidence reversal, generic policy compliance, evidence sensitivity, claim ledgers, or verifier-governed maintenance;
- the contribution is framed at the level of the scientific epistemic object: a four-action transition over separate research/computation/formal/review state axes with dependency, provenance, scope, staleness, contradiction, and artifact rules;
- executable numerical and Lean evidence bind some policy decisions to inspectable research artifacts;
- raw model decisions and deterministic enforcement remain separate quantities.

**Residual risk:** a reviewer may still consider the benchmark scope incremental. The paper therefore avoids an unqualified `first benchmark` claim and must earn significance through the scientific failure analysis, not priority language.

## 3. Does the evidence support the claims?

### Strongest v1 evidence

- frozen 150-pair / 300-instance hidden test;
- exact hidden/prompt commitment before inference;
- 24-run / 7,200-decision complete matrix;
- artifact-only recovery with no model re-query and exactly 27 semantic-format reclassifications;
- independent recomputation of the recovered study SHA and all headline counts;
- raw and effective behavior reported separately;
- coverage reported beside conditional gate metrics;
- executable exact-rational and Lean artifact checks;
- frozen two-reviewer human audit retained as mixed rather than repaired after unblinding.

### Primary scientific weakness

The two evaluated models are small and structured-output reliability is poor. Across 7,200 hidden decisions, 73.99% are format errors; all 1,873 parseable raw intents are ALLOW. This means v1 alone provides weak evidence about sophisticated policy reasoning or stronger contemporary models.

### Mitigation in the manuscript

The paper no longer presents the study as an arm-ranking success. It treats the result as a frozen negative diagnosis and makes only the narrower claims actually supported:

1. these small models fail to show selective raw intent under the frozen protocol;
2. the implemented deterministic gate enforces the frozen transition policy on covered structured intents;
3. structured decision production and deterministic enforcement must be measured separately.

### Post-v1 follow-up now isolated in Draft PR #20

A separate low-cost study addresses the two clearest v1 measurement confounds without rewriting v1:

- retain complete raw responses;
- classify syntax, schema, and cross-field semantic failures separately;
- compare free generation with llama.cpp schema-constrained output under identical model-facing prompt hashes;
- compute the gate only after generation, so the model is not told that a gate exists;
- make the controlled pair the main analysis unit;
- initially use only the two existing Qwen3 artifacts, 20 public pairs, one seed, and 160 total decisions, with no paid API or paid GPU runner.

No result from this follow-up should enter the paper until its own run artifacts and aggregate are complete. It is post-v1 evidence, never retroactive preregistration.

### Residual risks that cannot be edited away

- no larger/API-hosted model replication in v1;
- synthetic controlled pairs;
- one human reviewer falls below the supplementary 0.80 agreement threshold;
- three Python patch-version identity mismatches split intended matched comparison groups;
- free-form responses for pre-existing v1 parse failures were not preserved.

These are scientific limitations, not wording problems, and remain visible in the paper.

## 4. Does the work contribute sufficient value?

**Potential value:** the benchmark isolates a practical research-governance question that neighboring task-success, claim-verification, and workplace-action benchmarks do not directly measure: whether the evidence actually recorded for a scientific claim licenses a change in that claim's epistemic status. It also provides an auditable pattern for separating model intent from deterministic enforcement.

**Risk:** if read only as `two small models emit invalid JSON`, the contribution is weak. If read only as `a deterministic policy gate follows its own policy`, it is also weak.

**Mitigation:** the paper foregrounds the scientific transition object, controlled prerequisite pairs, explicit evidence scope/provenance/dependencies, executable bindings, prompt freeze, and raw-versus-effective evaluation boundary. The post-v1 study is specifically designed to determine whether the observed failure survives output-interface control.

**Residual acceptance uncertainty:** significance is ultimately a reviewer judgment. No editing, additional CI, or deterministic check can guarantee acceptance.

## Desk-reject / preventable-error audit

- [x] ICLR 2027 official style used by the submission builder.
- [x] Main-text page gate enforced at <= 9 pages.
- [x] Undefined citations/references fail the build.
- [x] Horizontal overflow fails the build.
- [x] Mandatory detailed AI-use statement included in the ICLR wrapper.
- [x] Author name, institution, account identifier, email, and searchable public provenance are removed from the ICLR wrapper.
- [x] ICLR TeX, extracted PDF text, and PDF metadata are scanned for identity leaks.
- [x] arXiv wrapper remains named and preserves exact public source/recovery workflow provenance.
- [x] Manuscript lint rejects stale pre-results language, unsupported absolute novelty claims, broken citation keys, broken labels/refs, loss of frozen headline numbers, and accidental re-mixing of raw and effective table semantics.
- [x] Latest Related Work explicitly covers the closest 2025--2026 action-boundary, counterfactual, and evidence-sensitivity neighbors.
- [ ] Final rendered PDF visual audit must be repeated on the latest anonymized build after the new citations and figure.
- [ ] Final full repository CI and pinned Lean workflow must be green on the latest substantive manuscript/build commit.
- [ ] Any post-v1 pilot result used in the ICLR paper must carry its own provenance and must not overwrite v1 tables or chronology.

## Submission-account items outside the repository

- OpenReview profile must exist and be current before the ICLR abstract deadline.
- arXiv account / any required endorsement must be handled by the human author.
- OpenReview form metadata, author list/order, topic selections, ethics acknowledgement, and final uploaded-PDF preview require a human account-side check.
