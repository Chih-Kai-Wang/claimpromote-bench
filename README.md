# ClaimPromoteBench

**Policy-Governed Evidence-State Transitions for Mathematical Research Agents**

> **ALPHA RESEARCH SCAFFOLD — MODEL EXPERIMENTS: PENDING**  
> No quantitative model result, technical report, external review, or independent
> reproduction is claimed in this repository yet.

ClaimPromoteBench asks a narrow question: can a machine-checkable evidence ledger and a
versioned deterministic transition gate reduce policy-invalid claim promotion while
preserving valid promotion?

The benchmark evaluates a requested **evidence-state transition**. It is not a general truth
classifier, an answer-abstention benchmark, or a proof that a natural-language mathematical
claim is true. The alpha validates the public contracts, oracle, controlled-pair design,
offline baselines, gate semantics, baseline evaluator, and alpha run-record evaluator
before any model experiment. The full arm-comparison automation remains pending.

## Current alpha

| Artifact | Checkable status |
|---|---|
| Dataset | 20 controlled pairs / 40 instances; six mathematical-evidence families |
| Gold decision | Versioned public policy + dependency closure + executable integrity/policy checks over synthetic fixtures |
| Non-model baselines | `always_allow`, `always_hold`, deterministic `policy_oracle` |
| Intervention renderers | Semantic narrative, typed ledger, ledger + passive verifier, ledger + verifier + gate notice |
| Model runs | **PENDING** — no Qwen result is reported |
| Hidden test commitment | **PENDING** — no digest exists until 150 test pairs are frozen |
| Technical report | **NOT YET PUBLISHED** |
| External review / reproduction | **PENDING** |

The alpha family distribution is `4/4/3/3/3/3`: dependency closure, numerical scope,
runtime failure, stale or contradictory evidence, independent provenance, and formal
certificate identity. Each pair keeps the claim and requested state fixed and changes one
policy prerequisite. The invalid member is balanced between neutral `a` and `b` IDs.

Alpha evidence artifacts are synthetic two-line fixtures. The implementation executes their
path/hash integrity checks and the policy oracle; it does not run Lean, numerical software,
or an external review process. Type-specific executable fixtures are a precondition for model
experiments.

## Orthogonal state

```text
ClaimState
  research_status:    PROPOSED | OPEN | RESOLVED
  computation_status: NONE | COMPUTATIONAL
  formal_status:      NONE | FORMALLY_CERTIFIED
  review_status:      UNREVIEWED | INDEPENDENTLY_VERIFIED
```

These axes are not a single confidence ladder. A Lean certificate applies only to the exact
formal statement and pinned trust base it checked. A completed numerical run remains
computational evidence. Independent reproduction is separate from both.

## Reproduce the alpha checks

Python 3.11 or newer is required. No network, model, GPU, or paid API is used after the
development dependencies are installed.

```bash
python -m pip install -e ".[dev]"
python scripts/build_alpha.py
python -m claimpromotebench validate data/alpha
python -m pytest --cov --cov-branch --cov-fail-under=80
```

Generate and score all three offline baselines:

```bash
python -m claimpromotebench baseline always_allow --out work/always-allow.jsonl
python -m claimpromotebench baseline always_hold --out work/always-hold.jsonl
python -m claimpromotebench baseline policy_oracle --out work/policy-oracle.jsonl
python -m claimpromotebench evaluate --gold data/alpha/gold.jsonl --runs work/policy-oracle.jsonl
```

See [Reproduction](docs/REPRODUCTION.md) for clean-environment steps and expected structural
checks. A passing oracle baseline proves internal pipeline agreement, not a research result.

## Public contracts

- `schemas/benchmark-input.schema.json`: model-independent benchmark input.
- `schemas/agent-decision.schema.json`: required JSON decision.
- `policies/math-evidence-transition-1.0.1-alpha.json`: complete, schema-validated alpha
  decision contract, thresholds, and trust base.
- `data/alpha/author-items.jsonl`: auditable authoring source with gold labels.
- `data/alpha/inputs.jsonl`: public input with gold removed.
- `data/alpha/gold.jsonl`: scorer labels generated from the authoring source.
- `data/alpha/pairs.json`: controlled factors and permitted JSON-pointer differences.
- `data/alpha/manifest.json`: frozen evaluation time and committed file hashes.

Prompt renderers remove item IDs, pair IDs, split labels, family labels, and gold fields. A
missing or malformed model output is a `FORMAT_ERROR`; it is never silently counted as
`HOLD`.

## Intended experiments

The frozen full-study design uses two local Qwen3 sizes, four intervention arms, 400
instances, and three seeds: 9,600 short decisions. Model artifacts, 4-bit quantization,
llama.cpp commit, prompts, and hardware must be hash-bound before the test set is opened.
The checked-in model configurations are currently `PENDING_ARTIFACT_FREEZE`; they are plans,
not executed runs.

Primary metrics are false promotion rate, valid promotion recall / false hold rate, and
paired transition accuracy. Reports must separate intent false promotions from effective
post-gate false promotions. A successful veto is a system effect, not improved model
calibration. See [Experiment protocol](docs/EXPERIMENTS.md).

`evaluate-runs` validates complete run records, refuses `FORMAT_ERROR` as a silent hold,
scores raw intent and post-gate decisions separately, and reports gate plus operational
metrics. Format errors reduce explicit coverage and are included in a worst-case safety
sensitivity analysis. Family/model stratification and automated six-way arm comparison remain
pre-run gates.

## Research boundary

The contribution is deliberately narrower than abstention, static scientific-claim
verification, claim-level specificity control, or general evidence audit trails. The working
claim and a comparison matrix are in [Related work](docs/RELATED_WORK.md). We use "we did not
find a public benchmark directly evaluating policy-governed research-claim state
transitions," not an unqualified first-of-kind claim.

## Status and accountability

- [Research decisions](RESEARCH_DECISIONS.md) records assumptions, rejected alternatives,
  negative results, and version changes.
- [AI assistance](AI_ASSISTANCE.md) separates tool assistance from human responsibility.
- [Roadmap](docs/ROADMAP.md) exposes the 2026–2027 gates without marking future work complete.
- [Mentor review](docs/MENTOR_REVIEW.md) defines the external-review gate.
- `technical-report/` remains explicitly unpublished until a reproducible pilot exists.

Created and maintained by **Chih-Kai Wang**, B.S. student, Mathematics Education Division,
Department of Mathematics and Information Education, National Taipei University of
Education. Expected 2028.

## License

Code and the alpha dataset are released under the [MIT License](LICENSE). Artifact hashes are
integrity digests, not digital signatures, identity proofs, or provenance guarantees.
