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
- `policy conditioned agent benchmark active policy switch`;
- `business rule flow benchmark language model`;
- `policy document internalization LLM agent benchmark`.
- `organization-specific policy alignment benchmark allowlist denylist`;
- `regression testing evolving LLM APIs policy update`.
- `behavioral specification agent test compilation policy evolution mutation testing`;
- `natural-language governance policy to executable tests`.

The refresh identified closer conceptual neighbors than the earlier survey: SeekBench, Omni-Decision,
EviGraph, the contemporaneous ClaimLedger technical report, and three 2026 policy-reasoning
benchmarks. Their existence materially narrows the novelty language. ClaimPromoteBench should
**not** claim to have invented evidence-state maintenance, claim ledgers, policy reasoning, or
verifier-governed updates.

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
| RuLES (2024 preprint) | Programmatically checked conversational rule following under ordinary and adversarial interactions | Executable checks are close prior art; the target is conversational rule violation, not matched evidence and active-policy mutations over typed state transitions |
| Inverse IFEval (ICLR 2026) | Following counter-intuitive instructions that conflict with learned response conventions | Tests instruction adaptability, not whether identical evidence produces the transition prescribed by a switched executable policy |
| Policy Compliance of User Requests (ACL Industry 2026) | Classification of natural-language user requests against organizational policies | Policy compliance classification, not relational state-transition conformance with item, pair, and route-failure accounting |
| COMPASS (ACL 2026) | Base and adversarial queries for organization-specific allow and deny lists, evaluated with an LLM judge | Organization-policy alignment is close prior art; ClaimPromoteBench instead uses the same typed state under two executable profiles, exact oracle scoring, and pair-level failure accounting |
| (Why) Is My Prompt Getting Worse? (CAIN 2024) | Regression testing for behavioral changes across evolving hosted LLM APIs | Changes the model-service dependency while preserving an application task; ClaimPromoteBench changes the application policy while holding the tested route and typed context fixed |
| Executable Governance / Policy-to-Tests (AAAI 2026 AI Governance Workshop) | Translates natural-language governance documents into normalized executable rules and tests downstream safeguards | Starts before ClaimPromoteBench's boundary; ClaimPromoteBench assumes two executable policies and tests whether one unchanged decision route follows their behavioral difference |
| TDAD (2026 preprint) | Generates agent tests, optimizes prompts, and studies specification evolution, hidden tests, and semantic mutation testing | Close release-testing prior art; ClaimPromoteBench does no prompt optimization, exhaustively differences two executable policies over a finite grammar, scores paired executions exactly, and separates changed-rule from reachable action-edge adequacy |
| Testing Software Design Modeled by Finite-State Machines (IEEE TSE 1978) | Specification-derived finite-state test sequences and test covers | Transition coverage is established prior art; ClaimPromoteBench instead covers ordered oracle-action changes induced by switching policy on an otherwise identical context |
| PolicyLLM / PolicyBench (ACL Findings 2026) | Bilingual public-policy memorization, understanding, and application over 21K cases | Broad policy comprehension, not matched evidence and policy interventions with an executable transition oracle |
| Analyzing and Internalizing Complex Policy Documents for LLM Agents (ACL 2026) | A controllable-complexity generator and methods for internalizing in-context business policies | Policy complexity and internalization, not whether the same evidence induces the prescribed action after only the active policy changes |
| Business as Rulesual / BREX (ACL 2026) | Extraction of rules, operators, and dependencies from real business documents | Rule-flow reconstruction from unstructured text, not conformance of a structured decision route to an already published executable policy |
| OSVBench (AAAI 2026) | Formal specification generation for operating-system verification | Specification synthesis, not whether heterogeneous evidence licenses a state change |
| SeekBench (2025 preprint) | Grounding, recovery, and readiness/calibration as evidence quality changes during information seeking | Evidence sufficiency affects answer readiness, but the benchmark target is not a four-way research-claim state-transition oracle |
| Omni-Decision (2026 preprint) | Progressive query-scoped evidence state with deterministic updates for multimodal QA | Explicit evidence-state maintenance is prior art; ClaimPromoteBench instead evaluates admissibility under a frozen research-transition policy |
| EviGraph (2026 preprint) | Typed claim–evidence graph for autonomous research, including detecting and repairing weak evidence chains | Evidence graph maintenance and research production, not controlled-pair evaluation of one policy prerequisite at a time |
| ClaimLedger (2026 technical report) | Generator-proposed claim-state changes checked by deterministic evidence-bound verification | Very close architectural prior art for verifier-governed maintenance; ClaimPromoteBench's contribution is the benchmark/protocol rather than the ledger architecture itself |

## Defensible contribution claim

The defensible claim is deliberately narrower:

> **ClaimPromoteBench compiles executable policy differences into failure-aware, controlled-pair
> regression tests for model-mediated state-transition routes.**

Its distinctive evaluation choices are the combination of:

1. an explicit four-action oracle (`ALLOW`, `HOLD`, `DEMOTE`, `ESCALATE`);
2. evidence-contrast pairs that hold policy and requested transition fixed while changing one
   registered prerequisite;
3. policy-contrast pairs that hold evidence, state, artifact, and request fixed while changing only
   the published active policy profile;
4. the same protocol exercised over authored research-evidence and software-artifact-admission
   ontologies;
5. item, pair, action, coverage, and conditional metrics that keep every scheduled route or output
   failure in the end-to-end denominator;
6. frozen one-call, zero-retry execution with replayable item records and fail-closed artifact
   validation;
7. learned comparators that expose both fixed-policy learnability and the registered
   profile-oblivious shortcut boundary; and
8. a two-coordinate policy-migration adequacy criterion that separates changed-rule coverage from
   reachable oracle-action edge coverage and records structurally impossible edges; and
9. a release-gate interpretation in which a policy revision regenerates the difference suite,
   while a route revision reruns the same frozen suite, separating coverage, output validity, and
   action-conformance failures; and
10. an executable edge-local stale-policy audit showing that rule-complete coverage detects 6/10
    registered migration mutants while graph-complete coverage detects 10/10. The mutant family
    operationalizes the adequacy definition; it is not a claimed distribution of production bugs;
    and
11. a provably minimum joint-adequacy smoke suite: ten pairs cover all ten reachable edges and all
    12 changed rules, reducing the structural route gate from 120 to 20 calls. The balanced 60-pair
    suite remains necessary for repeated-context diagnostics; and
12. a domain-independent compiler interface that accepts two deterministic policies and a finite
    context grammar, with an independent cross-check that reconstructs the frozen 10-pair witness.

This is not a truth benchmark. A transition can be admissible under the public policy while the underlying research claim remains scientifically wrong, unimportant, or semantically misstated; conversely, a true claim may correctly remain unpromoted because required evidence is absent.

## Priority language

Do **not** use “first benchmark,” “first system,” “first claim ledger,” “solves scientific verification,” or wording that collapses transition admissibility into claim truth.

Safe language for the current manuscript is:

> Existing work studies policy comprehension, rule extraction, claim verification, abstention, and
> verifier-governed workflows. ClaimPromoteBench evaluates a narrower boundary: whether a
> model-mediated route emits the action prescribed by a published transition policy. Matched pairs
> isolate changes in either one evidence prerequisite or the active policy itself, while end-to-end
> scoring retains all scheduled service and output failures.

The impact claim should remain operational rather than population-level: the protocol supplies a
replayable release gate for versioned executable policies and model-service routes. The present
synthetic studies do not establish natural policy prevalence, deployment safety, or transfer to
unseen policy domains.

## Remaining citation gate

Before an archival submission, re-check every bibliography record against its authoritative publication record and refresh this search if a material interval has passed or new adjacent work appears. The ClaimLedger entry should remain explicitly labeled a contemporaneous technical report unless an archival or citable repository record becomes available.
