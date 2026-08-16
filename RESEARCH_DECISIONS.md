# Research decisions

This log records decisions that materially affect the benchmark claim. Changes to a frozen
policy, dataset, prompt, model artifact, or seed require a new version and an explicit entry.

## 2026-08-13 — Evaluate transitions, not truth in general

**Decision.** The unit of evaluation is a requested transition in an orthogonal claim state:
research, computation, formal certification, and independent review. The benchmark does not
score general truth classification or answer abstention.

**Reason.** Static claim verification, abstention, and claim-level specificity already have
direct prior work. A narrower transition decision is both testable and aligned with the
existing deterministic evidence infrastructure.

## 2026-08-13 — Separate model intent from enforced outcome

**Decision.** Store the raw agent decision and the post-gate decision separately. A gate may
veto an invalid `ALLOW`; it may never promote a claim on the agent's behalf.

**Rejected alternative.** Reporting only post-gate decisions. That would make a deterministic
veto look like improved model calibration.

## 2026-08-13 — Use controlled pairs and a frozen clock

**Decision.** Alpha consists of 20 counterfactual pairs (40 instances). Each pair changes one
policy-relevant factor. Time-sensitive rules use the manifest's evaluation time, never the
machine clock.

**Limitation.** Three or four pairs per family validate the pipeline; they do not support a
research conclusion.

## 2026-08-13 — Do not fabricate a hidden-test commitment

**Decision.** The 150-pair test commitment remains `PENDING` until those items are frozen.
Alpha publishes no placeholder digest and no model result.

## 2026-08-13 — Keep formal certification below research resolution

**Decision.** Alpha may promote the formal axis only. It rejects any requested transition to
`research_status=RESOLVED`, even when an exact Lean certificate passes.

**Reason.** Kernel acceptance proves a fixed formal target. It does not by itself establish
natural-language alignment, novelty, scope, or independent research review.

## 2026-08-13 — Make interventions self-contained

**Decision.** Every model-facing arm receives the same complete versioned policy, frozen
evaluation time, thresholds, trust anchors, and reason vocabulary. The narrative arm uses
semantic prose rather than JSON-pointer sentences.

**Reason.** A model cannot decide under an unstated policy, and flattening a typed ledger does
not create a meaningful narrative-versus-structure intervention.

## 2026-08-16 — Bind numerical alpha to finite-grid executable evidence

**Decision.** The four `NUMERICAL` controlled pairs now reference four registered
exact-rational finite-grid JSON artifacts. Both members of a pair share identical artifact
bytes. Dataset validation recomputes all eight numerical evidence records; an `ALLOW` member
must additionally match the artifact's protocol, repetitions, preregistration, closed domain,
runtime result, and true predicate.

**Scope correction.** Numerical claim text is limited to the registered rational grid. The
artifact and validator do not establish a continuous-interval result. The other sixteen
pairs retain synthetic artifacts because their present purpose is to exercise dependency,
runtime, staleness, provenance, and formal-identity policy transitions rather than execute
those external systems.

**Controlled-pair rule.** Invalid numerical members still point to a valid recomputable
artifact. Their single declared metadata prerequisite remains intentionally invalid. This
prevents artifact corruption from becoming a second uncontrolled difference.

**Versioning.** This change creates a new immutable alpha dataset revision through the
refreshed manifest digest. No model run or external contribution was accepted against the
superseded revision, so no result migration or pooling is permitted or required.

**Rejected alternatives.** Treating grid evidence as continuous proof, giving the two sides
different artifact bytes, or skipping recomputation for the invalid side would each weaken
the benchmark's scope or counterfactual interpretation.

## 2026-08-16 — Execute formal alpha under a pinned Lean 4 trust base

**Decision.** The three `FORMAL` controlled pairs now reference three generated Lean source
artifacts and policy version `1.0.2-alpha`. The exact `lean-toolchain` bytes pin Lean
`v4.33.0` and are bound by SHA-256. CI builds the Lake package, replays the compiled library
with `leanchecker ClaimPromoteFormal`, and executes one positive and two negative standalone
fixtures.

**Claim alignment.** Generic continuous-domain placeholder text was removed from formal
items. Each natural-language claim now names the exact elementary theorem compiled in its
source: right-zero addition, left-zero addition, or conjunction commutativity. Every source
also embeds the pair ID, claim ID, statement SHA-256, and toolchain-lock SHA-256.

**Controlled-pair rule.** Both members of each formal pair share identical compilable source
bytes. The invalid member changes only its registered statement, claim, or toolchain scope
field. A compiler failure is not introduced as a second difference.

**Trust boundary.** A successful build and checker replay establish kernel acceptance of the
three exact declarations under the pinned toolchain. They do not establish novelty,
publication value, correctness of a broader informal proof, independent human review, or
`research_status=RESOLVED`.

**Versioning.** The prior `1.0.1-alpha` policy remains committed for historical inspection,
but the current alpha manifest binds `1.0.2-alpha`. Results from different dataset or policy
hashes must never be silently pooled.

**Rejected alternatives.** Trusting only a stored `verifier_result: PASS`, making the invalid
side syntactically uncompilable, using a mutable Lean release alias, or treating kernel
acceptance as research resolution would each confound or overstate the benchmark claim.
