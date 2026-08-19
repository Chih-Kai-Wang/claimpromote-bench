# Technical report

**Status: WORK IN PROGRESS — NOT SUBMISSION READY.**

The repository now contains an anonymous manuscript scaffold in [`main.tex`](main.tex) and a fail-closed [`SUBMISSION_GATE.md`](SUBMISSION_GATE.md).

The manuscript deliberately contains visible submission blockers and blank quantitative result cells. They must be removed or populated only after the frozen benchmark, model/runtime artifacts, and 9,600-decision study pass the repository's declared gates. A polished PDF is not evidence that the empirical study is complete.

The project supports a solo-author publication path. Independent external benchmark review is optional supplementary validation rather than a publication gate. If no external audit is available, the manuscript must say so explicitly and retain the corresponding limitation; the repository must not manufacture reviewer identities, agreement statistics, or independent-reproduction claims.

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

A preprint may be released when every empirical claim is bound to released, validated artifacts and the applicable mandatory gates in `SUBMISSION_GATE.md` pass. Absence of external review does not force a `PRELIMINARY TECHNICAL REPORT` label by itself; instead, it must be disclosed as a limitation and the paper must rely only on claims supported by the frozen deterministic benchmark and reproducible model-study artifacts.
