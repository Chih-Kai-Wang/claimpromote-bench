# ClaimPromoteBench v1 benchmark freeze protocol

This protocol turns the planned 200-pair study into a fail-closed sequence. It is intentionally stricter than “generate 400 rows and run models.” The public development set and hidden test set must use the same policy semantics, schema family, oracle, pair validator, executable artifact checks, prompt renderers, and study evaluator.

The machine-readable design is `configs/v1-benchmark-plan.json`. If prose and config disagree, stop and resolve the disagreement before constructing the frozen dataset.

## 1. Fixed study design

Version 1 contains exactly 200 controlled pairs / 400 instances. Every pair contains one policy-valid member and one counterfactual invalid member. The natural-language claim, current state, requested transition, and all fields outside the registered controlled pointer(s) stay fixed within a pair.

The 20 policy factors from the alpha scaffold each receive exactly 10 v1 pairs. This yields 40 dependency pairs, 40 numerical pairs, and 30 pairs in each of runtime, stale/contradiction, provenance, and formal families. Invalid sides are globally balanced 100 A / 100 B by the deterministic rule in the plan file. Invalid actions are preregistered as 180 HOLD, 10 DEMOTE, and 10 ESCALATE.

This is a factorial benchmark design, not permission to copy the same alpha sentence ten times. Variants must differ in non-decisive surface/context dimensions while the controlled semantic factor remains the only valid-vs-invalid difference inside each pair.

## 2. Public dev split

The dev split contains exactly 50 pairs / 100 instances and is public. `dev_variants` in the plan file select the factor variants allocated to dev. That allocation is frozen before the hidden test set is generated and gives 25 A-invalid / 25 B-invalid pairs and invalid-action counts HOLD=46, DEMOTE=2, ESCALATE=2.

Dev is for implementation debugging, prompt/rendering inspection, format robustness, and descriptive pilot analysis. Dev results must not be used to alter the hidden-test policy semantics, primary metrics, or controlled-factor definitions.

## 3. Hidden test split

The hidden test contains the remaining 150 pairs / 300 instances. It must not be committed in plaintext before the public commitment step.

Hidden generation requires a fresh 32-byte cryptographically random seed stored outside the public repository. There is no default seed. A public hash of the seed may be committed, but the seed bytes themselves may not be committed or pasted into public logs, issues, pull requests, workflow output, manuscript text, or model prompts.

The private seed controls only semantics-preserving surface/parameter choices and ordering. It must never change which policy factor a pair tests or alter the preregistered family/action/side counts.

## 4. Surface diversity requirements

The ten named surface profiles in the plan are a minimum coverage target, not ten decorative labels. Across variants, construction should vary several nuisance dimensions that do not decide the label, for example claim wording, mathematical object type, identifier morphology, evidence ordering, irrelevant-but-valid records, dependency graph shape where the tested factor permits it, numerical coefficients/grid values, and formal theorem surface.

Every such transformation must preserve the gold action under the deterministic oracle. If a proposed variation changes the gold label or introduces an uncontrolled valid-vs-invalid difference, reject the variation rather than relaxing the pair validator.

Formal variants must compile under the pinned Lean toolchain and bind the exact pair/claim/statement identifiers. Numerical variants must be regenerated and recomputed through the exact-rational verifier. Synthetic artifacts that merely claim success are not sufficient for these two families.

## 5. Construction order

1. Finalize v1-compatible schemas and policy identity before generating v1 rows.
2. Implement one reusable v1 constructor; do not maintain separate relaxed constructors for dev and test.
3. Build the 50-pair dev split and run full schema/pair/oracle/artifact/shortcut/metamorphic validation.
4. Exercise the four prompt arms on dev only; fix implementation defects without changing preregistered semantics.
5. Generate a fresh private 32-byte hidden seed outside the public repository.
6. Build the 150-pair hidden split privately with the same constructor and validator.
7. Validate the hidden set locally before any scored model run.
8. Produce a public commitment record containing the hidden manifest digest, relevant component digests, policy/schema/prompt identities, count summaries, and the SHA-256 of the private seed. Do not include plaintext hidden rows or the seed.
9. Commit that record to repository history.
10. Only after the commitment commit exists may scored hidden-test inference begin.

## 6. Prompt freeze

Before scored hidden-test inference, render every model-facing item for all four arms and bind the renderer source, policy file, prompt contract, and per-item prompt digest. The scorer must be able to verify that a run record refers to the frozen prompt bytes.

Any change that can alter model-facing semantics after this step is a protocol change, not a formatting fix. Create a new benchmark version and rerun affected experiments.

## 7. Gold and artifact integrity

Gold labels are generated by the deterministic policy oracle. They are never hand-edited in response to model behavior. The frozen study must pass all of the following before aggregate model results are inspected:

- schema validation;
- exactly two members per controlled pair;
- registered one-factor valid/invalid difference and no uncontrolled differences;
- oracle-to-gold equality;
- artifact path/hash binding;
- exact-rational numerical recomputation where applicable;
- pinned Lean binding and execution where applicable;
- shortcut diagnostics;
- registered semantics-preserving oracle/prompt invariance checks.

If an actual benchmark defect is found after commitment, preserve the failed version and issue a new version. Do not silently rewrite labels or policy fields in place.

## 8. Solo-author integrity boundary

A solo author can execute this protocol because its integrity claims are procedural and reproducible: preregistration, immutable commitments, executable artifact validation, deterministic labels, and no post-hoc semantic edits. These checks reduce author freedom after observing results; they do not create independent human judgment.

External human audit, if it later arrives, is supplementary. The core v1 freeze and model study must remain valid whether zero, one, or multiple external reviewers participate.

## 9. Completion criteria

The benchmark-freeze gate is complete only when the repository can point to:

- a validated public 50-pair dev manifest;
- a validated private 150-pair test manifest;
- a public test commitment commit that predates scored test inference;
- frozen policy/schema/prompt identities;
- an audit showing the plan counts exactly match the built dataset;
- no plaintext hidden labels or private seed in public history before the planned release/unblinding step.

Until then, the manuscript may describe the preregistered design but must not claim that the v1 benchmark is frozen.
