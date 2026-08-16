# Shortcut and leakage audit

ClaimPromoteBench must not appear difficult only because its policy oracle is detailed. A
model may still exploit accidental correlations such as prompt length, evidence count, field
presence, or dependency shape. The shortcut audit measures those attack surfaces without
calling a language model.

## Command

```bash
cpb-audit-shortcuts \
  --dataset data/alpha \
  --out work/shortcut-audit.json
```

The command first verifies the dataset manifest and then evaluates two frozen feature tiers.

### `metadata_only`

This tier reads lengths and counts only:

- serialized input length and claim length;
- evidence, dependency-edge, and basis counts;
- aggregate identifier and artifact-path lengths;
- scope and provenance field counts;
- number of changed state axes.

It never reads string contents or compares a value with a policy requirement.

### `shallow_structure`

This tier adds structural information that a simple parser can obtain without validating the
evidence:

- evidence-type counts;
- scope-key presence, but not scope values;
- present and missing basis/dependency references;
- dependency depth and cycle presence;
- runtime-result field presence;
- changed-axis indicators.

It does not check artifact hashes, timestamps, domain containment, numerical thresholds,
formal trust bases, reviewer independence, verifier outcomes, or policy-value equality.

## Cross-fitting

The audit is supervised, but every prediction is out of pair. For each held-out controlled
pair, the baseline learns a standardized linear direction from all other pairs and then
scores only the held-out pair. The valid and invalid members of the same pair are therefore
never split across training and evaluation.

The decision rule is deliberately fail-closed: `ALLOW` is emitted only when the cross-fitted
score is strictly greater than `0.5`; a tie becomes `HOLD`.

The report reuses the benchmark evaluator and includes:

- tie-aware stepwise AUPRC;
- valid-versus-invalid paired score ranking;
- false-promotion and valid-recall diagnostics;
- family breakdowns;
- per-feature within-pair differences;
- leave-one-pair-out univariate direction accuracy.

## Interpretation

A high policy-oracle score is expected and is not evidence of a shortcut. A high
`metadata_only` score is a serious dataset warning: surface size alone predicts the label. A
high `shallow_structure` score means the benchmark may be solvable through schema inspection
without checking the evidence values that the research question intends to test.

Alpha results remain diagnostics. The audit does not prove that a language model used a
shortcut, and a low score does not prove that every possible shortcut has been removed. New
datasets should retain the audit report, inspect the strongest features, and rebalance or
redesign pairs before freezing a hidden test set.
