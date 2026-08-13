# Alpha protocol

## Decision unit

Each input defines `(current state, requested target, policy version, evidence bundle)`. The
agent returns `ALLOW`, `HOLD`, `DEMOTE`, or `ESCALATE` plus a proposed state, calibrated
admissibility probability, evidence IDs, reason codes, and missing evidence IDs.

The oracle is a pure function of the item, versioned policy, and manifest evaluation time.
It does not read the wall clock, network, model output, or uncommitted environment state.
Artifact byte integrity is validated before scoring; corruption is a dataset error, not a
convenient negative example.

## Rule order

1. Validate policy identity, schemas, ID uniqueness, artifact paths, and SHA-256 digests.
2. Compute complete transitive dependency closure from the requested basis evidence.
3. Check missing, cyclic, failed, or unverified dependencies.
4. Check exact claim and statement scope.
5. Check tool completion and verifier result.
6. Evaluate time against `2026-08-13T00:00:00Z`, frozen in the manifest.
7. Escalate unresolved contradictions about the same claim.
8. Apply numerical protocol, repetition, preregistration, precision, and domain rules.
9. Apply exact formal statement, claim, verifier, and toolchain rules.
10. Apply independent reviewer, environment, and cold-start rules.
11. Demote a currently elevated axis whose bound artifact basis is invalid.

Alpha never promotes `research_status` to `RESOLVED`. A formal certificate can promote only
the exact formal axis; natural-language alignment and research resolution require a future,
separately versioned policy with additional evidence contracts.

Action precedence is `DEMOTE > ESCALATE > HOLD > ALLOW`. Alpha counterfactual negatives
manipulate one logical prerequisite, even where that prerequisite occupies multiple raw
fields (for example, a timeout has no exit code and an unknown verifier result).

## Gate semantics

The gate is a one-way safety filter. If the agent proposes `ALLOW` and the oracle rejects the
transition, the final decision becomes the oracle's non-allow action. Otherwise the raw
decision is preserved. In particular, an oracle `ALLOW` never converts an agent's `HOLD`
into a promotion.

Run records retain raw and final decisions. Results must report intent and effective false
promotion separately.
