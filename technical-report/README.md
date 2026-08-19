# Technical report

**Status: WORK IN PROGRESS — NOT SUBMISSION READY.**

The repository now contains an anonymous manuscript scaffold in [`main.tex`](main.tex) and a fail-closed [`SUBMISSION_GATE.md`](SUBMISSION_GATE.md).

The manuscript deliberately contains visible submission blockers and blank quantitative result cells. They must be removed or populated only after the frozen benchmark, model/runtime artifacts, 9,600-decision study, and independent benchmark review pass the repository's declared gates. A polished PDF is not evidence that the empirical study is complete.

## Build

From this directory:

```bash
pdflatex -interaction=nonstopmode -halt-on-error main.tex
bibtex main
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
```

The paper workflow compiles the same source on pull requests that change `technical-report/**` and fails on unresolved citations/references.

## Publication rule

A preprint may be released only when every empirical claim is bound to released, validated artifacts and the applicable gates in `SUBMISSION_GATE.md` pass. If independent review is still absent, the project must retain the `PRELIMINARY TECHNICAL REPORT` label rather than presenting infrastructure as review evidence.
