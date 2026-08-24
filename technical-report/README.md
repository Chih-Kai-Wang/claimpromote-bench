# Technical report

`main.tex` is the canonical scientific manuscript for *ClaimPromoteBench: Compiling Executable
Policy Revisions into Failure-Aware Model-Service Tests*.

The central evidence combines two exact upstream Gatekeeper policy revisions with a 12-pair finite
context set and three repeated executions on each of two hosted model IDs. Trivy, Cosign, Microsoft
Agent Governance Toolkit, and agentgateway provide independent policy, verifier, and guardrail
interface fault evidence. An authored SLSA migration stress-tests four-action transition coverage.
R6 and the public balanced challenge remain auxiliary evidence-state diagnostics.

Every scheduled call remains in end-to-end denominators. The manuscript separates strict top-level
JSON action, contract-action, and full-decision endpoints. Failed response contents are omitted;
content-free terminal classes and complete confusion matrices remain available.

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

The ICLR wrapper requires the official style files bound by `iclr2027-style-lock.json`. Run the
manuscript evidence checks with:

```bash
.venv/bin/python scripts/lint_paper_submission.py
```

The release workflow rebuilds both PDFs and source archives, generates the anonymous reviewer
bundle, verifies privacy receipts, renders every PDF page for visual inspection, and derives bundle
file totals from generated manifests.

## Scope and release boundary

The deterministic policy executor is the definitional policy ceiling. The central model IDs share
one provider/API and adapter configuration; provider-side serving internals remain opaque. Their
results are descriptive. The author-created public challenge measures robustness on known frozen
cases.

A passing local build does not authorize a merge, public release, OpenReview upload, or arXiv
submission. Completed one-shot studies remain frozen and are replayed only from committed records.
