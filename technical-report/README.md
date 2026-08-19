# Technical report

**Status: PRIMARY HIDDEN STUDY COMPLETE — PREPRINT FINALIZATION IN PROGRESS.**

The anonymous manuscript is [`main.tex`](main.tex); the fail-closed readiness record is [`SUBMISSION_GATE.md`](SUBMISSION_GATE.md). Version 1 now has a committed private hidden test, a complete frozen 24-run source matrix, artifact-only semantic recovery, and a validated 7,200-decision aggregate. Primary Results in the manuscript are populated from that recovered artifact rather than partial logs or manually inferred numbers.

The full benchmark contains 200 controlled pairs / 400 instances. The **primary scored study uses only the private 150-pair / 300-instance hidden test**; the 50-pair / 100-instance public development split is excluded from primary scoring.

## Primary study identity

- hidden commitment commit: `8d9b3f5c831f432cf6b321e6402724c4f52bb3e1`;
- scored inference head: `aa5268dcde2aa44f8eabf0246631efbca27de7e5`;
- source workflow run: `32255636879`;
- primary matrix: 300 hidden instances × 2 models × 4 arms × 3 seeds = **7,200 decisions**;
- artifact-only recovery workflow: `32274814703`;
- recovered study SHA-256: `sha256:3eb5b534ab486dac774a62de3d623fa33009be3705d9e8d620bb9942e8bfe664`.

Recovery reclassified exactly 27 frozen cross-field-semantic output violations as `FORMAT_ERROR`. It did not rerun either model and did not rewrite any legal model decision. The one-shot recovery trigger was removed after success.

## Main empirical result

Across the recovered primary matrix:

- 5,327/7,200 decisions (73.99%) are `FORMAT_ERROR`;
- all 1,873 parseable raw model intents request `ALLOW`;
- wherever raw conditional rates are defined, raw FPR = 1.00, VPR = 1.00, and PTA = 0;
- in the enforced-gate arm, conditional effective FPR = 0, VPR = 1, gate catch rate = 1, and false-block rate = 0 for every seed;
- gate-arm decision coverage is only 14.0%–49.0% for Qwen3-0.6B and 21.7%–48.3% for Qwen3-1.7B.

The manuscript therefore describes the gate result as a **system-level enforcement effect**, not improved model reasoning or calibration. Low structured-output coverage remains a central negative finding.

The official matched-comparison aggregate also retains an infrastructure-identity limitation: three jobs recorded Python 3.11.16 while most recorded 3.11.15, splitting three intended exact model×seed identity groups. The paper discloses this instead of regrouping runs after seeing results.

## Supplementary human audit

Two real independent reviewers completed the frozen 20-item procedural-blind alpha audit. Action agreement with frozen gold is 0.90 and 0.75, with 0.85 pairwise action agreement. The conservative supplementary gate therefore reports **mixed / not PASS**. Reviewer disagreements remain unchanged and are not used to rewrite policy or gold.

## Build

From this directory:

```bash
pdflatex -interaction=nonstopmode -halt-on-error main.tex
bibtex main
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
```

The paper workflow compiles the same source on pull requests and is expected to fail on unresolved citations or references.

## Remaining publication gates

Primary empirical completion does **not** automatically make the paper archival-submission-ready. Remaining checks are tracked in [`SUBMISSION_GATE.md`](SUBMISSION_GATE.md), including:

- authoritative bibliography verification;
- final post-results CI and LaTeX compile;
- visual PDF audit for overflow, broken references, stale blocker text, anonymity leaks, and metadata;
- final quantitative cross-check against the recovered artifact;
- venue-specific AI-assistance/disclosure review;
- immutable release/tag and clean-environment reproduction before archival submission.

A future replication may pin the exact Python patch version and retain malformed free-form model text, but it must be labeled as a new/supplementary study. It must not replace the frozen negative v1 result.
