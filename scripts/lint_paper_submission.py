#!/usr/bin/env python3
"""Fail-closed evidence and scope checks for the submission manuscript."""

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
SUBMISSION_BUILDER = ROOT / "scripts" / "build_submission_tex.py"
STYLE_AUDIT = ROOT / "docs" / "MANUSCRIPT_STYLE_AUDIT_2026-08-23.json"

UPSTREAM = ROOT / "v2" / "upstream-policy-revisions-v1"
TRIVY = ROOT / "v2" / "trivy-policy-revision-v1"
SIGSTORE = ROOT / "v2" / "sigstore-policy-verifier-revision-v1"
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

CANONICAL_TITLE = (
    "ClaimPromoteBench: Compiling Executable Policy Revisions into Paired "
    "Model-Service Regression Tests"
)
TEX_TITLE = (
    r"\cpb: Compiling Executable Policy Revisions into Paired Model-Service Regression Tests"
)


def fail(message: str) -> None:
    raise SystemExit(f"paper-lint: {message}")


def load_object(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        fail(f"missing {label}: {path.relative_to(ROOT)}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        fail(f"{label} must contain a JSON object")
    return value


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
        "martin2007policytests",
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
    expect(
        sum(
            route["metrics"]["endpoint_difference"]["extractable_items_outside_full_contract"]
            for route in routes
        ),
        69,
        "dual extra extractable items",
    )
    expect(
        sum(
            route["metrics"]["endpoint_difference"]["action_correct_items_outside_full_contract"]
            for route in routes
        ),
        49,
        "dual extra correct items",
    )
    expect(
        sum(
            route["metrics"]["endpoint_difference"]["additional_action_correct_pairs"]
            for route in routes
        ),
        40,
        "dual extra correct pairs",
    )
    by_id = {route["route_stack_id"]: route for route in routes}
    for lane_id, strict_items, contract_items, strict_pairs, contract_pairs in (
        ("challenge-deepseek-flash-host-schema", 105, 90, 19, 13),
        ("challenge-qwen-host-prompt", 132, 132, 48, 48),
        ("slsa-deepseek-flash-host-schema", 110, 108, 51, 49),
        ("slsa-qwen-host-prompt", 120, 88, 60, 28),
    ):
        metrics = by_id[lane_id]["metrics"]
        expect(
            nested(metrics, "action_only.correct_items"), strict_items, f"{lane_id} strict items"
        )
        expect(
            nested(metrics, "full_contract.action_correct_items"),
            contract_items,
            f"{lane_id} contract items",
        )
        expect(
            nested(metrics, "action_only.correct_pairs"), strict_pairs, f"{lane_id} strict pairs"
        )
        expect(
            nested(metrics, "full_contract.action_correct_pairs"),
            contract_pairs,
            f"{lane_id} contract pairs",
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


def validate_manuscript_claims(tex: str) -> None:
    required = {
        "synthetic scope": "synthetic, policy-constrained evaluation",
        "three endpoints": (
            "strict action $\\rightarrow$ contract action $\\rightarrow$ full decision"
        ),
        "definitional ceiling": "definitional policy ceiling",
        "weak Naive Bayes": "Naive Bayes sanity control is deliberately weak",
        "Gatekeeper coverage": "2/2 changed rules",
        "Gatekeeper minimum": "two-pair witness",
        "repeated Flash result": "53/72 items and 21/36 pairs",
        "repeated Qwen result": "10/72 strict and full decisions",
        "failure taxonomy": "12 read timeouts, three fenced objects",
        "dual endpoint totals": "49 are correct and create 40 additional correct pairs",
        "r6 result": "258/300",
        "challenge Qwen": "132/180",
        "challenge Flash": "90/180",
        "rare action": "4/30 \\demote, and Flash recovers 0/30",
        "historical interface": "obsolete frozen service interface",
        "causal boundary": "carry no causal comparison with the 401 lane",
        "public challenge boundary": "robustness check under known cases",
        "naturalistic decision": "zero admissible cases",
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
    validate_manuscript_claims(tex)
    validate_style_receipt()
    print("paper-lint: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
