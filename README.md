# ClaimPromoteBench

**Policy-Governed Evidence-State Transitions for Mathematical Research Agents**

> **MAIN-BRANCH ALPHA SNAPSHOT — MODEL EXPERIMENTS IN THIS SNAPSHOT: PENDING**
>
> The alpha source tree documented below contains no quantitative model result, technical report,
> completed external review, or independent reproduction.

Later research and submission records live in the still-unmerged draft
[PR #20](https://github.com/f0909172434/claimpromote-bench/pull/20). Its current research scope is
paired regression tests for versioned agent policies. The branch contains OpenReview submission
and revision receipts; it also contains a later upload preview that is not a submission receipt.
The `PENDING` labels below describe this alpha snapshot, not the complete research program.
See [Repository and submission status](docs/REPOSITORY_STATUS.md) for dated, commit-bound pointers
and the separate CI and release boundaries. No later study or frozen result is imported here.

ClaimPromoteBench asks a narrow question: can a machine-checkable evidence ledger and a
versioned deterministic transition gate reduce policy-invalid claim promotion while
preserving valid promotion?

The benchmark evaluates a requested **evidence-state transition**. It is not a general truth
classifier, an answer-abstention benchmark, or a proof that a natural-language mathematical
claim is true. The alpha validates the public contracts, oracle, controlled-pair design,
offline baselines, gate semantics, ranking metrics, run-record evaluator, exact matched-arm
comparison pipeline, shortcut diagnostics, model-free metamorphic invariance, numerical
exact-grid recomputation, pinned Lean formal-artifact execution, and blinded human-review
infrastructure before any model experiment. Model execution, model consistency measurement,
and real independent review remain pending.

## Alpha snapshot on main

| Artifact | Checkable status |
|---|---|
| Dataset | 20 controlled pairs / 40 instances; six mathematical-evidence families |
| Gold decision | Versioned public policy + dependency closure + artifact integrity; numerical and formal `ALLOW` cases additionally require executable artifact-to-scope agreement |
| Non-model baselines | `always_allow`, `always_hold`, deterministic `policy_oracle` |
| Shortcut audit | Leave-one-pair-out metadata-only and shallow-structure diagnostics run in CI |
| Metamorphic invariance audit | 331 semantics-preserving variants across all 40 items; 1,324 four-arm prompt renderings; zero schema, artifact, oracle, or prompt-expectation failures |
| Intervention renderers | Semantic narrative, typed ledger, ledger + passive verifier, ledger + verifier + gate notice |
| Evaluator | Fail-closed actions, tie-aware AUPRC, paired score ranking, family diagnostics, pair bootstrap intervals |
| Study comparison | Hash-bound run/study IDs, exact matched McNemar tests, Holm correction, metric deltas |
| Executable numerical alpha | Four numerical pairs / eight items use four exact-rational finite-grid JSON artifacts, recomputed during dataset validation |
| Executable numerical negative suite | Tamper, scope, protocol, preregistration, and repetition-digest failures are checked independently |
| Executable formal alpha | Three formal pairs / six items use three generated Lean sources under `leanprover/lean4:v4.33.0`; CI runs `lake build`, `leanchecker`, one positive fixture, and two negative fixtures |
| Blinded human-review workflow | HMAC-blinded packets, unbiased drafts, exact-coverage submission validation, reviewer-vs-gold and inter-reviewer statistics, disagreement export, and adjudication gate are implemented |
| Published independent reviews | **PENDING** — `reviews/` contains no completed reviewer package or empirical agreement result |
| Model runs | **PENDING** — no Qwen result is reported |
| Hidden test commitment | **PENDING** — no digest exists until 150 test pairs are frozen |
| Technical report | **NOT YET PUBLISHED** |
| Independent model reproduction | **PENDING** |

The alpha family distribution is `4/4/3/3/3/3`: dependency closure, numerical scope,
runtime failure, stale or contradictory evidence, independent provenance, and formal
certificate identity. Each pair keeps the claim and requested state fixed and changes one
policy prerequisite. The invalid member is balanced between neutral `a` and `b` IDs.

The four numerical pairs are bound to four generated exact-rational JSON artifacts. Both
members of each pair share identical artifact bytes. Dataset validation checks their paths
and SHA-256 values, validates the registered protocol, and recomputes every grid value,
extremum, predicate, and repetition digest. An `ALLOW` member must also match the artifact's
repetitions, preregistration, closed domain, runtime result, and true predicate. Numerical
claim text is limited to the registered rational grid; no continuous-domain conclusion is
made.

The three formal pairs are bound to three generated Lean source artifacts. Their natural-
language claims name the exact elementary declarations being compiled: right-zero addition,
left-zero addition, and conjunction commutativity. Both members of a pair share identical
compilable source bytes; the invalid member changes only the registered statement, claim, or
toolchain scope field. The exact `lean-toolchain` file is SHA-256-bound, CI builds the Lake
package, and `leanchecker ClaimPromoteFormal` replays the compiled library. This establishes
kernel acceptance of those exact declarations only; it does not establish novelty, a broader
informal theorem, independent review, or research resolution.

The remaining thirteen pairs retain synthetic two-line artifacts because their current role
is to test dependency, runtime, staleness, contradiction, and provenance transition policy.

The review workflow can produce a procedurally blinded packet, validate complete independent
submissions, unblind only after review closure, and compute per-reviewer action agreement,
confusion matrices, reason-set agreement, pairwise raw agreement, Cohen kappa, unanimous
agreement, and Fleiss kappa. It gates on every reviewer reaching at least 0.80 action
agreement with frozen gold and the minimum reviewer-pair raw action agreement reaching at
least 0.80. Every action or reason disagreement requires adjudication. No actual reviewer or
agreement value is present yet.

The metamorphic audit applies nine registered transformations to every applicable item. It
renames evidence, principal, environment, and provenance-run identifiers; changes evidence
presentation order; and inserts unrelated passing, failed, stale, or resolved evidence. It
then re-runs public schemas, artifact hashes, numerical and Lean bindings, the complete oracle
decision, and all four prompt renderers. Evidence IDs are mapped back before comparison. The
current alpha generated 331 variants and 1,324 prompt renderings with zero failures. This is
a deterministic pipeline result, not a claim that any language model is invariant.

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

Python 3.11 or newer is required. The Python-only checks use no model, GPU, or paid API.
Formal execution additionally requires the pinned Lean toolchain; installing it may download
the public Lean release when it is not already present.

```bash
python -m pip install -e ".[dev]"
python scripts/build_alpha.py
python -m claimpromotebench validate data/alpha
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

With Elan installed, run the formal gate:

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

`validate data/alpha` recomputes the four manifest-bound numerical artifacts and verifies the
source, identity markers, and toolchain binding of the three formal artifacts in addition to
checking schemas, pair controls, hashes, policy decisions, and gold labels. The invariance
audit generates semantics-preserving variants, revalidates every applicable artifact
binding, compares normalized complete oracle decisions, and renders every intervention arm.
The standalone numerical suite performs bounded exact-rational recomputation over positive
and negative finite-grid fixtures. The formal command compiles three unique alpha sources and
requires one valid plus two intentionally invalid Lean fixtures to have their declared
outcomes. These gates do not establish a result outside their registered transformations,
finite grids, or exact Lean statements. See
[Metamorphic invariance audit](docs/INVARIANCE_AUDIT.md),
[Executable numerical fixtures](docs/EXECUTABLE_FIXTURES.md),
[Pinned Lean formal alpha](docs/FORMAL_FIXTURES.md),
[Blinded review workflow](docs/REVIEW_WORKFLOW.md), and
[Shortcut audit](docs/SHORTCUT_AUDIT.md) for the frozen information and scope boundaries.

Generate and score all three offline baselines:

```bash
python -m claimpromotebench baseline always_allow --out work/always-allow.jsonl
python -m claimpromotebench baseline always_hold --out work/always-hold.jsonl
python -m claimpromotebench baseline policy_oracle --out work/policy-oracle.jsonl
python -m claimpromotebench evaluate --gold data/alpha/gold.jsonl --runs work/policy-oracle.jsonl
```

The evaluation JSON includes the full threshold-grouped precision-recall curve,
`auprc_stepwise`, prevalence lift, paired valid-versus-invalid score ranking, pair-bootstrap
intervals, and per-family diagnostics. See [Experiment protocol](docs/EXPERIMENTS.md) for the
exact definitions.

Complete model run-record files can be evaluated individually or accumulated directly:

```bash
python -m claimpromotebench evaluate-runs \
  --gold data/alpha/gold.jsonl \
  --runs work/qwen3-0.6b-narrative-seed-104729.jsonl \
  --out work/qwen3-0.6b-narrative-seed-104729.report.json

python -m claimpromotebench compare-runs \
  --gold data/alpha/gold.jsonl \
  --runs work/qwen3-0.6b-*-seed-104729.jsonl \
  --out work/qwen3-0.6b-seed-104729.study.json
```

`evaluate-runs` emits a path-independent run ID tied to the dataset fingerprint, immutable
model/run identity, and run-file hash. `compare-runs` accepts any number of complete run files,
deduplicates content and run identities, groups matched arms, reports missing arms, applies
exact McNemar tests with Holm correction, and emits a deterministic study ID. Re-running the
command with additional run files produces a larger cumulative study without rewriting prior
records.

See [Reproduction](docs/REPRODUCTION.md) for clean-environment steps and expected structural
checks. A passing oracle baseline or metamorphic audit proves internal pipeline agreement,
not a model result.

## Independent review commands

Prepare an active private packet and initialize a reviewer draft:

```bash
cpb-review prepare \
  --dataset data/alpha \
  --out work/review-alpha

cpb-review init-submission \
  --package work/review-alpha \
  --reviewer-id reviewer-01 \
  --out reviewer-01.json
```

After at least two independent reviewers have submitted and all decisions are frozen, unblind
and compute the deterministic report:

```bash
cpb-review-report analyze \
  --dataset data/alpha \
  --package work/review-alpha \
  --out work/review-alpha/review-report.json
```

When disagreements exist, create and validate complete adjudication:

```bash
cpb-review-report init-adjudication \
  --report work/review-alpha/review-report.json \
  --adjudicator-id adjudicator-01 \
  --out work/review-alpha/adjudication.json

cpb-review-report validate-adjudication \
  --dataset data/alpha \
  --package work/review-alpha \
  --report work/review-alpha/review-report.json \
  --adjudication work/review-alpha/adjudication.json
```

A failed numeric threshold remains `REVISION_REQUIRED`; adjudication cannot convert it into a
pass. See [the full workflow](docs/REVIEW_WORKFLOW.md).

## Public contracts

- `schemas/benchmark-input.schema.json`: model-independent benchmark input.
- `schemas/agent-decision.schema.json`: required JSON decision.
- `schemas/executable-fixture-case.schema.json`: positive/negative executable numerical cases.
- `schemas/invariance-report.schema.json`: deterministic metamorphic audit result and failure
  diagnostics.
- `schemas/review-packet-item.schema.json`: blinded reviewer-facing item.
- `schemas/review-packet-manifest.schema.json`: immutable packet identity.
- `schemas/review-private-key.schema.json`: private HMAC mapping used only after review closure.
- `schemas/review-submission.schema.json`: complete independent reviewer submission.
- `schemas/review-analysis.schema.json`: deterministic agreement and disagreement report.
- `schemas/review-adjudication.schema.json`: exact disagreement disposition record.
- `policies/math-evidence-transition-1.0.2-alpha.json`: current schema-validated alpha
  decision contract, thresholds, and pinned formal trust base.
- `policies/math-evidence-transition-1.0.1-alpha.json`: retained superseded policy for
  historical inspection; it is not the policy bound by the current alpha manifest.
- `data/alpha/author-items.jsonl`: auditable authoring source with gold labels.
- `data/alpha/inputs.jsonl`: public input with gold removed.
- `data/alpha/gold.jsonl`: scorer labels generated from the authoring source.
- `data/alpha/pairs.json`: controlled factors and permitted JSON-pointer differences.
- `data/alpha/manifest.json`: frozen evaluation time and committed file hashes.
- `data/alpha/artifacts/*.json`: manifest-bound exact-rational artifacts used by the four
  numerical controlled pairs.
- `data/alpha/artifacts/ClaimPromoteFormal/*.lean`: three pair-specific formal artifacts.
- `data/alpha/lean-toolchain`, `lakefile.toml`, and `lake-manifest.json`: pinned formal package
  environment.
- `fixtures/executable/`: standalone positive and negative exact-rational fixture suite.
- `fixtures/formal/`: one passing and two rejected Lean fixture programs.
- `reviews/`: completed, unblinded, immutable review packages only; currently empty apart from
  instructions.

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
paired transition accuracy. Ranking diagnostics include tie-aware stepwise AUPRC and direct
within-pair score ordering. Reports must separate intent false promotions from effective
post-gate false promotions. A successful veto is a system effect, not improved model
calibration. See [Experiment protocol](docs/EXPERIMENTS.md).

`evaluate-runs` validates complete run records, refuses `FORMAT_ERROR` as a silent hold,
scores raw intent and post-gate decisions separately, and reports gate plus operational
metrics. Format errors reduce explicit coverage and are included in a worst-case safety
sensitivity analysis. Family stratification and matched arm comparison are automatic.
`compare-runs` defaults to zero bootstrap resamples because its exact matched tests and metric
deltas do not require recomputing every run interval; a positive sample count can be requested
when a cumulative report also needs per-run intervals.

The registered metamorphic transformations are intended to become a separate consistency
slice for future model runs. Any model consistency score must be reported separately from
ordinary action accuracy and AUPRC, because a correct base decision can still be unstable
under a semantics-preserving prompt transformation.

## Research boundary

The contribution is deliberately narrower than abstention, static scientific-claim
verification, claim-level specificity control, or general evidence audit trails. The working
claim and a comparison matrix are in [Related work](docs/RELATED_WORK.md). We use "we did not
find a public benchmark directly evaluating policy-governed research-claim state
transitions," not an unqualified first-of-kind claim.

Executable artifact success is also narrower than research correctness. Exact-rational grid
recomputation supports a finite computational state only. Lean kernel acceptance supports the
exact formal declaration only. Neither substitutes for scope alignment, novelty assessment,
independent review, or a model experiment.

Review infrastructure is not review evidence. A generated packet, passing unit tests, or an
empty `reviews/` directory does not establish external agreement. Only completed independent
submissions, a reproducible unblinded report, and complete adjudication can produce a review
gate result. A negative result remains publishable and requires revision rather than
concealment.

Metamorphic oracle invariance is not model robustness. The 331 passing variants establish
only that the current deterministic schemas, artifact bindings, oracle, and prompt renderer
satisfy the nine registered equivalence expectations. Unregistered transformations and model
responses remain unmeasured.

## Status and accountability

- [Research decisions](RESEARCH_DECISIONS.md) records assumptions, rejected alternatives,
  negative results, and version changes.
- [AI assistance](AI_ASSISTANCE.md) separates tool assistance from human responsibility.
- [Roadmap](docs/ROADMAP.md) exposes the 2026–2027 gates without marking future work complete.
- [Metamorphic invariance audit](docs/INVARIANCE_AUDIT.md) defines the registered equivalence
  transformations and model-consistency boundary.
- [Mentor review](docs/MENTOR_REVIEW.md) defines the external-review gate.
- [Blinded review workflow](docs/REVIEW_WORKFLOW.md) defines preparation, statistics,
  adjudication, and publication.
- `technical-report/` remains explicitly unpublished until a reproducible pilot exists.

Created and maintained by **Chih-Kai Wang**, B.S. student, Mathematics Education Division,
Department of Mathematics and Information Education, National Taipei University of
Education. Expected 2028.

## License

Code and the alpha dataset are released under the [MIT License](LICENSE). Artifact hashes are
integrity digests, not digital signatures, identity proofs, or provenance guarantees.
