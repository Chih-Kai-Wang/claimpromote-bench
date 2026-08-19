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
TITLE = r"\cpb: Evaluating Whether Evidence Licenses Claim-State Transitions in AI Research Agents"

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

ICLR_REPRODUCIBILITY = r"""\section{Reproducibility and Artifact Policy}

The hidden set and exact model-facing prompts were frozen and committed before scored inference.
An artifact-only recovery workflow later reconstructed that frozen identity, validated all 24
source and 24 normalized runs, and produced the 7,200-record aggregate without querying either
model again. For double-blind review, public repository identifiers and searchable provenance
hashes are omitted from this submission. An anonymized review bundle can carry the frozen
manifests, run outputs, and recovery provenance; the public preprint/release retains the exact
identifiers.

The raw hidden seed is not included in the public or review artifacts. Any future change to
labels, policy rules, prompts, controlled factors, or hidden-test bytes requires a new benchmark
revision rather than silently mutating v1.

"""


def canonical_body() -> str:
    source = (REPORT / "main.tex").read_text(encoding="utf-8")
    body_start = source.index(r"\begin{abstract}")
    bib_start = source.rindex(r"\bibliographystyle")
    body = source[body_start:bib_start].rstrip() + "\n\n"

    ai_start = body.index(r"\section{AI Assistance Disclosure}")
    conclusion_start = body.index(r"\section{Conclusion}", ai_start)
    body = body[:ai_start] + AI_DISCLOSURE + body[conclusion_start:]

    # Keep exact identities in public repository/provenance records while avoiding long
    # monospace strings in venue-formatted prose. These substitutions never alter study data.
    replacements = {
        r"\texttt{aa5268dcde2aa44f8eabf0246631efbca27de7e5}": r"\texttt{aa5268dc...de7e5}",
        r"\texttt{8d9b3f5c831f432cf6b321e6402724c4f52bb3e1}": r"\texttt{8d9b3f5c...bb3e1}",
        r"\texttt{e2b09f30b0573cf7bcb244eef1917691755f2877}": r"\texttt{e2b09f30...f2877}",
        r"\texttt{3eb5b534ab486dac774a62de3d623fa33009be3705d9e8d620bb9942e8bfe664}": (
            r"\texttt{3eb5b534...e8bfe664}"
        ),
    }
    for old, new in replacements.items():
        body = body.replace(old, new)
    return body


def anonymize_for_iclr(body: str) -> str:
    """Remove searchable public provenance while preserving the scientific protocol."""

    repro_start = body.index(r"\section{Reproducibility and Artifact Policy}")
    ai_start = body.index(r"\section{AI Assistance Disclosure}", repro_start)
    body = body[:repro_start] + ICLR_REPRODUCIBILITY + body[ai_start:]

    replacements = {
        r"the frozen inference source is workflow run \texttt{32255636879}.": (
            "scored inference began only after the hidden set and exact prompts were frozen."
        ),
        r"Recovery run \texttt{32274814703} validated": "The recovery workflow validated",
        r"\texttt{32255636879}": r"\texttt{[anonymized-source-run]}",
        r"\texttt{32274814703}": r"\texttt{[anonymized-recovery-run]}",
        r"\texttt{aa5268dc...de7e5}": r"\texttt{[anonymized]}",
        r"\texttt{8d9b3f5c...bb3e1}": r"\texttt{[anonymized]}",
        r"\texttt{e2b09f30...f2877}": r"\texttt{[anonymized]}",
        r"\texttt{3eb5b534...e8bfe664}": r"\texttt{[anonymized]}",
    }
    for old, new in replacements.items():
        body = body.replace(old, new)

    sensitive_fragments = (
        "32255636879",
        "32274814703",
        "aa5268dc",
        "8d9b3f5c",
        "e2b09f30",
        "3eb5b534",
        "f0909172434",
    )
    leaks = [fragment for fragment in sensitive_fragments if fragment.lower() in body.lower()]
    if leaks:
        raise ValueError(f"ICLR body still contains searchable provenance: {leaks}")
    return body


def shared_commands() -> str:
    return r"""\newcommand{\cpb}{\textsc{ClaimPromoteBench}\xspace}
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
    # ICLR excludes the mandatory AI-use statement from the main-text page limit. The diagnostic
    # probe removes only that section; it retains the complete scientific narrative and omits
    # the bibliography below.
    anonymous_body = anonymize_for_iclr(body)
    body_for_output = (
        without_ai_disclosure(anonymous_body) if main_text_probe else anonymous_body
    )

    bibliography_tail = (
        "\n\\bibliographystyle{iclr2027_conference}\n"
        "\\bibliography{references}\n\n"
        "\\end{document}\n"
    )
    return (
        r"""\documentclass{article}
\usepackage{iclr2027_conference,times}
\usepackage{amsmath,amssymb}
\usepackage{booktabs}
\usepackage{enumitem}
\usepackage{microtype}
\usepackage[hidelinks]{hyperref}
\usepackage{xcolor}
\usepackage{xspace}

"""
        + shared_commands()
        + "\n"
        + rf"\title{{{TITLE}}}"
        + "\n"
        + r"\author{Anonymous authors}"
        + "\n\n"
        + r"\begin{document}"
        + "\n"
        + r"\maketitle"
        + "\n\n"
        + body_for_output
        + ("\n\\end{document}\n" if main_text_probe else bibliography_tail)
    )


def arxiv_tex(body: str) -> str:
    author = (
        r"\author{Chih-Kai Wang\\Department of Mathematics and Information Education\\"
        r"National Taipei University of Education}"
    )
    return (
        r"""\documentclass[10pt]{article}
\usepackage[margin=1in]{geometry}
\usepackage{amsmath,amssymb}
\usepackage{booktabs}
\usepackage{enumitem}
\usepackage{microtype}
\usepackage[hidelinks]{hyperref}
\usepackage{xcolor}
\usepackage{xspace}

"""
        + shared_commands()
        + "\n"
        + rf"\title{{{TITLE}}}"
        + "\n"
        + author
        + "\n"
        + r"\date{}"
        + "\n\n"
        + r"\begin{document}"
        + "\n"
        + r"\maketitle"
        + "\n\n"
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
