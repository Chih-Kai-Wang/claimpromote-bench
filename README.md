# ClaimPromoteBench

**A benchmark for deciding when evidence justifies a change in research-claim status.**

> **v1 primary hidden study and post-v1 public formatting-control pilot complete; paper revision in submission verification.**  
> Hidden v1 numbers come from the validated recovered study. The public pilot appears as a separate post-v1 diagnostic with its own aggregate and provenance.

ClaimPromoteBench asks a narrow question: **given a mathematical research claim, its evidence, its current status, and a requested status change, should that change be allowed under a fixed policy?**

The benchmark evaluates requested claim-status transitions under a fixed policy. It keeps research status, computation, formal certification, and independent review separate and uses four possible actions:

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

Primary scoring uses only the 300 hidden instances. The public development data are for implementation and separately labeled descriptive work.

## Main hidden-study result

The hidden study records:

- **5,327 / 7,200 decisions (73.99%) are `FORMAT_ERROR`.**
- All **1,873 parseable raw model decisions are `ALLOW`.**
- Wherever the raw rates are defined, raw false-promotion rate is 1.00, valid-promotion recall is 1.00, and paired transition accuracy is 0.
- In the gate arm, the final false-promotion rate is 0 on parseable decisions, with catch rate 1 and false-block rate 0.
- Gate-arm decision coverage is low: 14.0%–49.0% for Qwen3-0.6B and 21.7%–48.3% for Qwen3-1.7B.

The gate uses the same fixed policy that defines the benchmark labels. Its conditional gate scores quantify implementation--policy agreement on parseable cases. Raw model behavior appears separately in the coverage, pair-accuracy, and flip-rate results.

### Format errors by model and arm

Each cell contains 900 decisions across three seeds.

| Model | Narrative | Ledger | Ledger + verifier | Ledger + verifier + gate |
|---|---:|---:|---:|---:|
| Qwen3-0.6B | 900 | 261 | 335 | 585 |
| Qwen3-1.7B | 900 | 900 | 900 | 546 |

All three seeds are kept in the study.

## Post-v1 public formatting-control pilot

The hidden v1 records contain parse status and structured decisions; original free-form text for older parse failures is absent. A separately labeled **post-v1 public diagnostic** tests the output contract directly. It uses the 20 public alpha pairs, the same two frozen model artifacts and llama.cpp runtime, seed 104729, and the `ledger_verifier` prompt. The free and constrained runs have identical prompt hashes, model artifact, runtime, seed, and hardware record; JSON-schema-constrained decoding is the sole registered difference.

The pilot is a post-v1 public one-seed formatting control with 160 decisions, executed on the existing free runner and frozen model artifacts.

| Model | Decoding | Decision coverage | Complete-pair coverage | Raw action accuracy | Raw pair accuracy |
|---|---|---:|---:|---:|---:|
| Qwen3-0.6B | Free | 0.75 | 0.70 | 0.50 | 0.00 |
| Qwen3-0.6B | JSON schema | 1.00 | 1.00 | 0.50 | 0.00 |
| Qwen3-1.7B | Free | 0.00 | 0.00 | undefined | undefined |
| Qwen3-1.7B | JSON schema | 0.95 | 0.90 | 0.50 | 0.00 |

Schema constraints remove 10 schema errors for Qwen3-0.6B and 38 for Qwen3-1.7B. Across the constrained runs, **78 / 80 decisions are parseable and 38 / 40 controlled pairs are complete; every parseable decision selects `ALLOW`, and raw pair accuracy and raw flip rate remain 0.** The two remaining constrained responses contain duplicate `reason_codes` entries and remain schema errors in scoring. The measured scope covers two frozen small models, public controlled pairs, and one seed.

Pilot provenance:

- source workflow: `32291482079`;
- source trigger: `f998a05fec36b84e59230fe241f1e9961647ad2e`;
- artifact-only recovery: `32297818154`;
- public aggregate: `v2/pilot-results/v2-public-pilot-study.json`;
- aggregate SHA-256: `sha256:83dbee4923bca6a0d1908083172190d7b81e2a5e9613c22e4929cfa25c0b264e`.

## Recovery of v1 evaluator failures

The original model calls finished, but some jobs later failed during evaluation because an output could pass the JSON schema while violating a cross-field rule, such as returning `ALLOW` without proposing the requested target state.

The recovery procedure preserved the original model outputs. It:

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

The raw hidden seed remains in GitHub Actions secret storage.

## Matched-comparison limitation

The preregistered comparison code groups runs by exact model artifact, runtime, seed, and hardware summary. Three hosted jobs recorded Python 3.11.16 while most recorded Python 3.11.15. Because the Python patch version is part of that identity, the final aggregate has nine groups instead of the intended six model×seed groups; only three contain all four arms.

The analysis retains the original identity grouping. Exact McNemar/Holm comparisons are available when both arms occur in the same recorded group. A later replication should pin the exact Python patch release.


## Machine-checkable credibility

Gold actions are generated by the public versioned policy and function as policy-conformance labels. Credibility is supported by machine-checkable evidence:

- the hidden dataset and exact prompts were committed before scored inference;
- the complete 24-run / 7,200-decision matrix is preserved and bound to immutable artifacts;
- artifact-only recovery reused the original model responses and preserved every legal model decision;
- a public pair-contract audit checks all 20 policy factors, recomputes every public label, and rejects unregistered pair differences;
- exact-rational numerical artifacts and pinned Lean artifacts are replayed in CI;
- shortcut and metamorphic audits test identifier, ordering, and irrelevant-evidence invariance;
- the post-v1 formatting control holds prompt, model, runtime, seed, and hardware fixed while changing only the response-format constraint;
- an anonymous supplementary bundle reruns the public checks without revealing author identity.

These checks make the implementation and evidence chain inspectable. The policy remains an author-defined benchmark rule, and the paper states that scope explicitly.

## Naturalistic evaluation preparation

A deterministic, unlabeled, pointer-only pool of 12 public CORE-Bench candidates is frozen in `v2/naturalistic-candidates.json`. Selection occurred without looking at ClaimPromoteBench model outputs. Every candidate remains `PENDING_SOURCE_LEVEL_REVIEW` and outside the scored ClaimPromoteBench set. Source-level licensing, a defensible transition question, evaluation time, and evidence snapshot must all be verified before inclusion.

## What the executable evidence means

Numerical cases use exact-rational finite-grid artifacts whose registered values, extrema, predicates, repetitions, and scope are recomputed. Formal cases use generated Lean sources under a pinned toolchain. Provenance, freshness, dependencies, contradictions, review independence, statement identity, and runtime success remain separate policy requirements.

A Lean check supports the exact formal statement that was checked. A finite computation supports its registered computational scope. Broader research status follows the remaining policy fields and evidence dependencies.

## Reproduce public checks

Python 3.11+:

```bash
python -m pip install -e ".[dev]"
python scripts/build_alpha.py
python -m claimpromotebench validate data/alpha
python -m claimpromotebench.shortcuts --dataset data/alpha --out work/shortcut-audit.json
python -m claimpromotebench.invariance --dataset data/alpha --out work/invariance-audit.json
python -m claimpromotebench.executable --fixtures fixtures/executable --out work/executable-fixtures.json
python scripts/validate_v1_release_results.py
python scripts/validate_v2_public_pilot_study.py
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

`FORMAT_ERROR` remains a separate outcome from `HOLD`.

## Scope

Related work includes SeekBench, Omni-Decision, EviGraph, ClaimLedger, SteerBench-Work, policy-aware web-agent evaluation, scientific claim-verification benchmarks, reproducibility benchmarks, and abstention/selective-action evaluations. ClaimPromoteBench contributes a controlled-pair benchmark for deciding whether typed scientific evidence justifies a requested research-claim status change, with executable evidence checks, a committed hidden test, separate reporting of raw model decisions and deterministic gate actions, and a public formatting control for the tested models.

## Paper and project status

- Technical report: `technical-report/main.tex`
- Submission checklist: `technical-report/SUBMISSION_GATE.md`
- v2 pilot aggregate: `v2/pilot-results/v2-public-pilot-study.json`
- v2 pilot protocol: `docs/ICLR_V2_LOW_COST_PROTOCOL.md`
- Naturalistic source registry: `docs/V2_NATURALISTIC_SOURCE_REGISTRY.md`
- Experiment protocol/history: `docs/EXPERIMENTS.md`
- Roadmap: `docs/ROADMAP.md`
- Related work: `docs/RELATED_WORK.md`
- AI assistance disclosure: `AI_ASSISTANCE.md`

The v1 hidden model outputs remain frozen, and all analyses use the existing artifacts. PR #20 remains a draft through full CI, ICLR/arXiv compilation, anonymity checks, page-limit checks, and final visual review.
