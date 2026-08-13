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
score, NLL, risk–coverage / trapezoidal AURC, per-instance reason-code set-F1,
evidence-ID precision/recall, and
missing-evidence exact match. If there is no predicted promotion, FDR is `null` with
`defined=false`, never zero or NaN.

The alpha's AURC is the trapezoidal area under risk at unique `p_admissible` thresholds,
starting at `(coverage=0, risk=0)` and adding all tied scores together. It is labelled
`aurc_trapezoid` in machine output; it must not be compared to stepwise or rank-averaged AURC
without recomputation.

`false_hold_rate` counts every gold-valid transition whose prediction is not `ALLOW`; literal
`HOLD` predictions on valid items are also reported separately as a diagnostic. The alpha's
reason-code score averages set-F1 across instances and is named `reason_code_instance_set_f1`;
it is not conventional label-wise macro-F1.

Gate reports include intent FPR, effective FPR, catch rate, and false-block rate. Operational
reports include median/p95 latency, output tokens, and verifier calls. Recovery after a block
is not implemented in the alpha evaluator. Gate catches are system-level effects and must not
be described as model calibration.

`FORMAT_ERROR` rows are excluded from decision-conditioned rates and paired metrics, with
decision and complete-pair coverage reported explicitly. They never receive a correct HOLD or
safe-transition credit. For the primary false-promotion rate, the report also publishes a
worst-case sensitivity analysis that counts every format error on a gold-invalid item as a
false promotion.

## Statistics

Confidence intervals resample whole pairs with replacement, never 40 individual instances;
the fixed bootstrap seed is `20260813`. Arm comparisons use exact two-sided McNemar tests on
matched item correctness within each `model × seed`. Six pairwise arm comparisons use Holm
correction. Seeds are repeated stochastic runs, not independent datasets.

Alpha family estimates contain only three or four pairs. They validate computation and
report formatting and must be labelled preliminary pipeline checks, not scientific findings.
