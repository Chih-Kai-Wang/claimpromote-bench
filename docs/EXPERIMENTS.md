# Experiment protocol

## Frozen design

The eventual v1 experiment is planned as:

- 200 controlled pairs / 400 instances;
- Qwen3 0.6B and 1.7B, locally executed with a hash-bound 4-bit artifact;
- narrative, ledger, ledger + passive verifier readout, and ledger + verifier + enforced gate;
- three fixed seeds (`104729`, `130363`, `169087`);
- 9,600 short JSON decisions.

The alpha does not download these models or report their performance. A model configuration
is not frozen until its exact file hash, source revision, quantization, llama.cpp commit, and
prompt hash are recorded. If Vulkan is unstable on the RX 7700S, the declared fallback is a
32 GB RAM CPU run. The fallback must be recorded, not mixed silently with GPU runs.

## Metrics

Primary metrics:

1. False Promotion Rate among gold-invalid transitions.
2. Valid Promotion Recall and False Hold Rate.
3. Paired Transition Accuracy: both controlled members must have the exact action.

Secondary metrics include promotion FDR and coverage, counterfactual flip accuracy, Brier
score, NLL, risk–coverage / AURC, reason-code macro-F1, evidence-ID precision/recall, and
missing-evidence exact match. If there is no predicted promotion, FDR is `null` with
`defined=false`, never zero or NaN.

Gate reports include intent FPR, effective FPR, catch rate, false-block rate, and recovery
after a block. Operational reports include median/p95 latency, output tokens, and verifier
calls. Gate catches are system-level effects and must not be described as model calibration.

## Statistics

Confidence intervals resample whole pairs with replacement, never 40 individual instances;
the fixed bootstrap seed is `20260813`. Arm comparisons use exact two-sided McNemar tests on
matched item correctness within each `model × seed`. Six pairwise arm comparisons use Holm
correction. Seeds are repeated stochastic runs, not independent datasets.

Alpha family estimates contain only three or four pairs. They validate computation and
report formatting and must be labelled preliminary pipeline checks, not scientific findings.

