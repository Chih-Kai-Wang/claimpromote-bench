# Related-work boundary

This is a living comparison, not a claim of exhaustive priority. Publication status is kept explicit so that preprints, technical reports, workshop papers, and archival papers are not conflated.

## Fresh search record

A paper-preparation search was refreshed on **2026-08-23** after the r6 addendum and balanced public challenge had stabilized. Queries included:

- `research claim evidence state transition benchmark agent`;
- `policy governed claim promotion evidence benchmark`;
- `scientific claim status transition AI agent`;
- `research agent evidence ledger benchmark`;
- `claim verification abstention evidence sufficiency agent`;
- `formal proof scientific evidence provenance agent benchmark`;
- `evidence state agent benchmark`;
- `verifier governed claim state research agent`.
- `rule following benchmark explicit policy language model`.

The refresh identified several closer conceptual neighbors than the earlier survey: SeekBench, Omni-Decision, EviGraph, and the contemporaneous ClaimLedger technical report. Their existence materially narrows the novelty language. ClaimPromoteBench should **not** claim to have invented evidence-state maintenance, claim ledgers, or verifier-governed claim updates.

| Work | What it directly evaluates/builds | Boundary with ClaimPromoteBench |
|---|---|---|
| AbstentionBench (2025 preprint; NeurIPS 2025 D&B) | Answer versus abstain across unanswerable QA settings | Static QA abstention, not a typed research-claim transition with explicit evidence prerequisites |
| CLAIM-BENCH (IJCNLP-AACL 2025) | Scientific claim–evidence extraction and validation | Whether evidence supports a claim, not whether the current typed evidence licenses a requested status transition |
| DeepFact (ACL 2026) | Deep-research report factuality with audit-then-score benchmark revision | Claim-level factuality and benchmark adjudication, not a frozen transition-admissibility oracle |
| ClaimDB (ACL 2026) | Fact verification over large structured databases | Evidence-grounded fact verification and abstention, not research evidence-state governance |
| ScienceAgentBench (ICLR 2025) | Executable scientific data-analysis tasks | Task success, not whether an evidence-state promotion is policy-admissible |
| CORE-Bench (TMLR 2025) | Computational reproduction of published work | Reproduction correctness, not transitions across orthogonal evidence states |
| POPPER (ICML 2025) | Sequential falsification with statistical error control | Hypothesis testing, not versioned state-transition governance |
| RuleArena (ACL 2025) | Long-context natural-language rule application in airline, basketball, and tax scenarios | Domain rule-guided answers, not four-way transitions over a typed evidence ledger under a machine-readable policy |
| OSVBench (AAAI 2026) | Formal specification generation for operating-system verification | Specification synthesis, not whether heterogeneous evidence licenses a state change |
| SeekBench (2025 preprint) | Grounding, recovery, and readiness/calibration as evidence quality changes during information seeking | Evidence sufficiency affects answer readiness, but the benchmark target is not a four-way research-claim state-transition oracle |
| Omni-Decision (2026 preprint) | Progressive query-scoped evidence state with deterministic updates for multimodal QA | Explicit evidence-state maintenance is prior art; ClaimPromoteBench instead evaluates admissibility under a frozen research-transition policy |
| EviGraph (2026 preprint) | Typed claim–evidence graph for autonomous research, including detecting and repairing weak evidence chains | Evidence graph maintenance and research production, not controlled-pair evaluation of one policy prerequisite at a time |
| ClaimLedger (2026 technical report) | Generator-proposed claim-state changes checked by deterministic evidence-bound verification | Very close architectural prior art for verifier-governed maintenance; ClaimPromoteBench's contribution is the benchmark/protocol rather than the ledger architecture itself |

## Defensible contribution claim

The defensible claim is deliberately narrower:

> **ClaimPromoteBench turns versioned policy-governed research-claim transition admissibility into a controlled, artifact-bound evaluation problem.**

Its distinctive evaluation choices are the combination of:

1. an explicit four-action oracle (`ALLOW`, `HOLD`, `DEMOTE`, `ESCALATE`);
2. orthogonal evidence-state axes rather than a scalar confidence ladder;
3. controlled pairs that hold the claim and requested transition fixed while perturbing registered policy prerequisites;
4. executable numerical and pinned-formal evidence bindings;
5. raw-intent versus deterministic-enforcement evaluation;
6. preregistered public-dev/private-hidden construction and pre-inference commitment;
7. fail-closed artifact and run validation.

This is not a truth benchmark. A transition can be admissible under the public policy while the underlying research claim remains scientifically wrong, unimportant, or semantically misstated; conversely, a true claim may correctly remain unpromoted because required evidence is absent.

## Priority language

Do **not** use “first benchmark,” “first system,” “first claim ledger,” “solves scientific verification,” or wording that collapses transition admissibility into claim truth.

Safe language for the current manuscript is:

> Existing work studies claim verification, evidence-state maintenance, abstention, reproducibility, and verifier-governed claim workflows. ClaimPromoteBench focuses on a narrower evaluation target: whether a requested research-claim evidence-state transition is admissible under a frozen versioned policy, using matched prerequisite interventions and artifact-bound evidence.

## Remaining citation gate

Before an archival submission, re-check every bibliography record against its authoritative publication record and refresh this search if a material interval has passed or new adjacent work appears. The ClaimLedger entry should remain explicitly labeled a contemporaneous technical report unless an archival or citable repository record becomes available.
