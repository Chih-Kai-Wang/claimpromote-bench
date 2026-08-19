#!/usr/bin/env python3
"""Fail-closed checks for the submission-facing ClaimPromoteBench manuscript."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEX = ROOT / "technical-report" / "main.tex"
BIB = ROOT / "technical-report" / "references.bib"
RESULTS_FREEZE = ROOT / "technical-report" / "results-freeze.json"


def fail(message: str) -> None:
    raise SystemExit(f"paper-lint: {message}")


def pct(value: float, digits: int = 1) -> str:
    return f"{100 * value:.{digits}f}"


def main() -> int:
    tex = TEX.read_text(encoding="utf-8")
    bib = BIB.read_text(encoding="utf-8")
    frozen = json.loads(RESULTS_FREEZE.read_text(encoding="utf-8"))
    lower = tex.lower()

    stale = [
        "23 of 24",
        "9,600",
        "primary study is not yet complete",
        "no model results",
        "not yet published",
    ]
    for phrase in stale:
        if phrase in lower:
            fail(f"stale pre-results wording remains: {phrase!r}")

    overclaims = [
        r"\bfirst benchmark\b",
        r"\bfirst system\b",
        r"\bfirst framework\b",
        r"\bstate[- ]of[- ]the[- ]art\b",
        r"\bguarantees? safety\b",
    ]
    for pattern in overclaims:
        if re.search(pattern, tex, flags=re.IGNORECASE):
            fail(f"unqualified novelty/performance claim found: {pattern}")

    if frozen["source_study_sha256"] != (
        "sha256:3eb5b534ab486dac774a62de3d623fa33009be3705d9e8d620bb9942e8bfe664"
    ):
        fail("results-freeze.json is not bound to the validated recovered study SHA")
    if frozen["runs"] * frozen["instances_per_run"] != frozen["total_decisions"]:
        fail("frozen run matrix is internally inconsistent")
    expected_rate = frozen["format_error_count"] / frozen["total_decisions"]
    if abs(expected_rate - frozen["format_error_rate"]) > 1e-15:
        fail("frozen format-error rate is inconsistent with count/denominator")
    parseable_expected = frozen["total_decisions"] - frozen["format_error_count"]
    if parseable_expected != frozen["parseable_raw_decisions"]:
        fail("frozen parseable count is inconsistent")

    m06 = frozen["models"]["Qwen/Qwen3-0.6B"]
    m17 = frozen["models"]["Qwen/Qwen3-1.7B"]
    required = [
        f"{frozen['format_error_count']:,}/{frozen['total_decisions']:,}",
        f"{100 * frozen['format_error_rate']:.2f}\\%",
        f"{frozen['parseable_raw_decisions']:,}",
        f"Exactly {frozen['semantic_format_reclassified']} of {frozen['total_decisions']:,}",
        str(frozen["source_scored_workflow_run_id"]),
        str(frozen["source_recovery_workflow_run_id"]),
        "3eb5b534...e8bfe664",
        "Raw pre-enforcement behavior only",
        "Effective FPR",
        "decision coverage",
        "not evidence that the model learned the policy",
        "same frozen policy",
        "deterministic enforcement-consistency property",
        f"{pct(m06['gate_complete_pair_coverage_range'][0])}--{pct(m06['gate_complete_pair_coverage_range'][1])}\\%",
        f"{pct(m17['gate_complete_pair_coverage_range'][0])}--{pct(m17['gate_complete_pair_coverage_range'][1])}\\%",
    ]
    for phrase in required:
        if phrase.lower() not in lower:
            fail(f"required frozen result/boundary missing: {phrase!r}")

    for model in (m06, m17):
        if model["defined_raw_fpr_values"] != [1.0]:
            fail("frozen gate-arm raw FPR values changed")
        if model["defined_effective_fpr_values"] != [0.0]:
            fail("frozen gate-arm effective FPR values changed")
        if model["gate_catch_values"] != [1.0]:
            fail("frozen gate catch values changed")
        if model["false_block_values"] != [0.0]:
            fail("frozen false-block values changed")

    if r"\newcommand{\cpb}{\textsc{ClaimPromoteBench}\xspace}" not in tex:
        fail("ClaimPromoteBench macro must use xspace to prevent concatenated prose")
    if r"\usepackage{xspace}" not in tex:
        fail("xspace package missing")

    cite_keys: set[str] = set()
    for group in re.findall(r"\\cite(?:t|p)?\{([^}]+)\}", tex):
        cite_keys.update(k.strip() for k in group.split(",") if k.strip())
    bib_keys = set(re.findall(r"@\w+\{([^,]+),", bib))
    missing_bib = sorted(cite_keys - bib_keys)
    if missing_bib:
        fail(f"citation keys missing from references.bib: {missing_bib}")

    labels = re.findall(r"\\label\{([^}]+)\}", tex)
    dup_labels = sorted({label for label in labels if labels.count(label) > 1})
    if dup_labels:
        fail(f"duplicate labels: {dup_labels}")
    label_set = set(labels)
    refs = set(re.findall(r"\\(?:ref|eqref)\{([^}]+)\}", tex))
    missing_labels = sorted(refs - label_set)
    if missing_labels:
        fail(f"references without labels: {missing_labels}")

    abstract_match = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", tex, flags=re.DOTALL)
    if not abstract_match:
        fail("abstract not found")
    abstract_text = re.sub(r"\\[A-Za-z]+\*?(?:\{[^{}]*\})?", " ", abstract_match.group(1))
    abstract_words = re.findall(r"[A-Za-z0-9][A-Za-z0-9'._-]*", abstract_text)
    if len(abstract_words) > 250:
        word_count = len(abstract_words)
        fail(f"abstract is too long for a concise conference submission: {word_count} words")

    contrib_match = re.search(
        r"Our contributions are fourfold:\s*\\begin\{enumerate\}(.*?)\\end\{enumerate\}",
        tex,
        flags=re.DOTALL,
    )
    if not contrib_match:
        fail("fourfold contributions block not found")
    if len(re.findall(r"\\item\b", contrib_match.group(1))) != 4:
        fail("contributions block must contain exactly four non-overlapping items")

    raw_table = re.search(r"\\label\{tab:main-results\}(.*?)\\end\{table\}", tex, flags=re.DOTALL)
    if not raw_table:
        fail("raw main-results table not found")
    raw_text = raw_table.group(1)
    for model in ("Qwen3-0.6B", "Qwen3-1.7B"):
        pattern = (
            rf"{re.escape(model)}\s*&\s*Ledger \+ verifier \+ gate\s*&.*?"
            rf"&\s*1\.00\s*&\s*1\.00\s*&\s*0\.00"
        )
        if not re.search(pattern, raw_text):
            fail(f"gate row for {model} must report raw pre-enforcement FPR/VPR/PTA = 1/1/0")

    gate_table = re.search(r"\\label\{tab:gate-results\}(.*?)\\end\{table\}", tex, flags=re.DOTALL)
    if not gate_table or "Effective FPR" not in gate_table.group(1):
        fail("separate gate-enforcement table with Effective FPR is required")

    print(
        "paper-lint: PASS "
        f"({len(cite_keys)} citation keys, {len(label_set)} labels, "
        f"{len(abstract_words)} abstract words; frozen study {frozen['source_study_sha256']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
