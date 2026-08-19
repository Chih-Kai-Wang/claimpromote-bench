# Technical report

**Status: WORK IN PROGRESS — NOT SUBMISSION READY.**

The repository contains an anonymous manuscript in [`main.tex`](main.tex) and a fail-closed [`SUBMISSION_GATE.md`](SUBMISSION_GATE.md). The public v1 development path is now executable end to end: 50 controlled pairs / 100 instances are deterministically generated, audited, hash-frozen, and replayed under the pinned Lean trust base in CI. Two independent reviewers have also completed the frozen 20-item procedural-blind alpha audit; the closed result is deliberately reported as a supplementary mixed result rather than a multi-reviewer PASS.

The manuscript still contains a visible submission blocker and blank **primary hidden-study** result cells. Those cells must be populated only after the private 150-pair hidden split is generated and committed cryptographically before inference, prompt hashes are frozen, and the complete 2-model × 4-arm × 3-seed × 400-instance study produces validated artifacts for all 9,600 decisions. A polished PDF is not evidence that these empirical gates are complete.

## Build

From this directory:

```bash
pdflatex -interaction=nonstopmode -halt-on-error main.tex
bibtex main
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
```

The paper workflow compiles the same source on pull requests that change `technical-report/**` and fails on unresolved citations or references.

## Evidence boundaries

- Public v1 dev freeze: `configs/v1-public-dev-freeze.json`.
- Closed external audit: `external-audit/v1/` and `docs/EXTERNAL_REVIEW_V1_RESULTS.md`.
- Primary hidden-study results: **not yet available** and must not be inferred from alpha engineering pilots.
- Deterministic gate catches are system-level enforcement effects, not evidence of improved model reasoning or calibration.

## Publication rule

A preprint may be released only when every empirical claim is bound to released, validated artifacts and the applicable mandatory gates in `SUBMISSION_GATE.md` pass. The existing external audit may be reported because its submissions were closed and hash-frozen before unblinding; its mixed outcome must be retained exactly as observed. It does not replace the hidden scored study or deterministic integrity gates.
