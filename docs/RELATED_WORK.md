# Related-work boundary

This is a living comparison, not a claim of exhaustive priority. Publication status is kept
explicit so that preprints and workshop papers are not presented as archival results.

A fresh paper-preparation triage was performed on **2026-08-19**. The defensible contribution
claim remains deliberately narrow: ClaimPromoteBench evaluates whether an agent requests a
**policy-admissible evidence-state transition** for a research claim. It does not claim to be
the first benchmark for scientific claim verification, abstention, agent governance, research
reproducibility, or formal verification.

| Work | What it directly evaluates | Boundary with ClaimPromoteBench |
|---|---|---|
| [AbstentionBench (2025 preprint)](https://arxiv.org/abs/2506.09038) | Answer versus abstain across unanswerable QA settings | Static QA abstention, not a typed research-claim transition with explicit evidence prerequisites |
| [AgentAbstain (2026 preprint)](https://arxiv.org/abs/2607.10059) | Act/abstain under tool and environment failures | General agent action, not policy prerequisites for evidentiary state |
| [Answer Only as Precisely as Justified (2026 preprint)](https://arxiv.org/abs/2604.17487) | Claim-level specificity, omission, and calibrated selection | Post-hoc support granularity, not sequential status transitions |
| [CLAIM-BENCH (IJCNLP-AACL 2025)](https://aclanthology.org/2025.ijcnlp-long.127/) | Scientific claim–evidence extraction and validation | Whether evidence supports a claim, not whether the current typed evidence licenses a requested status transition |
| [DeepFact (ACL 2026)](https://aclanthology.org/2026.acl-long.1586/) | Deep-research report factuality with audit-then-score benchmark revision | Claim-level factuality and benchmark adjudication, not a deterministic transition-admissibility oracle |
| [ClaimDB (ACL 2026)](https://aclanthology.org/2026.acl-long.1589/) | Fact verification over large structured databases | Evidence-grounded fact verification and abstention, not research evidence-state governance |
| [Propose, Critique, Falsify (ICML 2026 AI4Science workshop)](https://openreview.net/forum?id=RyX98G24rP) | Valid/invalid/uncertain scientific claim verification | Claim verification and FDR, not a versioned transition oracle |
| [ScienceAgentBench (ICLR 2025)](https://proceedings.iclr.cc/paper_files/paper/2025/hash/f12b4df26344f3be803c06b555252efe-Abstract-Conference.html) | Executable scientific data-analysis tasks | Task success, not whether the report over-promotes evidence |
| [CORE-Bench (TMLR 2025)](https://openreview.net/forum?id=BsMMc4MEGS) | Computational reproduction of published work | Reproduction correctness, not evidence-state governance |
| [POPPER (ICML 2025)](https://proceedings.mlr.press/v267/huang25n.html) | Sequential falsification with statistical error control | Hypothesis testing, not transitions across orthogonal evidence types |
| [OSVBench (AAAI 2026)](https://ojs.aaai.org/index.php/AAAI/article/view/40437) | Formal specification generation for operating-system verification | Specification synthesis, not whether a heterogeneous research-evidence ledger licenses a state change |
| [NIST evaluation probes project (2026)](https://www.nist.gov/programs-projects/building-evaluation-probes-agentic-ai) | Deep-research audit trails and sufficiency probes | Structured audit is prior art; this benchmark isolates deterministic transition admissibility |
| [LeanDojo (NeurIPS 2023)](https://papers.neurips.cc/paper_files/paper/2023/file/4441469427094f8873d0fecb0c4e1cee-Paper-Datasets_and_Benchmarks.pdf) | Kernel-checked Lean theorem proving | Exact formal acceptance does not establish natural-language alignment or independent review |

## Defensible working claim

ClaimPromoteBench isolates a narrower failure mode than answer abstention, static claim
verification, research-task completion, or proof checking: whether a research agent requests a
policy-invalid transition in a claim's evidentiary state. Controlled, machine-checkable pairs
hold the claim and requested transition fixed while changing a single policy prerequisite.
Raw and post-gate records then separate agent intent from deterministic system enforcement.

This is not a truth benchmark. A transition can be admissible under the public policy while the
underlying research claim remains scientifically wrong, unimportant, or semantically
misstated; conversely, a true claim may correctly remain unpromoted because required evidence
is absent.

## Priority language

Until a systematic search is refreshed immediately before submission, use the cautious
formulation:

> **We did not find a public benchmark directly evaluating policy-governed research-claim
> evidence-state transitions under matched, machine-checkable prerequisites.**

Do **not** use “first benchmark,” “first system,” “solves scientific verification,” or any
wording that collapses transition admissibility into claim truth.

## Pre-submission search requirement

Immediately before a preprint or venue submission, rerun searches covering at least:

- `research claim evidence state transition benchmark agent`;
- `policy governed claim promotion evidence benchmark`;
- `scientific claim status transition AI agent`;
- `research agent evidence ledger benchmark`;
- `claim verification abstention evidence sufficiency agent`;
- `formal proof scientific evidence provenance agent benchmark`.

Record the search date and any newly adjacent work. A new paper should update positioning even
when it does not invalidate the contribution.
