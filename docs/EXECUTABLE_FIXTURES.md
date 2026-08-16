# Executable computation fixtures

The executable fixture pilot replaces trust in stored output with deterministic
recomputation. It is deliberately narrow: the registered verifier evaluates a polynomial on
a finite rational grid and checks an exact predicate over those grid values. It does not
prove a statement over a continuous interval.

## Run the suite

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

## Execution boundary

The verifier accepts data for one fixed operation set. It does not execute user-provided
program text, commands, modules, or executable paths, and it does not use external services.
Unknown artifact kinds and protocol versions are rejected.

## Negative fixtures

The committed suite checks rejection of:

- a tampered observed minimum;
- a tampered repetition digest;
- an unsupported protocol version;
- a finite-grid computation presented as a continuous-domain claim;
- a computation that was not preregistered.

## Research boundary

This is a standalone computation-fixture pilot. The current 20-pair alpha dataset still uses
its original synthetic two-line evidence artifacts and hash checks. The pilot is not yet
bound into every alpha item, and the repository still does not execute Lean certificates or
independent human review.

Passing this suite supports only the claim that the registered finite-grid fixtures can be
recomputed exactly and that the tested tampering, protocol, scope, and preregistration
violations fail closed. It does not establish truth outside the listed grid or validate
arbitrary numerical software.
