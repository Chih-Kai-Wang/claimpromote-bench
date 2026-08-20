# ClaimPromoteBench: Evaluating Whether Evidence Justifies Claim-State Transitions in AI Research Agents

**A benchmark for deciding when evidence justifies a change in research-claim status.**

> **SCIENTIFIC_RC_READY: v1 hidden study, accuracy-blind capable-model hidden extension, public formatting control, and GPT-5.4 public-development follow-up complete; account-side submission pending.**
> Hidden v1 numbers come from the validated recovered study. Every later study remains separately labeled with its own frozen plan, aggregate, and interpretation boundary.

ClaimPromoteBench asks a narrow question: **given a mathematical research claim, its evidence, its current status, and a requested status change, should that change be allowed under a fixed policy?**

The benchmark evaluates requested claim-status transitions under a fixed policy. It keeps research status, computation, formal certification, and independent review separate and uses four possible actions:

`ALLOW` · `HOLD` · `DEMOTE` · `ESCALATE`

A deterministic one-way gate can replace a parseable invalid `ALLOW` with the policy-oracle action. This is reported only as an implementation check, separately from model behavior.

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

## Original v1 hidden-study result

The hidden study records:

- **5,327 / 7,200 decisions (73.99%) are `FORMAT_ERROR`.**
- All **1,873 parseable raw model decisions are `ALLOW`.**
- End-to-end raw action accuracy is **960 / 7,200 (13.33%)** when every format error remains incorrect.
- End-to-end raw controlled-pair accuracy is **0 / 3,600**.
- Conditional FPR and VPR are both 1.00 wherever defined, a direct consequence of the uniform `ALLOW` action distribution.

The gate uses the same policy oracle that defines the evaluation labels, so its agreement is mechanically self-referential and provides no independent model-performance evidence.

### Format errors by model and arm

Each cell contains 900 decisions across three seeds.

| Model | Narrative | Ledger | Ledger + verifier | Ledger + verifier + gate |
|---|---:|---:|---:|---:|
| Qwen3-0.6B | 900 | 261 | 335 | 585 |
| Qwen3-1.7B | 900 | 900 | 900 | 546 |

All three seeds are kept in the study.

## Exploratory capable-model hidden extension

After the v1 and public-development outcomes were known, a separate protocol was frozen on the
unchanged 150-pair / 300-instance hidden split. It registered six model labels plus one same-label
service-path replication. Transport and parser error classes led to registered adapter amendments
and requalification on the same fixed 12 pilot inputs. The recorded inspection procedure excluded
actions, raw responses, gold comparisons, and accuracy, but analyses were not independently
escrowed; the study is therefore adaptive and exploratory.

Fourteen pilot attempts were executed and are all released. Two lanes reached terminal
qualification and received one fresh 300-item no-retry pass. The other five stopped before full
scoring, so no 300-item accuracy is reported for them. The table excludes the 12 reused pilot
instances and six pairs as a post-hoc sensitivity.

| Full-pass lane | Decision coverage | Complete-pair coverage | E2E action accuracy | E2E pair accuracy | Raw FPR |
|---|---:|---:|---:|---:|---:|
| Qwen3.7-Max | 0.990 | 0.979 | 0.938 | 0.875 | 0.071 |
| DeepSeek-V4-Flash | 0.913 | 0.826 | 0.628 | 0.257 | 0.689 |
| Always `ALLOW` | 1.000 | 1.000 | 0.500 | 0.000 | 1.000 |

On the nonpilot subset, Qwen3.7-Max gives 270/288 correct actions and 126/144 correct controlled
pairs; DeepSeek-V4-Flash gives 181/288 and 37/144. Including freshly regenerated pilot inputs gives
the archived full-pass counts 282/300 and 132/150, and 188/300 and 38/150. These are descriptive
one-pass service-lane results; they do not identify causal provider, tier, or serving-stack effects.
Both completed lanes score 0/8 on the nonpilot `DEMOTE` cases; four-action recall and confusion are
reported in the aggregate rather than hidden behind overall item accuracy.

- Compact aggregate: `v2/capable-hidden-results/capable-hidden-study.json`
- Aggregate SHA-256: `sha256:abfc25e9a01018bdc269b683cbf54ca423264f62cacbbfee0d504ef10beb6f91`
- Reviewer evidence: all 14 pilot attempts, two full runs, three historical request/parser
  snapshots, exact prompt packet, released hidden inputs and labels, item-level raw responses,
  parser replay, analyses, canonical-selection map, and recomputation checks
- Excluded: private construction seed

## Post-v1 public formatting-control pilot

The hidden v1 records contain parse status and structured decisions; original free-form text for older parse failures is absent. A separately labeled **post-v1 public diagnostic** tests the output contract directly. It uses the 20 public alpha pairs, the same two frozen model artifacts and llama.cpp runtime, seed 104729, and the `ledger_verifier` prompt. The free and constrained runs have identical prompt hashes, model artifact, runtime, seed, and hardware record; JSON-schema-constrained decoding is the sole registered difference.

The pilot is a post-v1 public one-seed formatting control with 160 decisions, executed on the existing free runner and frozen model artifacts.

| Model | Decoding | Decision coverage | Complete-pair coverage | E2E action accuracy | E2E pair accuracy |
|---|---|---:|---:|---:|---:|
| Qwen3-0.6B | Free | 0.75 | 0.70 | 0.375 | 0.00 |
| Qwen3-0.6B | JSON schema | 1.00 | 1.00 | 0.500 | 0.00 |
| Qwen3-1.7B | Free | 0.00 | 0.00 | 0.000 | 0.00 |
| Qwen3-1.7B | JSON schema | 0.95 | 0.90 | 0.475 | 0.00 |

Schema constraints remove 10 schema errors for Qwen3-0.6B and 38 for Qwen3-1.7B. Across the constrained runs, **78 / 80 decisions are parseable and 38 / 40 controlled pairs are complete; every parseable decision selects `ALLOW`, and raw pair accuracy and raw flip rate remain 0.** The two remaining constrained responses contain duplicate `reason_codes` entries and remain schema errors in scoring. The measured scope covers two frozen small models, public controlled pairs, and one seed.

Pilot provenance:

- source workflow: `32291482079`;
- source trigger: `f998a05fec36b84e59230fe241f1e9961647ad2e`;
- artifact-only recovery: `32297818154`;
- public aggregate: `v2/pilot-results/v2-public-pilot-study.json`;
- aggregate SHA-256: `sha256:eb2af5fcfce8466306a208a707e0046b389f2fd656d25d549f784acfc04199e5`.

## Post-protocol GPT-5.4 public-development follow-up

A separately frozen API-model extension evaluates GPT-5.4 on the 50-pair / 100-instance public development split with strict JSON Schema and zero retries. A 12-instance family-balanced pilot passes the accuracy-blind interface gate and triggers one fresh full pass.

| Phase | Records | Decision coverage | Complete-pair coverage | E2E action accuracy | E2E pair accuracy | Pair flip rate |
|---|---:|---:|---:|---:|---:|---:|
| Revised pilot | 12 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| Full public development | 100 | 0.99 | 0.98 | 0.99 | 0.98 | 1.00 |

The full pass contains 99 parseable decisions: 50 `ALLOW`, 45 `HOLD`, 2 `DEMOTE`, and 2 `ESCALATE`. All 99 match the policy oracle; all 49 complete pairs are correct and change with the decisive evidence. End-to-end action and pair accuracy are therefore 0.99 and 0.98. This result establishes solvability on the public split; the separately frozen capable-model study supplies hidden-split evidence for its two qualified lanes.

Follow-up provenance:

- frozen revision commit: `3634ce85785e9b516abc519711fff12388307331`;
- revised plan SHA-256: `sha256:8dd8d4887f48f053202c0ae6e51ca492ef9a4bc07e93ea101c7a918b2c515e5a`;
- pilot run SHA-256: `sha256:ba6ba3057d96443af989e5c6e28f405d891c0504cdb7d997a9c83453addda355`;
- full run SHA-256: `sha256:0054a4d73bdbd81e0ba31871ab4e51140ebf5f2421feda7cce40d57639b53ef7`;
- compact result: `v2/stronger-model-results/openrouter-openai-gpt-5.4-v2-study.json`;
- computed OpenRouter cost: **$2.1883195** across pilot and full phases.

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

Oracle actions are generated by the public versioned policy and function as policy-conformance labels. Credibility is supported by machine-checkable evidence:

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
python scripts/audit_public_pair_contracts.py --dataset data/alpha --out work/public-pair-contract-audit.json
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

Related work includes SeekBench, Omni-Decision, EviGraph, ClaimLedger, scientific
claim-verification benchmarks, reproducibility benchmarks, hypothesis-falsification systems,
abstention evaluation, and formal-specification benchmarks. ClaimPromoteBench contributes a
controlled-pair benchmark for deciding whether typed scientific evidence justifies a requested
research-claim status change, with executable evidence checks, a committed hidden test, separate
reporting of raw model decisions and deterministic gate actions, and a public formatting control
for the tested models.

## Paper and project status

- Technical report: `technical-report/main.tex`
- Submission checklist: `technical-report/SUBMISSION_GATE_V2.md`
- Copy-ready submission metadata: `docs/SUBMISSION_METADATA.md`
- v2 pilot aggregate: `v2/pilot-results/v2-public-pilot-study.json`
- v2 pilot protocol: `docs/ICLR_V2_LOW_COST_PROTOCOL.md`
- Naturalistic source registry: `docs/V2_NATURALISTIC_SOURCE_REGISTRY.md`
- Experiment protocol/history: `docs/EXPERIMENTS.md`
- Roadmap: `docs/ROADMAP.md`
- Related work: `docs/RELATED_WORK.md`
- AI assistance disclosure: `AI_ASSISTANCE.md`

The v1 hidden model outputs remain frozen, and all analyses use the existing artifacts. PR #20
remains Draft and unmerged until the author completes account-side preview checks and explicitly
authorizes any readiness or merge transition.
