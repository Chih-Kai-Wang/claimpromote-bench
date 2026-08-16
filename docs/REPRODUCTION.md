# Reproduction

## Clean alpha verification

From a fresh clone with Python 3.11–3.13:

```bash
python -m venv .venv
# Activate .venv using the command for your shell.
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python scripts/build_alpha.py
git diff --exit-code
python -m claimpromotebench verify-manifest data/alpha/manifest.json
python -m claimpromotebench check-pairs data/alpha
python -m claimpromotebench check-gold data/alpha
python -m claimpromotebench.shortcuts \
  --dataset data/alpha \
  --out work/shortcut-audit.json
python -m claimpromotebench.invariance \
  --dataset data/alpha \
  --out work/invariance-audit.json
python -m claimpromotebench.executable \
  --fixtures fixtures/executable \
  --out work/executable-fixtures.json
python -m claimpromotebench.review validate-root \
  --dataset data/alpha \
  --root reviews \
  --allow-empty \
  --out work/reviews.json
python -m claimpromotebench.review_analysis validate-root \
  --dataset data/alpha \
  --root reviews \
  --allow-empty \
  --out work/review-analysis.json
python -m pytest --cov --cov-branch --cov-fail-under=80
```

Expected structural output is 40 instances, 20 pairs, six families with distribution
`4/4/3/3/3/3`, four exact-rational numerical artifacts covering eight evidence records, three
Lean artifacts covering six formal evidence records, and oracle/gold equality. The
metamorphic report must contain no failure and must show complete schema, artifact, oracle,
and four-arm prompt processing for every registered variant. An empty published review root
must remain `PENDING`, not a passing external-review claim.

These checks do not constitute an external reproduction of a study because no model study or
completed independent review has been reported.

The model-facing renderers require the complete policy and frozen evaluation time; the CLI
loads both from the manifest-bound policy. The `evaluate-runs` command accepts the public
run-record schema and fails closed on any `FORMAT_ERROR` instead of treating missing output
as a hold.

## Metamorphic invariance verification

The invariance audit applies registered semantics-preserving transformations to every
applicable alpha item. It checks:

- recursive JSON object-key reordering;
- consistent evidence-ID renaming;
- consistent author, actor, environment, and run-ID renaming;
- evidence-array reversal;
- unrelated passing evidence;
- unrelated stale failed evidence;
- a resolved contradiction.

For every variant it reruns the public input schema, artifact containment and hashes,
exact-rational binding, Lean source binding, the complete oracle decision, and all four prompt
renderers. Evidence IDs are mapped back before decision comparison. Object-key reordering
must leave prompt bytes identical; model-facing transformations must change at least one
prompt while preserving the normalized oracle decision.

A passing report is evidence about the deterministic benchmark pipeline only. It is not a
model-consistency result and does not prove invariance under unregistered transformations.
See [the invariance audit contract](INVARIANCE_AUDIT.md).

## Pinned Lean verification

Install Elan, then let the committed `data/alpha/lean-toolchain` select exactly:

```text
leanprover/lean4:v4.33.0
```

The file hash must be:

```text
sha256:302cd63c54178885b89e669f33b38f12f4dd7ae7e5cac537b3203e3768d8fb2b
```

Run:

```bash
cd data/alpha
lake build
lake env leanchecker ClaimPromoteFormal
cd ../..
python -m claimpromotebench.formal \
  --dataset data/alpha \
  --fixtures fixtures/formal/cases.json \
  --out work/formal-fixtures.json
```

A successful formal report contains three compiled alpha artifacts, one passing standalone
fixture, and two rejected standalone fixtures. The generated `.lake`, `.olean`, and `.ilean`
files are build outputs and are not committed. See
[the formal fixture contract](FORMAL_FIXTURES.md) for the exact scope and interpretation.

## What an eventual clean-room reproduction must record

- repository commit and release/archive digest;
- Python, Lean, Lake, OS, CPU/GPU, RAM, and driver versions;
- exact model artifact hash, quantization, and source revision;
- exact llama.cpp commit and build flags;
- dataset, policy, prompt, seed, run-record, and toolchain hashes;
- shortcut, invariance, numerical, formal, review-integrity, and review-analysis reports;
- deviations, failures, retries, and all missing outputs.

The reproducer must be independent of the benchmark author and must not receive hidden test
labels before their run is committed. Compiling the alpha artifacts and passing the
metamorphic audit reproduce software and evidence-state gates, not a model experiment or an
independent scientific result.
