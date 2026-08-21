#!/usr/bin/env python3
"""Generate ICLR 2027 and arXiv TeX wrappers from the canonical manuscript body.

The canonical technical-report/main.tex remains the source of scientific content. This script
extracts the body and places it under venue-specific wrappers so the ICLR submission can remain
anonymous while the arXiv preprint carries author identity. Quantitative results pass through
unchanged.
"""

from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "technical-report"
TITLE = r"\cpb: Synthetic, Policy-Constrained Evaluation of Evidence-State Transitions"
ICLR_TITLE = (
    r"\mbox{\textsc{ClaimPromoteBench}: Synthetic}\protect\\"
    r"\mbox{Policy-Constrained Evaluation of}\protect\\"
    r"\mbox{Evidence-State Transitions}"
)

AI_DISCLOSURE = r"""\section{AI Assistance Disclosure}

Generative AI tools were used as assistants during literature search, research planning and
methodological discussion, synthetic benchmark-template and code drafting and debugging, analysis
checks and result interpretation, and parts of manuscript drafting and editing. The author chose
the research question, defined the benchmark policy and experimental protocol, made the final study
and analysis decisions, checked the generated benchmark through deterministic validators, checked
the reported results against the released artifacts, checked the references, and is responsible
for the final manuscript and submission. The quantitative results
reported in this paper come from the validated study artifacts. The author retains authorship
and final responsibility.

"""

ICLR_REPRODUCIBILITY = r"""\section{Reproducibility and Artifact Policy}

The original hidden set and exact prompts were fixed before scored inference. Artifact-only
recovery reconstructed the same dataset and prompt identity and recomputed the 7,200-record v1
aggregate from all 24 archived runs. It issued no model query and reclassified exactly 27
cross-field-invalid records as format errors by invoking the registered semantic validator omitted
by the original runner; no legal model decision was rewritten.

For the fresh study, public C0 and private-salt commitments precede a future randomness beacon and
C1 construction receipt. A frozen schedule contains 600 requests, and C2 seals all 600 terminal
cells before gold loading or analysis. A post-run audit found cleartext provider hidden-thinking
blocks inside 275 response envelopes. Scoring used final response text and parsed decisions alone,
so the defect left the C2 order and scientific values unchanged. The public release is a post-C2
text-only allowlist derivative with source-to-derived row and envelope hashes and byte-identical
scientific analysis. Its manifest records the generated tree's current file count.

The public balanced challenge froze its dataset, action distribution, prompt packet, adapters,
statistics, and one-call zero-retry schedule before inference. Its receipt validates all 360
item-level records and reports zero provider-account findings, retained provider response
identifiers, and hidden-reasoning findings. The challenge is public robustness evidence and is not
a hidden-test generalization estimate or a causal comparison between its differing service stacks.

The anonymous review bundle contains the fresh dataset, study plan, prompt packet, baseline
predictions, projected C2 records, item-level final outputs, gold, analysis, redaction receipt, and
frozen-manifest correction overlay. Its validator recomputes the complete statistics and both
registered lane dispositions. The bundle also retains all 14 pilot attempts and both full passes
from the adaptive extension, plus the original and public-control evidence and executable and Lean
replay inputs. Searchable repository provenance is replaced with role descriptions. The private
construction seed is excluded. Any change to labels, policy, prompts, controlled factors, or
hidden-test bytes creates a new benchmark version. Bundle construction records the actual file
count in its manifest, and validation recomputes that count from the generated tree.

"""

ICLR_PUBLIC_IDENTIFIERS = (
    "32255636879",
    "32274814703",
    "32291482079",
    "aa5268dc",
    "8d9b3f5c",
    "e2b09f30",
    "3eb5b534",
    "83dbee49",
    "eb2af5fc",
    "20904dd1",
    "abfc25e9",
    "3634ce85",
    "8dd8d488",
    "ba6ba305",
    "0054a4d7",
    "41480fba",
    "f2bb2e97",
    "32402699174",
    "32402993463",
    "32403718086",
    "32405565039",
    "32421292779",
    "32453310192",
    "119e4759",
    "b86ee1e1",
    "cc67096b",
    "8775a8f9",
    "05d9921c",
    "300dc094",
    "32509532820",
    "9460301513",
    "1901e471",
    "3746403e",
    "057e7854",
    "f44b01eb",
    "8821e710",
)


def canonical_body() -> str:
    source = (REPORT / "main.tex").read_text(encoding="utf-8")
    body_start = source.index(r"\begin{abstract}")
    bib_start = source.rindex(r"\bibliographystyle")
    body = source[body_start:bib_start].rstrip() + "\n\n"

    ai_start = body.index(r"\section{AI Assistance Disclosure}")
    conclusion_start = body.index(r"\section{Conclusion}", ai_start)
    body = body[:ai_start] + AI_DISCLOSURE + body[conclusion_start:]

    # Keep exact identities in public repository/provenance records while avoiding long
    # monospace strings in venue-formatted prose. These substitutions preserve study data.
    replacements = {
        r"\texttt{aa5268dcde2aa44f8eabf0246631efbca27de7e5}": r"\texttt{aa5268dc...de7e5}",
        r"\texttt{8d9b3f5c831f432cf6b321e6402724c4f52bb3e1}": r"\texttt{8d9b3f5c...bb3e1}",
        r"\texttt{e2b09f30b0573cf7bcb244eef1917691755f2877}": r"\texttt{e2b09f30...f2877}",
        r"\texttt{3eb5b534ab486dac774a62de3d623fa33009be3705d9e8d620bb9942e8bfe664}": (
            r"\texttt{3eb5b534...e8bfe664}"
        ),
        r"\texttt{eb2af5fcfce8466306a208a707e0046b389f2fd656d25d549f784acfc04199e5}": (
            r"\texttt{eb2af5fc...04199e5}"
        ),
    }
    for old, new in replacements.items():
        body = body.replace(old, new)
    return body


def anonymous_iclr_body(body: str) -> str:
    """Remove public repository provenance that could reveal the author during review."""

    replacements = {
        r"workflow run \texttt{32255636879}": "the frozen scored workflow",
        r"Recovery run \texttt{32274814703}": "The artifact-only recovery workflow",
        r"recovery run \texttt{32274814703}": "the artifact-only recovery workflow",
        r"workflow run \texttt{32291482079}": "the public pilot workflow",
        r"\texttt{32255636879}": "the frozen scored workflow",
        r"\texttt{32274814703}": "the artifact-only recovery workflow",
        r"\texttt{32291482079}": "the public pilot workflow",
        r"\texttt{aa5268dc...de7e5}": "the frozen scoring source",
        r"\texttt{8d9b3f5c...bb3e1}": "the hidden commitment source",
        r"\texttt{e2b09f30...f2877}": "the artifact-only recovery source",
        r"\texttt{3eb5b534...e8bfe664}": "a frozen recovered-study digest",
        r"\texttt{83dbee49...25c0b264e}": "a frozen public-pilot digest",
        r"\texttt{eb2af5fc...04199e5}": "a frozen public-pilot digest",
    }
    anonymous = body
    for old, new in replacements.items():
        anonymous = anonymous.replace(old, new)

    # Every manuscript citation is parenthetical. The official ICLR style gives bare \cite a
    # textual author-year rendering, which produces constructions such as "papers Author et al."
    # in otherwise parenthetical prose. Keep arXiv's numeric citations unchanged and use natbib's
    # explicit parenthetical command only in the ICLR wrapper.
    anonymous = anonymous.replace(r"\cite{", r"\citep{")

    leaked = [identifier for identifier in ICLR_PUBLIC_IDENTIFIERS if identifier in anonymous]
    if leaked:
        raise ValueError(f"ICLR body retains public provenance identifiers: {leaked}")
    return anonymous


def without_ai_disclosure(body: str) -> str:
    ai_start = body.index(r"\section{AI Assistance Disclosure}")
    conclusion_start = body.index(r"\section{Conclusion}", ai_start)
    return body[:ai_start] + body[conclusion_start:]


def without_reproducibility(body: str) -> str:
    reproducibility_start = body.index(r"\section{Reproducibility and Artifact Policy}")
    ai_start = body.index(r"\section{AI Assistance Disclosure}", reproducibility_start)
    return body[:reproducibility_start] + body[ai_start:]


def without_reproducibility_or_ai(body: str) -> str:
    return without_ai_disclosure(without_reproducibility(body))


def iclr_tex(body: str, *, main_text_probe: bool = False) -> str:
    # ICLR excludes both the mandatory AI-use statement and the reproducibility statement from
    # the main-text page limit. The diagnostic probe removes exactly those sections and omits the
    # bibliography; it otherwise keeps the full scientific text, including limitations and the
    # conclusion. The anonymous submission replaces repository-identifying provenance with a
    # double-blind reproducibility statement while the arXiv version retains exact identifiers.
    body_for_output = without_reproducibility(anonymous_iclr_body(body))
    reproducibility_start = body_for_output.index(r"\section{AI Assistance Disclosure}")
    body_for_output = (
        body_for_output[:reproducibility_start]
        + ICLR_REPRODUCIBILITY
        + body_for_output[reproducibility_start:]
    )
    if main_text_probe:
        body_for_output = without_reproducibility_or_ai(body_for_output)

    return (
        r"""\documentclass{article}
\usepackage{iclr2027_conference,times}
\usepackage{amsmath,amssymb}
\usepackage{booktabs}
\usepackage{enumitem}
\usepackage{float}
\usepackage{microtype}
\usepackage[hidelinks]{hyperref}
\usepackage{xcolor}
\usepackage{xspace}

"""
        + r"""\newcommand{\cpb}{\textsc{ClaimPromoteBench}\xspace}
\newcommand{\allow}{\texttt{ALLOW}}
\newcommand{\hold}{\texttt{HOLD}}
\newcommand{\demote}{\texttt{DEMOTE}}
\newcommand{\escalate}{\texttt{ESCALATE}}
"""
        + "\n"
        + rf"\title{{{ICLR_TITLE}}}"
        + "\n"
        + r"\author{Anonymous authors}"
        + "\n\n"
        + r"\begin{document}"
        + "\n"
        + r"\maketitle"
        + "\n\n"
        + body_for_output
        + (
            "\n\\end{document}\n"
            if main_text_probe
            else (
                "\n\\clearpage\n{\\small\n\\bibliographystyle{iclr2027_conference}\n"
                "\\bibliography{references}\n}\n\n\\end{document}\n"
            )
        )
    )


def arxiv_tex(body: str) -> str:
    return (
        r"""\documentclass[10pt]{article}
\usepackage[margin=1in]{geometry}
\usepackage{amsmath,amssymb}
\usepackage{booktabs}
\usepackage{enumitem}
\usepackage{float}
\usepackage{microtype}
\usepackage[hidelinks]{hyperref}
\usepackage{xcolor}
\usepackage{xspace}

"""
        + r"""\newcommand{\cpb}{\textsc{ClaimPromoteBench}\xspace}
\newcommand{\allow}{\texttt{ALLOW}}
\newcommand{\hold}{\texttt{HOLD}}
\newcommand{\demote}{\texttt{DEMOTE}}
\newcommand{\escalate}{\texttt{ESCALATE}}
"""
        + "\n"
        + rf"\title{{{TITLE}}}"
        + "\n"
        + (
            r"\author{Chih-Kai Wang\\"
            r"Department of Mathematics and Information Education\\"
            r"National Taipei University of Education}"
        )
        + "\n"
        + r"\date{}"
        + "\n\n"
        + r"\begin{document}"
        + "\n"
        + r"\maketitle"
        + "\n\n"
        + body
        + (
            "\n{\\small\n\\bibliographystyle{plain}\n"
            "\\bibliography{references}\n}\n\n\\end{document}\n"
        )
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
