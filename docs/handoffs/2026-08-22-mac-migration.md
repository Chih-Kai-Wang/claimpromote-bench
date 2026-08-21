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
- One-shot Actions run: `32509532820`, conclusion `success`, attempt 1
- Complete Actions artifact digest:
  `sha256:8821e710f867df95a932e9ce7cc4f3514a4995a6576d53bc0b5a71a84ee99b9b`

The Actions run and pull request are private links. Authenticate the same GitHub account on the Mac
before opening them. Do **not** rerun the balanced-public-v1 workflow: the frozen plan registered one
attempt and the successful singleton is already permanent evidence.

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
6. Local independent recomputation matched the Actions aggregate. Three values differed only at
   approximately `1e-16` across Python 3.11 and 3.14 float serialization and were equivalent under
   the repository's registered `1e-12` numeric tolerance; every nonnumeric field matched exactly.
7. Validation at the imported-results checkpoint: `190 passed`, Ruff passed, and strict mypy passed.

## Balanced challenge results to report

These are public-precommitted robustness results, **not** a hidden-test generalization estimate and
**not** a causal comparison between model weights or providers.

| Service configuration | Valid decisions | E2E item | Conditional item | Complete pairs | E2E pair | Conditional pair | Balanced recall | Macro-F1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen3.7-Max | 148/180 | 132/180 = .7333 | 132/148 = .8919 | 64/90 = .7111 | 48/90 = .5333 | 48/64 = .7500 | .6611 | .7004 |
| DeepSeek-V4-Flash | 146/180 | 90/180 = .5000 | 90/146 = .6164 | 61/90 = .6778 | 13/90 = .1444 | 13/61 = .2131 | .3722 | .5237 |

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
- `v2/balanced-public-challenge/results/github-artifact-receipt.json`
- `v2/balanced-public-challenge/results/runs/`
- `v2/confirmatory/r6-execution/reviewer-reporting-addendum.json`

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
  CORE-Bench pointer pool exists, but no labeled naturalistic study has been completed. Do not
  fabricate annotators or agreement.
- Nothing has been submitted to OpenReview or arXiv. PR `#20` must remain draft and unmerged unless
  the user explicitly authorizes submission or merge.

## Next work, in priority order

1. Re-read the branch, PR, Actions run, imported receipt, and tests before editing.
2. Rewrite `technical-report/main.tex` so the title, abstract, main table, discussion, limitations,
   conclusion, and artifact section include the balanced challenge and r6 coverage addendum. Reduce
   the claim from broad research-agent competence to synthetic policy-conformance evaluation.
3. Add the full coverage/conditional decomposition and confusion/action results. Avoid making the
   public challenge look hidden or confirmatory.
4. Either curate and precommit a small source-grounded naturalistic study from
   `v2/naturalistic-candidates.json`, explicitly labeled as author policy mapping with no human
   consensus, or leave naturalistic transfer open. Do not claim human validation without real human
   labels.
5. Strengthen and verify related work and citations (behavioral testing, contrast sets, metamorphic
   testing, structured output/constrained decoding, abstention/selective prediction, and research
   agents). Use primary sources and verified BibTeX metadata.
6. Add a compact benchmark/evidence-flow figure and remove reviewer-unnecessary implementation
   chronology. Keep the main ICLR-formatted body within its page limit.
7. Rebuild both PDFs and the anonymous review bundle. Visually inspect every PDF page for crowding,
   clipping, overlap, orphaned headings, and unreadable tables. Ensure new result records are
   anonymized and dynamically counted rather than relying on stale `179/170/619` prose.
8. Run the full test, Ruff, mypy, PDF, anonymous-evidence, and GitHub CI gates. Then request a fresh
   isolated, extremely strict review. The pre-fix strict review was `Reject / 3 of 10`; its main
   objections were rare-action concentration, one successful r6 model, a shallow baseline, sparse
   related work, no naturalistic/human validation, chronology not independently obvious from the
   anonymous bundle, and dense presentation.
9. Commit and push every useful artifact to the same private branch before ending a Mac session.

## Mac bootstrap

```bash
gh auth login
gh repo clone f0909172434/claimpromote-bench
cd claimpromote-bench
git fetch origin
git switch --track origin/agent/iclr2027-v2-low-cost-study
git status --short --branch
git log -3 --oneline

python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
PYTHONPATH=src python -m pytest -q
python -m ruff check .
python -m mypy
```

If `python3.11` is unavailable, use a supported Python version from `pyproject.toml`, but preserve the
frozen r6 runtime distinction when discussing historical recomputation. Never print or copy GitHub
Actions secrets into the Mac checkout.
