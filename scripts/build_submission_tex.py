#!/usr/bin/env python3
"""Generate ICLR 2027 and arXiv TeX wrappers from the canonical manuscript body.

The canonical technical-report/main.tex remains the source of scientific content. This script
extracts the body and places it under venue-specific wrappers so the ICLR submission can remain
anonymous while the arXiv preprint carries author identity. No quantitative result is recomputed
or edited here.
"""

from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "technical-report"
TITLE = r"\cpb: Evaluating Policy-Governed Evidence-State Transitions in AI Research Agents"

AI_DISCLOSURE = r"""\section{AI Assistance Disclosure}

Generative AI tools were used for literature search and triage, research-gap exploration,
methodology and experiment-design feedback, implementation and code drafting, CI debugging,
artifact analysis, interpretation of quantitative outputs, manuscript drafting and editing,
and reference formatting. AI tools also assisted in identifying possible failure modes and
checking consistency between the manuscript and machine-generated study artifacts. All
quantitative claims reported in this paper were derived from the validated recovered study
artifact rather than invented or inferred from partial logs. The human author reviewed the
AI-assisted work and is responsible for the research question, benchmark and policy semantics,
experimental decisions, released artifacts, quantitative claims, citation accuracy, and final
manuscript. AI systems are not treated as authors, independent human reviewers, or external
reproducers.

"""


def canonical_body() -> str:
    source = (REPORT / "main.tex").read_text(encoding="utf-8")
    body_start = source.index(r"\begin{abstract}")
    bib_start = source.rindex(r"\bibliographystyle")
    body = source[body_start:bib_start].rstrip() + "\n\n"

    ai_start = body.index(r"\section{AI Assistance Disclosure}")
    conclusion_start = body.index(r"\section{Conclusion}", ai_start)
    body = body[:ai_start] + AI_DISCLOSURE + body[conclusion_start:]
    return body


def shared_commands() -> str:
    return r"""\newcommand{\cpb}{\textsc{ClaimPromoteBench}}
\newcommand{\allow}{\texttt{ALLOW}}
\newcommand{\hold}{\texttt{HOLD}}
\newcommand{\demote}{\texttt{DEMOTE}}
\newcommand{\escalate}{\texttt{ESCALATE}}
"""


def without_ai_disclosure(body: str) -> str:
    ai_start = body.index(r"\section{AI Assistance Disclosure}")
    conclusion_start = body.index(r"\section{Conclusion}", ai_start)
    return body[:ai_start] + body[conclusion_start:]


def iclr_tex(body: str, *, main_text_probe: bool = False) -> str:
    # ICLR excludes the mandatory AI-use statement from the page limit. The diagnostic probe
    # therefore removes only that section; it keeps the full scientific text, including the
    # conclusion and our reproducibility/artifact discussion. References are omitted below.
    body_for_output = without_ai_disclosure(body) if main_text_probe else body

    return (
        r"""\documentclass{article}
\usepackage{iclr2027_conference,times}
\usepackage{amsmath,amssymb}
\usepackage{booktabs}
\usepackage{enumitem}
\usepackage{microtype}
\usepackage[hidelinks]{hyperref}
\usepackage{xcolor}

"""
        + shared_commands()
        + "\n"
        + rf"\title{{{TITLE}}}" + "\n"
        + r"\author{Anonymous authors}" + "\n\n"
        + r"\begin{document}" + "\n"
        + r"\maketitle" + "\n\n"
        + body_for_output
        + (
            "\n\\end{document}\n"
            if main_text_probe
            else "\n\\bibliographystyle{iclr2027_conference}\n\\bibliography{references}\n\n\\end{document}\n"
        )
    )


def arxiv_tex(body: str) -> str:
    return (
        r"""\documentclass[10pt]{article}
\usepackage[margin=1in]{geometry}
\usepackage{amsmath,amssymb}
\usepackage{booktabs}
\usepackage{enumitem}
\usepackage{microtype}
\usepackage[hidelinks]{hyperref}
\usepackage{xcolor}

"""
        + shared_commands()
        + "\n"
        + rf"\title{{{TITLE}}}" + "\n"
        + r"\author{Chih-Kai Wang\\Department of Mathematics and Information Education\\National Taipei University of Education}" + "\n"
        + r"\date{}" + "\n\n"
        + r"\begin{document}" + "\n"
        + r"\maketitle" + "\n\n"
        + body
        + "\n\\bibliographystyle{plain}\n\\bibliography{references}\n\n\\end{document}\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    body = canonical_body()

    (out / "iclr2027.tex").write_text(iclr_tex(body), encoding="utf-8")
    (out / "iclr2027-maintext-probe.tex").write_text(
        iclr_tex(body, main_text_probe=True), encoding="utf-8"
    )
    (out / "arxiv.tex").write_text(arxiv_tex(body), encoding="utf-8")
    (out / "references.bib").write_bytes((REPORT / "references.bib").read_bytes())
    print(f"generated submission sources in {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
