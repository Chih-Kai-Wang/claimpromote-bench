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

## 2026-08-16 — Separate active blind review from published unblinded evidence

**Decision.** Independent annotation review uses a private working package containing a
public reviewer packet, an immutable packet manifest, and a secret HMAC mapping. The packet
removes item ID, pair ID, split, family, and gold fields. Review IDs and ordering are derived
from a random 32-byte secret. Reviewers receive neither the private mapping nor gold, pair
descriptors, model outputs, aggregate results, or another reviewer's submission.

**Submission discipline.** Reviewer drafts contain no default action or confidence and begin
with every independence attestation set to false. Completed submissions must cover every
blinded item exactly once, use only the bound policy vocabulary, obey action/reason
constraints, and affirm independent work without gold, model output, or collaboration.
Missing judgments are never interpreted as `HOLD`.

**Release boundary.** Active packages remain outside the public repository. After every
reviewer has submitted and judgments are frozen, the packet, mapping, submissions, agreement
report, and adjudication record may be published together as an immutable package under
`reviews/`. An empty review root remains `PENDING`; it is not a passing external-review gate.

**Contamination limitation.** Because alpha inputs and gold are already public, alpha review
is procedurally blinded and depends on explicit reviewer attestations. It is not equivalent
to a contamination-resistant hidden review set. The future hidden set must be packetized
before its labels become public.

**Versioning.** Adding the review schemas changes the manifest-bound public contract but does
not alter the 40 item payloads or their gold decisions. No real review submission, agreement
result, or external reviewer is claimed by this infrastructure change.

**Rejected alternatives.** Publishing the mapping during active review, exposing family or
pair membership, pre-filling `HOLD`, accepting partial submissions, or counting repository
maintainer judgments as external review would each bias or overstate the review evidence.

## 2026-08-16 — Gate review on the weakest reviewer and weakest reviewer pair

**Decision.** The external annotation gate requires at least two reviewers, every reviewer to
reach at least 0.80 action agreement with frozen gold, and the minimum raw action agreement
across every reviewer pair to reach at least 0.80. The gate does not use the average reviewer
score or average pairwise agreement.

**Reason.** An average can conceal one reviewer who did not understand the policy or one pair
whose interpretations diverge materially. The weakest-reviewer rule is more conservative and
makes the gate's meaning easier to audit.

**Secondary statistics.** The report also computes action confusion matrices, exact
reason-set agreement, reason-set Jaccard similarity, Cohen kappa for every reviewer pair,
unanimous-action rate, and Fleiss kappa. Kappa is diagnostic rather than decisive because
class imbalance or degenerate marginals can make it unstable or undefined.

**Disagreement scope.** An item enters adjudication when any reviewer differs from gold on
action or reason set, or when reviewers differ from each other on action or reason set. Each
such item receives a deterministic disagreement ID bound to the packet and blinded item ID.

**Adjudication rule.** Every disagreement must be marked exactly once as `KEEP_GOLD`,
`REVISE_ITEM`, `REVISE_POLICY`, or `UNRESOLVED`. `KEEP_GOLD` must reproduce the exact frozen
gold action and reason list. A failed numeric threshold cannot be repaired by adjudication;
it requires revision and a fresh blind review.

**Negative-result preservation.** `REVISION_REQUIRED` is a valid scientific result. Published
negative review outcomes must remain reproducible and visible. CI therefore rejects missing,
stale, tampered, incomplete, or non-recomputable packages, but does not reject a package
merely because reviewers failed to support the current version.

**Versioning.** The analysis and adjudication schemas become part of the alpha manifest-bound
public contract. No empirical agreement value is added until real independent submissions
are published.

**Rejected alternatives.** Gating only on average agreement, treating kappa as the sole
criterion, ignoring reason-code disagreements, allowing partial adjudication, or suppressing
a failed review package would each overstate reliability or weaken auditability.

## 2026-08-16 — Register metamorphic equivalence rather than assume it

**Decision.** The alpha now has an explicit model-free metamorphic audit. Registered
transformations cover recursive JSON object-key reordering, consistent evidence-ID renaming,
consistent principal and environment renaming, provenance run-ID renaming, evidence-array
reversal, unrelated passing evidence, unrelated stale failed evidence, and a resolved
contradiction. Every applicable variant must pass the public input schema, artifact checks,
type-specific numerical or Lean binding, complete oracle evaluation, and all four prompt
renderers.

**Decision comparison.** Evidence identifiers are mapped back to the original namespace
before comparison. Evidence-ID collections in oracle output are canonicalized as sorted sets,
because a semantics-preserving rename can change lexicographic traversal order without
changing dependency-closure membership. Action, proposed state, probability, reason codes,
and all non-ID fields must remain exactly equal.

**Prompt boundary.** Recursive JSON object-key reordering must leave every rendered prompt
byte-identical. Transformations that alter model-visible identifiers, evidence order, or
records must change at least one prompt while preserving the normalized oracle decision. This
separates deterministic pipeline invariance from future model consistency measurement.

**Closure boundary.** A fresh unrelated artifact, a stale failed unrelated artifact, and a
resolved contradiction are intentionally inert. A failure outside the requested transition's
dependency closure must not invalidate the selected basis, while only a valid open
contradiction may escalate.

**Observed deterministic result.** The current 40-item alpha produces 331 applicable variants
and 1,324 prompt renderings. Every variant passed schema validation, artifact binding, and
normalized oracle equality with zero failures. This is a result about the registered
deterministic transformations only; it is not evidence that a language model is invariant.

**Versioning.** The invariance-report schema becomes part of the manifest-bound public
contract. The underlying 40 item payloads and gold decisions are unchanged. Future additions
or changes to the transformation registry require a new report identity and explicit
research-decision entry.

**Rejected alternatives.** Assuming identifier or ordering invariance without testing it,
comparing renamed IDs literally, treating irrelevant evidence failures as basis failures, or
reporting deterministic oracle invariance as model robustness would each weaken or overstate
the benchmark claim.
