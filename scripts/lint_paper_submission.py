#!/usr/bin/env python3
"""Fail-closed evidence and scope checks for the submission manuscript."""

from __future__ import annotations

import hashlib
import json
import re
import runpy
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TEX = ROOT / "technical-report" / "main.tex"
BIB = ROOT / "technical-report" / "references.bib"
README = ROOT / "README.md"
CITATION = ROOT / "CITATION.cff"
SUBMISSION_METADATA = ROOT / "docs" / "SUBMISSION_METADATA.md"
SUBMISSION_BUILDER = ROOT / "scripts" / "build_submission_tex.py"
STYLE_AUDIT = ROOT / "docs" / "MANUSCRIPT_STYLE_AUDIT_2026-08-23.json"

UPSTREAM = ROOT / "v2" / "upstream-policy-revisions-v1"
TRIVY = ROOT / "v2" / "trivy-policy-revision-v1"
SIGSTORE = ROOT / "v2" / "sigstore-policy-verifier-revision-v1"
AGENT_GOVERNANCE = ROOT / "v2" / "agent-governance-policy-interface-revision-v1"
EXTERNAL_AUDIT = ROOT / "v2" / "external-evidence-audit-v1"
REPETITION = ROOT / "v2" / "upstream-policy-route-repetition-v1"
DUAL_ENDPOINT = ROOT / "v2" / "dual-endpoint-audit-v1" / "aggregate.json"
R6_ADDENDUM = ROOT / "v2" / "confirmatory" / "r6-execution" / "reviewer-reporting-addendum.json"
CHALLENGE = ROOT / "v2" / "balanced-public-challenge" / "results" / "aggregate.json"
POLICY_SWITCH_COVERAGE = ROOT / "v2" / "policy-switch-v1" / "policy-difference-coverage.json"
GRAPH_COVERAGE = ROOT / "v2" / "policy-transition-graph-v1" / "frozen" / "transition-coverage.json"
GRAPH_MINIMUM = ROOT / "v2" / "policy-transition-graph-v1" / "minimal-release-suite.json"
GRAPH_ROUTES = (
    ROOT
    / "v2"
    / "local-model-replication-v1"
    / "transition-graph-v1"
    / "frozen"
    / "policy-transition-graph"
    / "results"
    / "aggregate.json"
)
NATURALISTIC = ROOT / "v2" / "naturalistic-review-decision.json"
FACTOR_COMPLETE = ROOT / "v2" / "factor-complete-route-breadth-v2" / "results"
EXTERNAL_AGENT_POLICY = ROOT / "v2" / "external-agent-policy-revision-v2" / "results"
NONALLOW_CONTROLS = ROOT / "v2" / "nonallow-policy-controls-v1" / "results"
OUTPUT_CONTRACT = ROOT / "v2" / "output-contract-ablation-v1" / "results"
OUTPUT_TRANSPORT = (
    ROOT / "v2" / "output-contract-ablation-v1" / "diagnostics" / "transport-diagnostics.json"
)

CANONICAL_TITLE = "ClaimPromoteBench: Paired Regression Tests for Versioned Agent Policies"
TEX_TITLE = r"\cpb: Paired Regression Tests for Versioned Agent Policies"


def fail(message: str) -> None:
    raise SystemExit(f"paper-lint: {message}")


def load_object(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        fail(f"missing {label}: {path.relative_to(ROOT)}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        fail(f"{label} must contain a JSON object")
    return value


def load_jsonl(path: Path, label: str) -> list[dict[str, Any]]:
    rows = [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    if any(not isinstance(row, dict) for row in rows):
        fail(f"{label} must contain JSON objects")
    return rows


def sha256_hex(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def expect(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        fail(f"{label}: expected {expected!r}, found {actual!r}")


def nested(value: dict[str, Any], path: str) -> Any:
    current: Any = value
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            fail(f"missing evidence field {path}")
        current = current[part]
    return current


def normalize_space(value: str) -> str:
    return " ".join(value.split())


def require_text(text: str, needle: str, label: str) -> None:
    if normalize_space(needle) not in normalize_space(text):
        fail(f"manuscript missing {label}")


def manuscript_abstract_plain(tex: str) -> str:
    match = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", tex, re.DOTALL)
    if match is None:
        fail("abstract is missing")
    value = match.group(1)
    macros = {
        "cpb": "ClaimPromoteBench",
        "allow": "ALLOW",
        "hold": "HOLD",
        "demote": "DEMOTE",
        "escalate": "ESCALATE",
    }
    value = re.sub(
        r"\\(cpb|allow|hold|demote|escalate)(?:\{\})?",
        lambda match: macros[match.group(1)],
        value,
    )
    value = value.replace(r"\%", "%").replace(r"\_", "_")
    value = re.sub(r"\\texttt\{([^{}]*)\}", r"\1", value)
    return normalize_space(value)


def validate_structure_and_metadata(tex: str, bib: str) -> None:
    expected_title = rf"\title{{{TEX_TITLE}}}"
    if expected_title not in tex:
        fail("canonical manuscript title changed")

    sections = [
        "Introduction",
        "Related Work",
        "Method",
        "Evidence and Evaluation Design",
        "Results",
        "Discussion",
        "Limitations",
        "Conclusion",
        "Reproducibility Statement",
        "AI Assistance Disclosure",
    ]
    positions = [tex.find(rf"\section{{{name}}}") for name in sections]
    if any(position < 0 for position in positions) or positions != sorted(positions):
        fail("required main-text sections are missing or out of order")
    bibliography = tex.find(r"\bibliographystyle{plain}")
    appendix = tex.find(r"\appendix")
    if bibliography < positions[-1] or appendix < bibliography:
        fail("bibliography or appendix boundary changed")

    abstract = manuscript_abstract_plain(tex)
    abstract_words = re.findall(r"[A-Za-z0-9][A-Za-z0-9'/-]*", abstract)
    if not 180 <= len(abstract_words) <= 300:
        fail(f"abstract length outside 180--300 words: {len(abstract_words)}")

    cite_groups = re.findall(r"\\cite\{([^}]+)\}", tex)
    cited = {key.strip() for group in cite_groups for key in group.split(",")}
    bib_keys = re.findall(r"@\w+\{([^,]+),", bib)
    if len(bib_keys) != len(set(bib_keys)):
        fail("duplicate BibTeX keys")
    missing = sorted(cited - set(bib_keys))
    if missing:
        fail(f"missing BibTeX entries: {missing}")

    for key in (
        "mullick2023evolving",
        "ji2026argus",
        "ribeiro2020checklist",
        "gardner2020contrastsets",
        "chan1998metamorphic",
        "tretmans1996conformance",
        "chow1978fsm",
        "tzorefbrill2017semantic",
        "martin2007policytests",
        "ma2024promptregression",
        "microsoft2026agentgovernance",
        "agentgateway2026bedrock",
        "zhou2025rulearena",
        "ahmed2025speceval",
        "diao2025guidebench",
        "rehan2026tdad",
        "scholak2021picard",
        "geifman2017selective",
        "chen2025scienceagentbench",
    ):
        if key not in cited:
            fail(f"required literature family is absent: {key}")

    readme = README.read_text(encoding="utf-8")
    citation = CITATION.read_text(encoding="utf-8")
    metadata = SUBMISSION_METADATA.read_text(encoding="utf-8")
    expect(readme.splitlines()[0], f"# {CANONICAL_TITLE}", "README title")
    if f'title: "{CANONICAL_TITLE}"' not in citation:
        fail("CITATION.cff title differs from the manuscript")
    if metadata.count(CANONICAL_TITLE) < 2:
        fail("ICLR and arXiv metadata titles are not bound")
    abstract_match = re.search(
        r"## ICLR 2027 abstract\s+```text\s+(.*?)\s+```", metadata, re.DOTALL
    )
    if abstract_match is None:
        fail("copy-ready ICLR abstract is missing")
    expect(
        normalize_space(abstract_match.group(1)),
        abstract,
        "submission metadata abstract",
    )

    for path in (README, SUBMISSION_METADATA, TEX):
        content = path.read_text(encoding="utf-8")
        if re.search(r"\b(?:179|170|619)\s+(?:files?|檔案)", content, re.IGNORECASE):
            fail(f"stale fixed file count in {path.relative_to(ROOT)}")


def validate_builder(tex: str) -> None:
    namespace = runpy.run_path(str(SUBMISSION_BUILDER))
    expect(namespace.get("TITLE"), TEX_TITLE, "arXiv wrapper title")
    body = namespace["canonical_body"]()
    appendix = namespace["canonical_appendix"]()
    if (
        body
        != tex[tex.index(r"\begin{abstract}") : tex.rindex(r"\bibliographystyle")].rstrip() + "\n\n"
    ):
        fail("submission builder changes the canonical scientific body")
    if not appendix.startswith(r"\appendix"):
        fail("submission builder dropped the appendix")
    anonymous = namespace["anonymous_iclr_body"](body)
    for marker in ("wangzhikai", "f0909172434", "Chih-Kai Wang", "National Taipei"):
        if marker.lower() in anonymous.lower():
            fail(f"anonymous manuscript retains identity marker: {marker}")


def validate_upstream_sources() -> None:
    coverage = load_object(UPSTREAM / "coverage.json", "Gatekeeper coverage")
    minimum = load_object(UPSTREAM / "minimum-suite.json", "Gatekeeper minimum suite")
    receipt = load_object(UPSTREAM / "source-validation-receipt.json", "Gatekeeper receipt")
    expect(coverage.get("candidate_pairs"), 12, "Gatekeeper pairs")
    expect(len(coverage.get("changed_rules", [])), 2, "Gatekeeper changed rules")
    expect(
        coverage.get("reachable_action_edges"), ["ALLOW->HOLD", "HOLD->ALLOW"], "Gatekeeper edges"
    )
    expect(
        coverage.get("contexts_per_transition"),
        {"ALLOW->HOLD": 6, "HOLD->ALLOW": 6},
        "Gatekeeper edge support",
    )
    expect(
        nested(minimum, "coverage.changed_rules"),
        {"covered": 2, "total": 2},
        "Gatekeeper rule minimum",
    )
    expect(
        nested(minimum, "coverage.action_edges"),
        {"covered": 2, "total": 2},
        "Gatekeeper edge minimum",
    )
    expect(minimum.get("witness_pairs"), 2, "Gatekeeper minimum size")
    expect(receipt.get("source_bytes_match_registry"), True, "Gatekeeper source bytes")
    expect(receipt.get("model_calls"), 0, "Gatekeeper pre-route model calls")
    expect(
        len(receipt.get("finite_grammar_oracle_evaluations", [])), 24, "Gatekeeper OPA evaluations"
    )

    trivy = load_object(TRIVY / "results.json", "Trivy results")
    trivy_min = load_object(TRIVY / "minimum-suite.json", "Trivy minimum suite")
    expect(len(trivy.get("results", [])), 4, "Trivy cases")
    expect(
        trivy.get("transition_support"), {"ALLOW->HOLD": 2, "HOLD->ALLOW": 2}, "Trivy transitions"
    )
    expect(trivy_min.get("witness_cases"), 2, "Trivy minimum")

    sigstore = load_object(SIGSTORE / "results.json", "Cosign verifier results")
    sigstore_min = load_object(SIGSTORE / "minimum-suite.json", "Cosign minimum suite")
    expect(len(sigstore.get("results", [])), 6, "Cosign cases")
    expect(len(sigstore.get("fault_mode_support", {})), 4, "Cosign fault modes")
    expect(sigstore_min.get("witness_cases"), 4, "Cosign minimum")

    agent_governance = load_object(
        AGENT_GOVERNANCE / "results.json", "Agent Governance Toolkit results"
    )
    agent_governance_minimum = load_object(
        AGENT_GOVERNANCE / "minimum-suite.json", "Agent Governance Toolkit minimum suite"
    )
    agent_governance_receipt = load_object(
        AGENT_GOVERNANCE / "source-validation-receipt.json",
        "Agent Governance Toolkit source receipt",
    )
    expect(
        agent_governance.get("old_upstream_tests"),
        {
            "failed": [
                "test_empty_text_with_zero_width_pattern_denies",
                "test_match_start_of_empty_match_is_zero",
                "test_zero_length_leftmost_match_still_denies",
                "test_zero_width_match_reports_placeholder_offset",
            ],
            "passed": 11,
            "total": 15,
        },
        "Agent Governance Toolkit old tests",
    )
    expect(
        agent_governance.get("new_upstream_tests"),
        {"failed": [], "passed": 15, "total": 15},
        "Agent Governance Toolkit fixed tests",
    )
    expect(
        agent_governance.get("transition_support"),
        {"ALLOW->HOLD": 2},
        "Agent Governance Toolkit transitions",
    )
    expect(agent_governance_minimum.get("witness_cases"), 1, "Agent Governance minimum")
    expect(agent_governance_receipt.get("model_calls"), 0, "Agent Governance model calls")
    expect(
        agent_governance_receipt.get("action_mapping_is_author_mapping"),
        True,
        "Agent Governance action mapping",
    )

    audit = load_object(EXTERNAL_AUDIT / "audit-receipt.json", "external evidence audit")
    registry = load_object(EXTERNAL_AUDIT / "candidate-registry.json", "external registry")
    agentgateway = load_object(
        EXTERNAL_AUDIT / "source-checks" / "agentgateway-bedrock-guardrail.json",
        "agentgateway source check",
    )
    expect(audit.get("formal_repository_seeds"), 465, "external repository seeds")
    expect(audit.get("deep_screened_candidates"), 11, "external source reviews")
    expect(audit.get("model_calls"), 0, "external audit model calls")
    expect(
        audit.get("status"),
        "GO_FOR_EXTERNAL_BOUNDARY_FAULT_EVIDENCE__NO_GO_FOR_NATURALISTIC_MODEL_POLICY_INTERPRETATION",
        "external audit decision",
    )
    expect(
        registry.get("outcome_counts"),
        {
            "ARCHITECTURE_ONLY": 6,
            "EXCLUDED": 3,
            "POLICY_REVISION_ONLY": 0,
            "QUALIFYING_ROUTE_REVISION": 2,
        },
        "external audit outcomes",
    )
    expect(agentgateway.get("model_calls"), 0, "agentgateway model calls")
    expect(agentgateway.get("aws_calls"), 0, "agentgateway AWS calls")
    expect(
        agentgateway.get("status"),
        "EXACT_CHANGE_COMMIT_OFFLINE_REGRESSION_TESTS_PASS",
        "agentgateway source status",
    )
    expect(agentgateway.get("test_run", {}).get("passed"), 33, "agentgateway selected tests")
    expect(agentgateway.get("test_run", {}).get("failed"), 0, "agentgateway failed tests")


def route_by_model(aggregate: dict[str, Any], model: str) -> dict[str, Any]:
    matches = [lane for lane in aggregate.get("lanes", []) if lane.get("model_requested") == model]
    if len(matches) != 1:
        fail(f"expected one repeated route for {model}, found {len(matches)}")
    return matches[0]


def validate_repeated_routes() -> None:
    aggregate = load_object(REPETITION / "results" / "aggregate.json", "repeated-route aggregate")
    diagnostic = load_object(
        REPETITION / "diagnostics" / "failure-modes.json", "repeated-route failure diagnostic"
    )
    expect(aggregate.get("scheduled_cells"), 144, "repeated scheduled cells")
    expect(aggregate.get("items_per_route_repetition"), 24, "items per repetition")
    expect(aggregate.get("pairs_per_route_repetition"), 12, "pairs per repetition")
    expect(
        [len(lane.get("by_repetition", [])) for lane in aggregate.get("lanes", [])],
        [3, 3],
        "repetition count",
    )
    expect(
        aggregate.get("raw_or_invalid_response_content_in_aggregate"), False, "aggregate privacy"
    )

    qwen = route_by_model(aggregate, "qwen3.7-max")
    flash = route_by_model(aggregate, "deepseek-v4-flash")
    for lane, model, items, full_items, pairs, full_pairs, repeats in (
        (qwen, "Qwen", 10, 10, 0, 0, [(3, 3, 0, 0), (2, 2, 0, 0), (5, 5, 0, 0)]),
        (flash, "Flash", 53, 52, 21, 20, [(15, 15, 6, 6), (19, 18, 7, 6), (19, 19, 8, 8)]),
    ):
        total = lane["descriptive_three_repeat_total"]
        expect(nested(total, "strict_action.accuracy.numerator"), items, f"{model} strict items")
        expect(nested(total, "strict_action.accuracy.denominator"), 72, f"{model} item denominator")
        expect(
            nested(total, "contract_action.accuracy.numerator"), items, f"{model} contract items"
        )
        expect(
            nested(total, "full_decision_exact.accuracy.numerator"),
            full_items,
            f"{model} full items",
        )
        expect(
            nested(total, "pair_accuracy.strict_action.numerator"), pairs, f"{model} strict pairs"
        )
        expect(
            nested(total, "pair_accuracy.strict_action.denominator"),
            36,
            f"{model} pair denominator",
        )
        expect(
            nested(total, "pair_accuracy.full_decision_exact.numerator"),
            full_pairs,
            f"{model} full pairs",
        )
        observed = []
        for repetition in lane["by_repetition"]:
            observed.append(
                (
                    nested(repetition, "strict_action.accuracy.numerator"),
                    nested(repetition, "full_decision_exact.accuracy.numerator"),
                    nested(repetition, "pair_accuracy.strict_action.numerator"),
                    nested(repetition, "pair_accuracy.full_decision_exact.numerator"),
                )
            )
        expect(observed, repeats, f"{model} repetition rows")

    expect(diagnostic.get("gold_loaded"), False, "failure diagnostic gold boundary")
    expect(diagnostic.get("raw_response_text_retained"), False, "failure diagnostic raw text")
    expect(diagnostic.get("hidden_reasoning_retained"), False, "failure diagnostic reasoning")
    expect(
        diagnostic.get("provider_response_identifiers_retained"), False, "failure diagnostic IDs"
    )
    expect(diagnostic.get("response_repair_or_rescoring_performed"), False, "failure repair")
    failure_by_model = {
        lane["model_requested"]: lane["failure_mode_counts"] for lane in diagnostic["lanes"]
    }
    expect(
        failure_by_model["qwen3.7-max"],
        {"CONTRACT_VALID": 10, "MARKDOWN_CODE_FENCE": 62},
        "Qwen failure modes",
    )
    expect(
        failure_by_model["deepseek-v4-flash"],
        {
            "CONTRACT_VALID": 53,
            "LENGTH_TERMINATED_NON_JSON": 1,
            "MARKDOWN_CODE_FENCE": 3,
            "NON_JSON_PREFIX_OR_ENVELOPE": 3,
            "READ_TIMEOUT": 12,
        },
        "Flash failure modes",
    )


def challenge_lane(aggregate: dict[str, Any], lane_id: str) -> dict[str, Any]:
    matches = [lane for lane in aggregate.get("lanes", []) if lane.get("lane_id") == lane_id]
    if len(matches) != 1:
        fail(f"expected one challenge lane {lane_id}")
    return matches[0]


def validate_auxiliary_results() -> None:
    dual = load_object(DUAL_ENDPOINT, "dual-endpoint audit")
    routes = dual.get("routes", [])
    expect(len(routes), 10, "dual-endpoint route count")
    expect(
        sum(route["metrics"]["scheduled_items"] for route in routes), 1320, "dual scheduled items"
    )
    overlap_expectations = {
        "raw_strict_extractable_outside_full_contract": 69,
        "raw_strict_correct_items_outside_full_contract": 49,
        "raw_strict_correct_pairs_outside_full_contract": 40,
        "full_contract_extractable_outside_raw_strict": 452,
        "full_contract_correct_items_outside_raw_strict": 329,
        "full_contract_correct_pairs_outside_raw_strict": 78,
    }
    for field, expected in overlap_expectations.items():
        expect(
            sum(route["metrics"]["endpoint_overlap"][field] for route in routes),
            expected,
            f"dual endpoint overlap {field}",
        )
    by_id = {route["route_stack_id"]: route for route in routes}
    for lane_id, raw_items, contract_items, raw_pairs, contract_pairs in (
        ("challenge-deepseek-flash-host-schema", 105, 90, 19, 13),
        ("challenge-qwen-host-prompt", 128, 132, 46, 48),
        ("slsa-deepseek-flash-host-schema", 110, 108, 51, 49),
        ("slsa-qwen-host-prompt", 120, 88, 60, 28),
    ):
        metrics = by_id[lane_id]["metrics"]
        expect(
            nested(metrics, "raw_strict_action.correct_items"),
            raw_items,
            f"{lane_id} raw-strict items",
        )
        expect(
            nested(metrics, "full_contract.action_correct_items"),
            contract_items,
            f"{lane_id} contract items",
        )
        expect(
            nested(metrics, "raw_strict_action.correct_pairs"),
            raw_pairs,
            f"{lane_id} raw-strict pairs",
        )
        expect(
            nested(metrics, "full_contract.action_correct_pairs"),
            contract_pairs,
            f"{lane_id} contract pairs",
        )
        expect(
            nested(metrics, "registered_parser_action.correct_items"),
            contract_items,
            f"{lane_id} registered-parser items",
        )
        expect(
            nested(metrics, "registered_parser_action.correct_pairs"),
            contract_pairs,
            f"{lane_id} registered-parser pairs",
        )

    expect(
        nested(
            by_id["challenge-qwen-host-prompt"],
            "metrics.registered_parser_provenance_counts",
        ),
        {
            "NO_REGISTERED_ACTION": 32,
            "REGISTERED_DIRECT_PARSE": 142,
            "REGISTERED_SINGLE_OBJECT_EXTRACTION": 6,
        },
        "challenge Qwen parser provenance",
    )

    r6 = load_object(R6_ADDENDUM, "r6 addendum")["qwen_service_configuration"]
    for field, expected in (
        ("valid_decisions", 272),
        ("correct_items", 258),
        ("correct_pairs", 113),
        ("complete_pairs", 123),
    ):
        expect(r6.get(field), expected, f"r6 {field}")

    challenge = load_object(CHALLENGE, "balanced challenge")
    qwen = challenge_lane(challenge, "opencode-go-qwen3.7-max")
    flash = challenge_lane(challenge, "opencode-go-deepseek-v4-flash-matched")
    for lane, label, valid, items, pairs, complete in (
        (qwen, "challenge Qwen", 148, 132, 48, 64),
        (flash, "challenge Flash", 146, 90, 13, 61),
    ):
        metrics = lane["metrics"]
        expect(metrics.get("parseable_items"), valid, f"{label} valid")
        expect(metrics.get("correct_items"), items, f"{label} items")
        expect(metrics.get("correct_pairs"), pairs, f"{label} pairs")
        expect(metrics.get("covered_pairs"), complete, f"{label} complete pairs")


def validate_authored_graph() -> None:
    switch = load_object(POLICY_SWITCH_COVERAGE, "authored rule coverage")
    graph = load_object(GRAPH_COVERAGE, "authored graph coverage")
    minimum = load_object(GRAPH_MINIMUM, "authored minimum suite")
    expect(
        nested(switch, "coverage.authored_profile_difference_factors_covered"),
        12,
        "rule-suite rules",
    )
    expect(
        nested(switch, "coverage.directed_nonself_action_transitions_covered"),
        6,
        "rule-suite edges",
    )
    expect(graph.get("authored_profile_difference_rules_covered"), 12, "graph rules")
    expect(graph.get("directed_action_transitions_covered"), 10, "graph edges")
    expect(nested(minimum, "coverage.changed_rules"), {"covered": 12, "total": 12}, "minimum rules")
    expect(
        nested(minimum, "coverage.reachable_edges"), {"covered": 10, "total": 10}, "minimum edges"
    )
    expect(nested(minimum, "execution_budget.minimum_smoke_pairs"), 10, "minimum pairs")
    expect(nested(minimum, "execution_budget.minimum_smoke_items"), 20, "minimum items")

    routes = load_object(GRAPH_ROUTES, "authored graph routes")
    pair_counts = {lane["lane_id"]: lane["metrics"]["correct_pairs"] for lane in routes["lanes"]}
    expect(
        pair_counts["local-mlx-mistral-small-3.2-24b-policy-transition-graph-v2"],
        10,
        "Mistral graph pairs",
    )
    expect(pair_counts["local-mlx-phi-4-policy-transition-graph-v2"], 2, "Phi graph pairs")


def validate_naturalistic() -> None:
    decision = load_object(NATURALISTIC, "naturalistic-candidate decision")
    expect(nested(decision, "candidate_pool.candidate_count"), 12, "naturalistic candidates")
    expect(nested(decision, "decision.cases_created"), 0, "naturalistic retained cases")
    expect(nested(decision, "decision.model_calls"), 0, "naturalistic model calls")
    expect(nested(decision, "decision.human_annotators"), 0, "naturalistic annotators")
    expect(nested(decision, "decision.agreement_statistic"), None, "naturalistic agreement")
    expect(
        nested(decision, "decision.selection_frozen_before_model_calls"),
        True,
        "naturalistic freeze boundary",
    )


def validate_current_route_studies() -> None:
    factor = load_object(FACTOR_COMPLETE / "aggregate.json", "factor-complete aggregate")
    factor_execution = load_object(
        FACTOR_COMPLETE / "execution-receipt.json", "factor-complete execution receipt"
    )
    factor_privacy = load_object(
        FACTOR_COMPLETE / "privacy-receipt.json", "factor-complete privacy receipt"
    )
    expect(factor.get("status"), "COMPLETE", "factor-complete status")
    expect(nested(factor, "coverage.factors"), 15, "factor-complete factors")
    expect(nested(factor, "execution.scheduled_model_item_cells"), 630, "factor calls")
    expect(nested(factor, "execution.client_retries"), 0, "factor retries")
    expect(
        factor_execution.get("status"),
        "COMPLETE_ALL_FROZEN_CELLS_TERMINAL",
        "factor execution status",
    )
    expect(factor_execution.get("durable_terminal_records"), 630, "factor terminal records")
    expect(factor_privacy.get("credentials_retained"), False, "factor credential privacy")

    first_rep_expected = {
        "glm-5.3": (9, 9, 1),
        "gpt-5.6-luna": (29, 26, 11),
        "hy3": (3, 3, 0),
        "kimi-k2.7-code": (16, 15, 4),
        "mimo-v2.5-pro": (16, 11, 1),
        "minimax-m2.7": (9, 7, 0),
        "qwen3.7-plus": (27, 25, 10),
    }
    observed: dict[str, tuple[int, int, int]] = {}
    pooled_status: Counter[str] = Counter()
    for route in factor.get("new_configurations", []):
        rep = next(row for row in route["per_replication"] if row["replication"] == 1)["metrics"]
        observed[str(route["model_requested"])] = (
            int(rep["parseable_items"]),
            int(rep["correct_items"]),
            int(rep["correct_pairs"]),
        )
        for status, count in route["pooled_three_replications"]["parse_status_counts"].items():
            pooled_status[str(status)] += int(count)
    expect(observed, first_rep_expected, "factor-complete first replication")
    expect(
        dict(pooled_status),
        {
            "JSON_SYNTAX_ERROR": 194,
            "OK": 319,
            "SCHEMA_ERROR": 87,
            "SEMANTIC_ERROR": 8,
            "TRANSPORT_ERROR": 22,
        },
        "factor-complete terminal taxonomy",
    )
    factor_rows = [
        row
        for path in sorted((FACTOR_COMPLETE / "runs").glob("*.jsonl"))
        for row in load_jsonl(path, f"factor-complete run {path.name}")
    ]
    length_limited = sum(
        row.get("parse_status") in {"JSON_SYNTAX_ERROR", "SCHEMA_ERROR"}
        and row.get("finish_reason") in {"length", "max_tokens"}
        for row in factor_rows
    )
    expect(length_limited, 280, "factor-complete output-limit failures")

    external = load_object(EXTERNAL_AGENT_POLICY / "aggregate.json", "external-policy aggregate")
    external_execution = load_object(
        EXTERNAL_AGENT_POLICY / "execution-receipt.json", "external-policy execution receipt"
    )
    external_privacy = load_object(
        EXTERNAL_AGENT_POLICY / "privacy-receipt.json", "external-policy privacy receipt"
    )
    expect(external.get("status"), "COMPLETE", "external-policy status")
    expect(nested(external, "coverage.external_policy_sources"), 2, "external-policy sources")
    expect(nested(external, "coverage.changed_pairs_per_replication"), 6, "changed pairs")
    expect(nested(external, "coverage.stable_control_pairs_per_replication"), 4, "stable pairs")
    expect(nested(external, "execution.scheduled_model_item_cells"), 480, "external calls")
    expect(nested(external, "execution.client_retries"), 0, "external retries")
    expect(
        external_execution.get("status"),
        "COMPLETE_ALL_FROZEN_CELLS_TERMINAL",
        "external execution status",
    )
    expect(external_execution.get("durable_terminal_records"), 480, "external terminal records")
    expect(
        external_privacy.get("status"),
        "EXTERNAL_AGENT_POLICY_PUBLIC_PRIVACY_PASS",
        "external privacy status",
    )

    totals: Counter[str] = Counter()
    external_status: Counter[str] = Counter()
    for route in external.get("configurations", []):
        rep = next(row for row in route["per_replication"] if row["replication"] == 1)["metrics"]
        for field in ("parseable_items", "correct_items", "correct_pairs", "covered_pairs"):
            totals[field] += int(rep[field])
        totals["changed_correct"] += int(rep["changed_pairs"]["correct_action_pairs"])
        totals["changed_complete"] += int(rep["changed_pairs"]["covered_pairs"])
        totals["changed_same"] += int(rep["changed_pairs"]["same_action_pairs"])
        totals["stable_correct"] += int(rep["stable_control_pairs"]["correct_action_pairs"])
        totals["stable_complete"] += int(rep["stable_control_pairs"]["covered_pairs"])
        for status, count in route["failure_causes"]["parse_status_counts"].items():
            external_status[str(status)] += int(count)
    expect(
        dict(totals),
        {
            "parseable_items": 132,
            "correct_items": 128,
            "correct_pairs": 52,
            "covered_pairs": 55,
            "changed_correct": 23,
            "changed_complete": 26,
            "changed_same": 3,
            "stable_correct": 29,
            "stable_complete": 29,
        },
        "external-policy first replication",
    )
    expect(
        dict(external_status),
        {"JSON_SYNTAX_ERROR": 9, "OK": 399, "SEMANTIC_ERROR": 46, "TRANSPORT_ERROR": 26},
        "external-policy terminal taxonomy",
    )

    nonallow = load_object(NONALLOW_CONTROLS / "aggregate.json", "non-ALLOW aggregate")
    nonallow_execution = load_object(
        NONALLOW_CONTROLS / "execution-receipt.json", "non-ALLOW execution receipt"
    )
    nonallow_privacy = load_object(
        NONALLOW_CONTROLS / "privacy-receipt.json", "non-ALLOW privacy receipt"
    )
    expect(nonallow.get("status"), "COMPLETE", "non-ALLOW status")
    expect(nested(nonallow, "execution.scheduled_cells"), 240, "non-ALLOW calls")
    expect(nested(nonallow, "execution.client_retries"), 0, "non-ALLOW retries")
    expect(
        nonallow_execution.get("status"),
        "COMPLETE_ALL_FROZEN_CELLS_TERMINAL",
        "non-ALLOW execution status",
    )
    expect(nonallow_execution.get("durable_terminal_records"), 240, "non-ALLOW records")
    expect(nonallow_privacy.get("status"), "PASS", "non-ALLOW privacy")

    nonallow_expected = {
        "glm-5.3": (44, 44, 20, 18, 2, 15, 12, 17),
        "hy3": (36, 36, 15, 14, 1, 11, 12, 13),
        "qwen3.7-plus": (43, 43, 21, 18, 3, 15, 12, 16),
    }
    nonallow_observed = {
        str(row["model_requested"]): (
            int(row["metrics"]["parseable_items"]),
            int(row["metrics"]["correct_items"]),
            int(row["metrics"]["correct_pairs"]),
            int(row["stable_controls"]["correct_pairs"]),
            int(row["changed_pairs"]["correct_pairs"]),
            int(row["metrics"]["per_action"]["HOLD"]["correct"]),
            int(row["metrics"]["per_action"]["DEMOTE"]["correct"]),
            int(row["metrics"]["per_action"]["ESCALATE"]["correct"]),
        )
        for row in nonallow["nonallow_policy_controls"]["primary_pooled_three_replications"]
    }
    expect(nonallow_observed, nonallow_expected, "non-ALLOW full-policy results")

    output = load_object(OUTPUT_CONTRACT / "aggregate.json", "output-contract aggregate")
    output_execution = load_object(
        OUTPUT_CONTRACT / "execution-receipt.json", "output-contract execution receipt"
    )
    output_privacy = load_object(
        OUTPUT_CONTRACT / "privacy-receipt.json", "output-contract privacy receipt"
    )
    expect(output.get("status"), "COMPLETE", "output-contract status")
    expect(nested(output, "execution.scheduled_cells"), 360, "output-contract calls")
    expect(nested(output, "execution.client_retries"), 0, "output-contract retries")
    expect(
        output_execution.get("status"),
        "COMPLETE_ALL_FROZEN_CELLS_TERMINAL",
        "output-contract execution status",
    )
    expect(output_execution.get("durable_terminal_records"), 360, "output-contract records")
    expect(output_privacy.get("status"), "PASS", "output-contract privacy")

    output_expected = {
        ("glm-5.3", "prompt-4096"): (4, 4, 0, 21),
        ("glm-5.3", "prompt-8192"): (15, 15, 6, 10),
        ("glm-5.3", "prompt-12288"): (18, 18, 7, 6),
        ("glm-5.3", "json-schema-4096"): (7, 7, 2, 17),
        ("hy3", "prompt-4096"): (3, 3, 0, 22),
        ("hy3", "prompt-8192"): (18, 18, 7, 6),
        ("hy3", "prompt-12288"): (22, 22, 9, 2),
        ("hy3", "json-schema-4096"): (3, 3, 0, 21),
        ("qwen3.7-plus", "prompt-4096"): (22, 18, 7, 0),
        ("qwen3.7-plus", "prompt-8192"): (20, 17, 5, 0),
        ("qwen3.7-plus", "prompt-12288"): (21, 19, 7, 0),
        ("qwen3.7-plus", "json-schema-4096"): (23, 13, 2, 0),
    }
    output_observed = {
        (str(lane["model_requested"]), str(lane["condition_id"])): (
            int(lane["metrics"]["parseable_items"]),
            int(lane["metrics"]["correct_items"]),
            int(lane["metrics"]["correct_pairs"]),
            int(lane["route_diagnostics"]["length_termination_count"]),
        )
        for lane in output["lanes"]
    }
    expect(output_observed, output_expected, "output-contract route conditions")

    transport = load_object(OUTPUT_TRANSPORT, "output transport diagnostic")
    expect(
        transport.get("transport_failure_categories"),
        {"NETWORK": 3, "QUOTA_OR_BILLING_REJECTION": 63, "SERVER_5XX": 6, "TIMEOUT": 4},
        "output transport categories",
    )
    expect(
        [
            row["rejected_item_sets_equal"]
            for row in transport["registered_primary_contrast_quota_balance"]
        ],
        [True, True, True],
        "output primary quota balance",
    )


def validate_manuscript_claims(tex: str) -> None:
    required = {
        "synthetic scope": "evaluates synthetic, policy-constrained evidence-state transitions",
        "caller obligations": "Users remain responsible for policy parsing",
        "endpoint layers": (
            "raw-strict $\\rightarrow$ registered parser $\\rightarrow$ full contract "
            "$\\rightarrow$ exact decision"
        ),
        "definitional ceiling": "definitional policy ceiling",
        "weak Naive Bayes": "Naive Bayes control supplies a weak shortcut check",
        "Gatekeeper coverage": "2/2 changed rules",
        "Gatekeeper minimum": "two-pair witness",
        "repeated Flash result": "Flash reaches 53/72 raw-strict items and 21/36 pairs",
        "repeated Qwen result": "Qwen reaches 10/72 items and 0/36 pairs",
        "semantic route boundary": "All 63 extracted actions match the executable oracle",
        "shared route configuration": "same provider, base URL",
        "failure taxonomy": "12 read timeouts, three fenced objects",
        "raw-strict outside contract": "49 actions and 40 pairs are correct",
        "contract outside raw-strict": ("including 329 correct actions and 78 correct pairs"),
        "challenge parser provenance": (
            "balanced-challenge parser accepts six fenced Qwen objects, including four correct "
            "actions and two correct pairs"
        ),
        "challenge raw-strict score": (
            "Qwen therefore scores 128/180 items and 46/90 pairs under raw-strict parsing"
        ),
        "profile-blind control": "profile-blind control reaches 57/120 items and 0/60 pairs",
        "r6 result": "258/300",
        "challenge Qwen": "132/180",
        "challenge Flash": "90/180",
        "rare action": "Their \\demote{} recalls are 4/30 and 0/30",
        "historical interface": "historical Flash lane is excluded from model evidence",
        "causal boundary": "does not estimate a model-family, policy-reasoning, or",
        "public challenge boundary": "estimand is robustness on known cases",
        "pre-inference challenge": "fix its cases and labels before inference",
        "external source-screen scope": (
            "fixed query screened 465 public repository seeds and inspected 11 model--policy "
            "candidates"
        ),
        "external Agent Governance result": (
            "fixed revision's 15 upstream tests against the Agent Governance Toolkit parent "
            "yields 11 passes"
        ),
        "external agentgateway result": "all 33 selected tests pass",
        "external policy primary item result": "128/160 actions agree with author targets",
        "external policy primary pair result": (
            "52/80 end-to-end and 52/55 conditional pair agreement"
        ),
        "external changed pairs": "23/48 target-agreeing pairs end to end and 23/26 conditional",
        "external stable controls": "29/32 pairs end to end and 29/29 conditional",
        "external mapping authorship": (
            "we authored the scenarios, finite actions, precedence rule, action mapping"
        ),
        "external annotation boundary": (
            "human agreement and policy-owner validity were not measured"
        ),
        "non-ALLOW stable controls": "stable restrictive-action controls score 50/54 pairs",
        "non-ALLOW decomposition": (
            "50 agreeing, zero complete-disagreeing, and four incomplete stable pairs"
        ),
        "non-ALLOW validity boundary": "not an isolated policy-use effect",
        "Always-ALLOW control": "scores 0/16 items and 0/8 pairs",
        "request-cap comparison": (
            "complete target-agreeing pairs change from 0/15 to 7/15 for GLM"
        ),
        "request-cap selection": "routes were selected after an earlier screen",
        "request-cap replication": "each cell receives one call",
        "output-contract quota boundary": "classifies 63 as quota-or-billing rejections",
        "prose target boundary": "not policy-owner ground truth",
        "PolicyBank relation": "PolicyBank introduces controlled policy gaps",
        "ReguSim relation": "ReguSim separates stated reasoning",
        "structural minimum boundary": (
            "Stochastic fault detection and release sufficiency remain unmeasured"
        ),
        "replay boundary": "cannot be independently re-adjudicated",
    }
    for label, needle in required.items():
        require_text(tex, needle, label)

    forbidden = {
        "broad research-agent claim": r"general research[- ]agent (?:ability|capability)",
        "model-family ranking": r"(?:rank|ranking|outperform\w*)[^.]{0,80}model famil",
        "causal route claim": (
            r"(?:proves?|establishes?) (?:that )?(?:the )?"
            r"(?:model|provider|schema|adapter).{0,50}(?:caus|improv)"
        ),
        "human agreement claim": (
            r"(?:inter[- ]annotator|annotator agreement|human agreement)\s*(?:=|of|was|is)"
        ),
        "invalid response quotation": r"raw (?:invalid|failed) response(?: text)?\s*[:=]",
        "fixed obsolete file count": r"\b(?:179|170|619)\s+files?\b",
        "internal run label": r"\br6\b",
        "workflow receipt trace": r"\bworkflow receipts?\b",
        "literal reviewer command": r"\\texttt\{(?:python|bash|sh|make|pytest|ruff|mypy)\b",
        "internal terminal enum": (
            r"\b(?:MARKDOWN_CODE_FENCE|READ_TIMEOUT|NON_JSON_PREFIX_OR_ENVELOPE|"
            r"LENGTH_TERMINATED_NON_JSON)\b"
        ),
    }
    for label, pattern in forbidden.items():
        if re.search(pattern, tex, re.IGNORECASE | re.DOTALL):
            fail(f"forbidden manuscript claim: {label}")


def validate_style_receipt() -> None:
    audit = load_object(STYLE_AUDIT, "manuscript style audit")
    expect(audit.get("status"), "PASS", "style audit status")
    expect(
        nested(audit, "after.manuscript_sha256"), sha256_hex(TEX), "style audit manuscript digest"
    )
    findings = nested(audit, "after.configured_pattern_findings")
    if any(value != 0 for value in findings.values()):
        fail(f"style audit contains negative-pattern findings: {findings}")


def main() -> int:
    tex = TEX.read_text(encoding="utf-8")
    bib = BIB.read_text(encoding="utf-8")
    validate_structure_and_metadata(tex, bib)
    validate_builder(tex)
    validate_upstream_sources()
    validate_repeated_routes()
    validate_auxiliary_results()
    validate_authored_graph()
    validate_naturalistic()
    validate_current_route_studies()
    validate_manuscript_claims(tex)
    validate_style_receipt()
    print("paper-lint: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
