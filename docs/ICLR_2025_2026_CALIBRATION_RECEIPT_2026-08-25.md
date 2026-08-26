# ICLR 2025--2026 writing and submission calibration receipt

Status: complete
Verified: 2026-08-25
Purpose: editorial and submission-threshold calibration only. This corpus supplies no empirical
evidence for the paper's scientific claims.

## Authoritative venue sources

- [ICLR 2025 proceedings](https://proceedings.iclr.cc/paper_files/paper/2025): 3,703 accepted-paper
  entries in the retrieved index. Snapshot SHA-256:
  `cb577947dc0a1b4519d313eee0b551a17b9882677803a8296f52e5d3de124fac`.
- [ICLR 2026 proceedings](https://proceedings.iclr.cc/paper_files/paper/2026): 5,351 accepted-paper
  entries in the retrieved index. Snapshot SHA-256:
  `0c06df11f39b98f21ec01ad13eef823b2a247101686cf058d53700841f5e0b13`.
- [ICLR 2027 author guide](https://iclr.cc/Conferences/2027/AuthorGuidelines): nine main-text
  pages at submission; references and appendices are excluded; AI-use and reproducibility
  statements are outside the main-text limit.
- [ICLR 2027 reviewer guide](https://iclr.cc/Conferences/2027/ReviewerGuidelines): calibration axes
  are a specific problem, literature-grounded motivation, support for the claims, and significance.
  State-of-the-art performance is not required.
- [ICLR 2026 review retrospective](https://blog.iclr.cc/2026/03/31/a-retrospective-on-the-iclr-2026-review-process/):
  5,355 acceptances among 19,525 valid submissions; 13,763 papers received a decision.

The proceedings index and retrospective report published-paper and acceptance counts that differ by
four. This receipt records both source-defined populations and does not substitute one denominator
for the other.

The two proceedings indexes contain 9,054 titles in total. A title-level screen covered benchmark,
agent, evaluation, policy/rule, reliability/failure, and software/code strata. Twelve accepted papers
per year were then selected for full-text calibration. The selection is topical and purposive; it is
not a random sample or an acceptance predictor. The 24 PDFs contain 897 pages. The TSV selection
record has SHA-256 `9d07fb0d0718d1f10486dd0751b310d14b7829188a251fcdb2dd28b9ff63e101`.

## Full-text calibration set

| Year | Accepted paper | Proceedings ID | Pages |
|---|---|---:|---:|
| 2025 | AndroidWorld: A Dynamic Benchmarking Environment for Autonomous Agents | 01a83bc2f2732a58e6aa731e659e7101 | 36 |
| 2025 | SWE-bench Multimodal: Do AI Systems Generalize to Visual Software Domains? | 07d6332ae36730707fddddba736d7b6c | 36 |
| 2025 | InsightBench: Evaluating Business Analytics Agents Through Multi-Step Insight Generation | 0dfe31d6e703e138d46a7d2fced38b7c | 33 |
| 2025 | tau-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains | 1b126cc38b8638e07bef37e7b2bb72bf | 53 |
| 2025 | LiveXiv: A Multi-Modal Live Benchmark Based on arXiv Papers | 1eaa1373fe55b223c2dfe1fd29a277d7 | 33 |
| 2025 | Style Outweighs Substance: Failure Modes of LLM Judges in Alignment Benchmarking | 1eb36d07ebb13be16ddbda679a95018b | 31 |
| 2025 | CertainlyUncertain: A Benchmark and Metric for Multimodal Epistemic and Aleatoric Awareness | 21b5788d81f886ff81671379b4ff9453 | 30 |
| 2025 | TestGenEval: A Real World Unit Test Generation and Test Completion Benchmark | 26ded5c8ee8ec1bc4caced4e1c9b1584 | 53 |
| 2025 | How to Evaluate Reward Models for RLHF | 2e01083b381b4865919b4915ef32e3d2 | 36 |
| 2025 | Cheating Automatic LLM Benchmarks: Null Models Achieve High Win Rates | 9adc8ada9183f4b9a007a02773fd8114 | 34 |
| 2025 | ScienceAgentBench: Toward Rigorous Assessment of Language Agents for Data-Driven Scientific Discovery | f12b4df26344f3be803c06b555252efe | 57 |
| 2025 | How Efficient Is LLM-Generated Code? A Rigorous and High-Standard Benchmark | 06694da057cb15fef11542270a592627 | 29 |
| 2026 | EXP-Bench: Can AI Conduct AI Research Experiments? | c411f5b2d9c55f1685e72db224ad8b0e | 50 |
| 2026 | HeurekaBench: A Benchmarking Framework for AI Co-scientist | 12d25b1673452b017fe9c866d9f494a0 | 33 |
| 2026 | WebDS: An End-to-End Benchmark for Web-based Data Science | 35686e5837762715a9b105c96cba43af | 19 |
| 2026 | Gaia2: Benchmarking LLM Agents on Dynamic and Asynchronous Environments | c26a67e0470774df98c12480ec5d2d7b | 32 |
| 2026 | LogiConBench: Benchmarking Logical Consistencies of LLMs | 01db36a646c07c64dd39a92b4eceb417 | 31 |
| 2026 | OpenEstimate: Evaluating LLMs on Reasoning Under Uncertainty with Real-World Data | 04d39dca309cb02e8d7a8f16b75f41c5 | 19 |
| 2026 | PluriHarms: Benchmarking the Full Spectrum of Human Judgments on AI Harm | 04cea5800f4d71fe0d89d5f64e33408e | 36 |
| 2026 | jqBench: A Benchmark for Reading and Editing JSON from Natural Language and Examples | 0df1f1c4606bfa57108990f3beab56bf | 14 |
| 2026 | DRBench: A Realistic Benchmark for Enterprise Deep Research | 0ba520d93c3df592c83a611961314c98 | 69 |
| 2026 | WideSearch: Benchmarking Agentic Broad Info-Seeking | 1119587863e78451f080da2a768c4935 | 75 |
| 2026 | Characterizing Deep Research: A Benchmark and Formal Definition | 114e1dc345fe31b8b9b0c6f7b55a0644 | 35 |
| 2026 | AgenTracer: Who Is Inducing Failure in LLM Agentic Systems? | 134ed7a477770f227f12450ef0cbb8f4 | 23 |

## Editorial findings applied to the manuscript

The selected abstracts use a compact sequence: concrete problem, unresolved evaluation gap,
artifact or protocol, evaluation scale, numerical result, and bounded implication. Their median is
about 213 words and nine sentences; the median sentence carries about 23 words. These values guide
editing ranges and do not determine paper quality.

The manuscript applies the following constraints:

1. Define one specific object: paired route conformance under a versioned repository policy.
2. State novelty as the missing joint test object and its construction, without self-labels such as
   "novel" or "groundbreaking."
3. Give denominators wherever a score appears and keep terminal failures in end-to-end metrics.
4. Separate source authorship, case authorship, mapping authorship, and model-service behavior.
5. Lead the results with independently authored policy revisions; use synthetic instruments to
   diagnose factors, action support, parsers, and output limits.
6. Restrict comparisons to route stacks when provider, adapter, time, or serving state differs.
7. Place full matrices, repetition details, and proofs in the appendix while keeping the claims and
   decisive numbers in the main text.
8. End each section once its evidentiary function is complete; omit execution chronology and
   reviewer-facing commands from the paper.

The broader writing corpus retained in `PAPER_STYLE_CORPUS_*` adds 70 award-recognized or
genre-aligned computer-science papers (2,438 PDF pages) and supplies sentence-level style ranges.
The final prose audit must report zero configured formulaic-pivot, grandiose, throat-clearing,
signposted-summary, superficial-participle, and vague-importance patterns.

## Bibliographic validity audit

All 66 unique `url` fields in `technical-report/references.bib` were resolved on 2026-08-25. Sixty-one
returned a successful or redirecting HTTP status. Five ACM DOI resolver endpoints returned HTTP 403
to the automated `HEAD` request; each has a syntactically valid DOI and none returned 404. No URL
timed out or failed DNS resolution.

Primary records were also inspected for the literature closest to the paper's claim boundary:

- the MSR 2026 record and arXiv source for repository context-file prevalence;
- arXiv records for Agent READMEs, the AGENTS.md efficiency study, the AGENTBENCH evaluation, and
  the two-agent context-file ablation;
- the ACL Anthology record for evolving-policy moderation and the arXiv records for SpecEval and
  TDAD; and
- official proceedings or publisher records for behavioral testing, contrast sets, conformance,
  structured output, selective prediction, and research-agent benchmarks.

These checks establish that the cited works and bibliographic targets exist. Claims in the related-
work section remain limited to what the corresponding abstracts, papers, or official records state.
