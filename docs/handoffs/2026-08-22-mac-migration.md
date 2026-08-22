# ClaimPromoteBench Mac migration handoff — 2026-08-22

This handoff is self-contained in GitHub. Do not depend on the former Windows checkout, Codex
attachments, `work/` directories, browser state, or local credentials.

## Canonical GitHub state

- Repository: `f0909172434/claimpromote-bench`
- Visibility: **PRIVATE**, confirmed by GitHub readback on 2026-08-22 (Asia/Taipei).
- Working branch: `agent/iclr2027-v2-low-cost-study`
- Draft pull request: `#20`, targeting `paper/v1-submission-prep`
- Frozen pre-inference commit: `1901e471bdf94f434f9671708b93599a106b1543`
- Imported-results commit: `3746403ea8784a95ae2cb1c66ee1b95e4a67ad42`
- Scientific/release checkpoint before the user-requested additional review:
  `4ce6680d9ff7826db66fd01dcd87982a28574684`
- Additional-review scientific/release commit:
  `b3dd1d60726bc3c10ac8555d4aab1401ad9d139b`
- One-shot Actions run: `32509532820`, conclusion `success`, attempt 1
- Complete Actions artifact digest:
  `sha256:8821e710f867df95a932e9ce7cc4f3514a4995a6576d53bc0b5a71a84ee99b9b`
- Post-private-conversion PR checks: **externally blocked before runner allocation**. For scientific
  head `4ce6680d9ff7826db66fd01dcd87982a28574684`, all 11 triggered runs completed as failures, but all
  21 jobs have `steps=[]`. Representative CI run `32551751541` says that recent account payments
  failed or the Actions spending limit must be increased. This is not a code-test failure.

The Actions run and pull request are private links. Authenticate the same GitHub account on the Mac
before opening them. Do **not** rerun the balanced-public-v1 workflow: the frozen plan registered one
attempt and the successful singleton is already permanent evidence.

The successful one-shot study ran before the repository was made private and remains valid and
committed. New private-repository CI will not obtain a GitHub-hosted runner until the account's
Billing & plans issue or Actions spending limit is resolved. Keep the repository private unless the
user explicitly authorizes another visibility change; use the local Mac gates in the meantime.

## What is complete

1. The anonymous evidence builder now removes stable provider-account identifiers from nested raw
   errors and fails closed if one survives. Regression tests cover the leak without retaining a real
   identifier.
2. The r6 confirmatory evidence has a post-study descriptive addendum with decision and pair
   coverage, conditional accuracy, the complete confusion matrix, factor concentration, and a
   deterministic policy-executor ceiling explicitly labeled as definitional rather than learned.
3. A public, precommitted action-balanced challenge was frozen before any challenge request:
   90 pairs, 180 items, 15 factors, and invalid-action counts of 30 `HOLD`, 30 `DEMOTE`, and 30
   `ESCALATE`, plus 90 valid `ALLOW` members.
4. Two service configurations each executed all 180 registered calls once with no client retry. The
   workflow independently validated all 360 terminal records and generated a failure-aware report.
5. The complete safe results are committed under
   `v2/balanced-public-challenge/results/`. The result receipt binds the workflow, artifact, source
   commit, every imported file digest, privacy scan, and budget interpretation.
6. Local independent recomputation matched the historical Actions aggregate at the imported-results
   checkpoint. Three values differed only at approximately `1e-16` across Python 3.11 and 3.14
   float serialization and were equivalent under the repository's registered `1e-12` numeric
   tolerance; every nonnumeric field matched exactly. A later audit identified one distinct
   reporting-definition issue: the historical Flash Macro-F1 omitted a zero-prediction class. The
   historical aggregate remains immutable and the versioned correction receipt covers exactly five
   derived fields.
7. The manuscript is now scoped as a synthetic, policy-constrained evidence-state transition
   evaluation. It includes the r6 coverage addendum, balanced challenge, complete confusion and
   action diagnostics, conditional and end-to-end metrics, bounded service-interface claims,
   primary-source related work, and a compact evidence-flow figure.
8. Source-level review of the 12 frozen naturalistic pointers produced zero cases and zero model
   calls because the pointers do not contain enough time-stamped policy-transition evidence. This is
   an author-policy inclusion decision, not a naturalistic result or a human-label study.
9. The ICLR and arXiv PDFs, source archives, anonymous reviewer bundle, checksums, and validation
   receipts were rebuilt deterministically. The latest manifest lists 737 payload files; including
   the manifest, the reviewer ZIP has 738 entries. Counts are generated from the staged tree rather
   than copied into manuscript prose. After the additional-review resolutions, the ICLR PDF has 10
   physical pages and a seven-page main-text probe; the arXiv PDF has nine pages. Current SHA-256
   values are `5bab8da80ca51c4d4203cb9c0a79376a9144d0b915bf4c5429ba9ea058416c9b`
   (ICLR), `0c71b1aeaf8b88db2800b5e3001d80a5a5e81971eb9188a7e6f1b6e5c533e874`
   (arXiv), and `acfdb0b2746d86aeb5f337447b567b142192635f7791e9483c1edd219605e501`
   (anonymous ZIP).
10. One isolated final strict review found zero high-severity issues and one medium-severity issue:
    the Flash fixed-four-class Macro-F1 definition. Commit `4ce6680` corrected it without model calls
    or primary-endpoint changes. At the user's later explicit request, one additional isolated,
    read-only strict AI reviewer was created. It found no blocker/high issue, two medium reporting
    defects, and one low citation defect; all were resolved from frozen evidence without model calls.
11. Final Mac validation on Python 3.12.13: 196 tests passed, branch coverage was 83.24%, Ruff lint
    and formatting passed, strict mypy passed for 28 source files, paper lint passed, the anonymous
    one-command replay passed, and all six tracked Lean packages plus the staged anonymous Lean
    package passed `lake build` and `leanchecker`.
12. A continuation audit found that local Lean builds created ignored `.lake` caches that made the
    permanent evidence manifest report a false extra-file mismatch. The manifest tool now ignores
    only `.lake` directories and retains fail-closed rejection for every other unmanifested file;
    regression coverage exercises both sides of that boundary. The full suite passes with a real
    Lean cache present: 197 tests passed.
13. The additional review correction reports the old r6 Flash service configuration as 0/300 E2E
    items and 0/150 E2E pairs while retaining conditional correctness and model efficacy as `N/E`.
    The r6 reporting addendum now binds all 20 factor-level pair outcomes, and the paper summarizes
    factor support, coverage, E2E ranges, and zero/perfect-factor counts for all three reported
    configurations. The technical-report citation for ClaimLedger uses its direct report URL rather
    than the DOI that identifies the tagged software release. The full suite now has 198 tests.

## Balanced challenge results to report

These are public-precommitted robustness results, **not** a hidden-test generalization estimate and
**not** a causal comparison between model weights or providers.

| Service configuration | Valid decisions | E2E item | Conditional item | Complete pairs | E2E pair | Conditional pair | Balanced recall | Macro-F1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen3.7-Max | 148/180 | 132/180 = .7333 | 132/148 = .8919 | 64/90 = .7111 | 48/90 = .5333 | 48/64 = .7500 | .6611 | .7004 |
| DeepSeek-V4-Flash | 146/180 | 90/180 = .5000 | 90/146 = .6164 | 61/90 = .6778 | 13/90 = .1444 | 13/61 = .2131 | .3722 | .3928 |

Post-review reporting correction: the historical aggregate omitted Flash's zero-prediction
`DEMOTE` class from Macro-F1. The fixed-four-class values are `.3928` end to end and `.4682`
conditional; `results/reporting-correction-v1.json` binds the unchanged raw records and historical
aggregate. No model calls or primary endpoints changed.

End-to-end action recall in `ALLOW / HOLD / DEMOTE / ESCALATE` order:

- Qwen3.7-Max: `.8778 / .8667 / .1333 / .7667`.
- DeepSeek-V4-Flash: `.7556 / .3000 / .0000 / .4333`.

Failure decomposition:

- Qwen: 148 valid decisions, 31 transport failures (27 HTTP 500 and 4 HTTP 503), and one
  semantic-invalid decision.
- Flash: 146 valid decisions and 34 semantic-invalid decisions; no transport failure. The semantic
  failures comprise 16 invalid `DEMOTE` state transitions, 16 `ESCALATE` outputs that changed the
  current state, and two invalid missing-evidence lists.
- The earlier r6 Flash lane's 300 HTTP 401 responses should now be described as an old frozen
  service-interface failure. The successful new Flash route shows that the model path can execute,
  but differing service stacks prevent a strict causal ablation claim.
- Incremental cash spend was `$0.00`; host-usage-derived subscription quota value was `$4.137798288`.

Primary evidence files:

- `v2/balanced-public-challenge-study-plan.json`
- `v2/balanced-public-challenge/prompt-packet.json`
- `v2/balanced-public-challenge/results/aggregate.json`
- `v2/balanced-public-challenge/results/reporting-correction-v1.json`
- `v2/balanced-public-challenge/results/github-artifact-receipt.json`
- `v2/balanced-public-challenge/results/runs/`
- `v2/confirmatory/r6-execution/reviewer-reporting-addendum.json`
- `release/submission-kit/validation-receipt.json`
- `docs/reviews/2026-08-22-isolated-final-review-disposition.md`
- `docs/reviews/2026-08-22-additional-isolated-review-disposition.md`

## Important truth boundaries

- The new balanced challenge is `COMPUTATIONAL` evidence from a publicly visible prespecified set.
  It does not replace the hidden r6 estimate.
- The two service configurations differ in interface and output constraints. Report each one
  independently; do not call their difference a model-size, provider, or decoding ablation.
- Every transport, syntax, schema, or semantic failure stays in the end-to-end denominator.
- The policy executor is a definitional ceiling, not an empirical learned baseline.
- The frozen public-development Naive Bayes comparator remains shallow. Do not claim that strong
  learned or retrieval baselines have been exhausted.
- Naturalistic transfer and independent human policy agreement remain open. A frozen 12-candidate
  CORE-Bench pointer pool exists; bound source-level review created zero cases before model access
  because the pointers lacked sufficient policy-transition evidence. No labeled naturalistic study
  has been completed. Do not fabricate annotators or agreement.
- Nothing has been submitted to OpenReview or arXiv. PR `#20` must remain draft and unmerged unless
  the user explicitly authorizes submission or merge.

## Completed continuation state

The previous priority list is complete on the private working branch. The scientific and release
candidate is `SCIENTIFIC_RC_READY` under `technical-report/SUBMISSION_GATE_V2.md`; this status does
not authorize submission, merging, public release, or archival tagging.

For any future continuation:

1. Fetch the private branch and inspect PR `#20` for new commits, comments, or review findings before
   editing. The remote branch, not a workstation copy, remains authoritative.
2. Treat `b3dd1d60726bc3c10ac8555d4aab1401ad9d139b` as the completed additional-review
   scientific/release checkpoint. Make further scientific changes only for a concrete defect, new
   authorized evidence, or a user-directed scope change; do not add unsupported claims merely to
   create activity.
3. Do not rerun the balanced-public-v1 singleton or any completed model study. Two context-isolated
   internal AI review checkpoints are now complete; do not create another unless the user explicitly
   asks for it.
4. If manuscript or reviewer-bundle inputs change, rebuild both PDFs, source archives, anonymous
   bundle, checksums, receipts, and visual QA. For documentation-only changes, run proportionate
   local checks and preserve the existing release bytes.
5. Keep PR `#20` draft and the repository private. OpenReview, arXiv, merge, release, billing, and
   visibility changes all require explicit user authorization.

GitHub-hosted CI will not turn green until the repository owner resolves the **Billing & plans** or
spending-limit condition. Do not classify the current zero-step red checks as scientific or code
regressions. Do not inspect or change billing, and do not change repository visibility, without the
user's explicit authorization.

## Mac bootstrap

```bash
gh auth login
gh repo clone f0909172434/claimpromote-bench
cd claimpromote-bench
git fetch origin
git switch --track origin/agent/iclr2027-v2-low-cost-study
git status --short --branch
git log -3 --oneline

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
python -m pytest --cov --cov-branch --cov-report=term-missing --cov-fail-under=80
ruff check .
ruff format --check .
mypy src
python scripts/lint_paper_submission.py
```

Use a Python version supported by `pyproject.toml`; the final Mac checkpoint used Python 3.12.13.
Preserve the frozen r6 runtime distinction when discussing historical recomputation. Invoke pytest
as `python -m pytest` so the repository-root `release` validation package resolves consistently.
Never print or copy GitHub Actions secrets into the Mac checkout.
