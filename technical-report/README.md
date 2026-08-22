# Technical report

`main.tex` is the canonical scientific manuscript. It evaluates evidence-state transitions under
an authored, machine-checkable policy. The experiments are synthetic and configuration-specific;
they do not measure general research-agent ability or natural-distribution performance.

The paper reports two principal evaluations:

- a fresh hidden r6 diagnostic with 300 items and 150 controlled pairs; and
- a precommitted, action-balanced public challenge with 180 items and 90 pairs.

Every scheduled service, syntax, schema, and semantic failure remains incorrect in end-to-end
metrics. Conditional accuracy is reported only alongside decision or pair coverage. The
deterministic policy executor defines the labels and is therefore a definitional policy ceiling,
not a learned baseline.

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
