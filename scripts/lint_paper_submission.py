#!/usr/bin/env python3
"""Fail-closed checks for the submission-facing ClaimPromoteBench manuscript."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TEX = ROOT / "technical-report" / "main.tex"
BIB = ROOT / "technical-report" / "references.bib"
README = ROOT / "README.md"
CITATION = ROOT / "CITATION.cff"
SUBMISSION_METADATA = ROOT / "docs" / "SUBMISSION_METADATA.md"
PAGE_RULES = ROOT / "docs" / "FREE_SUBMISSION_AND_PAGE_RULES.md"
SUBMISSION_GATE = ROOT / "technical-report" / "SUBMISSION_GATE_V2.md"
SUBMISSION_BUILDER = ROOT / "scripts" / "build_submission_tex.py"

RESULTS_FREEZE = ROOT / "technical-report" / "results-freeze.json"
R6_RESULT = ROOT / "v2" / "confirmatory" / "r6-execution" / "study-result.json"
R6_ADDENDUM = ROOT / "v2" / "confirmatory" / "r6-execution" / "reviewer-reporting-addendum.json"
R6_REDACTION = (
    ROOT
    / "release"
    / "reviewer-evidence-source"
    / "fresh-confirmatory"
    / "public-release-scientific-equivalence.json"
)
R6_CORRECTION = (
    ROOT / "v2" / "confirmatory" / "r6-execution" / "frozen-manifest-metadata-correction.json"
)
CHALLENGE_PLAN = ROOT / "v2" / "balanced-public-challenge-study-plan.json"
CHALLENGE_RESULT = ROOT / "v2" / "balanced-public-challenge" / "results" / "aggregate.json"
CHALLENGE_RECEIPT = (
    ROOT / "v2" / "balanced-public-challenge" / "results" / "github-artifact-receipt.json"
)
CHALLENGE_CORRECTION = (
    ROOT / "v2" / "balanced-public-challenge" / "results" / "reporting-correction-v1.json"
)
NATURALISTIC_POOL = ROOT / "v2" / "naturalistic-candidates.json"
NATURALISTIC_DECISION = ROOT / "v2" / "naturalistic-review-decision.json"

CANONICAL_TITLE = (
    "ClaimPromoteBench: Synthetic, Policy-Constrained Evaluation of Evidence-State Transitions"
)
ACTIONS = ("ALLOW", "HOLD", "DEMOTE", "ESCALATE")


def fail(message: str) -> None:
    raise SystemExit(f"paper-lint: {message}")


def load_object(path: Path, label: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        fail(f"{label} must contain a JSON object")
    return value


def self_digest(value: dict[str, Any], field: str) -> str:
    payload = dict(value)
    payload.pop(field, None)
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def require_regex(text: str, pattern: str, description: str) -> None:
    if not re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL):
        fail(f"required result or boundary missing: {description}")


def normalize_space(value: str) -> str:
    return " ".join(value.split())


def manuscript_abstract_plain(tex: str) -> str:
    match = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", tex, flags=re.DOTALL)
    if not match:
        fail("abstract not found")
    value = match.group(1)
    macros = {
        "cpb": "ClaimPromoteBench",
        "allow": "ALLOW",
        "hold": "HOLD",
        "demote": "DEMOTE",
        "escalate": "ESCALATE",
    }

    def replace_macro(match: re.Match[str]) -> str:
        return macros[match.group(1)]

    value = re.sub(r"\\(cpb|allow|hold|demote|escalate)(?:\{\})?", replace_macro, value)
    value = value.replace(r"\%", "%").replace(r"\_", "_")
    value = re.sub(r"\\texttt\{([^{}]*)\}", r"\1", value)
    return normalize_space(value)


def validate_submission_metadata(tex: str) -> None:
    readme = README.read_text(encoding="utf-8")
    citation = CITATION.read_text(encoding="utf-8")
    metadata = SUBMISSION_METADATA.read_text(encoding="utf-8")
    page_rules = PAGE_RULES.read_text(encoding="utf-8")

    if readme.splitlines()[0] != f"# {CANONICAL_TITLE}":
        fail("README title differs from canonical title")
    if f'title: "{CANONICAL_TITLE}"' not in citation:
        fail("CITATION.cff title differs from canonical title")
    if metadata.count(CANONICAL_TITLE) < 2:
        fail("ICLR and arXiv metadata titles must match canonical title")
    expected_tex_title = (
        r"\title{\cpb: Synthetic, Policy-Constrained Evaluation of Evidence-State Transitions}"
    )
    if expected_tex_title not in tex:
        fail("manuscript title differs from canonical title")

    abstract_match = re.search(
        r"## ICLR 2027 abstract\s+```text\s+(.*?)\s+```",
        metadata,
        flags=re.DOTALL,
    )
    if not abstract_match:
        fail("copy-ready ICLR abstract is missing")
    if normalize_space(abstract_match.group(1)) != manuscript_abstract_plain(tex):
        fail("submission metadata abstract differs from manuscript abstract")
    if "## arXiv abstract" not in metadata or "same canonical abstract" not in metadata:
        fail("arXiv abstract binding is missing")

    required_metadata = (
        "Chih-Kai Wang",
        "Department of Mathematics and Information Education",
        "National Taipei University of Education",
        "Suggested primary category: `cs.AI`",
        "Possible cross-list: `cs.LG`",
        "synthetic benchmarks",
        "policy conformance",
        "evidence-state transitions",
        "behavioral testing",
        "structured decision making",
        "trustworthy AI",
        "formal verification / verification-aware systems",
    )
    for phrase in required_metadata:
        if phrase not in metadata:
            fail(f"required submission metadata is missing: {phrase!r}")

    for date in ("2026-09-18", "2026-09-25"):
        if date not in metadata or date not in page_rules:
            fail(f"official ICLR date is missing: {date}")
    for stale in ("2026-09-11", "2026-09-16"):
        if stale in metadata or stale in page_rules:
            fail(f"stale ICLR date remains: {stale}")


def validate_no_stale_file_counts() -> None:
    paths = (TEX, README, SUBMISSION_METADATA, SUBMISSION_GATE, SUBMISSION_BUILDER)
    pattern = re.compile(r"\b(?:179|170|619)(?:-file|\s+files?)\b", flags=re.IGNORECASE)
    for path in paths:
        match = pattern.search(path.read_text(encoding="utf-8"))
        if match:
            fail(
                f"stale fixed artifact count remains in {path.relative_to(ROOT)}: {match.group(0)}"
            )


def validate_r6_evidence(tex: str) -> None:
    result = load_object(R6_RESULT, "r6 result")
    addendum = load_object(R6_ADDENDUM, "r6 reporting addendum")
    redaction = load_object(R6_REDACTION, "r6 redaction receipt")
    correction = load_object(R6_CORRECTION, "r6 metadata correction")

    if result.get("study_result_sha256") != self_digest(result, "study_result_sha256"):
        fail("r6 study-result self-digest changed")
    if result.get("status") != "R6_QWEN_CONFIRMATORY_SUPPORTED_FLASH_MODEL_EFFICACY_NON_EVALUABLE":
        fail("r6 disposition changed")
    if result.get("c2", {}).get("sealed_cells") != 600:
        fail("r6 C2 sealed-cell count changed")
    qwen_result = result.get("qwen_service_configuration", {})
    flash_result = result.get("deepseek_flash_service_configuration", {})
    expected_result_metrics = {
        "valid_decisions": 272,
        "end_to_end_item_accuracy": 0.86,
        "end_to_end_pair_accuracy": 0.753333333333333,
        "decision_coverage": 0.906666666666667,
        "balanced_action_recall": 0.599807213930348,
        "macro_f1": 0.626502732240437,
    }
    for key, expected in expected_result_metrics.items():
        if qwen_result.get(key) != expected:
            fail(f"r6 Qwen metric changed: {key}")
    if (
        flash_result.get("http_401_records") != 300
        or flash_result.get("model_outputs") != 0
        or flash_result.get("model_capability_interpretation") != "NON_EVALUABLE_NO_MODEL_OUTPUT"
    ):
        fail("r6 Flash interface disposition changed")

    if addendum.get("self_digest") != self_digest(addendum, "self_digest"):
        fail("r6 reporting-addendum self-digest changed")
    qwen = addendum.get("qwen_service_configuration", {})
    expected_addendum = {
        "items": 300,
        "pairs": 150,
        "valid_decisions": 272,
        "complete_pairs": 123,
        "correct_items": 258,
        "correct_pairs": 113,
        "decision_coverage": 0.9066666666666666,
        "pair_coverage": 0.82,
        "end_to_end_item_accuracy": 0.86,
        "end_to_end_pair_accuracy": 0.7533333333333333,
        "conditional_item_accuracy_given_valid_decision": 0.9485294117647058,
        "conditional_pair_accuracy_given_complete_pair": 0.9186991869918699,
    }
    for key, expected in expected_addendum.items():
        if qwen.get(key) != expected:
            fail(f"r6 addendum metric changed: {key}")
    expected_confusion = {
        "ALLOW": {"ALLOW": 143, "HOLD": 0, "DEMOTE": 0, "ESCALATE": 0, "NO_DECISION": 7},
        "HOLD": {"ALLOW": 4, "HOLD": 110, "DEMOTE": 0, "ESCALATE": 2, "NO_DECISION": 18},
        "DEMOTE": {"ALLOW": 8, "HOLD": 0, "DEMOTE": 0, "ESCALATE": 0, "NO_DECISION": 0},
        "ESCALATE": {"ALLOW": 0, "HOLD": 0, "DEMOTE": 0, "ESCALATE": 5, "NO_DECISION": 3},
    }
    if qwen.get("confusion") != expected_confusion:
        fail("r6 full confusion matrix changed")
    if addendum.get("public_dev_text_nb") != {
        "balanced_action_recall": 0.3283582089552239,
        "end_to_end_item_accuracy": 0.6133333333333333,
        "end_to_end_pair_accuracy": 0.22666666666666666,
        "macro_f1": 0.3123610914077647,
    }:
        fail("r6 Naive Bayes addendum changed")
    ceiling = addendum.get("deterministic_policy_executor", {})
    if (
        ceiling.get("item_accuracy") != 1.0
        or ceiling.get("pair_accuracy") != 1.0
        or ceiling.get("role") != "DEFINITIONAL_POLICY_CEILING_NOT_A_LEARNED_EMPIRICAL_BASELINE"
    ):
        fail("r6 definitional policy ceiling changed")
    if (
        redaction.get("hidden_reasoning_present_in_public_release") is not False
        or redaction.get("scientific_analysis_payload_byte_identical") is not True
    ):
        fail("r6 redaction disposition changed")
    if correction.get("self_digest") != self_digest(correction, "self_digest"):
        fail("r6 metadata-correction self-digest changed")

    required = (
        (r"272/300\s+valid decisions", "r6 valid-decision count"),
        (r"123/150\s+complete pairs", "r6 complete-pair count"),
        (r"\.9485", "r6 conditional item accuracy"),
        (r"\.9187", "r6 conditional pair accuracy"),
        (r"\.9067", "r6 decision coverage"),
        (r"\.8200", "r6 pair coverage"),
        (r"300\s+HTTP 401", "r6 Flash HTTP 401 count"),
        (r"old frozen service interface", "old Flash interface boundary"),
        (r"weak baseline", "Naive Bayes weakness"),
        (r"definitional policy ceiling", "deterministic ceiling role"),
    )
    for pattern, description in required:
        require_regex(tex, pattern, description)


def challenge_lane(aggregate: dict[str, Any], lane_id: str) -> dict[str, Any]:
    lanes = aggregate.get("lanes")
    if not isinstance(lanes, list):
        fail("balanced challenge lanes are missing")
    for lane in lanes:
        if isinstance(lane, dict) and lane.get("lane_id") == lane_id:
            return lane
    fail(f"balanced challenge lane missing: {lane_id}")
    raise AssertionError


def validate_challenge_lane(
    lane: dict[str, Any],
    *,
    expected: dict[str, Any],
    confusion: dict[str, dict[str, int]],
    recalls: dict[str, float],
) -> None:
    metrics = lane.get("metrics")
    if not isinstance(metrics, dict):
        fail(f"balanced challenge metrics missing: {lane.get('lane_id')}")
    for key, value in expected.items():
        if metrics.get(key) != value:
            fail(f"balanced challenge metric changed: {lane.get('lane_id')}.{key}")
    if metrics.get("confusion_matrix", {}).get("counts") != confusion:
        fail(f"balanced challenge confusion changed: {lane.get('lane_id')}")
    per_action = metrics.get("per_action", {})
    for action, recall in recalls.items():
        if per_action.get(action, {}).get("end_to_end_recall") != recall:
            fail(f"balanced challenge recall changed: {lane.get('lane_id')}.{action}")
    if (
        metrics.get("failure_rule")
        != "Every non-OK response remains in the denominator as incorrect."
    ):
        fail(f"balanced challenge denominator rule changed: {lane.get('lane_id')}")


def validate_balanced_challenge(tex: str) -> None:
    plan = load_object(CHALLENGE_PLAN, "balanced challenge plan")
    aggregate = load_object(CHALLENGE_RESULT, "balanced challenge aggregate")
    receipt = load_object(CHALLENGE_RECEIPT, "balanced challenge receipt")
    correction = load_object(CHALLENGE_CORRECTION, "balanced challenge reporting correction")

    dataset = plan.get("dataset", {})
    design = plan.get("design", {})
    if (
        plan.get("status") != "FROZEN_BEFORE_SCORED_INFERENCE"
        or dataset.get("pairs") != 90
        or dataset.get("instances") != 180
        or dataset.get("factors") != 15
        or dataset.get("invalid_action_counts") != {"HOLD": 30, "DEMOTE": 30, "ESCALATE": 30}
        or design.get("planned_model_item_cells") != 360
        or design.get("attempts_per_item") != 1
        or design.get("held_out_generalization_claim") is not False
    ):
        fail("balanced challenge frozen design changed")
    if (
        aggregate.get("status") != "COMPLETE"
        or aggregate.get("design") != "PUBLIC_PRECOMMITTED_BALANCED_CHALLENGE"
        or aggregate.get("truth_status") != "COMPUTATIONAL"
    ):
        fail("balanced challenge aggregate disposition changed")
    if (
        self_digest(correction, "receipt_sha256") != correction.get("receipt_sha256")
        or correction.get("status") != "REPORTING_CORRECTION"
        or correction.get("metric_convention")
        != "FIXED_FOUR_CLASS_MACRO_F1_WITH_ZERO_DIVISION_EQUAL_TO_ZERO"
        or correction.get("scope", {}).get("model_calls_performed") != 0
        or correction.get("scope", {}).get("raw_or_terminal_records_changed") is not False
        or correction.get("scope", {}).get("primary_endpoints_changed") is not False
    ):
        fail("balanced challenge reporting-correction boundary changed")
    for relative, expected in correction.get("source_bindings", {}).items():
        if sha256_file(ROOT / relative) != expected:
            fail(f"balanced challenge reporting-correction binding changed: {relative}")

    qwen_confusion = {
        "ALLOW": {"ALLOW": 79, "HOLD": 0, "DEMOTE": 0, "ESCALATE": 0, "NO_VALID_DECISION": 11},
        "HOLD": {"ALLOW": 0, "HOLD": 26, "DEMOTE": 0, "ESCALATE": 0, "NO_VALID_DECISION": 4},
        "DEMOTE": {"ALLOW": 8, "HOLD": 4, "DEMOTE": 4, "ESCALATE": 4, "NO_VALID_DECISION": 10},
        "ESCALATE": {"ALLOW": 0, "HOLD": 0, "DEMOTE": 0, "ESCALATE": 23, "NO_VALID_DECISION": 7},
    }
    flash_confusion = {
        "ALLOW": {"ALLOW": 68, "HOLD": 4, "DEMOTE": 0, "ESCALATE": 8, "NO_VALID_DECISION": 10},
        "HOLD": {"ALLOW": 13, "HOLD": 9, "DEMOTE": 0, "ESCALATE": 0, "NO_VALID_DECISION": 8},
        "DEMOTE": {"ALLOW": 25, "HOLD": 3, "DEMOTE": 0, "ESCALATE": 0, "NO_VALID_DECISION": 2},
        "ESCALATE": {"ALLOW": 0, "HOLD": 3, "DEMOTE": 0, "ESCALATE": 13, "NO_VALID_DECISION": 14},
    }
    qwen = challenge_lane(aggregate, "opencode-go-qwen3.7-max")
    flash = challenge_lane(aggregate, "opencode-go-deepseek-v4-flash-matched")
    validate_challenge_lane(
        qwen,
        expected={
            "items": 180,
            "pairs": 90,
            "parseable_items": 148,
            "covered_pairs": 64,
            "correct_items": 132,
            "correct_pairs": 48,
            "decision_coverage": 0.8222222222222222,
            "pair_coverage": 0.7111111111111111,
            "end_to_end_item_accuracy": 0.7333333333333333,
            "end_to_end_pair_accuracy": 0.5333333333333333,
            "conditional_item_accuracy": 0.8918918918918919,
            "conditional_pair_accuracy": 0.75,
            "balanced_action_recall": 0.6611111111111111,
            "macro_f1": 0.7004084238512532,
            "parse_status_counts": {"OK": 148, "SEMANTIC_ERROR": 1, "TRANSPORT_ERROR": 31},
        },
        confusion=qwen_confusion,
        recalls={
            "ALLOW": 0.8777777777777778,
            "HOLD": 0.8666666666666667,
            "DEMOTE": 0.13333333333333333,
            "ESCALATE": 0.7666666666666667,
        },
    )
    validate_challenge_lane(
        flash,
        expected={
            "items": 180,
            "pairs": 90,
            "parseable_items": 146,
            "covered_pairs": 61,
            "correct_items": 90,
            "correct_pairs": 13,
            "decision_coverage": 0.8111111111111111,
            "pair_coverage": 0.6777777777777778,
            "end_to_end_item_accuracy": 0.5,
            "end_to_end_pair_accuracy": 0.14444444444444443,
            "conditional_item_accuracy": 0.6164383561643836,
            "conditional_pair_accuracy": 0.21311475409836064,
            "balanced_action_recall": 0.37222222222222223,
            "macro_f1": 0.5236761371215153,
            "parse_status_counts": {"OK": 146, "SEMANTIC_ERROR": 34},
        },
        confusion=flash_confusion,
        recalls={
            "ALLOW": 0.7555555555555555,
            "HOLD": 0.3,
            "DEMOTE": 0.0,
            "ESCALATE": 0.43333333333333335,
        },
    )
    flash_correction = correction.get("affected_lanes", {}).get(
        "opencode-go-deepseek-v4-flash-matched", {}
    )
    if flash_correction.get("historical") != {
        "conditional_macro_f1": 0.6243032962151766,
        "macro_f1": 0.5236761371215153,
        "per_action.DEMOTE.conditional_f1": None,
        "per_action.DEMOTE.end_to_end_f1": None,
        "per_action.DEMOTE.precision": None,
    } or flash_correction.get("corrected") != {
        "conditional_macro_f1": 0.46822747216138244,
        "macro_f1": 0.39275710284113646,
        "per_action.DEMOTE.conditional_f1": 0.0,
        "per_action.DEMOTE.end_to_end_f1": 0.0,
        "per_action.DEMOTE.precision": 0.0,
    }:
        fail("balanced challenge reporting-correction values changed")
    ceiling = aggregate.get("deterministic_policy_executor", {})
    if (
        ceiling.get("end_to_end_item_accuracy") != 1.0
        or ceiling.get("end_to_end_pair_accuracy") != 1.0
        or ceiling.get("label") != "DEFINITIONAL_POLICY_CEILING_NOT_A_LEARNED_EMPIRICAL_BASELINE"
    ):
        fail("balanced challenge definitional ceiling changed")
    validation = receipt.get("validation", {})
    if (
        receipt.get("status") != "IMPORTED_AND_INDEPENDENTLY_RECOMPUTED"
        or receipt.get("workflow", {}).get("conclusion") != "success"
        or validation.get("terminal_records_validated") != 360
        or validation.get("non_numeric_fields_exact") is not True
        or validation.get("provider_account_identifier_findings") != 0
        or validation.get("retained_provider_response_ids") != 0
        or validation.get("hidden_reasoning_field_findings") != 0
    ):
        fail("balanced challenge receipt changed")

    required = (
        (r"90\s+pairs and 15 factors", "challenge size"),
        (r"148/180\s+valid decisions", "challenge Qwen coverage count"),
        (r"146/180\s+valid decisions", "challenge Flash coverage count"),
        (r"\.7333/\.5333", "challenge Qwen end-to-end metrics"),
        (r"\.8919/\.7500", "challenge Qwen conditional metrics"),
        (r"\.5000/\.1444", "challenge Flash end-to-end metrics"),
        (r"\.6164/\.2131", "challenge Flash conditional metrics"),
        (r"\.3928", "corrected challenge Flash fixed-four-class Macro-F1"),
        (r"\.4682", "corrected challenge Flash conditional Macro-F1"),
        (r"zero division", "fixed-four-class zero-division convention"),
        (r"public, preregistered robustness challenge", "public challenge boundary"),
        (r"strict causal", "cross-service causal boundary"),
    )
    for pattern, description in required:
        require_regex(tex, pattern, description)


def parse_confusion_table(tex: str) -> dict[tuple[str, str], tuple[int, ...]]:
    match = re.search(
        r"\\label\{tab:confusion\}(.*?)\\end\{table\}",
        tex,
        flags=re.DOTALL,
    )
    if not match:
        fail("full confusion table is missing")
    current = ""
    rows: dict[tuple[str, str], tuple[int, ...]] = {}
    action_macros = {
        r"\allow{}": "ALLOW",
        r"\hold{}": "HOLD",
        r"\demote{}": "DEMOTE",
        r"\escalate{}": "ESCALATE",
    }
    for line in match.group(1).splitlines():
        if "&" not in line or not line.rstrip().endswith(r"\\"):
            continue
        fields = [field.strip() for field in line.rstrip()[:-2].split("&")]
        if len(fields) != 7 or fields[0] == "Configuration":
            continue
        if fields[0]:
            current = fields[0]
        gold = action_macros.get(fields[1])
        if not current or gold is None:
            continue
        try:
            values = tuple(int(field) for field in fields[2:])
        except ValueError:
            continue
        rows[(current, gold)] = values
    return rows


def validate_manuscript_tables(tex: str) -> None:
    table_rows = parse_confusion_table(tex)
    expected = {
        ("r6 Qwen", "ALLOW"): (143, 0, 0, 0, 7),
        ("r6 Qwen", "HOLD"): (4, 110, 0, 2, 18),
        ("r6 Qwen", "DEMOTE"): (8, 0, 0, 0, 0),
        ("r6 Qwen", "ESCALATE"): (0, 0, 0, 5, 3),
        ("Challenge Qwen", "ALLOW"): (79, 0, 0, 0, 11),
        ("Challenge Qwen", "HOLD"): (0, 26, 0, 0, 4),
        ("Challenge Qwen", "DEMOTE"): (8, 4, 4, 4, 10),
        ("Challenge Qwen", "ESCALATE"): (0, 0, 0, 23, 7),
        ("Challenge Flash", "ALLOW"): (68, 4, 0, 8, 10),
        ("Challenge Flash", "HOLD"): (13, 9, 0, 0, 8),
        ("Challenge Flash", "DEMOTE"): (25, 3, 0, 0, 2),
        ("Challenge Flash", "ESCALATE"): (0, 3, 0, 13, 14),
    }
    if table_rows != expected:
        fail("manuscript confusion table differs from bound evidence")

    for label in ("tab:core-results", "tab:action-recall", "tab:confusion"):
        if rf"\label{{{label}}}" not in tex:
            fail(f"required result table missing: {label}")
    core_rows = (
        (
            r"r6 Qwen3\.7-Max\s*&\s*272/300\s*&\s*\.8600\s*&\s*\.9485"
            r"\s*&\s*\.8200\s*&\s*\.7533\s*&\s*\.9187"
        ),
        (
            r"Public challenge Qwen\s*&\s*148/180\s*&\s*\.7333\s*&\s*\.8919"
            r"\s*&\s*\.7111\s*&\s*\.5333\s*&\s*\.7500"
        ),
        (
            r"Public challenge Flash\s*&\s*146/180\s*&\s*\.5000\s*&\s*\.6164"
            r"\s*&\s*\.6778\s*&\s*\.1444\s*&\s*\.2131"
        ),
    )
    for pattern in core_rows:
        require_regex(tex, pattern, "core result table row")
    action_rows = (
        (
            r"r6 Qwen3\.7-Max\s*&\s*\.9533\s*&\s*\.8209\s*&\s*\.0000"
            r"\s*&\s*\.6250\s*&\s*\.5998\s*&\s*\.6265"
        ),
        (
            r"Public challenge Qwen\s*&\s*\.8778\s*&\s*\.8667\s*&\s*\.1333"
            r"\s*&\s*\.7667\s*&\s*\.6611\s*&\s*\.7004"
        ),
        (
            r"Public challenge Flash\s*&\s*\.7556\s*&\s*\.3000\s*&\s*\.0000"
            r"\s*&\s*\.4333\s*&\s*\.3722\s*&\s*\.3928"
        ),
    )
    for pattern in action_rows:
        require_regex(tex, pattern, "action-recall table row")


def validate_naturalistic_decision(tex: str) -> None:
    pool_bytes = NATURALISTIC_POOL.read_bytes()
    pool = load_object(NATURALISTIC_POOL, "naturalistic candidate pool")
    decision = load_object(NATURALISTIC_DECISION, "naturalistic review decision")
    observed_sha = "sha256:" + hashlib.sha256(pool_bytes).hexdigest()
    if decision.get("candidate_pool") != {
        "path": "v2/naturalistic-candidates.json",
        "sha256": observed_sha,
        "candidate_count": len(pool.get("candidates", [])),
    }:
        fail("naturalistic decision is not bound to candidate pool")
    expected_ids = [row.get("candidate_id") for row in pool.get("candidates", [])]
    if decision.get("reviewed_candidate_ids") != expected_ids:
        fail("naturalistic reviewed candidate list changed")
    if decision.get("decision") != {
        "cases_created": 0,
        "model_calls": 0,
        "claimpromotebench_model_outputs_consulted": False,
        "human_annotators": 0,
        "agreement_statistic": None,
        "selection_frozen_before_model_calls": True,
    }:
        fail("naturalistic pre-model decision changed")
    required = (
        (r"zero naturalistic benchmark cases", "zero naturalistic cases"),
        (r"zero model calls", "zero naturalistic model calls"),
        (r"No human annotators", "no fabricated human annotation"),
        (r"Naturalistic transfer remains open", "naturalistic limitation"),
    )
    for pattern, description in required:
        require_regex(tex, pattern, description)


def validate_v1_diagnostic(tex: str) -> None:
    frozen = load_object(RESULTS_FREEZE, "v1 results freeze")
    if frozen.get("source_study_sha256") != (
        "sha256:3eb5b534ab486dac774a62de3d623fa33009be3705d9e8d620bb9942e8bfe664"
    ):
        fail("v1 results freeze changed")
    if frozen.get("format_error_count") != 5327 or frozen.get("parseable_raw_decisions") != 1873:
        fail("v1 diagnostic counts changed")
    for pattern, description in (
        (r"7,200-decision", "v1 decision count"),
        (r"5,327\s+format errors", "v1 format errors"),
        (r"1,873\s+parseable", "v1 parseable decisions"),
        (r"\.1333\s+end-to-end item accuracy", "v1 end-to-end accuracy"),
    ):
        require_regex(tex, pattern, description)


def validate_structure_and_citations(tex: str, bib: str) -> tuple[int, int, int]:
    lower = tex.lower()
    for section in (
        "Introduction",
        "Related Work",
        "Task and Evidence Flow",
        "Benchmark and Evaluation Design",
        "Results",
        "Discussion",
        "Limitations",
        "Conclusion",
    ):
        if rf"\section{{{section}}}" not in tex:
            fail(f"required manuscript section missing: {section}")
    if r"\label{fig:evidence-flow}" not in tex:
        fail("benchmark/evidence-flow figure is missing")

    overclaims = (
        r"\bfirst benchmark\b",
        r"\bfirst system\b",
        r"\bfirst framework\b",
        r"\bstate[- ]of[- ]the[- ]art\b",
        r"\bguarantees? safety\b",
        r"general research-agent competence is established",
    )
    for pattern in overclaims:
        if re.search(pattern, tex, flags=re.IGNORECASE):
            fail(f"unsupported novelty or capability claim found: {pattern}")
    for phrase in (
        "synthetic policy-conformance problem",
        "author-defined policy",
        "Every transport, syntax, schema, and semantic failure",
        "public robustness challenge",
        "not a causal ablation",
        "No human annotation study",
    ):
        if phrase.lower() not in lower:
            fail(f"required interpretation boundary missing: {phrase!r}")

    cite_keys: set[str] = set()
    for group in re.findall(r"\\cite(?:t|p)?\{([^}]+)\}", tex):
        cite_keys.update(key.strip() for key in group.split(",") if key.strip())
    bib_keys = set(re.findall(r"@\w+\{([^,]+),", bib))
    missing = sorted(cite_keys - bib_keys)
    if missing:
        fail(f"citation keys missing from references.bib: {missing}")
    required_citations = {
        "ribeiro2020checklist",
        "gardner2020contrastsets",
        "chan1998metamorphic",
        "scholak2021picard",
        "geng2023grammar",
        "geifman2017selective",
        "geifman2019selectivenet",
        "chen2025scienceagentbench",
        "siegel2025corebench",
        "huang2025popper",
    }
    if not required_citations <= cite_keys:
        fail(f"required primary-source citations missing: {sorted(required_citations - cite_keys)}")

    labels = re.findall(r"\\label\{([^}]+)\}", tex)
    duplicates = sorted({label for label in labels if labels.count(label) > 1})
    if duplicates:
        fail(f"duplicate labels: {duplicates}")
    refs = set(re.findall(r"\\(?:ref|eqref)\{([^}]+)\}", tex))
    missing_labels = sorted(refs - set(labels))
    if missing_labels:
        fail(f"references without labels: {missing_labels}")

    abstract = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", tex, flags=re.DOTALL)
    if not abstract:
        fail("abstract not found")
    abstract_text = re.sub(r"\\[A-Za-z]+\*?(?:\{[^{}]*\})?", " ", abstract.group(1))
    abstract_words = re.findall(r"[A-Za-z0-9][A-Za-z0-9'._-]*", abstract_text)
    if len(abstract_words) > 250:
        fail(f"abstract exceeds 250 words: {len(abstract_words)}")

    contributions = re.search(
        r"Our contributions are:\s*\\begin\{enumerate\}(.*?)\\end\{enumerate\}",
        tex,
        flags=re.DOTALL,
    )
    if not contributions:
        fail("contributions block not found")
    contribution_count = len(re.findall(r"\\item\b", contributions.group(1)))
    if not 3 <= contribution_count <= 5:
        fail("contributions block must contain three to five items")
    if "The author chose" not in tex or "responsible for the manuscript" not in tex:
        fail("AI assistance disclosure must retain author responsibility")
    return len(cite_keys), len(set(labels)), len(abstract_words)


def main() -> int:
    tex = TEX.read_text(encoding="utf-8")
    bib = BIB.read_text(encoding="utf-8")
    validate_submission_metadata(tex)
    validate_no_stale_file_counts()
    validate_r6_evidence(tex)
    validate_balanced_challenge(tex)
    validate_manuscript_tables(tex)
    validate_naturalistic_decision(tex)
    validate_v1_diagnostic(tex)
    citation_count, label_count, abstract_words = validate_structure_and_citations(tex, bib)
    print(
        "paper-lint: PASS "
        f"({citation_count} citation keys, {label_count} labels, "
        f"{abstract_words} abstract words; r6 addendum and balanced challenge bound)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
