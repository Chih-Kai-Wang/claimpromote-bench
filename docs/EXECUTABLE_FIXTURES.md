# Executable computation fixtures

The executable evidence contract replaces trust in stored numerical output with deterministic
recomputation. It is deliberately narrow: the registered verifier evaluates a polynomial on
a finite rational grid and checks an exact predicate over those grid values. It does not
prove a statement over a continuous interval.

## Run the standalone suite

```bash
cpb-verify-fixtures \
  --fixtures fixtures/executable \
  --out work/executable-fixtures.json
```

The equivalent module command is:

```bash
python -m claimpromotebench.executable \
  --fixtures fixtures/executable \
  --out work/executable-fixtures.json
```

A successful suite means every positive fixture recomputed exactly and every negative
fixture failed with its declared stable error code.

## Registered protocol

The only registered artifact kind is `CPB_EXACT_RATIONAL_GRID`, protocol
`cpb-exact-grid-v1` version `1.0.0`. An artifact contains:

- a finite domain and an ordered grid including both endpoints;
- bounded polynomial coefficients;
- a predicate using `>=`, `<=`, or `==`;
- exact rational observations, extrema, and predicate outcome;
- a fixed repetition count and one digest per deterministic repetition;
- an explicit `FINITE_GRID_ONLY` claim scope;
- explicit preregistration.

All arithmetic uses exact rational values. The verifier imposes bounds on coefficient count,
grid size, rational-string size, and repetitions before recomputation.

## Numerical alpha binding

The four `NUMERICAL` controlled pairs in `data/alpha` are bound to four generated JSON
artifacts under this protocol. Each pair's valid and invalid members reference the same
artifact bytes, so the only within-pair difference remains the declared policy factor.

`python -m claimpromotebench validate data/alpha` now:

1. checks each evidence path and SHA-256 against the manifest-bound artifact;
2. validates the artifact structure against the registered schema;
3. recomputes every grid value, minimum, maximum, predicate result, and repetition digest;
4. rejects unknown protocols, invalid arithmetic, malformed grids, or observation tampering;
5. requires an `ALLOW` member's evidence metadata to agree with artifact repetitions,
   preregistration, closed domain, runtime result, and true predicate.

The intentionally invalid member is still recomputed. Its artifact remains valid while one
metadata prerequisite—such as repetitions, domain coverage, preregistration, or precision—is
held invalid by the controlled-pair design. This avoids introducing artifact corruption as a
second counterfactual difference.

The numerical claim text is explicitly limited to the registered rational grid. Passing
artifact recomputation therefore supports a finite-grid computational state transition only.

## Execution boundary

The verifier accepts data for one fixed operation set. It does not execute user-provided
program text, commands, modules, or executable paths, and it does not use external services.
Unknown artifact kinds and protocol versions are rejected.

## Negative fixtures

The standalone suite checks rejection of:

- a tampered observed minimum;
- a tampered repetition digest;
- an unsupported protocol version;
- a finite-grid computation presented as a continuous-domain claim;
- a computation that was not preregistered.

## Research boundary

Executable binding currently covers the four numerical pairs, or eight of the forty alpha
items. The remaining sixteen pairs retain synthetic two-line artifacts because they test
policy transitions for dependency closure, runtime records, staleness or contradiction,
independent provenance, and formal-certificate identity. The repository still does not run
Lean certificates or execute independent human review.

Passing the alpha and standalone checks supports only the claim that the registered
finite-grid artifacts can be recomputed exactly and that the tested integrity, protocol,
scope, and preregistration violations fail closed. It does not establish truth outside the
listed grid or validate arbitrary numerical software.
