# ICLR 2027 reviewer-level risk audit after the public controls

Date: 2026-08-20

This audit applies to the revised manuscript on PR #20. It is an adversarial checklist, not a
prediction of acceptance. The frozen v1 hidden study remains the primary experiment. The post-v1
public formatting pilot and post-protocol GPT-5.4 public-development follow-up are separately
labeled diagnostics that address output-contract and model-breadth threats.

## Executive assessment

The revised paper is materially stronger than the v1-only version because it no longer asks the
reader to infer policy-decision failure from a high aggregate format-error rate. The public pilot
holds the prompt, model artifact, runtime, seed, and hardware record fixed while changing only the
response-format constraint. Coverage rises to 1.00 and 0.95 for the two models, yet all 78
constrained parseable actions remain `ALLOW`; controlled-pair accuracy and decision flip rate remain
zero over 38 complete pairs.

This supports a narrow conclusion: **for the two tested small models on the public controlled pairs,
fixing the output contract does not recover sensitivity to the decisive evidence change.** It does
not support a broad claim about frontier models or natural research records. A separately frozen
GPT-5.4 pass returns 99 parseable decisions from 100, matches the policy oracle on all 99, and
changes correctly on all 49 covered pairs. This establishes that the benchmark can distinguish a
stronger model's evidence-sensitive behavior from the small models' uniform `ALLOW` strategy, but
only on public development data in one post-protocol pass.

## Reviewer attack 1: “The v1 result is mostly an invalid-JSON benchmark”

**Severity before pilot:** HIGH  
**Current status:** SUBSTANTIALLY MITIGATED, NOT ELIMINATED

Evidence now available:

- free and constrained conditions use identical model-facing prompt hashes;
- only `response_format` differs;
- Qwen3-0.6B coverage rises from 0.75 to 1.00;
- Qwen3-1.7B coverage rises from 0 to 0.95;
- 78 of 80 constrained decisions are parseable;
- 38 of 40 controlled pairs are complete;
- every constrained parseable action remains `ALLOW`;
- raw pair accuracy and raw flip rate are both zero.

Residual risk:

- the control uses public data, one seed, and was designed after the v1 limitation was known;
- it cannot retrospectively recover the hidden v1 parse-failure text;
- two small models may not represent stronger systems.

Required manuscript language:

- call it a **post-v1 public formatting-control pilot**;
- keep the frozen hidden study primary;
- do not call the pilot preregistered or hidden;
- do not generalize beyond the tested models and public pairs.

## Reviewer attack 2: “Always choosing ALLOW gets 50% accuracy, so what is new?”

**Severity:** HIGH  
**Current status:** MITIGATED BY THE CONTROLLED-PAIR RESULT

The public set is balanced, so an always-`ALLOW` model obtains 0.50 conditional instance accuracy.
The controlled-pair unit reveals the failure that instance accuracy hides: the action never changes
when the decisive prerequisite changes, giving zero pair accuracy and zero flip rate. This is now a
central empirical point rather than an implied property of the benchmark.

The paper should not headline 0.50 accuracy. It should headline the separation among:

1. structured-output coverage;
2. instance-level action accuracy;
3. controlled-pair evidence sensitivity;
4. deterministic post-processing.

## Reviewer attack 3: “The deterministic gate trivially matches its own oracle”

**Severity:** HIGH  
**Current status:** MITIGATED BY CLAIM SCOPE

The gate and benchmark oracle apply the same fixed policy. Perfect post-gate scores on covered
responses are therefore implementation-level enforcement evidence, not an independently learned
result. The pilot improves the causal comparison because the gate is not disclosed to the model and
is applied only after generation, but it does not make gate correctness a model capability.

The manuscript must continue to state:

- raw and post-gate actions are different quantities;
- gate correctness is conditional on parseable output;
- post-gate accuracy is not evidence of model learning, calibration, or reasoning improvement.

## Reviewer attack 4: “Only two tiny open-weight models are tested”

**Severity:** HIGH  
**Current status:** PARTIALLY MITIGATED, STILL NARROW

The GPT-5.4 follow-up adds one API-hosted stronger model under the same public prompt packet and
fixed policy. Its 99/100 decision coverage, 99/99 covered action accuracy, and 49/49 covered pair
accuracy show that the task is not intrinsically an always-`ALLOW` or unusable-output benchmark.
This materially improves external-validity evidence but does not make the model sample broad.

Protections on this extension include:

- a frozen 12-instance continuation gate before the successful pilot;
- direct OpenAI upstream routing, strict schema, zero retries, and request/response hash binding;
- preservation of the initial transport-only `STOP` and the one-field interface revision;
- one fresh pass over all 100 public-development instances after the revised pilot passed;
- explicit reporting of the 99/100 coverage and the output-ceiling failure;
- a computed OpenRouter cost of $2.1883195 under the authorized $8 cap.

Residual risk remains substantial: the extension is public, post-protocol, one-pass, and limited to
one API model. Independent frontier-model replication and a held-out stronger-model evaluation are
still absent.

## Reviewer attack 5: “The benchmark is synthetic and author-constructed”

**Severity:** HIGH  
**Current status:** OPEN, PREPARATION IMPROVED

Controlled pairs give clean counterfactual isolation but limited ecological validity. A deterministic,
unlabeled, pointer-only pool of 12 CORE-Bench candidates is frozen before any ClaimPromoteBench
scoring. A naturalistic-case schema now separates source provenance, licensing, evaluation time,
model-visible evidence, evaluator-only labels, and inclusion decisions made without model outputs.

This work is preparation, not evidence. The paper must not claim a completed naturalistic
benchmark or real-world replication until source-level cases are defensibly curated and labeled.
An empty validated case root is preferable to weak or invented cases.

## Reviewer attack 6: “The public pilot is post-hoc and may be overfit”

**Severity:** MEDIUM-HIGH  
**Current status:** MITIGATED BY TRANSPARENCY

The interface control was selected after observing v1. This is disclosed. Protections include:

- a frozen one-shot protocol before the pilot outputs were observed;
- one canonical source workflow;
- full raw-response retention;
- no manual response repair;
- no seed selection;
- no paid rerun;
- immutable source artifacts;
- artifact-only recomputation twice with byte-identical aggregate output;
- machine validation of all paper-facing pilot values.

The public pilot should be interpreted as measurement diagnosis, not a new confirmatory hidden
study.

## Reviewer attack 7: “Without human labels, why trust the benchmark decisions?”

**Severity:** HIGH  
**Current status:** MITIGATED AS A POLICY-CONFORMANCE TASK, NOT INDEPENDENTLY VALIDATED

The submission no longer uses the small two-person audit. ClaimPromoteBench does not define gold by majority human judgment: each gold action is the deterministic output of the published versioned policy. A new public pair-contract audit checks all 20 factors, recomputes every public label, verifies one admissible and one inadmissible member per pair, and rejects unregistered differences between pair members. Exact-rational, Lean, shortcut, metamorphic, hidden-commitment, and artifact-recovery checks provide additional implementation evidence.

Residual risk remains: the policy and synthetic factors were designed by the author. The machine checks show that the implementation follows the disclosed contract; they do not show that the contract is a universal scientific norm. The manuscript must state this directly rather than replacing one weak human study with an overclaim about automation.

## Reviewer attack 8: “Novelty overlaps evidence-state and policy benchmarks”

**Severity:** HIGH  
**Current status:** MITIGATED BY NARROW POSITIONING

The paper does not claim to invent evidence-state maintenance, counterfactual pairs, evidence
reversal, claim ledgers, or policy-aware agents. Close neighbors include SeekBench,
SteerBench-Work, ST-WebAgentBench, Omni-Decision, EviGraph, ClaimLedger, scientific
claim-verification benchmarks, reproducibility benchmarks, and abstention evaluations.

The defensible contribution is the combination of:

- typed scientific evidence and orthogonal claim-state axes;
- a four-action transition policy;
- controlled pairs that alter one registered prerequisite;
- executable numerical and pinned formal evidence;
- pre-inference hidden/prompt commitment;
- explicit separation of output coverage, raw decision sensitivity, and deterministic enforcement;
- a public formatting control showing that restored coverage does not restore pair sensitivity for
  the tested small models;
- a separately frozen GPT-5.4 public-development follow-up showing near-complete coverage and
  evidence-sensitive actions under the same benchmark policy.

## Reviewer attack 9: “The evidence recovery or follow-up may have changed answers”

**Severity:** MEDIUM  
**Current status:** MITIGATED BY ARTIFACT-ONLY REPLAY

For v1, recovery used the 24 original source artifacts, did not query the models, and reclassified
only 27 cross-field-invalid structured outputs as format errors. For the public pilot, recovery
downloaded both immutable model artifacts, required the complete four-run / 160-decision matrix,
validated every record, and reproduced the public aggregate twice with identical bytes.

For GPT-5.4, the initial transport-only failure, revised frozen plan, successful pilot, and full pass
remain distinct artifacts. Validation checks prompt-packet identity, registered provider, every
request and final-response hash, exact item coverage, metrics, and token-derived costs. The sole
nonparseable full response is retained as an output-ceiling failure.

The manuscript must continue to distinguish evaluator correction from model-answer rewriting.

## Preventable submission risks

The final revised head must pass all of the following together:

- repository lint, formatting, type-checking, tests, and branch coverage;
- deterministic public dataset rebuild;
- pinned Lean alpha and v1-dev replay;
- v1 hidden/scored/recovery guards;
- v1 public release-result validation;
- v2 public pilot validation;
- GPT-5.4 pilot/full protocol, provider, hash, metric, and cost validation;
- naturalistic schema/validator tests;
- official ICLR 2027 style compilation;
- main-text page count at or below 9 pages;
- zero unresolved citations/references;
- zero horizontal overflow;
- ICLR author/provenance anonymity checks, including v1 and v2 workflow/hash identifiers;
- arXiv author and full public provenance checks;
- final page-by-page visual inspection of both PDFs.

## Current acceptance bottleneck

After the public controls, the largest remaining scientific risks are no longer the JSON interface
alone or whether a stronger model can express evidence sensitivity. They are:

1. model breadth beyond one post-protocol API model;
2. synthetic/public external validity;
3. author-defined policy scope without independent normative validation;
4. narrow task significance relative to adjacent policy/evidence benchmarks.

These risks should be addressed by honest scope and, where feasible, future evidence breadth—not by
more stylistic polishing or by overstating the deterministic gate.
