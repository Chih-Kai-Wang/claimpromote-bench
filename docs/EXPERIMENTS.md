# Experiment protocol and v1 execution record

## Frozen design

ClaimPromoteBench v1 contains 200 controlled pairs / 400 instances, but the **primary scored study uses only the private 150-pair / 300-instance hidden test**. The 50-pair / 100-instance public development split is reserved for implementation debugging, prompt inspection, and descriptive pilot work.

Primary hidden matrix:

- hidden instances: 300;
- models: Qwen3-0.6B Q8_0 and Qwen3-1.7B Q8_0;
- arms: narrative, ledger, ledger + passive verifier, ledger + verifier + enforced gate;
- seeds: `104729`, `130363`, `169087`;
- primary scored decisions: **300 × 2 × 4 × 3 = 7,200**;
- llama.cpp runtime commit: `de699957b92f490efebad149665b0dccf127eaff`.

The gate arm discloses in the prompt that a deterministic veto may block an invalid `ALLOW`. Raw intent in that arm is therefore not an identical-prompt control relative to the passive-verifier arm. The actual enforcement contrast is raw versus effective decision **within the gate arm**.

## Hidden commitment and frozen inference chronology

The chronology is immutable and must not be rewritten:

- hidden commitment commit: `8d9b3f5c831f432cf6b321e6402724c4f52bb3e1`;
- scored inference trigger/head: `aa5268dcde2aa44f8eabf0246631efbca27de7e5`;
- source workflow run: `32255636879`;
- commitment SHA-256: `sha256:55a3d2bffb6f23b7253715a9f091d951daaf589e205033d3f46dfd9e6ff6590e`;
- dataset-manifest SHA-256: `sha256:fe838548389ee1516d9cf9442201a22c291add0ddb6cabf4f39de99b6489caba`;
- prompt-manifest SHA-256: `sha256:b6c1dacdb6db34aef4a9532df8e24a6e6f51724df75b0f2e8a14ffa01dca2957`;
- hidden-seed SHA-256: `sha256:b91b5b36268bf2af3acc4c2d0890613b92c02a125db3fe5a1e12c099800fe285`.

The raw hidden seed remains a GitHub Actions secret and must never be printed or committed.

## Metrics

Primary metrics:

1. False Promotion Rate (FPR) among gold-non-`ALLOW` transitions.
2. Valid Promotion Recall (VPR).
3. False Hold Rate.
4. Paired Transition Accuracy (PTA): both controlled members must receive the exact four-way gold action.

Secondary metrics include promotion FDR, decision coverage, complete-pair coverage, counterfactual flip accuracy, Brier score, NLL, tie-aware stepwise AUPRC, paired score ranking, reason-code instance set-F1, evidence-ID precision/recall, missing-evidence exact match, and family diagnostics.

Gate reports include raw-intent FPR, effective-system FPR, gate catch rate, and false-block rate. Gate catches are **system-level enforcement effects**; they are not evidence of improved model reasoning or calibration.

`FORMAT_ERROR` is never converted to `HOLD`. It reduces decision coverage and complete-pair coverage and is excluded from decision-conditioned rates. False-promotion reporting also retains worst-case format-error sensitivity.

### Precision-recall and AUPRC

A gold `ALLOW` transition is the positive class and `p_admissible` is the ranking score. Equal scores are grouped at one threshold before updating precision and recall. The evaluator reports stepwise average precision as `precision_recall.auprc_stepwise` plus the full threshold curve, prevalence, lift, score coverage, and unique-threshold count.

Rows with `FORMAT_ERROR` have no score and reduce score coverage. `paired_score_ranking` tests the valid-versus-invalid member ordering within controlled pairs and reports strict/tie-adjusted accuracy, wins/ties/losses, margins, and pair coverage.

## Statistics

Confidence intervals resample whole controlled pairs. The fixed bootstrap seed is `20260813`; the recovered primary aggregate uses 10,000 pair-bootstrap samples.

Arm comparisons use exact two-sided McNemar tests on matched item correctness within each exact `model artifact × runtime × seed × hardware` group. Holm correction is applied separately to raw-intent and effective-system comparisons within that group.

### v1 exact-identity drift

The hosted source matrix recorded Python 3.11.15 for most jobs and Python 3.11.16 for three jobs. Python version is included in the frozen hardware-summary string, so the official `compare-runs` aggregate contains nine identity groups rather than the intended six model×seed groups. Only three groups contain all four arms.

This is retained fail-closed. We do **not** regroup runs after seeing results merely because the CPU/platform and model runtime otherwise look equivalent. A future replication should pin the Python patch release before inference.

## Artifact-only semantic recovery

The original source workflow finished all 24 inference artifacts. Some jobs failed the original evaluator after inference because a model output could be JSON-schema-valid while violating a frozen cross-field decision invariant, such as `ALLOW` without the requested target state.

That defect is handled as an evaluator interpretation bug, not as permission to improve model answers.

Recovery workflow run `32274814703` at head `e2b09f30b0573cf7bcb244eef1917691755f2877`:

1. reconstructed the hidden set and prompt identity from the frozen scoring source;
2. bound exactly 24 immutable `cpb-v1-scored-*` source artifacts from run `32255636879`;
3. required exactly 24 source `run.jsonl`, 24 preflights, and 7,200 source records;
4. reclassified only frozen cross-field semantic violations to `FORMAT_ERROR` using rule `semantic-format-error-v1`;
5. validated 24 normalized `run.jsonl` and exact prompt hashes;
6. generated a 10,000-pair-bootstrap aggregate;
7. froze recovery provenance and uploaded `claimpromotebench-v1-scored-study-recovered`.

Exactly **27 / 7,200** records were reclassified by the semantic recovery rule. No legal model decision was rewritten and no model inference was rerun.

Validated recovered identities:

- source runs / records: 24 / 7,200;
- normalized runs / records: 24 / 7,200;
- recovery status: `COMPLETE_VALIDATED_RECOVERY`;
- study SHA-256: `sha256:3eb5b534ab486dac774a62de3d623fa33009be3705d9e8d620bb9942e8bfe664`;
- normalization SHA-256: `sha256:2daf94115a3ab0a228a2a64babd476e44707eb3926f342323149b097d3c4ec80`;
- source-artifact-manifest SHA-256: `sha256:9cd2362502d4a5e3aca7688f32b6b0fc65afc3ed89b39c8c818ea6eac7f5d5ea`.

The one-shot recovery trigger was deleted immediately after success.

## Primary hidden results

Across the 7,200 normalized decisions:

- `FORMAT_ERROR`: **5,327 / 7,200 = 73.99%**;
- parseable raw decisions: **1,873**;
- raw actions among all parseable decisions: **`ALLOW` only**.

Therefore, where raw rates are defined, raw FPR = 1.00, raw VPR = 1.00, and raw PTA = 0. The raw models do not discriminate admissible from inadmissible transitions under this frozen protocol.

### Decision coverage by seed

Seed order in the table is `104729 / 130363 / 169087`.

| Model | Arm | Decision coverage |
|---|---|---:|
| Qwen3-0.6B | narrative | 0 / 0 / 0 |
| Qwen3-0.6B | ledger | .667 / .893 / .570 |
| Qwen3-0.6B | ledger + verifier | .703 / .787 / .393 |
| Qwen3-0.6B | ledger + verifier + gate | .490 / .420 / .140 |
| Qwen3-1.7B | narrative | 0 / 0 / 0 |
| Qwen3-1.7B | ledger | 0 / 0 / 0 |
| Qwen3-1.7B | ledger + verifier | 0 / 0 / 0 |
| Qwen3-1.7B | ledger + verifier + gate | .483 / .217 / .480 |

### Format-error counts by model/arm

Each model/arm cell contains 900 decisions across three seeds.

| Model | Narrative | Ledger | Ledger + verifier | Ledger + verifier + gate |
|---|---:|---:|---:|---:|
| Qwen3-0.6B | 900 | 261 | 335 | 585 |
| Qwen3-1.7B | 900 | 900 | 900 | 546 |

### Gate behavior

For every gate-arm seed with parseable decisions:

- raw-intent FPR = 1.00;
- effective-system FPR = 0.00;
- VPR = 1.00;
- gate catch rate = 1.00;
- false-block rate = 0.00;
- effective PTA = 1.00 on complete covered pairs.

These rates are conditional on low decision/pair coverage. They demonstrate deterministic policy enforcement, not successful model policy learning.

## Important diagnostic limitation

Source run records retain parse status, prompt hashes, structured raw/final decisions when parsing succeeds, latency, token counts, verifier calls, and identity. They do **not** retain the original free-form model text for records already classified as parse failures. Consequently, the high pre-existing `FORMAT_ERROR` rate can be counted and localized by run, but its exact linguistic cause cannot be reconstructed from the frozen artifacts. Rerunning the models after seeing results would break the primary-study freeze, so v1 does not do that.

## Supplementary human audit

Two real independent reviewers completed the frozen 20-item procedural-blind alpha audit:

- reviewer-01 action agreement: 18/20 = 0.90;
- reviewer-01 exact reason agreement: 18/20 = 0.90;
- immutable ID `reviwer-02` action agreement: 15/20 = 0.75;
- exact reason agreement: 14/20 = 0.70;
- pairwise action agreement: 17/20 = 0.85;
- pairwise exact reason agreement: 16/20 = 0.80;
- diagnostic Cohen κ ≈ 0.716.

The conservative supplementary gate requires every reviewer to reach 0.80 action agreement. The result is therefore **MIXED / NOT PASS**. Gold and policy are not changed to make reviewer-02 pass.

## Interpretation boundary

The frozen result supports three claims and no stronger ones:

1. The benchmark and artifact-bound hidden protocol can execute end-to-end and preserve a committed 24-run inference matrix through fail-closed evaluator recovery.
2. Under the frozen small-Qwen protocol, raw structured policy decisions are unreliable and collapse to `ALLOW` whenever parseable.
3. Deterministic state-transition enforcement can eliminate measured false promotion among covered decisions, but cannot repair missing/malformed model intents.

It does **not** establish theorem truth, general scientific truth, improved model reasoning, or broad human-level policy reliability.
