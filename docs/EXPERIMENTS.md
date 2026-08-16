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
score, NLL, precision-recall / AUPRC, risk-coverage / trapezoidal AURC, paired score ranking,
per-instance reason-code set-F1, evidence-ID precision/recall, and missing-evidence exact
match. If there is no predicted promotion, FDR is `null` with `defined=false`, never zero or
NaN.

### Precision-recall and AUPRC

A gold `ALLOW` transition is the positive class and `p_admissible` is the ranking score. The
machine output groups every equal score into one threshold before updating precision and
recall. It reports the resulting stepwise average precision as
`precision_recall.auprc_stepwise`, together with the full threshold curve, positive
prevalence, lift over prevalence, score coverage, and the number of unique thresholds.

The area is

```text
sum over thresholds: (recall_t - recall_(t-1)) * precision_t
```

This tie-aware definition never invents an order between equal scores. It is not a
trapezoidal PR area and must not be compared with a differently interpolated AUPRC without
recomputation. A 95% interval resamples whole controlled pairs. Rows with `FORMAT_ERROR` have
no score, reduce score coverage, and are excluded from the ranking calculation.

`paired_score_ranking` directly tests the controlled-pair ordering. A win means that the
gold-valid member receives a higher `p_admissible` than its invalid counterpart; a tie earns
half credit only in `tie_adjusted_accuracy`. Strict accuracy, win/tie/loss counts, score
margins, and pair coverage are also reported.

### Other metrics

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

The evaluator also emits `by_family` results for the six evidence families. Alpha families
contain only three or four pairs, so these values are diagnostics for failure localization,
not standalone scientific estimates.

## Statistics

Confidence intervals resample whole pairs with replacement, never 40 individual instances;
the fixed bootstrap seed is `20260813`. Metrics requested in the same evaluation share one
sequence of pair resamples, which preserves comparability while avoiding duplicate bootstrap
work. A request for zero bootstrap samples records `samples_defined=0` with null bounds and
does no resampling.

Arm comparisons use exact two-sided McNemar tests on matched item correctness within each
`model artifact × runtime × seed × hardware` group. Every pair of available arms is compared
for raw intent and effective post-gate correctness. Holm correction is applied separately to
the raw and effective p-values within that group. Metric output also reports `arm_b - arm_a`
for false promotion rate, valid promotion recall, paired transition accuracy, and stepwise
AUPRC. Seeds are repeated stochastic runs, not independent datasets.

### Run accumulation and provenance

`evaluate-runs` first validates complete item coverage, the run-record schema, frozen prompt
hashes, action/state semantics, and one uniform identity per file. The identity consists of
model ID, model artifact SHA-256, quantization, runtime commit, arm, seed, and hardware. Its
output includes:

- a dataset fingerprint containing gold, input, manifest, and policy hashes;
- the SHA-256 of the run-record file;
- a path-independent `run_id` over the dataset fingerprint, run identity, and file hash.

`compare-runs` accepts one or more validated run-record files. It rejects duplicate file
content and duplicate run identities, groups comparable arms, lists missing arms, and
requires identical item IDs before running a matched test. Input order does not affect the
resulting `study_id`. The study ID binds the dataset fingerprint and sorted run IDs, so adding
a new run creates a new cumulative study while leaving earlier run IDs unchanged.

Comparison defaults to zero bootstrap samples because exact matched tests and metric deltas do
not require recomputing each run's confidence interval. A positive
`--bootstrap-samples` value includes per-run pair-bootstrap intervals in the same study report.

Alpha family estimates contain only three or four pairs. They validate computation and
report formatting and must be labelled preliminary pipeline checks, not scientific findings.
