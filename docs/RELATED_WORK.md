# Related-work boundary

This is a living comparison, not a claim of exhaustive priority. Publication status is kept
explicit so that preprints and workshop papers are not presented as archival results.

| Work | What it directly evaluates | Boundary with ClaimPromoteBench |
|---|---|---|
| [AbstentionBench (ICML 2025)](https://arxiv.org/abs/2506.09038) | Answer versus abstain across unanswerable QA settings | Static QA abstention, not a typed research-claim transition |
| [AgentAbstain (2026 preprint)](https://arxiv.org/abs/2607.10059) | Act/abstain under tool and environment failures | General agent action, not policy prerequisites for evidentiary state |
| [Answer Only as Precisely as Justified (2026 preprint)](https://arxiv.org/abs/2604.17487) | Claim-level specificity, omission, and calibrated selection | Post-hoc support granularity, not sequential status transitions |
| [Propose, Critique, Falsify (ICML 2026 AI4Science workshop)](https://openreview.net/forum?id=RyX98G24rP) | Valid/invalid/uncertain scientific claim verification | Claim verification and FDR, not a versioned transition oracle |
| [ScienceAgentBench (ICLR 2025)](https://proceedings.iclr.cc/paper_files/paper/2025/hash/f12b4df26344f3be803c06b555252efe-Abstract-Conference.html) | Executable scientific data-analysis tasks | Task success, not whether the report over-promotes evidence |
| [CORE-Bench (TMLR 2025)](https://openreview.net/forum?id=BsMMc4MEGS) | Computational reproduction of published work | Reproduction correctness, not evidence-state governance |
| [POPPER (ICML 2025)](https://proceedings.mlr.press/v267/huang25n.html) | Sequential falsification with statistical error control | Hypothesis testing, not transitions across orthogonal evidence types |
| [NIST evaluation probes project (2026)](https://www.nist.gov/programs-projects/building-evaluation-probes-agentic-ai) | Deep-research audit trails and sufficiency probes | Structured audit is prior art; this benchmark isolates deterministic transition admissibility |
| [LeanDojo (NeurIPS 2023)](https://papers.neurips.cc/paper_files/paper/2023/file/4441469427094f8873d0fecb0c4e1cee-Paper-Datasets_and_Benchmarks.pdf) | Kernel-checked Lean theorem proving | Exact formal acceptance does not establish natural-language alignment or independent review |

## Defensible working claim

ClaimPromoteBench isolates a narrower failure mode than answer abstention or static claim
verification: whether a research agent requests a policy-invalid transition in a claim's
evidentiary state. Controlled, machine-checkable pairs separate over-promotion from universal
holding, while raw and post-gate records separate agent intent from system enforcement.

Until a preregistered search is refreshed immediately before submission, the repository uses
the cautious formulation: **we did not find a public benchmark directly evaluating
policy-governed research-claim state transitions**. It does not use “first benchmark.”

