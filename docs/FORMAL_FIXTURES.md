# Pinned Lean formal alpha

The three `FORMAL` controlled pairs are bound to three committed Lean 4 source files and a
manifest-bound Lake package. They test whether a requested transition to
`FORMALLY_CERTIFIED` is supported by the exact theorem, exact claim identity, exact statement
identity, and exact toolchain declared by the evidence ledger.

## Pinned environment

The package uses:

```text
leanprover/lean4:v4.33.0
```

The exact UTF-8/LF `data/alpha/lean-toolchain` bytes are bound by:

```text
sha256:302cd63c54178885b89e669f33b38f12f4dd7ae7e5cac537b3203e3768d8fb2b
```

`data/alpha/lakefile.toml`, `data/alpha/lake-manifest.json`, the root module, and all three
source files are named in `data/alpha/manifest.json`. CI uses the official Lean action pinned
to commit `8dd5d0978ba1c4ec4ae0835a93f88d946799944f`, runs `lake build`, and then replays the built
library with:

```bash
cd data/alpha
lake env leanchecker ClaimPromoteFormal
```

The explicit library argument is intentional: the Lake package name and the built Lean
library name are different objects.

## Exact alpha claims

The three compiled declarations are deliberately small and directly aligned with their
natural-language claim text:

```lean
theorem formal01 (n : Nat) : n + 0 = n := Nat.add_zero n

theorem formal02 (n : Nat) : 0 + n = n := Nat.zero_add n

theorem formal03 (p q : Prop) : p ∧ q ↔ q ∧ p :=
  ⟨fun h => ⟨h.2, h.1⟩, fun h => ⟨h.2, h.1⟩⟩
```

Each generated source embeds four deterministic markers in a comment:

- controlled-pair ID;
- claim ID;
- natural-language statement SHA-256;
- `lean-toolchain` SHA-256.

Dataset validation checks the source path, source hash, complete marker set, item identity,
statement identity, toolchain bytes, evidence runtime status, and verifier declaration. For
the `ALLOW` member it additionally requires every evidence scope field to equal the source
markers.

## Controlled-pair rule

Both members of a formal pair reference identical compilable source bytes. The invalid member
changes exactly one registered evidence field:

- statement SHA-256;
- claim ID; or
- toolchain-lock SHA-256.

The invalid member is therefore rejected by the versioned transition policy, not by a second
uncontrolled compiler failure. Both sides remain hash-bound to the same theorem artifact.

## Positive and negative fixtures

Run the full formal gate after installing the pinned Lean toolchain:

```bash
python -m claimpromotebench.formal \
  --dataset data/alpha \
  --fixtures fixtures/formal/cases.json \
  --out work/formal-fixtures.json
```

The command recompiles the three unique alpha artifacts and executes three standalone cases:

- one valid theorem that must pass;
- one false theorem proved by `rfl` that must be rejected;
- one unknown identifier that must be rejected.

A successful report requires all three alpha artifacts to compile, the positive fixture to
pass, and both negative fixtures to fail.

## Research boundary

Passing this gate establishes only that three exact Lean declarations compile under the
pinned toolchain, their generated source bytes are bound to the declared item identities, and
the registered invalid programs are rejected. It does not establish:

- novelty or publication value;
- correctness of a broader informal proof;
- correctness outside the exact formal statements;
- independent human review;
- `research_status=RESOLVED`;
- a model-performance result.

Formal certification remains one orthogonal evidence-state axis rather than a general truth
or research-resolution label.
