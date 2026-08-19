# ClaimPromoteBench Submission Risk Audit

This is an adversarial review checklist for the submission-facing v1 paper. It is deliberately stricter than ordinary copy editing. A risk marked **OPEN** is not permission to weaken, rerun, or rewrite the frozen study; it identifies what the manuscript must state clearly or what a future supplementary study would need to address.

## Executive assessment

The paper's strongest defensible contribution is the benchmark/evaluation formulation and the separation of **structured-output coverage -> raw transition intent -> deterministic enforcement**. The v1 model study is a useful stress test and negative result, but it should not be sold as broad evidence about modern frontier research agents.

The paper is most vulnerable to reviewer criticism if it overstates the gate result, treats the frozen policy as human truth, hides the structured-output contract as a measurement confound, generalizes from the two small Qwen3 models, or claims novelty for counterfactual/evidence-reversal techniques that now have clear neighboring precedents.

## Critical reviewer attacks and mitigations

### 1. "The gate result is tautological because the gate and oracle use the same policy"

**Severity:** HIGH  
**Status:** MITIGATED IN MANUSCRIPT

The deterministic gate is not an independently learned predictor. Its perfect covered catch/false-block behavior is expected when it faithfully enforces the same frozen transition policy used to define admissibility. The paper must therefore describe this as an **enforcement/implementation property**, not an empirical discovery of model capability or a general safety guarantee.

The scientifically interesting comparison is the decomposition: raw model intent collapses to ALLOW, while a deterministic policy layer can prevent invalid effective transitions wherever a parseable intent reaches it.

### 2. "Only two tiny open-weight models are tested"

**Severity:** HIGH  
**Status:** OPEN / EXPLICIT LIMITATION

Qwen3-0.6B and Qwen3-1.7B cannot support claims about frontier or API-hosted systems. The manuscript explicitly scopes the result to the frozen small-model protocol. A stronger post-v1 paper would benefit from a clearly labeled supplementary replication on larger/stronger models, but that study must not replace or mutate frozen v1 after unblinding.

### 3. "The 73.99% FORMAT_ERROR rate may measure interface compatibility more than policy reasoning"

**Severity:** HIGH  
**Status:** MITIGATED, CAUSE NOT RECOVERABLE

This is a real measurement threat. v1 source records retain parse status and structured decisions but not the original free-form text for pre-existing parse failures, so the linguistic causes cannot be reconstructed without new inference. The paper therefore treats structured-output reliability as a separate failure layer and does not attribute all FORMAT_ERROR to reasoning failure.

A future replication should retain raw text and distinguish syntax/schema/cross-field semantic failure categories from policy-decision errors.

### 4. "The human audit is mixed; why trust the oracle?"

**Severity:** HIGH  
**Status:** MITIGATED BY SCOPE

The deterministic oracle is normative **by benchmark definition**: it applies a frozen public transition policy to registered evidence. The two-reviewer audit is supplementary evidence about human policy application, not a proof that the oracle is a human ground-truth ceiling. The manuscript preserves the mixed result and does not revise labels after seeing reviewer disagreement.

### 5. "The benchmark is synthetic and author-constructed"

**Severity:** MEDIUM-HIGH  
**Status:** OPEN / EXPLICIT LIMITATION

Controlled pairs provide counterfactual control but reduce ecological validity. Deterministic regeneration, hidden commitment, executable artifacts, shortcut audits, metamorphic checks, and external procedural review reduce post-hoc flexibility; they do not create independent authorship or real-world representativeness.

### 6. "Conditional FPR=0 hides missing decisions"

**Severity:** HIGH  
**Status:** MITIGATED

Every effective safety rate must be presented together with decision coverage. FORMAT_ERROR is never converted to HOLD. For PTA and pairwise quantities, complete-pair coverage must also remain visible in artifact outputs and supplementary reporting.

### 7. "Why are the preregistered matched comparisons incomplete?"

**Severity:** MEDIUM  
**Status:** MITIGATED / PRESERVED

Three jobs recorded Python 3.11.16 instead of 3.11.15. Exact hardware identity was preregistered as part of grouping, so three intended model×seed matched groups split. The official analysis does not regroup after unblinding. Missing comparisons are reported as infrastructure drift rather than silently repaired.

### 8. "The gate-arm prompt changes model behavior before enforcement"

**Severity:** MEDIUM  
**Status:** MITIGATED

The gate is disclosed in the gate-arm prompt, so passive-verifier vs gate raw-intent differences cannot be interpreted as pure post-processing effects. The within-gate raw-versus-effective comparison isolates the deterministic enforcement step.

### 9. "Novelty is close to evidence ledgers / verifier-governed research agents"

**Severity:** HIGH  
**Status:** MITIGATED BY NARROW CLAIM

The paper must not claim invention of claim ledgers, evidence-state maintenance, or verifier-governed research agents. The defensible novelty is the controlled-pair, four-action, policy-governed **scientific transition-admissibility evaluation target**, with prompt/hidden commitment, executable evidence bindings, and explicit raw-intent vs enforcement separation.

### 10. "SteerBench-Work and policy-agent benchmarks already test evidence-conditioned action boundaries"

**Severity:** HIGH  
**Status:** MITIGATED BY UPDATED RELATED WORK / MUST MONITOR

SteerBench-Work is a contemporaneous and unusually close neighbor: it evaluates proceed/hold decisions at workplace action boundaries and includes evidence-reversed mirrors. ST-WebAgentBench evaluates policy compliance during enterprise web-agent tasks. Counterfactual evaluation itself is also established by work such as CofCA, while MEDSYN already uses the term `Evidence Sensitivity` for clinical evidence use.

Therefore, do **not** claim any of the following as unique to ClaimPromoteBench:

- using counterfactual or evidence-reversed examples;
- testing whether an action should proceed under evidence and policy;
- the general phrase `evidence sensitivity`;
- policy compliance as a benchmark target.

The narrower distinction to defend is the scientific epistemic object: whether typed research evidence licenses a change in a claim-state vector with separate research/computation/formal/review axes, four transition actions, explicit dependency/provenance/scope/staleness rules, and executable numerical/formal bindings. The manuscript must cite the closest action-boundary and counterfactual benchmarks directly rather than relying on a generic novelty statement.

### 11. "Preregistration language may overstate what was registered"

**Severity:** MEDIUM  
**Status:** MONITOR

Use `preregistered` only for quantities/procedures demonstrably frozen in Git before scored inference. Prefer `precommitted`, `frozen before scoring`, or exact commit chronology when discussing engineering identities. Do not imply registration in an external registry unless one exists.

### 12. "Main results omit uncertainty"

**Severity:** MEDIUM  
**Status:** PARTIALLY MITIGATED

The recovered artifact contains 10,000-pair bootstrap intervals. Because all defined raw FPR values equal 1.0, their pair-bootstrap 95% intervals are exactly [1.0, 1.0] under the frozen analysis. The manuscript should note this without pretending the interval resolves the much larger coverage problem. Conditional metrics remain secondary to coverage interpretation.

### 13. "Strong statistical significance may simply reflect format/coverage differences"

**Severity:** MEDIUM  
**Status:** MITIGATED BY NON-EMPHASIS

McNemar/Holm results exist only within exact matched identity groups and can be driven by availability/formatting differences. The main paper should not elevate p-values above the directly interpretable failure decomposition. Effect semantics and coverage are more important than significance here.

## Presentation failure modes to reject during editing

- Abstract contains more than one paragraph or more than one central empirical message.
- Introduction hides the negative result until Results.
- Raw and effective actions share a table column with changing semantics.
- A table reports conditional FPR without coverage in the caption/body.
- A sentence says the gate `improves model reasoning`, `calibration`, or `policy learning`.
- A sentence calls the benchmark a theorem prover, truth evaluator, or proof of research correctness.
- A sentence generalizes v1 to larger models without a new replication.
- A sentence claims counterfactual pairs, evidence reversal, generic policy compliance, or `evidence sensitivity` as a new technique introduced by ClaimPromoteBench.
- Human review is called validation of universal gold truth.
- Infrastructure drift is omitted to make a cleaner significance panel.
- Full hashes create layout overflow in the submission PDF.
- Submission-facing text contains author identity in the ICLR anonymous wrapper.

## Scientific changes that must be new/supplementary studies

The following would materially strengthen a later revision but cannot be folded into frozen v1 as if preregistered:

- larger/open or API-hosted model replication;
- raw-response retention and structured failure taxonomy;
- independently authored policy/item audit at larger scale;
- real research-record evaluation beyond synthetic controlled pairs;
- a pure post-processing gate condition whose model-facing prompt is identical to the passive-verifier arm;
- exact runtime/environment pinning that avoids Python patch-version identity drift.

These should be labeled post-v1 or supplementary rather than used to overwrite the current negative result.
