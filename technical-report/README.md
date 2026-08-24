# Technical report

`main.tex` is the canonical scientific manuscript. It evaluates policy-conditioned state transitions
with matched evidence and policy contrasts. The experiments are synthetic and
configuration-specific; they do not measure general research-agent ability or natural-distribution
performance.

The central validation uses one authored migration, two 60-pair suites, and the same two pinned
local route stacks without independent replication. Three additional frozen datasets provide
auxiliary evidence and failure diagnostics:

- a hidden research-evidence realization with 300 items and 150 evidence pairs;
- a public action-balanced challenge with 180 items and 90 evidence pairs;
- and a software-artifact portability study with 120 items and 60 evidence pairs.

The central rule-stratified suite changes only the active profile and covers all 12 changed rules;
the central graph suite covers all ten semantically reachable directed non-self action transitions.
A later auxiliary Ox Alpha route replay reuses the preexisting ten-pair minimum witness. Its route
was selected after other results were known, while the schedule and strict failure rule were frozen
before its first call. It is a time-stamped route smoke test rather than another dataset, model-family
comparison, independent policy replication, or reliability estimate.

Every scheduled service, syntax, schema, and semantic failure remains incorrect in end-to-end
metrics. Conditional accuracy is reported only alongside decision or pair coverage. The
deterministic policy executor generates the labels and is therefore a definitional policy ceiling,
not a learned baseline. The Naive Bayes and structured Random Forest rows are weak or
construction-dependent sanity controls, not competitive baselines.

## Build and validate

Build the canonical report from this directory:

```bash
pdflatex -interaction=nonstopmode -halt-on-error main.tex
bibtex main
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
```

Generate the anonymous ICLR and named arXiv wrappers from the repository root:

```bash
.venv/bin/python scripts/build_submission_tex.py --out work/submission
```

The ICLR wrapper additionally requires the official style files pinned by
`iclr2027-style-lock.json`. Run the manuscript truth checks with:

```bash
.venv/bin/python scripts/lint_paper_submission.py
```

The complete release procedure rebuilds both PDFs, source archives, the anonymous reviewer bundle,
checksums, and validation receipts. It renders every PDF page for visual inspection and derives
bundle file totals from the generated manifests.

## Release boundary

`SUBMISSION_GATE_V2.md` records the current scientific and packaging gates. A passing local build
does not authorize a merge, public release, OpenReview upload, or arXiv submission. Completed
singleton studies must be replayed from their committed records rather than rerun.
