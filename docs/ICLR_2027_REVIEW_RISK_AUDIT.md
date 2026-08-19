# ICLR 2027 reviewer-level risk audit

Date: 2026-08-20

This is an internal pre-submission audit. It uses the ICLR 2027 reviewer questions as an
adversarial checklist rather than as a prediction of acceptance.

## 1. What specific question does the paper tackle?

**Current answer:** whether a registered body of evidence licenses a requested research
claim-state transition under a frozen, machine-checkable policy.

**Risk:** the original manuscript used stacked nouns and could be mistaken for general theorem
verification, scientific fact checking, or an end-to-end research-agent benchmark.

**Mitigation now in the manuscript:**

- the title asks whether evidence licenses a claim-state transition;
- the first paragraph gives three concrete over-promotion examples;
- one explicit research question anchors the introduction;
- the task-definition section states that the oracle is a transition-policy oracle, not a truth
  oracle;
- a compact overview figure separates raw model intent from deterministic enforcement.

**Residual risk:** the task remains narrow and synthetic. This is intentionally disclosed.

## 2. Is the approach well motivated and placed in the literature?

**Current answer:** related work now distinguishes claim verification, reproducibility,
research-agent evaluation, evidence-state maintenance, abstention, and formal-verification
evaluation from transition admissibility.

**Risk:** verifier-governed ledgers and evidence-state maintenance already exist, so claiming
that the underlying architecture itself is novel would be indefensible.

**Mitigation:**

- the manuscript explicitly does **not** claim to invent claim ledgers or verifier-governed
  maintenance;
- the contribution is framed as the controlled-pair, four-action, artifact-bound evaluation of
  transition admissibility with raw intent separated from enforcement;
- recent close neighbors (SeekBench, Omni-Decision, EviGraph, ClaimLedger, DeepFact,
  CLAIM-BENCH, CORE-Bench, ScienceAgentBench, AbstentionBench, OSVBench) are positioned by task
  difference rather than dismissed.

**Residual risk:** a reviewer may still find the benchmark scope incremental. The paper therefore
avoids an unqualified “first benchmark” claim.

## 3. Does the evidence support the claims?

### Strongest evidence

- frozen 150-pair / 300-instance hidden test;
- exact hidden/prompt commitment before inference;
- 24-run / 7,200-decision complete matrix;
- artifact-only recovery with no model re-query and exactly 27 semantic-format
  reclassifications;
- independent recomputation of the recovered study SHA and all headline counts;
- raw and effective behavior reported separately;
- coverage reported beside conditional gate metrics;
- executable exact-rational and Lean artifact checks;
- frozen two-reviewer human audit retained as mixed rather than repaired after unblinding.

### Primary scientific weakness

The two evaluated models are small and structured-output reliability is poor. Across 7,200
hidden decisions, 73.99% are format errors; all 1,873 parseable raw intents are ALLOW. This means
the primary model experiment provides weak evidence about sophisticated policy reasoning.

### Mitigation

The manuscript no longer presents the study as an arm-ranking success. It treats the result as a
frozen negative diagnosis and makes only the narrower claims actually supported:

1. these small models fail to show selective raw intent under the frozen protocol;
2. the implemented deterministic gate enforces the frozen transition policy on covered
   structured intents;
3. structured decision production and deterministic enforcement must be measured separately.

### Residual risks that cannot be edited away

- no larger/API-hosted model replication in v1;
- synthetic controlled pairs;
- one human reviewer falls below the supplementary 0.80 agreement threshold;
- three Python patch-version identity mismatches split intended matched comparison groups;
- free-form responses for pre-existing parse failures were not preserved, preventing post-hoc
  diagnosis without new inference.

These are scientific limitations, not wording problems, and remain visible in the paper.

## 4. Does the work contribute sufficient value?

**Potential value:** the benchmark turns a practical research-governance failure into an explicit
counterfactual decision task and provides a reproducibility pattern for separating model intent
from deterministic enforcement. The negative result also demonstrates why effective safety rates
without coverage can be misleading.

**Risk:** if read only as “two small models emit invalid JSON,” the contribution is weak.

**Mitigation:** the paper foregrounds the benchmark design, controlled policy-sensitive pairs,
artifact binding, prompt freeze, and raw-versus-effective evaluation boundary before interpreting
the small-model study.

**Residual acceptance uncertainty:** significance is ultimately a reviewer judgment. No editing or
CI system can guarantee acceptance.

## Desk-reject / preventable-error audit

- [x] ICLR 2027 official style used by the submission builder.
- [x] Main-text page gate enforced at <= 9 pages.
- [x] Undefined citations/references fail the build.
- [x] Horizontal overflow fails the build.
- [x] Mandatory detailed AI-use statement included in the ICLR wrapper.
- [x] Author name, institution, account identifier, email, and searchable public provenance are
      removed from the ICLR wrapper.
- [x] ICLR TeX, extracted PDF text, and PDF metadata are scanned for identity leaks.
- [x] arXiv wrapper remains named and preserves exact public source/recovery workflow provenance.
- [x] Manuscript lint rejects stale pre-results language, unsupported absolute novelty claims,
      broken citation keys, broken labels/refs, loss of frozen headline numbers, and accidental
      re-mixing of raw and effective table semantics.
- [ ] Final rendered PDF visual audit must be repeated on the latest anonymized build.
- [ ] Final full repository CI and pinned Lean workflow must be green on the latest substantive
      manuscript/build commit.

## Submission-account items outside the repository

- OpenReview profile must exist and be current before the ICLR abstract deadline.
- arXiv account / any required endorsement must be handled by the human author.
- OpenReview form metadata, author list/order, topic selections, ethics acknowledgement, and final
  uploaded-PDF preview require a human account-side check.
