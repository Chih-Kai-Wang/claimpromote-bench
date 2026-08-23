#!/usr/bin/env python3
"""Fail-closed checks for the submission-facing ClaimPromoteBench manuscript."""

from __future__ import annotations

import hashlib
import json
import re
import runpy
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
STYLE_AUDIT = ROOT / "docs" / "MANUSCRIPT_STYLE_AUDIT_2026-08-23.json"
STYLE_CORPUS_MANIFEST = ROOT / "docs" / "PAPER_STYLE_CORPUS_MANIFEST_2026-08-23.json"
STYLE_CORPUS_STATISTICS = ROOT / "docs" / "PAPER_STYLE_CORPUS_STATISTICS_2026-08-23.json"

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
SLSA_ROOT = ROOT / "v2" / "slsa-portability-v1" / "replacement-v2"
SLSA_RESULT = SLSA_ROOT / "results" / "aggregate.json"
POLICY_SWITCH_ROOT = ROOT / "v2" / "policy-switch-v1" / "frozen"
POLICY_SWITCH_RESULT = POLICY_SWITCH_ROOT / "results" / "aggregate.json"
POLICY_DIFFERENCE_COVERAGE = ROOT / "v2" / "policy-switch-v1" / "policy-difference-coverage.json"
HOSTED_POLICY_REPLACEMENT_RECEIPT = (
    ROOT
    / "v2"
    / "policy-switch-v1"
    / "hosted-replacement-v2"
    / "results"
    / "manuscript-eligibility-receipt.json"
)
LOCAL_REPLICATION_ROOT = ROOT / "v2" / "local-model-replication-v1" / "replacement-v2" / "frozen"
BREADTH_PLAN = ROOT / "v2" / "public-model-breadth-v1" / "study-plan.json"
BREADTH_RESULT_ROOT = ROOT / "v2" / "public-model-breadth-v1" / "results"
BREADTH_RESULT = BREADTH_RESULT_ROOT / "reported-aggregate.json"
BREADTH_FAILURE_ADDENDUM = BREADTH_RESULT_ROOT / "failure-cause-addendum.json"
BREADTH_FAILURE_DERIVER = ROOT / "scripts" / "derive_public_model_breadth_failure_addendum.py"
BREADTH_PRIVATE_JOURNAL = (
    ROOT
    / "v2"
    / "public-model-breadth-v1"
    / "private-results"
    / "journal"
    / "terminal-records.jsonl"
)
BREADTH_PACKET = ROOT / "v2" / "balanced-public-challenge" / "prompt-packet.json"
BREADTH_DATASET = ROOT / "v2" / "balanced-public-challenge" / "dataset"
BREADTH_VERIFIER = ROOT / "release" / "tools" / "verify_public_model_breadth_public_evidence.py"
NATURALISTIC_POOL = ROOT / "v2" / "naturalistic-candidates.json"
NATURALISTIC_DECISION = ROOT / "v2" / "naturalistic-review-decision.json"

CANONICAL_TITLE = (
    "ClaimPromoteBench: Failure-Aware Conformance Testing for Policy-Conditioned State Transitions"
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
        r"\title{\cpb: Failure-Aware Conformance Testing for Policy-Conditioned State Transitions}"
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


def validate_manuscript_style_audit() -> None:
    audit = load_object(STYLE_AUDIT, "manuscript style audit")
    after = audit.get("after")
    boundary = audit.get("scientific_content_boundary")
    if not isinstance(after, dict) or not isinstance(boundary, dict):
        fail("manuscript style audit is malformed")
    expected_hashes = {
        "corpus_manifest_sha256": sha256_file(STYLE_CORPUS_MANIFEST).removeprefix("sha256:"),
        "corpus_statistics_sha256": sha256_file(STYLE_CORPUS_STATISTICS).removeprefix("sha256:"),
    }
    if audit.get("status") != "PASS" or any(
        audit.get(field) != value for field, value in expected_hashes.items()
    ):
        fail("manuscript style audit corpus binding changed")
    if after.get("manuscript_sha256") != sha256_file(TEX).removeprefix("sha256:"):
        fail("manuscript style audit is stale for technical-report/main.tex")
    findings = after.get("configured_pattern_findings")
    if (
        not isinstance(findings, dict)
        or not findings
        or any(value != 0 for value in findings.values())
    ):
        fail("manuscript style audit retains a configured negative-pattern finding")
    if (
        boundary.get("metrics_changed") is not True
        or boundary.get("existing_terminal_records_changed") is not False
        or boundary.get("new_scored_terminal_records_added") != 720
        or boundary.get("scored_model_calls_performed") != 720
        or boundary.get("void_protocol_application_posts") != 1
        or boundary.get("total_application_posts_during_revision") != 721
        or boundary.get("completed_singleton_workflows_rerun") is not False
        or boundary.get("balanced_public_v1_rerun") is not False
        or boundary.get("paper_binding_validator") != "scripts/lint_paper_submission.py"
    ):
        fail("manuscript style audit scientific-content boundary changed")


def validate_no_stale_file_counts() -> None:
    paths = (TEX, README, SUBMISSION_METADATA, SUBMISSION_GATE, SUBMISSION_BUILDER)
    pattern = re.compile(r"\b(?:179|170|619)(?:-file|\s+files?)\b", flags=re.IGNORECASE)
    for path in paths:
        match = pattern.search(path.read_text(encoding="utf-8"))
        if match:
            fail(
                f"stale fixed artifact count remains in {path.relative_to(ROOT)}: {match.group(0)}"
            )


def validate_submission_builder(tex: str) -> None:
    namespace = runpy.run_path(str(SUBMISSION_BUILDER))
    canonical_body = namespace["canonical_body"]()
    canonical_appendix = namespace["canonical_appendix"]()
    body_start = tex.index(r"\begin{abstract}")
    bib_start = tex.rindex(r"\bibliographystyle")
    expected_body = tex[body_start:bib_start].rstrip() + "\n\n"
    if canonical_body != expected_body:
        fail("submission builder changes the canonical manuscript body")
    bibliography = r"\bibliography{references}"
    bibliography_end = tex.rindex(bibliography) + len(bibliography)
    document_end = tex.rindex(r"\end{document}")
    appendix = tex[bibliography_end:document_end].strip()
    expected_appendix = appendix + ("\n" if appendix else "")
    if canonical_appendix != expected_appendix:
        fail("submission builder changes the canonical appendix")

    reproducibility_start = expected_body.index(r"\section{Reproducibility Statement}")
    conclusion_start = expected_body.index(r"\section{Conclusion}", reproducibility_start)
    canonical_tail = expected_body[reproducibility_start:conclusion_start]
    rendered = {
        "ICLR": namespace["iclr_tex"](canonical_body, canonical_appendix),
        "arXiv": namespace["arxiv_tex"](canonical_body, canonical_appendix),
    }
    for label, wrapper in rendered.items():
        if canonical_tail not in wrapper:
            fail(f"{label} wrapper changes reproducibility or AI-disclosure prose")
        if canonical_appendix not in wrapper:
            fail(f"{label} wrapper drops the canonical appendix")
    for stale in (
        "same 7,200-record aggregate",
        "all 14 pilot attempts",
        "ICLR_REPRODUCIBILITY",
        "AI_DISCLOSURE =",
    ):
        if stale in SUBMISSION_BUILDER.read_text(encoding="utf-8"):
            fail(f"submission builder retains stale injected prose: {stale!r}")


def validate_factor_metrics(
    metrics: Any,
    *,
    label: str,
    factor_count: int,
    pair_support: set[int],
    pair_coverage_range: tuple[float, float],
    end_to_end_range: tuple[float, float],
    zero_factor_ids: set[str],
    perfect_factor_ids: set[str],
) -> dict[str, dict[str, Any]]:
    if not isinstance(metrics, list) or not all(isinstance(row, dict) for row in metrics):
        fail(f"{label} factor metrics are malformed")
    by_id = {str(row.get("factor_id")): row for row in metrics}
    if len(metrics) != factor_count or len(by_id) != factor_count:
        fail(f"{label} factor count changed")
    if {int(row.get("pairs", -1)) for row in metrics} != pair_support:
        fail(f"{label} pair support changed")
    coverages = [float(row.get("pair_coverage", -1)) for row in metrics]
    accuracies = [float(row.get("end_to_end_pair_accuracy", -1)) for row in metrics]
    if (min(coverages), max(coverages)) != pair_coverage_range:
        fail(f"{label} factor pair-coverage range changed")
    if (min(accuracies), max(accuracies)) != end_to_end_range:
        fail(f"{label} factor end-to-end pair range changed")
    observed_zero = {
        factor_id for factor_id, row in by_id.items() if row.get("end_to_end_pair_accuracy") == 0
    }
    observed_perfect = {
        factor_id for factor_id, row in by_id.items() if row.get("end_to_end_pair_accuracy") == 1
    }
    if observed_zero != zero_factor_ids or observed_perfect != perfect_factor_ids:
        fail(f"{label} zero/perfect factor identities changed")
    return by_id


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
    if addendum.get("schema_version") != "1.1.0":
        fail("r6 reporting-addendum schema changed")
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
    r6_factors = validate_factor_metrics(
        qwen.get("factor_metrics"),
        label="r6 Qwen",
        factor_count=20,
        pair_support={7, 8},
        pair_coverage_range=(2 / 7, 1.0),
        end_to_end_range=(0.0, 1.0),
        zero_factor_ids={"current_binding", "dependency_statement"},
        perfect_factor_ids={
            "dependency_verifier",
            "precision",
            "preregistration",
            "repetitions",
            "tool_exit",
            "transitive_dependency",
            "verifier_execution",
        },
    )
    if (
        r6_factors["dependency_statement"].get("covered_pairs") != 2
        or r6_factors["dependency_statement"].get("pairs") != 7
        or r6_factors["current_binding"].get("covered_pairs") != 6
        or r6_factors["current_binding"].get("pairs") != 8
    ):
        fail("r6 zero-accuracy factor details changed")
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
        (r"123/150", "r6 complete-pair count"),
        (r"258/272", "r6 conditional item accuracy"),
        (r"113/123", "r6 conditional pair accuracy"),
        (r"272/300", "r6 decision coverage"),
        (r"123/150", "r6 pair coverage"),
        (r"(?:300\s+HTTP 401|HTTP 401[^.]{0,40}300 requests)", "r6 Flash HTTP 401 count"),
        (r"old (?:r6 )?Flash interface", "old Flash interface boundary"),
        (
            r"dependency.statement changes.*0/7|0/7.*dependency.statement",
            "r6 dependency-statement factor result",
        ),
        (
            r"current.state binding.*0/8|0/8.*current.state binding",
            "r6 current-binding factor result",
        ),
        (r"Naive Bayes.*weak|weak.*Naive Bayes", "Naive Bayes weakness"),
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
    validate_factor_metrics(
        qwen.get("metrics", {}).get("factor_metrics"),
        label="challenge Qwen",
        factor_count=15,
        pair_support={6},
        pair_coverage_range=(0.5, 1.0),
        end_to_end_range=(0.0, 1.0),
        zero_factor_ids={
            "current_computation_binding",
            "current_computation_stale",
            "current_review_environment",
        },
        perfect_factor_ids={"contradiction_status", "tool_exit"},
    )
    validate_factor_metrics(
        flash.get("metrics", {}).get("factor_metrics"),
        label="challenge Flash",
        factor_count=15,
        pair_support={6},
        pair_coverage_range=(0.0, 1.0),
        end_to_end_range=(0.0, 5 / 6),
        zero_factor_ids={
            "age",
            "contradiction_claim_identity",
            "contradiction_freshness",
            "contradiction_reviewer_identity",
            "contradiction_verifier_execution",
            "current_computation_binding",
            "current_computation_stale",
            "current_computation_verifier",
            "current_review_environment",
            "current_review_identity",
            "reviewer_identity",
        },
        perfect_factor_ids=set(),
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
        (r"90\s+pairs", "challenge pair count"),
        (r"15\s+factors", "challenge factor count"),
        (r"148/180", "challenge Qwen coverage count"),
        (r"146/180", "challenge Flash coverage count"),
        (r"132/180.*48/90", "challenge Qwen end-to-end metrics"),
        (r"132/148.*48/64", "challenge Qwen conditional metrics"),
        (r"90/180.*13/90", "challenge Flash end-to-end metrics"),
        (r"90/146.*13/61", "challenge Flash conditional metrics"),
        (r"public challenge", "public challenge boundary"),
        (r"causal (?:comparison|ablation)", "cross-service causal boundary"),
        (r"factor.*pair", "factor-level pair reporting"),
    )
    for pattern, description in required:
        require_regex(tex, pattern, description)


def paper_rate(value: Any) -> str:
    if value is None:
        return "N/E"
    if not isinstance(value, (int, float)):
        fail(f"paper rate is not numeric: {value!r}")
    return f"{float(value):.4f}".removeprefix("0")


def load_jsonl(path: Path, label: str) -> list[dict[str, Any]]:
    rows = [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    if any(not isinstance(row, dict) for row in rows):
        fail(f"{label} contains a non-object JSONL row")
    return rows


def recompute_synthetic_lanes(
    *,
    study_root: Path,
    dataset_root: Path,
    aggregate_path: Path,
    expected_design: str,
) -> dict[str, dict[str, Any]]:
    aggregate = load_object(aggregate_path, f"{study_root.name} aggregate")
    execution = load_object(study_root / "results" / "execution-receipt.json", "execution receipt")
    result_receipt = load_object(
        study_root / "results" / "result-receipt.json", "synthetic-policy result receipt"
    )
    if (
        aggregate.get("status") != "COMPLETE"
        or aggregate.get("design") != expected_design
        or execution.get("status") != "COMPLETE_ALL_FROZEN_CELLS_TERMINAL"
        or execution.get("planned_cells") != 240
        or execution.get("durable_terminal_records") != 240
        or execution.get("client_retry_count") != 0
        or result_receipt.get("status") != "SYNTHETIC_POLICY_RESULTS_SEALED"
        or result_receipt.get("planned_and_terminal_cells") != 240
        or result_receipt.get("all_failures_retained_in_end_to_end_denominator") is not True
    ):
        fail(f"completed synthetic-policy boundary changed: {study_root}")
    if aggregate.get("deterministic_policy_executor", {}).get("label") != (
        "DEFINITIONAL_POLICY_CEILING_NOT_A_LEARNED_BASELINE"
    ):
        fail(f"deterministic ceiling role changed: {study_root}")

    analyzer = runpy.run_path(str(ROOT / "scripts" / "analyze_balanced_public_challenge.py"))
    derive = analyzer.get("derive_reporting_metrics")
    if not callable(derive):
        fail("balanced metrics recomputation entry point is missing")
    gold = load_jsonl(dataset_root / "evaluation-gold.jsonl", "synthetic-policy gold")
    pairs = json.loads((dataset_root / "evaluation-pairs.json").read_text(encoding="utf-8"))
    if not isinstance(pairs, list):
        fail("synthetic-policy pair index is malformed")
    lanes = {
        str(row.get("lane_id")): row for row in aggregate.get("lanes", []) if isinstance(row, dict)
    }
    if len(lanes) != 2:
        fail(f"synthetic-policy lane count changed: {study_root}")
    for lane_id, lane in lanes.items():
        run_path = study_root / "results" / f"{lane_id}.jsonl"
        rows = load_jsonl(run_path, f"{lane_id} run")
        recomputed = derive(gold, pairs, rows)
        if recomputed != lane.get("metrics"):
            fail(f"paper aggregate differs from item records: {lane_id}")
        if lane.get("run_sha256") != sha256_file(run_path):
            fail(f"paper aggregate run binding changed: {lane_id}")
    return lanes


def legacy_configs() -> list[dict[str, Any]]:
    qwen = {
        "items": 300,
        "parseable_items": 272,
        "correct_items": 258,
        "pairs": 150,
        "covered_pairs": 123,
        "correct_pairs": 113,
        "balanced_action_recall": 0.599807213930348,
        "per_action": {
            "ALLOW": {"end_to_end_recall": 143 / 150},
            "HOLD": {"end_to_end_recall": 110 / 134},
            "DEMOTE": {"end_to_end_recall": 0.0},
            "ESCALATE": {"end_to_end_recall": 5 / 8},
        },
        "confusion_matrix": {
            "counts": {
                "ALLOW": {
                    "ALLOW": 143,
                    "HOLD": 0,
                    "DEMOTE": 0,
                    "ESCALATE": 0,
                    "NO_VALID_DECISION": 7,
                },
                "HOLD": {
                    "ALLOW": 4,
                    "HOLD": 110,
                    "DEMOTE": 0,
                    "ESCALATE": 2,
                    "NO_VALID_DECISION": 18,
                },
                "DEMOTE": {
                    "ALLOW": 8,
                    "HOLD": 0,
                    "DEMOTE": 0,
                    "ESCALATE": 0,
                    "NO_VALID_DECISION": 0,
                },
                "ESCALATE": {
                    "ALLOW": 0,
                    "HOLD": 0,
                    "DEMOTE": 0,
                    "ESCALATE": 5,
                    "NO_VALID_DECISION": 3,
                },
            }
        },
    }
    nb = {
        "items": 300,
        "parseable_items": 300,
        "correct_items": 184,
        "pairs": 150,
        "covered_pairs": 150,
        "correct_pairs": 34,
        "balanced_action_recall": 0.3283582089552239,
        "per_action": {
            "ALLOW": {"end_to_end_recall": 0.5},
            "HOLD": {"end_to_end_recall": 109 / 134},
            "DEMOTE": {"end_to_end_recall": 0.0},
            "ESCALATE": {"end_to_end_recall": 0.0},
        },
        "confusion_matrix": {
            "counts": {
                "ALLOW": {
                    "ALLOW": 75,
                    "HOLD": 75,
                    "DEMOTE": 0,
                    "ESCALATE": 0,
                    "NO_VALID_DECISION": 0,
                },
                "HOLD": {
                    "ALLOW": 25,
                    "HOLD": 109,
                    "DEMOTE": 0,
                    "ESCALATE": 0,
                    "NO_VALID_DECISION": 0,
                },
                "DEMOTE": {
                    "ALLOW": 8,
                    "HOLD": 0,
                    "DEMOTE": 0,
                    "ESCALATE": 0,
                    "NO_VALID_DECISION": 0,
                },
                "ESCALATE": {
                    "ALLOW": 8,
                    "HOLD": 0,
                    "DEMOTE": 0,
                    "ESCALATE": 0,
                    "NO_VALID_DECISION": 0,
                },
            }
        },
    }
    old_flash = {
        "items": 300,
        "parseable_items": 0,
        "correct_items": 0,
        "pairs": 150,
        "covered_pairs": 0,
        "correct_pairs": 0,
        "balanced_action_recall": 0.0,
        "per_action": {action: {"end_to_end_recall": 0.0} for action in ACTIONS},
        "confusion_matrix": {
            "counts": {
                "ALLOW": {
                    "ALLOW": 0,
                    "HOLD": 0,
                    "DEMOTE": 0,
                    "ESCALATE": 0,
                    "NO_VALID_DECISION": 150,
                },
                "HOLD": {
                    "ALLOW": 0,
                    "HOLD": 0,
                    "DEMOTE": 0,
                    "ESCALATE": 0,
                    "NO_VALID_DECISION": 134,
                },
                "DEMOTE": {
                    "ALLOW": 0,
                    "HOLD": 0,
                    "DEMOTE": 0,
                    "ESCALATE": 0,
                    "NO_VALID_DECISION": 8,
                },
                "ESCALATE": {
                    "ALLOW": 0,
                    "HOLD": 0,
                    "DEMOTE": 0,
                    "ESCALATE": 0,
                    "NO_VALID_DECISION": 8,
                },
            }
        },
    }
    return [
        {"label": "r6 Qwen", "metrics": qwen},
        {"label": "r6 text NB", "metrics": nb},
        {"label": "Old r6 Flash interface", "metrics": old_flash},
    ]


def challenge_configs() -> list[dict[str, Any]]:
    aggregate = load_object(CHALLENGE_RESULT, "balanced challenge aggregate")
    labels = {
        "opencode-go-qwen3.7-max": "Challenge Qwen",
        "opencode-go-deepseek-v4-flash-matched": "Challenge Flash",
    }
    lanes = {
        str(row.get("lane_id")): row for row in aggregate.get("lanes", []) if isinstance(row, dict)
    }
    if set(lanes) != set(labels):
        fail("balanced challenge paper lane set changed")
    return [{"label": labels[lane_id], "metrics": lanes[lane_id]["metrics"]} for lane_id in labels]


def synthetic_configs() -> list[dict[str, Any]]:
    slsa = recompute_synthetic_lanes(
        study_root=SLSA_ROOT,
        dataset_root=SLSA_ROOT / "dataset",
        aggregate_path=SLSA_RESULT,
        expected_design="PROSPECTIVELY_FROZEN_SECOND_POLICY_PORTABILITY_STUDY",
    )
    labels = {
        "opencode-go-qwen3.7-max-slsa-v2": "SLSA Qwen",
        "opencode-go-deepseek-v4-flash-slsa-v2": "SLSA Flash",
    }
    if set(slsa) != set(labels):
        fail("hosted SLSA paper lane set changed")
    result = [
        {"label": labels[lane_id], "metrics": lane["metrics"]} for lane_id, lane in slsa.items()
    ]
    slsa_aggregate = load_object(SLSA_RESULT, "SLSA aggregate")
    result.append(
        {
            "label": "SLSA structured RF",
            "metrics": slsa_aggregate["structured_random_forest_action_baseline"]["metrics"],
        }
    )
    return result


def local_configs() -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for dataset_key, prefix, source_root in (
        ("slsa", "SLSA", SLSA_ROOT / "dataset"),
        ("policy-switch", "Switch", POLICY_SWITCH_ROOT / "dataset"),
    ):
        study_root = LOCAL_REPLICATION_ROOT / dataset_key
        lanes = recompute_synthetic_lanes(
            study_root=study_root,
            dataset_root=source_root,
            aggregate_path=study_root / "results" / "aggregate.json",
            expected_design=(
                "LOCAL_MODEL_REPLICATION_REPLACEMENT_V2_OF_FROZEN_SLSA_POLICY_STUDY"
                if dataset_key == "slsa"
                else "LOCAL_MODEL_REPLICATION_REPLACEMENT_V2_OF_FROZEN_POLICY_SWITCH_STUDY"
            ),
        )
        families = {
            str(row.get("model_family")): row for row in lanes.values() if isinstance(row, dict)
        }
        if set(families) != {"Mistral", "Phi"}:
            fail(f"local replication family set changed: {dataset_key}")
        for family, label in (("Mistral", "Mistral local"), ("Phi", "Phi-4 local")):
            result.append({"label": f"{prefix} {label}", "metrics": families[family]["metrics"]})
        if dataset_key == "policy-switch":
            aggregate = load_object(
                study_root / "results" / "aggregate.json", "local policy-switch aggregate"
            )
            comparators = aggregate.get("structured_random_forest_comparators", {})
            for comparator_id, label in (
                ("policy_aware", "Switch policy-aware RF"),
                ("profile_blind", "Switch profile-blind RF"),
            ):
                result.append(
                    {
                        "label": label,
                        "metrics": comparators[comparator_id]["metrics"],
                    }
                )
    return result


def metric_configs() -> list[dict[str, Any]]:
    configs = [*legacy_configs(), *challenge_configs(), *synthetic_configs(), *local_configs()]
    labels = [str(row["label"]) for row in configs]
    if len(labels) != len(set(labels)):
        fail("paper configuration labels are not unique")
    return configs


def confusion_counts(metrics: dict[str, Any]) -> dict[str, dict[str, int]]:
    matrix = metrics.get("confusion_matrix", {})
    counts = matrix.get("counts") if isinstance(matrix, dict) else None
    if not isinstance(counts, dict) or set(counts) != set(ACTIONS):
        fail("paper configuration lacks a four-row confusion matrix")
    return counts


def validate_metric_rows(tex: str, configs: list[dict[str, Any]]) -> None:
    for label in ("tab:core-results", "tab:action-recall", "tab:confusion"):
        if rf"\label{{{label}}}" not in tex:
            fail(f"required paper table is missing: {label}")
    for config in configs:
        label = str(config["label"])
        metrics = config["metrics"]
        items = int(metrics["items"])
        pairs = int(metrics["pairs"])
        valid = int(metrics["parseable_items"])
        correct_items = int(metrics["correct_items"])
        complete = int(metrics["covered_pairs"])
        correct_pairs = int(metrics["correct_pairs"])
        conditional_item = "N/E" if valid == 0 else f"{correct_items}/{valid}"
        conditional_pair = "N/E" if complete == 0 else f"{correct_pairs}/{complete}"
        core = (
            f"{label} & {valid}/{items} & {correct_items}/{items} & {conditional_item} & "
            f"{complete}/{pairs} & {correct_pairs}/{pairs} & {conditional_pair}"
        )
        if core not in tex:
            fail(f"paper core-result row is missing or stale: {label}")
        per_action = metrics.get("per_action")
        if not isinstance(per_action, dict) or set(per_action) != set(ACTIONS):
            fail(f"paper action metrics are malformed: {label}")
        action = f"{label} & " + " & ".join(
            [
                *(paper_rate(per_action[name]["end_to_end_recall"]) for name in ACTIONS),
                paper_rate(metrics["balanced_action_recall"]),
            ]
        )
        if action not in tex:
            fail(f"paper action-recall row is missing or stale: {label}")
        counts = confusion_counts(metrics)
        confusion = f"{label} & " + " & ".join(
            "/".join(
                str(counts[gold].get(predicted, counts[gold].get("NO_DECISION", -1)))
                for predicted in (*ACTIONS, "NO_VALID_DECISION")
            )
            for gold in ACTIONS
        )
        if "-1" in confusion or confusion not in tex:
            fail(f"paper confusion row is missing or stale: {label}")


def validate_new_study_claims(tex: str) -> None:
    if "TBD" in tex or "TODO" in tex:
        fail("manuscript contains an unresolved result placeholder")
    for excluded_row in ("Switch Qwen &", "Switch Flash &"):
        if excluded_row in tex:
            fail(f"quota-confounded hosted policy row entered the paper: {excluded_row}")
    exclusion = load_object(
        POLICY_SWITCH_ROOT / "results" / "manuscript-exclusion-receipt.json",
        "hosted policy-switch exclusion receipt",
    )
    if (
        exclusion.get("status") != "HOSTED_POLICY_SWITCH_EXCLUDED_IN_FULL_SHARED_QUOTA_EXHAUSTION"
        or exclusion.get("decision", {}).get("hosted_model_rows_enter_manuscript") is not False
        or exclusion.get("decision", {}).get("successful_row_subset_selected") is not False
    ):
        fail("hosted policy-switch exclusion boundary changed")
    replacement_exclusion = load_object(
        HOSTED_POLICY_REPLACEMENT_RECEIPT,
        "hosted policy-switch replacement exclusion receipt",
    )
    replacement_classification = replacement_exclusion.get("classification", {})
    replacement_decision = replacement_exclusion.get("decision", {})
    if (
        replacement_exclusion.get("status")
        != "HOSTED_REPLACEMENT_EXCLUDED_IN_FULL_PERSISTENT_SHARED_RESOURCE_EXHAUSTION"
        or replacement_exclusion.get("self_digest")
        != self_digest(replacement_exclusion, "self_digest")
        or replacement_classification.get("eligible_for_model_efficacy_reporting") is not False
        or replacement_classification.get("explicit_resource_exhaustion_errors") != 240
        or replacement_classification.get("persistent_exhaustion_trigger_sequence") != 0
        or replacement_decision.get("all_240_terminal_outcomes_considered") is not True
        or replacement_decision.get("hosted_model_rows_enter_manuscript") is not False
        or replacement_decision.get("conditional_success_subset_selected") is not False
        or replacement_exclusion.get("free_form_error_text_included") is not False
    ):
        fail("hosted policy-switch replacement exclusion boundary changed")
    difference_coverage = load_object(
        POLICY_DIFFERENCE_COVERAGE, "policy-difference coverage receipt"
    )
    coverage = difference_coverage.get("coverage", {})
    source_bindings = difference_coverage.get("source_bindings", {})
    expected_bindings = {
        "evaluation_items_sha256": sha256_file(
            POLICY_SWITCH_ROOT / "dataset" / "evaluation-items.jsonl"
        ),
        "evaluation_gold_sha256": sha256_file(
            POLICY_SWITCH_ROOT / "dataset" / "evaluation-gold.jsonl"
        ),
        "evaluation_pairs_sha256": sha256_file(
            POLICY_SWITCH_ROOT / "dataset" / "evaluation-pairs.json"
        ),
        "dataset_manifest_sha256": sha256_file(POLICY_SWITCH_ROOT / "dataset" / "manifest.json"),
        "policy_contract_sha256": sha256_file(
            ROOT / "v2" / "policy-switch-v1" / "policy-contract.json"
        ),
    }
    if (
        difference_coverage.get("status") != "POLICY_DIFFERENCE_COVERAGE_COMPLETE"
        or difference_coverage.get("record_sha256")
        != self_digest(difference_coverage, "record_sha256")
        or source_bindings != expected_bindings
        or coverage.get("authored_profile_difference_factors_covered") != 12
        or coverage.get("authored_profile_difference_factors_total") != 12
        or coverage.get("contexts_per_factor") != 5
        or coverage.get("directed_nonself_action_transitions_covered") != 6
        or coverage.get("directed_nonself_action_transitions_possible_over_four_actions") != 12
        or set(coverage.get("blue_to_amber_transition_counts", {}).values()) != {10}
        or coverage.get("transition_scope") != "ADMISSION_CENTERED_STAR_NOT_COMPLETE_ACTION_GRAPH"
    ):
        fail("policy-difference coverage receipt changed")
    policy_aggregate = load_object(
        LOCAL_REPLICATION_ROOT / "policy-switch" / "results" / "aggregate.json",
        "local policy-switch aggregate",
    )
    comparators = policy_aggregate.get("structured_random_forest_comparators", {})
    aware = comparators.get("policy_aware", {}).get("metrics", {})
    blind = comparators.get("profile_blind", {}).get("metrics", {})
    if (
        aware.get("correct_items") != 120
        or aware.get("correct_pairs") != 60
        or blind.get("correct_items") != 60
        or blind.get("correct_pairs") != 0
    ):
        fail("registered policy-switch shortcut result changed")
    for aggregate_path in (
        LOCAL_REPLICATION_ROOT / "slsa" / "results" / "aggregate.json",
        LOCAL_REPLICATION_ROOT / "policy-switch" / "results" / "aggregate.json",
    ):
        aggregate = load_object(aggregate_path, "local replication aggregate")
        lanes = aggregate.get("lanes")
        if (
            aggregate.get("status") != "COMPLETE"
            or not isinstance(lanes, list)
            or len(lanes) != 2
            or {str(row.get("model_family")) for row in lanes} != {"Mistral", "Phi"}
        ):
            fail("local replication model-family boundary changed")
    required = (
        (r"intervention-blind certificate", "intervention-blind shortcut certificate"),
        (r"same action for both members", "policy-blind proof premise"),
        (r"0/60 pair accuracy", "profile-blind shortcut result"),
        (r"all 12 authored.*five contexts each", "policy-difference factor coverage"),
        (r"six admission-centered transitions.*ten pairs each", "policy transition balance"),
        (r"does not cover transitions between two non-.*actions", "transition-graph boundary"),
        (r"30.*\\allow.*ten.*other action", "per-profile action balance"),
        (r"Mistral Small 3\.2 24B", "pinned Mistral route"),
        (r"Phi-4", "pinned Phi route"),
        (r"four-bit", "local quantization boundary"),
        (r"SLSA.*in-toto.*do not endorse", "source-standard interpretation boundary"),
        (r"different service stack", "old and new Flash stack boundary"),
        (r"neither model improvement nor an ablation effect", "Flash causal boundary"),
        (r"invalid response contents are omitted", "invalid-content publication boundary"),
        (r"hosted policy-switch.*excluded in full", "hosted full-study exclusion"),
        (r"no successful hosted row", "no valid-subset selection"),
    )
    for pattern, description in required:
        require_regex(tex, pattern, description)


def validate_public_model_breadth(tex: str) -> bool:
    if not BREADTH_RESULT.exists():
        return False

    verifier_module = runpy.run_path(str(BREADTH_VERIFIER))
    verify = verifier_module.get("verify_public_evidence")
    if not callable(verify):
        fail("public model-breadth verifier entry point is missing")
    verification = verify(
        BREADTH_RESULT_ROOT,
        BREADTH_PLAN,
        BREADTH_PACKET,
        BREADTH_DATASET,
        api_key="",
    )
    if verification.get("status") != "PUBLIC_MODEL_BREADTH_EVIDENCE_PASS":
        fail("public model-breadth evidence replay failed")

    plan = load_object(BREADTH_PLAN, "public model-breadth plan")
    aggregate = load_object(BREADTH_RESULT, "public model-breadth aggregate")
    failure_addendum = load_object(BREADTH_FAILURE_ADDENDUM, "breadth failure addendum")
    failure_deriver = runpy.run_path(str(BREADTH_FAILURE_DERIVER))
    derive_failure_addendum = failure_deriver.get("derive")
    if not callable(derive_failure_addendum):
        fail("breadth failure-addendum derivation entry point is missing")
    _, expected_public_addendum = derive_failure_addendum(BREADTH_PRIVATE_JOURNAL)
    if failure_addendum != expected_public_addendum:
        fail("breadth failure addendum differs from the frozen private journal")
    lane_order = plan.get("execution", {}).get("base_lane_order")
    if not isinstance(lane_order, list) or len(lane_order) != 7:
        fail("public model-breadth plan does not retain seven lanes")
    lane_ids = {str(value) for value in lane_order}
    lanes = {
        str(lane.get("lane_id")): lane
        for lane in aggregate.get("lanes", [])
        if isinstance(lane, dict)
    }
    if set(lanes) != lane_ids:
        fail("public model-breadth aggregate lane set changed")
    if (
        aggregate.get("status") != "COMPLETE"
        or aggregate.get("design") != "PUBLIC_PRECOMMITTED_MODEL_BREADTH_SUPPLEMENT"
        or aggregate.get("service_comparison", {}).get("causal_model_ablation_claimed") is not False
        or aggregate.get("scope_limits")
        != {
            "breadth_dimension_added": "MODEL_FAMILY_ONLY",
            "hidden_generalization_claimed": False,
            "naturalistic_cases": 0,
            "ontology_count": 1,
            "policy_count": 1,
            "public_known_challenge": True,
        }
    ):
        fail("public model-breadth interpretation boundary changed")

    labels = {
        "opencode-go-qwen3.8-max-breadth": "Qwen3.8-Max",
        "opencode-go-deepseek-v4-pro-breadth": "DeepSeek-V4-Pro",
        "opencode-go-glm-5.3-breadth": "GLM-5.3",
        "opencode-go-kimi-k3-breadth": "Kimi-K3",
        "opencode-go-mimo-v2.5-pro-breadth": "MiMo-V2.5-Pro",
        "opencode-go-minimax-m3-breadth": "MiniMax-M3",
        "opencode-go-hy3-breadth": "Hunyuan-HY3",
    }
    if set(labels) != lane_ids:
        fail("public model-breadth paper label map changed")
    for lane_id in lane_order:
        lane = lanes[str(lane_id)]
        metrics = lane.get("metrics")
        if not isinstance(metrics, dict):
            fail(f"public model-breadth metrics are missing: {lane_id}")
        confusion = metrics.get("confusion_matrix", {})
        counts = confusion.get("counts")
        per_action = metrics.get("per_action")
        if (
            not isinstance(counts, dict)
            or set(counts) != set(ACTIONS)
            or any(
                not isinstance(counts.get(action), dict)
                or set(counts[action])
                != {"ALLOW", "HOLD", "DEMOTE", "ESCALATE", "NO_VALID_DECISION"}
                for action in ACTIONS
            )
            or not isinstance(per_action, dict)
            or set(per_action) != set(ACTIONS)
        ):
            fail(f"public model-breadth class reporting is incomplete: {lane_id}")
        conditional_items = (
            "N/E"
            if metrics["parseable_items"] == 0
            else f"{metrics['correct_items']}/{metrics['parseable_items']}"
        )
        conditional_pairs = (
            "N/E"
            if metrics["covered_pairs"] == 0
            else f"{metrics['correct_pairs']}/{metrics['covered_pairs']}"
        )
        core_row = (
            f"{labels[str(lane_id)]} & {metrics['parseable_items']}/180 & "
            f"{metrics['correct_items']}/180 & {conditional_items} & "
            f"{metrics['covered_pairs']}/90 & {metrics['correct_pairs']}/90 & "
            f"{conditional_pairs}"
        )
        if core_row not in tex:
            fail(f"public model-breadth result row is missing or changed: {lane_id}")
        action_row = (
            f"{labels[str(lane_id)]} & "
            + " & ".join(paper_rate(per_action[action]["end_to_end_recall"]) for action in ACTIONS)
            + f" & {paper_rate(metrics['balanced_action_recall'])} & "
            f"{paper_rate(metrics['macro_f1'])}"
        )
        if action_row not in tex:
            fail(f"public model-breadth action row is missing or changed: {lane_id}")
        confusion_row = f"{labels[str(lane_id)]} & " + " & ".join(
            "/".join(str(counts[gold][predicted]) for predicted in (*ACTIONS, "NO_VALID_DECISION"))
            for gold in ACTIONS
        )
        if confusion_row not in tex:
            fail(f"public model-breadth confusion row is missing or changed: {lane_id}")

    for label in (
        "tab:breadth-results",
        "tab:breadth-action-recall",
        "tab:breadth-confusion",
    ):
        if rf"\label{{{label}}}" not in tex:
            fail(f"required public model-breadth table missing: {label}")
    required = (
        (r"frozen service-route stress test", "frozen route stress test"),
        (r"seven.*service configurations", "seven route configurations"),
        (r"1\{?,?\}?260.*terminal", "breadth terminal-cell count"),
        (r"known public.*challenge", "known-public interpretation"),
        (r"final 547.*quota/rate-limit", "shared quota confound"),
        (
            r"547 quota/rate-limit, 76 authorization, five server, one timeout, and one connection",
            "transport failure categories",
        ),
        (r"complete route confusion matrices", "route class artifact"),
        (r"model identity.*serving implementation.*API adapter", "route causal boundary"),
    )
    for pattern, description in required:
        require_regex(tex, pattern, description)
    return True


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
        ("r6 text NB", "ALLOW"): (75, 75, 0, 0, 0),
        ("r6 text NB", "HOLD"): (25, 109, 0, 0, 0),
        ("r6 text NB", "DEMOTE"): (8, 0, 0, 0, 0),
        ("r6 text NB", "ESCALATE"): (8, 0, 0, 0, 0),
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

    for label in (
        "tab:core-results",
        "tab:factor-inventory",
        "tab:action-recall",
        "tab:confusion",
        "tab:factor-results",
    ):
        if rf"\label{{{label}}}" not in tex:
            fail(f"required result table missing: {label}")
    core_rows = (
        (
            r"r6 Qwen3\.7-Max\s*&\s*272/300\s*&\s*258/300\s*&\s*258/272"
            r"\s*&\s*123/150\s*&\s*113/150\s*&\s*113/123"
        ),
        (
            r"r6 public-dev text NB\s*&\s*300/300\s*&\s*184/300\s*&\s*184/300"
            r"\s*&\s*150/150\s*&\s*34/150\s*&\s*34/150"
        ),
        (
            r"Public challenge Qwen\s*&\s*148/180\s*&\s*132/180\s*&\s*132/148"
            r"\s*&\s*64/90\s*&\s*48/90\s*&\s*48/64"
        ),
        (
            r"Public challenge Flash\s*&\s*146/180\s*&\s*90/180\s*&\s*90/146"
            r"\s*&\s*61/90\s*&\s*13/90\s*&\s*13/61"
        ),
        (
            r"Old Flash service-interface failure\s*&\s*0/300\s*&\s*0/300\s*&\s*N/E"
            r"\s*&\s*0/150\s*&\s*0/150\s*&\s*N/E"
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
            r"r6 public-dev text NB\s*&\s*\.5000\s*&\s*\.8134\s*&\s*\.0000"
            r"\s*&\s*\.0000\s*&\s*\.3284\s*&\s*\.3124"
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
    factor_rows = (
        "r6 Qwen & 20 & .2857--1.0000 & .0000--1.0000 & 2 / 7",
        "Challenge Qwen & 15 & .5000--1.0000 & .0000--1.0000 & 3 / 2",
        "Challenge Flash & 15 & .0000--1.0000 & .0000--.8333 & 11 / 0",
    )
    for row in factor_rows:
        if row not in tex:
            fail(f"factor-result table row missing or changed: {row}")


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
        (r"created zero cases", "zero naturalistic cases"),
        (r"zero model calls", "zero naturalistic model calls"),
        (r"No human annotators", "no fabricated human annotation"),
        (r"Naturalistic validity therefore remains untested", "naturalistic limitation"),
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
    # The frozen v1 artifact remains bound and available to reviewers, but its execution history
    # is no longer required in the main narrative. The paper centers the r6 and balanced-challenge
    # evidence regimes.


def validate_structure_and_citations(tex: str, bib: str) -> tuple[int, int, int]:
    lower = tex.lower()
    for section in (
        "Introduction",
        "Related Work",
        "Task and Protocol",
        "Evaluation Design",
        "Results",
        "Discussion",
        "Limitations",
        "Reproducibility Statement",
        "AI Assistance Disclosure",
        "Conclusion",
    ):
        if rf"\section{{{section}}}" not in tex:
            fail(f"required manuscript section missing: {section}")
    if r"\label{fig:evidence-flow}" not in tex:
        fail("benchmark/evidence-flow figure is missing")
    for phrase in (
        "complete versioned policy contract",
        "exactly six fields",
        "first matching row fixes the action, proposed state, and ordered reason codes",
        "Every scheduled service, syntax, schema, and semantic failure",
        "intervention-blind certificate",
        "definitional policy ceiling",
    ):
        if phrase not in tex:
            fail(f"self-contained task description is missing: {phrase!r}")

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
    excluded_study_markers = (
        "1,260",
        "78/1,260",
        "quota/rate-limit",
        "Qwen3.8-Max",
        "DeepSeek-V4-Pro",
        "Kimi-K3",
        "MiniMax-M3",
        "tab:breadth-results",
        "tab:breadth-action-recall",
        "tab:breadth-confusion",
    )
    for marker in excluded_study_markers:
        if marker in tex:
            fail(f"excluded seven-route study leaked into manuscript: {marker}")
    for phrase in (
        "synthetic conformance-testing protocol",
        "author-defined executable specification",
        "service, syntax, schema, and semantic failure",
        "No human annotators or agreement statistic are claimed",
        "Naturalistic validity therefore remains untested",
        "between-route comparisons are descriptive",
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
        "omg2024dmn",
        "tretmans1996conformance",
        "geng2025jsonschemabench",
        "yan2025bfcl",
        "geifman2017selective",
        "geifman2019selectivenet",
        "zhou2025rulearena",
        "mu2024rules",
        "zhang2026inverseifeval",
        "cisneros2026policycompliance",
        "bao2026policyllm",
        "diao2025guidebench",
        "liu2026augmentedpolicy",
        "choi2026compass",
        "ma2024promptregression",
        "liu2026policyinternalization",
        "yang2026rulesual",
        "chen2025scienceagentbench",
        "siegel2025corebench",
        "huang2025popper",
        "slsa2026v12",
        "intoto2026attestation",
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
    if len(abstract_words) > 220:
        fail(f"abstract exceeds 220 words: {len(abstract_words)}")

    for pattern in (
        r"\bit is worth noting\b",
        r"\bserves as\b",
        r"\bin conclusion\b",
        r"\bto sum up\b",
        r"\bdelve\b",
        r"\btapestry\b",
        r"\b(?:research|technical|ai) landscape\b",
        r"\bpost-v1 public formatting control\b",
        r"\badaptive hidden service study\b",
    ):
        if re.search(pattern, tex, flags=re.IGNORECASE):
            fail(f"manuscript retains formulaic or reader-irrelevant prose: {pattern}")

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
    validate_manuscript_style_audit()
    validate_no_stale_file_counts()
    validate_submission_builder(tex)
    validate_r6_evidence(tex)
    validate_balanced_challenge(tex)
    configs = metric_configs()
    validate_metric_rows(tex, configs)
    validate_new_study_claims(tex)
    validate_naturalistic_decision(tex)
    validate_v1_diagnostic(tex)
    citation_count, label_count, abstract_words = validate_structure_and_citations(tex, bib)
    print(
        "paper-lint: PASS "
        f"({citation_count} citation keys, {label_count} labels, "
        f"{abstract_words} abstract words; {len(configs)} configurations bound; "
        "seven-route study excluded)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
