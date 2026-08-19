# ClaimPromoteBench

**A benchmark for deciding when evidence justifies a change in research-claim status.**

> **v1 primary hidden study complete; paper in final submission preparation.**  
> The primary study contains 24 runs and 7,200 hidden decisions. The numbers below come from the validated recovered study, not from partial logs.

ClaimPromoteBench asks a narrow question: **given a mathematical research claim, its evidence, its current status, and a requested status change, should that change be allowed under a fixed policy?**

The benchmark is not a theorem-truth classifier or a general scientific fact checker. It keeps research status, computation, formal certification, and independent review separate and uses four possible actions:

`ALLOW` · `HOLD` · `DEMOTE` · `ESCALATE`

A deterministic gate can replace an invalid `ALLOW` after the model responds. We report that gate behavior separately from the model's own decision.

## v1 benchmark

| Component | v1 |
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
| Scored inference | workflow `32255636879`, head `aa5268dcde2aa44f8eabf0246631efbca27de7e5` |
| Recovery | workflow `32274814703`, head `e2b09f30b0573cf7bcb244eef1917691755f2877` |
| Recovered matrix | 24 original runs + 24 normalized runs; 7,200 records each |
| Study SHA-256 | `sha256:3eb5b534ab486dac774a62de3d623fa33009be3705d9e8d620bb9942e8bfe664` |

Primary scoring uses only the 300 hidden instances. The public development data are for implementation and descriptive pilot work.

## Main result

The result is mostly negative:

- **5,327 / 7,200 decisions (73.99%) are `FORMAT_ERROR`.**
- All **1,873 parseable raw model decisions are `ALLOW`.**
- Wherever the raw rates are defined, raw false-promotion rate is 1.00, valid-promotion recall is 1.00, and paired transition accuracy is 0.
- In the gate arm, the final false-promotion rate is 0 on parseable decisions, with catch rate 1 and false-block rate 0.
- Gate-arm decision coverage is low: 14.0%–49.0% for Qwen3-0.6B and 21.7%–48.3% for Qwen3-1.7B.

The gate uses the same fixed policy that defines the benchmark labels. Its perfect conditional gate scores therefore show that the implementation follows that policy on parseable cases; they do **not** show that the model learned the policy or reasoned better.

### Format errors by model and arm

Each cell contains 900 decisions across three seeds.

| Model | Narrative | Ledger | Ledger + verifier | Ledger + verifier + gate |
|---|---:|---:|---:|---:|
| Qwen3-0.6B | 900 | 261 | 335 | 585 |
| Qwen3-1.7B | 900 | 900 | 900 | 546 |

All three seeds are kept in the study.

## Recovery of evaluator failures

The original model calls finished, but some jobs later failed during evaluation because an output could pass the JSON schema while violating a cross-field rule, such as returning `ALLOW` without proposing the requested target state.

The recovery procedure did not rerun the models and did not rewrite otherwise valid decisions. It:

1. used exactly the 24 original source artifacts from workflow `32255636879`;
2. required 24 `run.jsonl` files and 7,200 source records;
3. rebuilt the committed hidden set and prompt identity from the original scoring source;
4. reclassified only the affected invalid structured outputs as `FORMAT_ERROR`;
5. validated all 24 normalized runs and prompt hashes;
6. produced the 10,000-pair-bootstrap aggregate and recovery record.

Exactly **27 records** were reclassified by `semantic-format-error-v1`. The one-time recovery trigger was removed after the recovery succeeded.

Study identifiers:

- commitment SHA-256: `sha256:55a3d2bffb6f23b7253715a9f091d951daaf589e205033d3f46dfd9e6ff6590e`
- dataset-manifest SHA-256: `sha256:fe838548389ee1516d9cf9442201a22c291add0ddb6cabf4f39de99b6489caba`
- prompt-manifest SHA-256: `sha256:b6c1dacdb6db34aef4a9532df8e24a6e6f51724df75b0f2e8a14ffa01dca2957`
- hidden-seed SHA-256: `sha256:b91b5b36268bf2af3acc4c2d0890613b92c02a125db3fe5a1e12c099800fe285`

The raw hidden seed remains a GitHub Actions secret and is not printed or committed.

## Matched-comparison limitation

The preregistered comparison code groups runs by exact model artifact, runtime, seed, and hardware summary. Three hosted jobs recorded Python 3.11.16 while most recorded Python 3.11.15. Because the Python patch version is part of that identity, the final aggregate has nine groups instead of the intended six model×seed groups; only three contain all four arms.

We keep the original grouping rather than combining runs after seeing the results. Exact McNemar/Holm comparisons are therefore available only when both arms occur in the same recorded group. A later replication should pin the exact Python patch release.

## Human policy audit

Two independent reviewers completed a 20-item blinded audit using the public alpha data.

| Evidence | Result |
|---|---:|
| reviewer-01 action agreement | 18/20 = 0.90 |
| reviewer-01 exact reason agreement | 18/20 = 0.90 |
| `reviwer-02` action agreement | 15/20 = 0.75 |
| `reviwer-02` exact reason agreement | 14/20 = 0.70 |
| pairwise action agreement | 17/20 = 0.85 |
| pairwise exact reason agreement | 16/20 = 0.80 |
| diagnostic Cohen κ | ≈ 0.716 |

The preregistered audit criterion requires every reviewer to reach 0.80 action agreement, so the result is **mixed / not PASS**. The `reviwer-02` identifier typo is part of the immutable submission and is kept as-is.

## What the executable evidence means

Numerical cases use exact-rational finite-grid artifacts whose registered values, extrema, predicates, repetitions, and scope are recomputed. Formal cases use generated Lean sources under a pinned toolchain. Provenance, freshness, dependencies, contradictions, review independence, statement identity, and runtime success remain separate policy requirements.

A Lean check supports the exact formal statement that was checked. A finite computation supports only its registered computational scope. Neither automatically settles a broader research claim.

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

Formal checks with the pinned Lean environment:

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

Evaluate a run or compare matched runs:

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

`FORMAT_ERROR` is never silently counted as `HOLD`.

## Scope

ClaimPromoteBench does not claim to invent claim ledgers, evidence-state maintenance, or verifier-governed research agents. Related work includes SeekBench, Omni-Decision, EviGraph, ClaimLedger, scientific claim-verification benchmarks, reproducibility benchmarks, and abstention/selective-action evaluations.

The contribution is narrower: a preregistered controlled-pair benchmark for deciding whether registered evidence justifies a requested research-claim status change, with executable evidence checks, a committed hidden test, and separate reporting of raw model decisions and deterministic gate actions.

The paper does not make an unqualified “first benchmark” or “first system” claim.

## Paper and project status

- Technical report: `technical-report/main.tex`
- Submission checklist: `technical-report/SUBMISSION_GATE.md`
- Experiment protocol/history: `docs/EXPERIMENTS.md`
- Roadmap: `docs/ROADMAP.md`
- Related work: `docs/RELATED_WORK.md`
- AI assistance disclosure: `AI_ASSISTANCE.md`

The v1 hidden model outputs are fixed and should not be rerun or rewritten to make the result cleaner. Remaining work is release preparation and the account-side steps needed to submit the preprint and conference paper.
