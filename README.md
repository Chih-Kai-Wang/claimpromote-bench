# ClaimPromoteBench

**Policy-Governed Evidence-State Transitions for Mathematical Research Agents**

> **v1 primary hidden study complete; manuscript finalization in progress.**  
> The frozen primary study contains 24 runs / 7,200 scored hidden decisions. Results below are bound to the validated recovered aggregate artifact, not partial logs.

ClaimPromoteBench asks a narrow question: **given a mathematical research claim, typed evidence, a current evidence state, and a requested transition, is that transition admissible under a frozen versioned policy?**

It is **not** a theorem-truth classifier, general scientific fact checker, or a claim that Lean acceptance implies an unrestricted natural-language conclusion. It separates four orthogonal state axes—research, computation, formal certification, and independent review—and evaluates one of four actions:

`ALLOW` · `HOLD` · `DEMOTE` · `ESCALATE`

A deterministic gate may veto an invalid `ALLOW`, but gate catches are reported as **system-level enforcement effects**, not improved model reasoning or calibration.

## v1 benchmark

| Component | Frozen v1 status |
|---|---|
| Total benchmark | 200 controlled pairs / 400 instances |
| Public development | 50 pairs / 100 instances |
| Private hidden primary test | 150 pairs / 300 instances |
| Policy factors | 20 |
| Primary models | Qwen3-0.6B Q8_0; Qwen3-1.7B Q8_0 |
| Arms | narrative; ledger; ledger + passive verifier; ledger + verifier + gate |
| Seeds | 104729; 130363; 169087 |
| Primary matrix | 300 × 2 × 4 × 3 = **7,200 decisions** |
| llama.cpp | `de699957b92f490efebad149665b0dccf127eaff` |
| Hidden commitment commit | `8d9b3f5c831f432cf6b321e6402724c4f52bb3e1` |
| Frozen inference source | workflow `32255636879`, head `aa5268dcde2aa44f8eabf0246631efbca27de7e5` |
| Artifact-only recovery | workflow `32274814703`, head `e2b09f30b0573cf7bcb244eef1917691755f2877` |
| Recovered matrix | 24 source runs + 24 normalized runs; 7,200 records each side |
| Study file SHA-256 | `sha256:3eb5b534ab486dac774a62de3d623fa33009be3705d9e8d620bb9942e8bfe664` |

Public development is for implementation debugging and descriptive pilot work only. **Primary scoring uses only the 300 hidden instances.**

## Primary hidden result

The main result is a structured-output failure, not a small difference between intervention means:

- **5,327 / 7,200 decisions (73.99%) are `FORMAT_ERROR`.**
- Across all **1,873 parseable raw model decisions, the raw action is always `ALLOW`.**
- Therefore, whenever raw primary rates are defined, raw false-promotion rate is 1.00, valid-promotion recall is 1.00, and paired transition accuracy is 0.
- In the enforced-gate arm, among parseable decisions, effective false-promotion rate is 0, valid-promotion recall is 1, gate catch rate is 1, and false-block rate is 0 across every seed.
- Those gate rates are **conditional on low coverage**: Qwen3-0.6B gate-arm decision coverage ranges from 14.0% to 49.0%; Qwen3-1.7B ranges from 21.7% to 48.3%.

The correct interpretation is therefore: **deterministic enforcement can prevent policy-invalid promotion when a structured intent exists, but it does not make the model selective and it does not solve structured-output reliability.**

### Per-model/arm format-error counts

Each model/arm cell contains 900 decisions across three seeds.

| Model | Narrative | Ledger | Ledger + verifier | Ledger + verifier + gate |
|---|---:|---:|---:|---:|
| Qwen3-0.6B | 900 | 261 | 335 | 585 |
| Qwen3-1.7B | 900 | 900 | 900 | 546 |

All three seeds are retained. No result was removed because it was inconvenient.

## Transparent artifact-only recovery

The original source inference finished, but some jobs failed at evaluation because a model output could be JSON-schema-valid while violating a frozen cross-field decision invariant—for example, `ALLOW` without proposing the requested target state.

The recovery path did **not** rerun either model and did **not** rewrite any legal model decision. It:

1. bound exactly 24 immutable source artifacts from workflow `32255636879`;
2. required exactly 24 source `run.jsonl` and 7,200 inference records;
3. reconstructed the committed hidden set and prompt identity from the frozen scoring source;
4. reclassified only frozen cross-field semantic violations as `FORMAT_ERROR`;
5. validated all 24 normalized runs and exact prompt hashes;
6. generated the 10,000-pair-bootstrap aggregate and recovery provenance.

Exactly **27 records** were reclassified by `semantic-format-error-v1`. The one-shot recovery trigger was removed immediately after successful recovery.

Frozen public-safe identities:

- commitment SHA-256: `sha256:55a3d2bffb6f23b7253715a9f091d951daaf589e205033d3f46dfd9e6ff6590e`
- dataset-manifest SHA-256: `sha256:fe838548389ee1516d9cf9442201a22c291add0ddb6cabf4f39de99b6489caba`
- prompt-manifest SHA-256: `sha256:b6c1dacdb6db34aef4a9532df8e24a6e6f51724df75b0f2e8a14ffa01dca2957`
- hidden-seed SHA-256: `sha256:b91b5b36268bf2af3acc4c2d0890613b92c02a125db3fe5a1e12c099800fe285`

The raw hidden seed remains a GitHub Actions secret and is never printed or committed.

## Matched-comparison limitation

The preregistered comparison pipeline groups runs by exact model artifact, runtime, seed, and hardware-summary identity. Three hosted jobs recorded Python 3.11.16 while most recorded Python 3.11.15. Because the Python patch version is part of that exact identity string, the official aggregate contains nine identity groups rather than the intended six model×seed groups; only three contain all four arms.

We **do not regroup them post hoc** after seeing the results. Exact McNemar/Holm comparisons remain available only for arm pairs that coexist in an exact recorded identity group. A future replication should pin the exact Python patch release, but it must not replace frozen v1.

## Supplementary real-human audit

Two real independent reviewers completed the frozen 20-item procedural-blind alpha audit.

| Evidence | Result |
|---|---:|
| reviewer-01 action agreement | 18/20 = 0.90 |
| reviewer-01 exact reason agreement | 18/20 = 0.90 |
| `reviwer-02` action agreement | 15/20 = 0.75 |
| `reviwer-02` exact reason agreement | 14/20 = 0.70 |
| pairwise action agreement | 17/20 = 0.85 |
| pairwise exact reason agreement | 16/20 = 0.80 |
| diagnostic Cohen κ | ≈ 0.716 |

The repository's supplementary gate requires every reviewer to reach 0.80 action agreement, so this is a **mixed result / not PASS**. The immutable `reviwer-02` identifier typo is intentionally preserved.

## Evidence and executable bindings

ClaimPromoteBench deliberately prevents one kind of successful evidence from being treated as universal research proof:

- numerical cases use exact-rational finite-grid artifacts whose registered values, extrema, predicates, repetitions, and scope are recomputed;
- formal cases bind generated Lean sources and a pinned trust base;
- provenance, freshness, dependencies, contradiction state, review independence, statement identity, and runtime success remain separate policy prerequisites.

Kernel acceptance proves the exact formal declaration in the pinned environment. A successful finite computation proves only its registered computational scope. Neither automatically promotes research status.

## Reproduce public checks

Python 3.11+:

```bash
python -m pip install -e ".[dev]"
python scripts/build_alpha.py
python -m claimpromotebench validate data/alpha
python -m claimpromotebench.shortcuts --dataset data/alpha --out work/shortcut-audit.json
python -m claimpromotebench.invariance --dataset data/alpha --out work/invariance-audit.json
python -m claimpromotebench.executable --fixtures fixtures/executable --out work/executable-fixtures.json
python -m pytest --cov --cov-branch --cov-fail-under=80
```

Formal gate with the pinned Lean environment:

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

Evaluate a complete run or compare matched runs:

```bash
python -m claimpromotebench evaluate-runs \
  --gold data/alpha/gold.jsonl \
  --runs work/example-run.jsonl \
  --out work/example-run.eval.json

python -m claimpromotebench compare-runs \
  --gold data/alpha/gold.jsonl \
  --runs work/*.jsonl \
  --out work/study.json
```

`FORMAT_ERROR` is never silently counted as `HOLD`. Decision coverage and worst-case format-error sensitivity remain explicit.

## Research boundary and novelty claim

ClaimPromoteBench does not claim to invent claim ledgers, evidence-state maintenance, or verifier-governed research agents. Related work includes SeekBench, Omni-Decision, EviGraph, ClaimLedger, scientific claim-verification benchmarks, reproducibility benchmarks, and abstention/selective-action evaluations.

The defensible contribution is narrower: **a preregistered, controlled-pair, four-action, artifact-bound, prompt-frozen, hidden-test-committed benchmark for policy-governed research-claim evidence-state transition admissibility, with raw model intent separated from deterministic enforcement.**

The manuscript uses cautious language such as: *we did not find a public benchmark directly evaluating policy-governed research-claim evidence-state transitions under matched, machine-checkable prerequisites.* It does not make an unqualified “first benchmark” or “first system” claim.

## Paper and project status

- Technical report: `technical-report/main.tex`
- Fail-closed readiness checklist: `technical-report/SUBMISSION_GATE.md`
- Experiment protocol/history: `docs/EXPERIMENTS.md`
- Roadmap: `docs/ROADMAP.md`
- Related work: `docs/RELATED_WORK.md`
- AI assistance disclosure: `AI_ASSISTANCE.md`

The frozen v1 primary inference should **not** be rerun or rewritten to make the result cleaner. Remaining work is final manuscript/CI/PDF verification, bibliography authority checks, and release-quality clean-environment reproduction. See `technical-report/SUBMISSION_GATE.md` for the exact distinction between primary-study completion, preprint readiness, and archival-submission readiness.
