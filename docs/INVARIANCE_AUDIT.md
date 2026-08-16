# Metamorphic invariance audit

**Status: deterministic oracle audit implemented; model consistency remains unmeasured.**

The shortcut audit asks whether simple surface features can predict labels. The metamorphic
audit asks a different question: when a benchmark item is changed in a way that preserves
its policy semantics, do schema validation, artifact binding, the deterministic oracle, and
prompt rendering behave as expected?

No model, GPU, external service, or paid API is used.

## Run the audit

```bash
cpb-audit-invariance \
  --dataset data/alpha \
  --out work/invariance-audit.json
```

The module form is equivalent:

```bash
python -m claimpromotebench.invariance \
  --dataset data/alpha \
  --out work/invariance-audit.json
```

The command first validates the complete manifest-bound dataset. It then applies every
registered transformation to every applicable alpha item.

## Registered transformations

### Recursive JSON object-key reversal

All dictionary insertion orders are reversed recursively. JSON object order is not semantic,
so every one of the four rendered prompts must remain byte-identical. This catches accidental
dependence on Python dictionary insertion order.

### Consistent evidence-ID renaming

Every evidence ID is replaced consistently across:

- evidence records;
- dependency references;
- transition basis IDs;
- current-state basis IDs;
- references to intentionally missing evidence.

Oracle output evidence IDs are mapped back to the original namespace before comparison. ID
lists are compared as normalized sets because lexicographic traversal order may change after
renaming while dependency closure membership remains the same.

### Consistent principal renaming

The author ID and every evidence actor ID are renamed together. Equality and inequality
relations are preserved, so self-review remains self-review and independent review remains
independent review.

### Consistent environment renaming

The author environment and all evidence environments receive new SHA-256 values while
preserving their equality relations. This checks that review independence depends on the
relation, not a memorized digest.

### Provenance run-ID renaming

Run identifiers are replaced without changing evidence, scope, execution status, or
provenance role. Run IDs are recorded for traceability but are not transition-policy inputs.

### Evidence-array reversal

Items with at least two evidence records receive a reversed evidence array. Dependency
closure is policy-defined and lexicographically ordered, so the normalized decision must not
depend on presentation order. The model-facing prompt is expected to change because the
ledger presents a different array order.

### Valid unreferenced evidence

A fresh passing `ARTIFACT` record is appended outside the requested transition's dependency
closure. It must remain unused and must not change the decision.

### Stale failed unreferenced evidence

A stale, failed `ARTIFACT` record is prepended outside the dependency closure. The oracle must
not treat unrelated evidence as a failure of the requested basis.

### Resolved contradiction

An independently sourced `CONTRADICTION` record with status `RESOLVED` is appended. The
contradiction authority scans all contradiction records, but only a valid open contradiction
may escalate the transition.

## Validation layers

Every generated variant must pass all applicable layers:

1. public benchmark-input JSON Schema;
2. artifact path containment and SHA-256 verification;
3. exact-rational numerical artifact recomputation when applicable;
4. Lean source, marker, and toolchain binding when applicable;
5. complete deterministic oracle evaluation;
6. normalized decision equality with the original item;
7. rendering of narrative, ledger, ledger-plus-verifier, and gate-notice arms;
8. prompt identity or prompt-change expectation for the selected transformation.

A single failure sets the report status to `FAIL` and causes the CLI and CI step to return a
nonzero exit code. The report still records the item, transformation, stage, and error so the
failure is diagnosable.

## What is compared

The oracle comparison includes:

- action;
- proposed state;
- admissibility probability;
- reason codes;
- used evidence closure;
- missing evidence IDs;
- minimal missing evidence.

For evidence-ID renaming, IDs are mapped back before comparison. Evidence-ID arrays are
canonicalized as sorted sets; all other fields must match exactly.

## Relationship to future model experiments

Most transformations intentionally change the model-facing prompt while preserving the gold
decision. They therefore form a reusable source of future consistency tests:

- does the model react to arbitrary identifier spelling?
- does evidence order change its action or score?
- does unrelated failed evidence cause over-conservative holding?
- does a resolved contradiction cause false escalation?

Those questions are not answered by the current audit. Passing only proves that the
benchmark's deterministic contracts remain invariant. Model consistency must be measured on
a frozen model artifact and reported separately from ordinary AUPRC or action accuracy.

## Research boundary

The registered transformations are not an exhaustive characterization of semantic
equivalence. Passing does not prove that every harmless rewrite is safe, that the dataset has
no shortcuts, or that a language model will ignore surface changes. The result is evidence
about the current oracle and artifact pipeline only.
