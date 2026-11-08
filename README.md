# ClaimPromoteBench

**Policy-Governed Evidence-State Transitions for Mathematical Research Agents**

> **Status of this snapshot.** The `main` branch holds an alpha snapshot, and its model experiments are still PENDING.
> The alpha source tree described below contains no quantitative model result, technical report,
> completed external review or independent reproduction.

Later research and submission records live in draft
[PR #20](https://github.com/Chih-Kai-Wang/claimpromote-bench/pull/20), which has not been merged. Its
current research scope is paired regression tests for versioned agent policies. The branch contains
OpenReview submission and revision receipts. It also contains a later upload preview, which is not a
submission receipt. The `PENDING` labels in this README describe the alpha snapshot only, not the
whole research program. [Repository and submission status](docs/REPOSITORY_STATUS.md) gives dated
pointers tied to specific commits and keeps the CI and release boundaries separate. Nothing from a
later study or frozen result is imported here.

ClaimPromoteBench asks a narrow question. Can a machine-checkable evidence ledger, combined with a
versioned deterministic gate on state transitions, reduce claim promotions that the policy does not
allow, while keeping the promotions it does allow?

The benchmark evaluates a requested **evidence-state transition**. It is not a general truth
classifier or an answer-abstention benchmark, and it does not prove that a natural-language
mathematical claim is true. Before any model experiment, the alpha validates the public contracts,
the oracle, the controlled-pair design, the offline baselines, the gate semantics, the ranking
metrics, the run-record evaluator and the exact matched-arm comparison pipeline. It also validates
the shortcut diagnostics, model-free metamorphic invariance, exact recomputation of numerical grids,
execution of pinned Lean formal artifacts and the blinded human-review infrastructure. Model
execution, measurement of model consistency and real independent review are still pending.

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
The alpha family distribution is `4/4/3/3/3/3` across dependency closure, numerical scope,
runtime failure, stale or contradictory evidence, independent provenance and formal certificate
identity. Within each pair, the claim and the requested state stay fixed and exactly one policy
prerequisite changes. The invalid member is split evenly between the neutral IDs `a` and `b`.

The four numerical pairs are bound to four generated exact-rational JSON artifacts. Both members
of a pair share identical artifact bytes. Dataset validation checks the artifact paths and SHA-256
values, validates the registered protocol, and recomputes every grid value, extremum, predicate and
repetition digest. An `ALLOW` member must also match the artifact's repetitions, preregistration,
closed domain, runtime result and true predicate. Numerical claims speak only about the registered
rational grid and draw no conclusion about a continuous domain.

The three formal pairs are bound to three generated Lean source artifacts. Their natural-language
claims name the exact elementary declarations being compiled: right-zero addition, left-zero
addition and conjunction commutativity. Both members of a pair share identical compilable source
bytes. The invalid member changes only the registered statement, claim or toolchain scope field.
The exact `lean-toolchain` file is bound by its SHA-256, CI builds the Lake package, and
`leanchecker ClaimPromoteFormal` replays the compiled library. This shows that the Lean kernel
accepts those exact declarations and nothing more. It does not establish novelty, a broader
informal theorem, independent review or the resolution of a research question.

The remaining thirteen pairs keep synthetic two-line artifacts, because their current job is to
test the transition policy for dependency, runtime, staleness, contradiction and provenance.

The review workflow can produce a procedurally blinded packet, validate complete independent
submissions, and unblind only after review closes. It then computes, for each reviewer, action
agreement, confusion matrices and reason-set agreement, and across reviewers, pairwise raw
agreement, Cohen kappa, unanimous agreement and Fleiss kappa. The gate requires every reviewer to
reach at least 0.80 action agreement with the frozen gold labels, and the lowest raw action
agreement between any two reviewers to reach at least 0.80. Every disagreement on an action or a
reason requires adjudication. No real reviewer has taken part yet, so no agreement value exists.

The metamorphic audit applies nine registered transformations to every item where they apply. It
renames evidence, principal, environment and provenance-run identifiers, changes the order in which
evidence is presented, and inserts unrelated passing, failed, stale or resolved evidence. It then
re-runs the public schemas, artifact hashes, numerical and Lean bindings, the complete oracle
decision and all four prompt renderers. Evidence IDs are mapped back before comparison. The current
alpha generated 331 variants and 1,324 prompt renderings with zero failures. This is a result about
the deterministic pipeline. It does not claim that any language model is invariant.

## Orthogonal state

```text
ClaimState
  research_status:    PROPOSED | OPEN | RESOLVED
  computation_status: NONE | COMPUTATIONAL
  formal_status:      NONE | FORMALLY_CERTIFIED
  review_status:      UNREVIEWED | INDEPENDENTLY_VERIFIED
```

These axes do not form a single confidence ladder. A Lean certificate applies only to the exact
formal statement and pinned trust base that it checked. A completed numerical run is still
computational evidence. Independent reproduction is separate from both.

## Reproduce the alpha checks

You need Python 3.11 or newer. The Python-only checks use no model, GPU or paid API. Formal
execution also needs the pinned Lean toolchain, and installing it may download the public Lean
release if it is not already present.

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

Besides checking schemas, pair controls, hashes, policy decisions and gold labels,
`validate data/alpha` recomputes the four manifest-bound numerical artifacts. It also verifies the source,
the identity markers and the toolchain binding of the three formal artifacts. The invariance audit
generates semantics-preserving variants, revalidates every applicable artifact binding, compares
the normalized complete oracle decisions and renders every intervention arm. The standalone
numerical suite performs bounded exact-rational recomputation over positive and negative
finite-grid fixtures. The formal command compiles the three unique alpha sources and requires one
valid and two intentionally invalid Lean fixtures to produce their declared outcomes. None of these
gates establishes anything beyond its registered transformations, finite grids or exact Lean
statements. The frozen information and scope boundaries are documented in
[Metamorphic invariance audit](docs/INVARIANCE_AUDIT.md),
[Executable numerical fixtures](docs/EXECUTABLE_FIXTURES.md),
[Pinned Lean formal alpha](docs/FORMAL_FIXTURES.md),
[Blinded review workflow](docs/REVIEW_WORKFLOW.md), and
[Shortcut audit](docs/SHORTCUT_AUDIT.md).

Generate and score all three offline baselines:

```bash
python -m claimpromotebench baseline always_allow --out work/always-allow.jsonl
python -m claimpromotebench baseline always_hold --out work/always-hold.jsonl
python -m claimpromotebench baseline policy_oracle --out work/policy-oracle.jsonl
python -m claimpromotebench evaluate --gold data/alpha/gold.jsonl --runs work/policy-oracle.jsonl
```

The evaluation JSON includes the full precision-recall curve grouped by threshold, `auprc_stepwise`,
the lift over prevalence, paired score ranking of valid against invalid items, pair-bootstrap
intervals and per-family diagnostics. [Experiment protocol](docs/EXPERIMENTS.md) gives the exact
definitions.

Complete model run-record files can be evaluated one at a time or accumulated into a study:

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

`evaluate-runs` emits a run ID that does not depend on the file path. The ID is tied to the
dataset fingerprint, the immutable model and run identity, and the hash of the run file.
`compare-runs` accepts any number of complete run files. It removes duplicate content and run
identities, groups matched arms, reports missing arms, applies exact McNemar tests with Holm
correction and emits a deterministic study ID. Running the command again with more run files
produces a larger cumulative study and leaves earlier records unchanged.

[Reproduction](docs/REPRODUCTION.md) gives clean-environment steps and the expected structural
checks. A passing oracle baseline or metamorphic audit shows that the pipeline agrees with itself.
It is not a model result.

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

After at least two independent reviewers have submitted and all decisions are frozen, unblind the
packet and compute the deterministic report:

```bash
cpb-review-report analyze \
  --dataset data/alpha \
  --package work/review-alpha \
  --out work/review-alpha/review-report.json
```

When there are disagreements, create and validate a complete adjudication:

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

A failed numeric threshold stays `REVISION_REQUIRED`, and adjudication cannot turn it into a pass.
See [the full workflow](docs/REVIEW_WORKFLOW.md).

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

Prompt renderers remove item IDs, pair IDs, split labels, family labels and gold fields. A
missing or malformed model output is recorded as a `FORMAT_ERROR` and is never silently counted as
`HOLD`.

## Intended experiments

The frozen design for the full study uses two local Qwen3 sizes, four intervention arms, 400
instances and three seeds, which gives 9,600 short decisions. Before the test set is opened, the
model artifacts, the 4-bit quantization, the llama.cpp commit, the prompts and the hardware must
all be bound by hash. The checked-in model configurations are currently marked
`PENDING_ARTIFACT_FREEZE`. They are plans, not executed runs.

The primary metrics are the false promotion rate, valid promotion recall or false hold rate, and
paired transition accuracy. Ranking diagnostics include tie-aware stepwise AUPRC and the direct
ordering of scores within each pair. Reports must separate false promotions in the model's intent
from false promotions that remain after the gate. A successful veto is an effect of the system, not
evidence of better model calibration. See [Experiment protocol](docs/EXPERIMENTS.md).

`evaluate-runs` validates complete run records and refuses to treat a `FORMAT_ERROR` as a silent
hold. It scores the raw intent and the post-gate decision separately and reports gate and
operational metrics. Format errors reduce explicit coverage and are included in a worst-case
safety sensitivity analysis. Family stratification and matched-arm comparison happen
automatically. `compare-runs` uses zero bootstrap resamples by default, because its exact matched
tests and metric deltas do not need every run interval to be recomputed. You can request a
positive sample count when a cumulative report also needs per-run intervals.

The registered metamorphic transformations are meant to become a separate consistency slice for
future model runs. Any model consistency score must be reported apart from ordinary action
accuracy and AUPRC, because a correct base decision can still change under a prompt transformation
that preserves its meaning.

## Research boundary

The contribution is deliberately narrower than abstention, static verification of scientific
claims, control of claim-level specificity, or general evidence audit trails.
[Related work](docs/RELATED_WORK.md) states the working claim and gives a comparison matrix. The
project says "we did not find a public benchmark directly evaluating policy-governed
research-claim state transitions" and does not claim to be the first of its kind.

Success on an executable artifact is also narrower than research correctness. Exact-rational grid
recomputation supports a finite computational state only. Lean kernel acceptance supports the
exact formal declaration only. Neither replaces scope alignment, novelty assessment, independent
review or a model experiment.

Review infrastructure is not review evidence. A generated packet, passing unit tests or an empty
`reviews/` directory does not establish external agreement. A review gate result can come only from
completed independent submissions, a reproducible unblinded report and a complete adjudication. A
negative result can still be published, and it leads to revision rather than concealment.

Metamorphic invariance of the oracle is not robustness of a model. The 331 passing variants show
only that the current deterministic schemas, artifact bindings, oracle and prompt renderer meet the
nine registered equivalence expectations. Unregistered transformations and model responses have not
been measured.

## Status and accountability

- [Research decisions](RESEARCH_DECISIONS.md) records assumptions, rejected alternatives,
  negative results and version changes.
- [AI assistance](AI_ASSISTANCE.md) separates what tools assisted with from what a person is
  responsible for.
- [Roadmap](docs/ROADMAP.md) lists the 2026–2027 gates without marking future work as complete.
- [Metamorphic invariance audit](docs/INVARIANCE_AUDIT.md) defines the registered equivalence
  transformations and the boundary for model consistency.
- [Mentor review](docs/MENTOR_REVIEW.md) defines the external-review gate.
- [Blinded review workflow](docs/REVIEW_WORKFLOW.md) defines preparation, statistics,
  adjudication and publication.
- `technical-report/` stays explicitly unpublished until a reproducible pilot exists.

Created and maintained by **Chih-Kai Wang**, B.S. student, Mathematics Education Division,
Department of Mathematics and Information Education, National Taipei University of
Education. Expected 2028.

## License

Code and the alpha dataset are released under the [MIT License](LICENSE). Artifact hashes are
integrity digests. They are not digital signatures, identity proofs or provenance guarantees.
