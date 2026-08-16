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
