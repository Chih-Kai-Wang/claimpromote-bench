# Writing Style Distillation for ClaimPromoteBench

This document records the writing and presentation rules used for the submission-facing manuscript. It is a **style/methodology distillation**, not a source of scientific claims. The paper must continue to derive quantitative claims from the frozen ClaimPromoteBench artifacts and must not copy phrasing from any reference paper.

## Corpus

The distillation pass sampled recent, high-quality computer-science papers from official proceedings and publication pages, with emphasis on benchmark/evaluation, agent, software-engineering, scientific-agent, and negative-result work. Representative examples include:

- DeepFact (ACL 2026)
- DREAM (ACL 2026)
- AgencyBench (ACL 2026)
- AgentGym2 (ACL 2026)
- HSCodeComp (ACL 2026)
- BrowseComp-Plus (ACL 2026)
- PaperMind (Findings ACL 2026)
- When Benchmarks Age (EACL 2026)
- Mr Dre / multi-turn report revision evaluation (ACL 2026)
- AnalystBench (Findings ACL 2026)
- Survey on Evaluation of LLM-based Agents (Findings ACL 2026)
- SWE-bench Goes Live (NeurIPS 2025 Datasets and Benchmarks)
- SWE-rebench (NeurIPS 2025 Datasets and Benchmarks)
- SWE-smith (NeurIPS 2025 Datasets and Benchmarks)
- AlgoTune (NeurIPS 2025 Datasets and Benchmarks)
- Reliable and Efficient Amortized Model-based Evaluation (ICML 2025)
- tinyBenchmarks (ICML 2024)
- SWE-agent (NeurIPS 2024)
- SWT-Bench (NeurIPS 2024)
- BLADE (Findings EMNLP 2024)
- DSEval / Benchmarking Data Science Agents (ACL 2024)
- MultiAgentBench (ACL 2025)
- CSR-Bench (NAACL 2025)
- LMR-BENCH (EMNLP 2025)
- Benchmarking Agentic Workflow Generation (ICLR 2025)
- IterGen (ICLR 2025)

The corpus intentionally spans venues and subfields so the resulting rules reflect durable CS-paper conventions rather than one paper's voice.

## Distilled rules

### 1. Open with the failure mode, not the project

Strong papers make the reader understand the problem before naming the method. The first paragraph should make the failure concrete and consequential in domain language. Project architecture and implementation details come later.

**Applied rule:** ClaimPromoteBench begins with the distinction between valid evidence and an invalid requested claim-state promotion.

### 2. State the neighboring literature gap in one bounded paragraph

Do not spend the first page surveying the field. Name the closest task families, state what they evaluate, then isolate the missing decision variable.

**Applied rule:** distinguish truth/factuality, reproducibility, scientific-task execution, hypothesis testing, abstention, and evidence-state transition admissibility.

### 3. Introduce one crisp research question

A benchmark paper is easier to remember when the task is expressible in one sentence. Avoid stacking several research questions unless the benchmark genuinely has multiple independent axes.

### 4. Put the empirical answer on page 1

Strong benchmark/evaluation papers increasingly reveal the dominant result in the Introduction rather than hiding it in Results. This is especially important for negative findings.

**Applied rule:** report the 73.99% format-error rate, the all-ALLOW raw-intent collapse, and the conditional nature of gate enforcement in the Introduction.

### 5. Make contributions orthogonal

Contribution bullets should not repeat the same idea at different levels. A strong set typically separates: task/benchmark definition, construction or artifact contribution, evaluation methodology, and empirical finding.

### 6. Separate capability, coverage, and enforcement

Evaluation papers often become misleading when one aggregate metric conflates whether a model produced an evaluable output, whether its decision was correct, and whether a downstream system corrected it.

**Applied rule:** ClaimPromoteBench treats these as separate layers:

1. structured-output coverage;
2. raw model transition intent;
3. effective post-gate action.

No conditional safety metric should be reported without coverage.

### 7. Lead Results with 2--4 headline findings

Readers should know the hierarchy of findings before reading tables. Each headline should be a claim that a table or figure directly supports. Avoid chronological "we first ran... then..." narration.

### 8. Give every table one semantic job

Do not mix raw and effective actions in the same column without an explicit visual distinction. Prefer one table for raw model behavior and one for enforcement behavior. Captions should state conditioning and denominator assumptions.

### 9. Treat negative results as findings, not apologies

High-quality negative-result writing states exactly what failed, quantifies the failure, and explains what remains learnable. Avoid defensive language and avoid converting a system-level mitigation into a model-capability claim.

### 10. Use short interpretation paragraphs after quantitative blocks

After a table, state the single interpretation the reader should retain. Do not restate every number. The interpretation must remain no stronger than the table supports.

### 11. Distinguish "establishes" from "does not establish"

For governance/safety/evaluation papers, this is a high-value reviewer aid. It prevents downstream overclaiming and makes limitations part of the argument rather than a compliance appendix.

### 12. Group limitations by threat type

Use categories such as external validity, measurement, causal interpretation/infrastructure, and benchmark construction/external audit. This is clearer than an unstructured list of caveats.

### 13. Keep reproducibility prose compact; put hashes in artifacts

The paper should identify the frozen source and provenance mechanism, but full machine identifiers belong in the repository/provenance bundle unless a full value is necessary to establish identity. Long hashes reduce readability and create layout risk.

### 14. Use calibrated verbs

Preferred: `shows`, `finds`, `measures`, `supports`, `establishes under the frozen protocol`, `is consistent with`, `demonstrates a conditional enforcement property`.

Avoid unless literally justified: `solves`, `proves` (for empirical claims), `guarantees` (outside deterministic formal scope), `first`, `unprecedented`, `state of the art`, `human-level`, `safe`.

### 15. Make the conclusion narrower than the abstract

The conclusion should recover the design lesson, not introduce new evidence or repeat the full paper. It should explicitly preserve the boundary between model behavior and system enforcement.

## ClaimPromoteBench-specific style constraints

- Never describe gate catches as improved model reasoning or calibration.
- Never treat `FORMAT_ERROR` as an implicit HOLD.
- Never report effective FPR without nearby decision coverage.
- Never claim theorem truth or scientific truth is evaluated.
- Never imply the two-reviewer audit validates the oracle as a human gold standard.
- Never conceal Python patch-version drift or silently regroup frozen matched identities.
- Never claim the v1 study generalizes to larger/API-hosted systems.
- Never rewrite or rerun frozen v1 inference to improve presentation after unblinding.
- Any post-v1 replication must be labeled supplementary/new study.

## Submission-facing structure target

1. Abstract: problem -> benchmark -> freeze/artifacts -> dominant raw result -> gate result + coverage -> implication.
2. Introduction: concrete failure -> neighboring gap -> one research question -> benchmark mechanism -> page-1 result -> four orthogonal contributions.
3. Related Work: only closest task families; end each paragraph with the distinction.
4. Task/Construction/Protocol: define what is frozen, what changes, and what is measured.
5. Results: headline findings -> raw behavior -> enforcement -> identity limitation -> human audit.
6. Discussion: what v1 establishes -> what it does not -> design implication.
7. Limitations: grouped threats, no boilerplate.
8. Reproducibility/AI disclosure: concise and auditable.
9. Conclusion: one bounded design lesson.
