#!/usr/bin/env python3
"""Fail-closed checks for the submission-facing ClaimPromoteBench manuscript."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TEX = ROOT / "technical-report" / "main.tex"
BIB = ROOT / "technical-report" / "references.bib"
RESULTS_FREEZE = ROOT / "technical-report" / "results-freeze.json"
V2_PILOT = ROOT / "v2" / "pilot-results" / "v2-public-pilot-study.json"
V2_PILOT_SHA = "sha256:83dbee4923bca6a0d1908083172190d7b81e2a5e9613c22e4929cfa25c0b264e"


def fail(message: str) -> None:
    raise SystemExit(f"paper-lint: {message}")


def pct(value: float, digits: int = 1) -> str:
    return f"{100 * value:.{digits}f}"


def require_regex(tex: str, pattern: str, description: str) -> None:
    if not re.search(pattern, tex, flags=re.IGNORECASE | re.DOTALL):
        fail(f"required frozen result/boundary missing: {description}")


def load_object(path: Path, label: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        fail(f"{label} must contain a JSON object")
    return value


def validate_v2_pilot_binding(tex: str, pilot: dict[str, Any]) -> None:
    if pilot.get("study_sha256") != V2_PILOT_SHA:
        fail("post-v1 public pilot is not bound to the validated aggregate SHA")
    if pilot.get("source_workflow_run_id") != 32291482079:
        fail("post-v1 public pilot source workflow changed")
    if pilot.get("aggregate_status_counts") != {"OK": 108, "SCHEMA_ERROR": 52}:
        fail("post-v1 public pilot status counts changed")

    protocol = pilot.get("protocol")
    if not isinstance(protocol, dict):
        fail("post-v1 public pilot protocol is missing")
    expected_protocol = {
        "instances": 40,
        "pairs": 20,
        "seed": 104729,
        "total_decisions": 160,
        "paid_api_calls": 0,
    }
    for key, expected in expected_protocol.items():
        if protocol.get(key) != expected:
            fail(f"post-v1 public pilot protocol.{key} changed")

    required_patterns = [
        (r"post-v1 public", "post-v1 public scope label"),
        (r"all\s+78\s+constrained parseable decisions remain", "78 constrained decisions"),
        (r"38\s+complete pairs", "38 constrained complete pairs"),
        (r"coverage from 75\\% to 100\\%", "Qwen3-0.6B constrained coverage change"),
        (r"from 0\\% to 95\\%", "Qwen3-1.7B constrained coverage change"),
        (r"raw pair accuracy and flip rate remain zero", "zero pair accuracy and flip rate"),
        (r"workflow run \\texttt\{32291482079\}", "public pilot source workflow"),
        (r"\\texttt\{83dbee49\.\.\.25c0b264e\}", "public pilot aggregate SHA"),
    ]
    for pattern, description in required_patterns:
        require_regex(tex, pattern, description)

    pilot_table = re.search(
        r"\\label\{tab:v2-pilot\}(.*?)\\end\{table\}",
        tex,
        flags=re.DOTALL,
    )
    if not pilot_table:
        fail("post-v1 public pilot table not found")
    table = pilot_table.group(1)
    expected_rows = [
        r"Qwen3-0\.6B\s*&\s*Free\s*&\s*\.75\s*&\s*\.70\s*&\s*\.50\s*&\s*\.00",
        r"Qwen3-0\.6B\s*&\s*Schema\s*&\s*1\.00\s*&\s*1\.00\s*&\s*\.50\s*&\s*\.00",
        r"Qwen3-1\.7B\s*&\s*Free\s*&\s*\.00\s*&\s*\.00\s*&\s*undef\.\s*&\s*undef\.",
        r"Qwen3-1\.7B\s*&\s*Schema\s*&\s*\.95\s*&\s*\.90\s*&\s*\.50\s*&\s*\.00",
    ]
    for pattern in expected_rows:
        if not re.search(pattern, table):
            fail(f"post-v1 public pilot table row changed: {pattern}")


def main() -> int:
    tex = TEX.read_text(encoding="utf-8")
    bib = BIB.read_text(encoding="utf-8")
    frozen = load_object(RESULTS_FREEZE, "results-freeze.json")
    pilot = load_object(V2_PILOT, "v2 public pilot study")
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

    human_study_phrases = [
        "supplementary human audit",
        "human policy audit",
        "reviewer 1 &",
        "reviewer 2 &",
        "cohen's $\\kappa",
        "mixed / not pass",
        "two-reviewer audit",
        "independent human reviewers",
    ]
    for phrase in human_study_phrases:
        if phrase in lower:
            fail(f"removed human-study wording remains in manuscript: {phrase!r}")

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

    style_smells = [
        "artifact-bound",
        "fail-closed",
        "enforcement-consistency property",
        "first-order failure",
        "operationally important",
        "correspondingly narrow",
        "frozen empirical diagnosis",
        "conditional enforcement boundary",
        "normative by benchmark definition",
    ]
    for phrase in style_smells:
        if phrase in lower:
            fail(f"internal/jargon-heavy wording remains in manuscript: {phrase!r}")

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

    total = f"{frozen['total_decisions']:,}"
    errors = f"{frozen['format_error_count']:,}"
    parseable = f"{frozen['parseable_raw_decisions']:,}"
    reclassified = frozen["semantic_format_reclassified"]

    require_regex(
        tex,
        rf"{re.escape(errors)}\s*(?:/|of)\s*{re.escape(total)}",
        f"format-error count {errors}/{total}",
    )
    require_regex(
        tex,
        rf"{100 * frozen['format_error_rate']:.2f}\\%",
        "73.99 percent format-error rate",
    )
    require_regex(tex, re.escape(parseable), f"parseable raw decision count {parseable}")
    require_regex(
        tex,
        rf"Exactly\s+{reclassified}\s+of\s+{re.escape(total)}",
        "semantic-format recovery count",
    )

    required_plain = [
        str(frozen["source_scored_workflow_run_id"]),
        str(frozen["source_recovery_workflow_run_id"]),
        "3eb5b534...e8bfe664",
        "Effective FPR",
        "decision coverage",
        "same fixed policy used to define the benchmark labels",
        "not evidence that the model learned the policy",
        "Machine-checkable validation strategy",
        "public pair-contract audit",
        "author-defined policy is a universal scientific norm",
        (
            f"{pct(m06['gate_complete_pair_coverage_range'][0])}--"
            f"{pct(m06['gate_complete_pair_coverage_range'][1])}\\%"
        ),
        (
            f"{pct(m17['gate_complete_pair_coverage_range'][0])}--"
            f"{pct(m17['gate_complete_pair_coverage_range'][1])}\\%"
        ),
    ]
    for phrase in required_plain:
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

    validate_v2_pilot_binding(tex, pilot)

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
        r"Our contributions are:\s*\\begin\{enumerate\}(.*?)\\end\{enumerate\}",
        tex,
        flags=re.DOTALL,
    )
    if not contrib_match:
        fail("contributions block not found")
    if len(re.findall(r"\\item\b", contrib_match.group(1))) != 4:
        fail("contributions block must contain exactly four items")

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
        fail("separate gate table with Effective FPR is required")

    if "The author" not in tex or "AI systems are not listed as authors" not in tex:
        fail("AI assistance disclosure must state author responsibility and non-authorship of AI")

    print(
        "paper-lint: PASS "
        f"({len(cite_keys)} citation keys, {len(label_set)} labels, "
        f"{len(abstract_words)} abstract words; frozen study {frozen['source_study_sha256']}; "
        f"public pilot {pilot['study_sha256']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
