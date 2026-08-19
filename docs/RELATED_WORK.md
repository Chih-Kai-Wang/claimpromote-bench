# Related-work boundary

This is a living comparison, not a claim of exhaustive priority. Publication status is kept explicit so that preprints, technical reports, and archival papers are not treated as the same thing.

## Fresh search record

The search was refreshed again on **2026-08-20** because several unusually close papers appeared in 2026, including one posted only days before this revision. The refresh included searches around:

- evidence-conditioned action boundaries;
- policy-aware agents and state transitions;
- counterfactual or evidence-reversed agent evaluation;
- scientific claim verification and evidence reasoning;
- evidence sensitivity and multi-evidence synthesis;
- research-agent evidence state, claim maintenance, and verifier-governed updates.

The most important conclusion is that ClaimPromoteBench should not claim novelty for counterfactual pairs, evidence reversal, generic policy compliance, evidence-state maintenance, claim ledgers, or the phrase `evidence sensitivity`. The contribution has to be stated at the level of the scientific claim-state decision itself.

## Closest neighbors

| Work | What it directly evaluates/builds | Boundary with ClaimPromoteBench |
|---|---|---|
| SteerBench-Work (2026 preprint) | Proceed/hold steering at workplace action boundaries, with 106 incident-anchored scenarios and evidence-reversed mirrors | Very close methodologically. It evaluates external workplace actions and a two-way proceed/hold decision; ClaimPromoteBench evaluates four-way changes to a scientific claim's epistemic state, with separate research/computation/formal/review axes and evidence dependency/provenance/scope rules |
| ST-WebAgentBench (ICLR 2026) | Enterprise web-agent task completion under explicit safety and trustworthiness policies | General action/task policy compliance rather than whether scientific evidence licenses a change in claim status |
| CofCA (ICLR 2025) | Step-wise counterfactual multi-hop QA that separates contextual reasoning from memorized factual answers | Establishes counterfactual evidence manipulation as prior evaluation methodology; ClaimPromoteBench ties each controlled change to a named transition-policy prerequisite |
| MEDSYN (Findings ACL 2026) | Multi-evidence clinical diagnosis and an `Evidence Sensitivity` analysis of cross-modal evidence use | Establishes the phrase and a neighboring evidence-use metric; ClaimPromoteBench studies policy-governed claim-state transitions rather than diagnosis |
| RECV (Findings ACL 2025) | Deductive and abductive reasoning for evidence-based claim verification, including real-world claims | Claim truth/support reasoning rather than whether already-recorded evidence licenses a requested state transition |
| AbstentionBench (2025 preprint; NeurIPS 2025 D&B) | Answer versus abstain across unanswerable QA settings | Static QA abstention, not a typed research-claim transition with explicit evidence prerequisites |
| CLAIM-BENCH (IJCNLP-AACL 2025) | Scientific claim–evidence extraction and validation | Whether evidence supports a claim, not whether the current typed evidence licenses a requested status transition |
| DeepFact (ACL 2026) | Deep-research report factuality with benchmark revision and auditing | Claim-level factuality and benchmark adjudication, not a frozen transition-admissibility oracle |
| ClaimDB (ACL 2026) | Fact verification over large structured databases | Evidence-grounded fact verification and abstention, not research evidence-state governance |
| ScienceAgentBench (ICLR 2025) | Executable scientific data-analysis tasks | Task success, not whether an evidence-state promotion is policy-admissible |
| CORE-Bench (TMLR 2025) | Computational reproduction of published work | Reproduction correctness, not transitions across orthogonal evidence states |
| POPPER (ICML 2025) | Sequential falsification with statistical error control | Hypothesis testing, not versioned state-transition governance |
| OSVBench (AAAI 2026) | Formal specification generation for operating-system verification | Specification synthesis, not whether heterogeneous evidence licenses a state change |
| SeekBench (ICLR 2026) | Grounding, recovery, and readiness/calibration as evidence quality changes during information seeking | Evidence sufficiency affects answer readiness, but the target is not a four-way research-claim state transition |
| Omni-Decision (2026 preprint) | Progressive query-scoped evidence state with deterministic updates for multimodal QA | Explicit evidence-state maintenance is prior art; ClaimPromoteBench evaluates admissibility under a fixed research-transition policy |
| EviGraph (2026 preprint) | Typed claim–evidence graph for autonomous research, including weak-evidence detection and repair | Evidence graph maintenance and research production, not controlled-pair evaluation of one policy prerequisite at a time |
| ClaimLedger (2026 technical report) | Generator-proposed claim-state changes checked by deterministic evidence-bound verification | Very close architectural prior art; ClaimPromoteBench's contribution is the benchmark and evaluation protocol rather than ledger architecture |

## Defensible contribution claim

The strongest defensible statement is:

> **ClaimPromoteBench evaluates whether typed scientific evidence licenses a requested change in a claim's epistemic state under a fixed policy.**

The distinctive object is the combination of:

1. four actions (`ALLOW`, `HOLD`, `DEMOTE`, `ESCALATE`);
2. separate research, computation, formal-certification, and independent-review state axes;
3. policy rules over dependencies, provenance, scope, staleness, runtime status, contradictions, and artifact identity;
4. controlled pairs in which one registered policy prerequisite changes while the claim and requested transition remain fixed;
5. executable numerical and pinned Lean evidence;
6. separate measurement of the model's raw decision and deterministic post-processing;
7. a committed hidden evaluation with exact prompt identity and preserved run artifacts.

No one component above should be described as independently new. The contribution is the scientific transition-admissibility evaluation target and the way these pieces are assembled to isolate it.

This is not a truth benchmark. A transition can be admissible under the policy while the underlying research claim remains scientifically wrong, unimportant, or poorly stated. Conversely, a true claim may correctly remain unpromoted because the registered evidence is insufficient for the requested state.

## Priority language

Do **not** use:

- `first benchmark`, `first system`, or `first claim ledger`;
- `first evidence-sensitivity benchmark`;
- language claiming that controlled pairs or evidence reversal are new;
- language claiming that policy-compliance evaluation is new;
- wording that collapses transition admissibility into theorem or scientific truth.

Safe wording is:

> Existing work studies claim verification, policy-aware agent actions, counterfactual evidence use, evidence-state maintenance, abstention, reproducibility, and verifier-governed claim workflows. ClaimPromoteBench focuses on a narrower scientific decision: whether the evidence recorded for a research claim is sufficient for a particular change in that claim's epistemic status under a fixed policy.

## Remaining citation gate

Before submission, bibliography entries should be checked against authoritative publication records again, and the search should be refreshed if new work appears before the ICLR deadline. The SteerBench-Work citation is currently a contemporaneous arXiv preprint and should remain labeled as such unless its status changes. ClaimLedger should remain labeled a technical report unless an archival publication appears.
