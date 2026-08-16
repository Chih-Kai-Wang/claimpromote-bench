"""Analyze completed independent reviews and enforce adjudication coverage."""

from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from datetime import datetime
from itertools import combinations
from pathlib import Path
from typing import Any

from .dataset import load_json, load_jsonl, repository_root, validate_with_schema
from .errors import ClaimPromoteBenchError, DatasetIntegrityError
from .hashing import canonical_json, sha256_bytes, sha256_file
from .policy import load_policy
from .review import (
    MANIFEST_FILENAME,
    PRIVATE_KEY_FILENAME,
    SUBMISSIONS_DIRECTORY,
    validate_review_package,
)

SCHEMA_VERSION = "1.0.0"
REPORT_FILENAME = "review-report.json"
ADJUDICATION_FILENAME = "adjudication.json"
ACTION_ORDER = ("ALLOW", "HOLD", "DEMOTE", "ESCALATE")
ACTION_SET = set(ACTION_ORDER)
MINIMUM_REVIEWERS = 2
MINIMUM_PER_REVIEWER_ACTION_AGREEMENT = 0.80
MINIMUM_PAIRWISE_ACTION_AGREEMENT = 0.80
DISPOSITIONS = {"KEEP_GOLD", "REVISE_ITEM", "REVISE_POLICY", "UNRESOLVED"}


def _schema(name: str) -> Path:
    return repository_root() / "schemas" / name


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _mean(values: list[float]) -> float:
    if not values:
        raise DatasetIntegrityError("cannot compute a mean over no values")
    return sum(values) / len(values)


def _reason_set(decision: dict[str, Any]) -> frozenset[str]:
    reasons = decision.get("reason_codes")
    if not isinstance(reasons, list) or not reasons:
        raise DatasetIntegrityError("review analysis encountered an empty reason set")
    return frozenset(str(value) for value in reasons)


def _reason_jaccard(left: dict[str, Any], right: dict[str, Any]) -> float:
    left_set = _reason_set(left)
    right_set = _reason_set(right)
    return len(left_set & right_set) / len(left_set | right_set)


def _empty_confusion() -> dict[str, dict[str, int]]:
    return {expected: {observed: 0 for observed in ACTION_ORDER} for expected in ACTION_ORDER}


def _cohen_kappa(left: list[str], right: list[str]) -> float | None:
    if len(left) != len(right) or not left:
        raise DatasetIntegrityError("Cohen kappa requires two non-empty aligned action lists")
    observed = sum(a == b for a, b in zip(left, right, strict=True)) / len(left)
    left_counts = {action: left.count(action) / len(left) for action in ACTION_ORDER}
    right_counts = {action: right.count(action) / len(right) for action in ACTION_ORDER}
    expected = sum(left_counts[action] * right_counts[action] for action in ACTION_ORDER)
    if expected == 1.0:
        return None
    return (observed - expected) / (1.0 - expected)


def _fleiss_kappa(action_rows: list[list[str]]) -> float | None:
    if not action_rows:
        raise DatasetIntegrityError("Fleiss kappa requires at least one reviewed item")
    reviewer_count = len(action_rows[0])
    if reviewer_count < 2:
        return None
    if any(len(row) != reviewer_count for row in action_rows):
        raise DatasetIntegrityError("Fleiss kappa requires a constant reviewer count")

    per_item_agreement: list[float] = []
    total_counts = {action: 0 for action in ACTION_ORDER}
    for row in action_rows:
        counts = {action: row.count(action) for action in ACTION_ORDER}
        for action, count in counts.items():
            total_counts[action] += count
        numerator = sum(count * count for count in counts.values()) - reviewer_count
        per_item_agreement.append(numerator / (reviewer_count * (reviewer_count - 1)))

    item_count = len(action_rows)
    observed = _mean(per_item_agreement)
    category_proportions = {
        action: total_counts[action] / (item_count * reviewer_count) for action in ACTION_ORDER
    }
    expected = sum(value * value for value in category_proportions.values())
    if expected == 1.0:
        return None
    return (observed - expected) / (1.0 - expected)


def _report_identity(report: dict[str, Any]) -> dict[str, Any]:
    identity = deepcopy(report)
    identity.pop("report_id", None)
    return identity


def _report_id(report: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json(_report_identity(report)).encode("utf-8"))


def _load_report(path: Path) -> dict[str, Any]:
    value = load_json(path)
    if not isinstance(value, dict):
        raise DatasetIntegrityError("review analysis report must be an object")
    validate_with_schema(value, _schema("review-analysis.schema.json"), str(path))
    if value["report_id"] != _report_id(value):
        raise DatasetIntegrityError("review analysis report_id is stale")
    return value


def _parse_completed_at(value: str) -> None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DatasetIntegrityError("adjudication completed_at is not a valid date-time") from exc
    if parsed.tzinfo is None:
        raise DatasetIntegrityError("adjudication completed_at must include a timezone")


def _load_package_data(
    dataset_dir: Path,
    package_dir: Path,
) -> tuple[
    dict[str, Any],
    dict[str, str],
    dict[str, dict[str, Any]],
    list[dict[str, Any]],
]:
    validate_review_package(dataset_dir, package_dir)

    manifest = load_json(package_dir / MANIFEST_FILENAME)
    key = load_json(package_dir / PRIVATE_KEY_FILENAME)
    dataset_manifest = load_json(dataset_dir / "manifest.json")
    if not all(isinstance(value, dict) for value in (manifest, key, dataset_manifest)):
        raise DatasetIntegrityError("review analysis package metadata is malformed")

    mapping = {str(value["review_item_id"]): str(value["item_id"]) for value in key["mapping"]}
    gold = {str(record["id"]): record for record in load_jsonl(dataset_dir / "gold.jsonl")}
    paths = sorted((package_dir / SUBMISSIONS_DIRECTORY).glob("*.json"))
    submissions: list[dict[str, Any]] = []
    for path in paths:
        submission = load_json(path)
        if not isinstance(submission, dict):
            raise DatasetIntegrityError(f"review submission is not an object: {path}")
        value = deepcopy(submission)
        value["submission_sha256"] = sha256_file(path)
        submissions.append(value)
    submissions.sort(key=lambda value: str(value["reviewer_id"]))
    return manifest, mapping, gold, submissions


def _decision_map(submission: dict[str, Any]) -> dict[str, dict[str, Any]]:
    decisions = submission.get("decisions")
    if not isinstance(decisions, list):
        raise DatasetIntegrityError("review submission decisions are malformed")
    return {str(value["review_item_id"]): value for value in decisions}


def _reviewer_metrics(
    mapping: dict[str, str],
    gold: dict[str, dict[str, Any]],
    submission: dict[str, Any],
) -> dict[str, Any]:
    decisions = _decision_map(submission)
    action_matches = 0
    exact_reason_matches = 0
    reason_jaccards: list[float] = []
    confidences: list[float] = []
    confusion = _empty_confusion()
    for review_item_id in sorted(mapping):
        item_id = mapping[review_item_id]
        expected = gold[item_id]["decision"]
        observed = decisions[review_item_id]
        expected_action = str(expected["action"])
        observed_action = str(observed["action"])
        action_matches += expected_action == observed_action
        exact_reason_matches += _reason_set(expected) == _reason_set(observed)
        reason_jaccards.append(_reason_jaccard(expected, observed))
        confidences.append(float(observed["confidence"]))
        confusion[expected_action][observed_action] += 1
    item_count = len(mapping)
    return {
        "reviewer_id": submission["reviewer_id"],
        "submission_sha256": submission["submission_sha256"],
        "action_agreement_with_gold": action_matches / item_count,
        "exact_reason_set_agreement_with_gold": exact_reason_matches / item_count,
        "mean_reason_jaccard_with_gold": _mean(reason_jaccards),
        "mean_confidence": _mean(confidences),
        "action_confusion_with_gold": confusion,
    }


def _pairwise_metrics(
    mapping: dict[str, str],
    left: dict[str, Any],
    right: dict[str, Any],
) -> dict[str, Any]:
    left_decisions = _decision_map(left)
    right_decisions = _decision_map(right)
    left_actions: list[str] = []
    right_actions: list[str] = []
    exact_reasons = 0
    reason_jaccards: list[float] = []
    for review_item_id in sorted(mapping):
        left_decision = left_decisions[review_item_id]
        right_decision = right_decisions[review_item_id]
        left_actions.append(str(left_decision["action"]))
        right_actions.append(str(right_decision["action"]))
        exact_reasons += _reason_set(left_decision) == _reason_set(right_decision)
        reason_jaccards.append(_reason_jaccard(left_decision, right_decision))
    item_count = len(mapping)
    return {
        "reviewer_a": left["reviewer_id"],
        "reviewer_b": right["reviewer_id"],
        "raw_action_agreement": sum(
            a == b for a, b in zip(left_actions, right_actions, strict=True)
        )
        / item_count,
        "cohen_kappa": _cohen_kappa(left_actions, right_actions),
        "exact_reason_set_agreement": exact_reasons / item_count,
        "mean_reason_jaccard": _mean(reason_jaccards),
    }


def _disagreements(
    packet_id: str,
    mapping: dict[str, str],
    gold: dict[str, dict[str, Any]],
    submissions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    decision_maps = {
        str(submission["reviewer_id"]): _decision_map(submission) for submission in submissions
    }
    disagreements: list[dict[str, Any]] = []
    for review_item_id in sorted(mapping):
        item_id = mapping[review_item_id]
        gold_record = gold[item_id]
        expected = gold_record["decision"]
        reviewer_decisions = [
            {
                "reviewer_id": reviewer_id,
                "action": decisions[review_item_id]["action"],
                "reason_codes": decisions[review_item_id]["reason_codes"],
                "confidence": decisions[review_item_id]["confidence"],
                "rationale": decisions[review_item_id]["rationale"],
            }
            for reviewer_id, decisions in sorted(decision_maps.items())
        ]
        actions = {str(value["action"]) for value in reviewer_decisions}
        reviewer_reason_sets = {
            frozenset(str(reason) for reason in value["reason_codes"])
            for value in reviewer_decisions
        }
        expected_reason_set = _reason_set(expected)
        kinds: list[str] = []
        if any(str(value["action"]) != expected["action"] for value in reviewer_decisions):
            kinds.append("GOLD_ACTION")
        if len(actions) > 1:
            kinds.append("REVIEWER_ACTION")
        if any(
            frozenset(str(reason) for reason in value["reason_codes"]) != expected_reason_set
            for value in reviewer_decisions
        ):
            kinds.append("GOLD_REASON_SET")
        if len(reviewer_reason_sets) > 1:
            kinds.append("REVIEWER_REASON_SET")
        if not kinds:
            continue
        disagreements.append(
            {
                "disagreement_id": sha256_bytes(
                    canonical_json(
                        {
                            "packet_id": packet_id,
                            "review_item_id": review_item_id,
                        }
                    ).encode("utf-8")
                ),
                "review_item_id": review_item_id,
                "item_id": item_id,
                "pair_id": gold_record["pair_id"],
                "family": gold_record["family"],
                "kinds": kinds,
                "gold_action": expected["action"],
                "gold_reason_codes": expected["reason_codes"],
                "reviewer_decisions": reviewer_decisions,
            }
        )
    return disagreements


def analyze_review_package(dataset_dir: Path, package_dir: Path) -> dict[str, Any]:
    """Compute deterministic agreement, disagreement, and pre-adjudication gate results."""

    manifest, mapping, gold, submissions = _load_package_data(dataset_dir, package_dir)
    reviewer_metrics = [_reviewer_metrics(mapping, gold, submission) for submission in submissions]
    pairwise = [
        _pairwise_metrics(mapping, left, right) for left, right in combinations(submissions, 2)
    ]
    pairwise_agreements = [float(value["raw_action_agreement"]) for value in pairwise]
    decision_maps = [_decision_map(submission) for submission in submissions]
    action_rows = [
        [str(decisions[review_item_id]["action"]) for decisions in decision_maps]
        for review_item_id in sorted(mapping)
    ]
    unanimous_action_rate = sum(len(set(row)) == 1 for row in action_rows) / len(action_rows)
    disagreements = _disagreements(
        str(manifest["packet_id"]),
        mapping,
        gold,
        submissions,
    )

    reviewer_count_pass = len(submissions) >= MINIMUM_REVIEWERS
    per_reviewer_pass = reviewer_count_pass and all(
        float(value["action_agreement_with_gold"]) >= MINIMUM_PER_REVIEWER_ACTION_AGREEMENT
        for value in reviewer_metrics
    )
    minimum_pairwise = min(pairwise_agreements) if pairwise_agreements else None
    mean_pairwise = _mean(pairwise_agreements) if pairwise_agreements else None
    pairwise_pass = (
        reviewer_count_pass
        and minimum_pairwise is not None
        and minimum_pairwise >= MINIMUM_PAIRWISE_ACTION_AGREEMENT
    )
    metrics_pass = reviewer_count_pass and per_reviewer_pass and pairwise_pass
    if not reviewer_count_pass:
        gate_status = "PENDING"
    elif not metrics_pass:
        gate_status = "REVISION_REQUIRED"
    elif disagreements:
        gate_status = "NEEDS_ADJUDICATION"
    else:
        gate_status = "PASS"

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "packet_id": manifest["packet_id"],
        "dataset_manifest_sha256": manifest["dataset_manifest_sha256"],
        "policy_sha256": manifest["policy_sha256"],
        "item_count": len(mapping),
        "reviewer_count": len(submissions),
        "thresholds": {
            "minimum_reviewers": MINIMUM_REVIEWERS,
            "minimum_per_reviewer_action_agreement": (MINIMUM_PER_REVIEWER_ACTION_AGREEMENT),
            "minimum_pairwise_action_agreement": MINIMUM_PAIRWISE_ACTION_AGREEMENT,
        },
        "reviewers": reviewer_metrics,
        "inter_reviewer": {
            "pairwise": pairwise,
            "minimum_pairwise_action_agreement": minimum_pairwise,
            "mean_pairwise_action_agreement": mean_pairwise,
            "unanimous_action_rate": unanimous_action_rate,
            "fleiss_kappa": _fleiss_kappa(action_rows),
        },
        "disagreements": disagreements,
        "gate": {
            "status": gate_status,
            "reviewer_count_pass": reviewer_count_pass,
            "per_reviewer_action_agreement_pass": per_reviewer_pass,
            "pairwise_action_agreement_pass": pairwise_pass,
            "metrics_pass": metrics_pass,
            "disagreement_count": len(disagreements),
        },
    }
    report["report_id"] = _report_id(report)
    validate_with_schema(report, _schema("review-analysis.schema.json"), "review-analysis")
    return report


def initialize_adjudication(
    report_path: Path,
    adjudicator_id: str,
    out_path: Path,
) -> dict[str, Any]:
    """Create an intentionally incomplete adjudication draft for every disagreement."""

    report = _load_report(report_path)
    draft = {
        "schema_version": SCHEMA_VERSION,
        "analysis_report_id": report["report_id"],
        "packet_id": report["packet_id"],
        "adjudicator_id": adjudicator_id,
        "completed_at": None,
        "entries": [
            {
                "disagreement_id": value["disagreement_id"],
                "disposition": "UNRESOLVED",
                "recommended_action": None,
                "recommended_reason_codes": [],
                "note": "",
            }
            for value in report["disagreements"]
        ],
    }
    _write_json(out_path, draft)
    return {
        "status": "DRAFT_CREATED",
        "disagreements": len(draft["entries"]),
        "out": str(out_path),
    }


def _policy_reason_codes(dataset_dir: Path) -> set[str]:
    manifest = load_json(dataset_dir / "manifest.json")
    if not isinstance(manifest, dict):
        raise DatasetIntegrityError("dataset manifest is malformed")
    policy = load_policy(repository_root() / "policies" / str(manifest["policy_file"]))
    reasons = policy.get("reason_precedence")
    if not isinstance(reasons, list):
        raise DatasetIntegrityError("policy reason vocabulary is malformed")
    return {str(value) for value in reasons}


def _validate_action_reasons(
    action: str,
    reasons: list[str],
    allowed_reasons: set[str],
) -> None:
    if action not in ACTION_SET:
        raise DatasetIntegrityError(f"unknown adjudicated action: {action}")
    if not reasons:
        raise DatasetIntegrityError("adjudicated action requires at least one reason code")
    unknown = set(reasons) - allowed_reasons
    if unknown:
        raise DatasetIntegrityError(f"unknown adjudicated reason codes: {sorted(unknown)}")
    if action == "ALLOW" and reasons != ["POLICY_SATISFIED"]:
        raise DatasetIntegrityError("adjudicated ALLOW requires POLICY_SATISFIED only")
    if action != "ALLOW" and "POLICY_SATISFIED" in reasons:
        raise DatasetIntegrityError("adjudicated non-ALLOW cannot use POLICY_SATISFIED")


def _validate_adjudication_value(
    dataset_dir: Path,
    report: dict[str, Any],
    value: dict[str, Any],
    label: str,
) -> dict[str, Any]:
    validate_with_schema(value, _schema("review-adjudication.schema.json"), label)
    if value["analysis_report_id"] != report["report_id"]:
        raise DatasetIntegrityError("adjudication analysis_report_id is stale")
    if value["packet_id"] != report["packet_id"]:
        raise DatasetIntegrityError("adjudication packet_id is stale")
    _parse_completed_at(str(value["completed_at"]))

    disagreements = {
        str(disagreement["disagreement_id"]): disagreement
        for disagreement in report["disagreements"]
    }
    entries = value.get("entries")
    if not isinstance(entries, list):
        raise DatasetIntegrityError("adjudication entries must be an array")
    observed: set[str] = set()
    allowed_reasons = _policy_reason_codes(dataset_dir)
    for entry in entries:
        if not isinstance(entry, dict):
            raise DatasetIntegrityError("adjudication entry must be an object")
        disagreement_id = str(entry["disagreement_id"])
        if disagreement_id in observed:
            raise DatasetIntegrityError(f"duplicate adjudication entry: {disagreement_id}")
        observed.add(disagreement_id)
        if disagreement_id not in disagreements:
            raise DatasetIntegrityError(f"unknown adjudication disagreement: {disagreement_id}")
        disposition = str(entry["disposition"])
        if disposition not in DISPOSITIONS:
            raise DatasetIntegrityError(f"unknown adjudication disposition: {disposition}")
        action = entry["recommended_action"]
        reasons = [str(reason) for reason in entry["recommended_reason_codes"]]
        disagreement = disagreements[disagreement_id]
        if disposition == "UNRESOLVED":
            if action is not None or reasons:
                raise DatasetIntegrityError(
                    "UNRESOLVED adjudication cannot contain a recommendation"
                )
        elif disposition == "KEEP_GOLD":
            if (
                action != disagreement["gold_action"]
                or reasons != disagreement["gold_reason_codes"]
            ):
                raise DatasetIntegrityError("KEEP_GOLD must reproduce the frozen gold decision")
        else:
            if not isinstance(action, str):
                raise DatasetIntegrityError("revision disposition requires a recommended action")
            _validate_action_reasons(action, reasons, allowed_reasons)
    expected = set(disagreements)
    if observed != expected:
        missing = sorted(expected - observed)
        extra = sorted(observed - expected)
        raise DatasetIntegrityError(
            f"adjudication coverage mismatch; missing={missing}, extra={extra}"
        )
    return value


def evaluate_final_gate(
    report: dict[str, Any],
    adjudication: dict[str, Any] | None,
) -> dict[str, Any]:
    """Combine frozen agreement metrics with adjudication dispositions."""

    metrics_pass = bool(report["gate"]["metrics_pass"])
    disagreement_count = int(report["gate"]["disagreement_count"])
    if report["reviewer_count"] < MINIMUM_REVIEWERS:
        status = "PENDING"
    elif not metrics_pass:
        status = "REVISION_REQUIRED"
    elif disagreement_count == 0:
        status = "PASS"
    elif adjudication is None:
        status = "NEEDS_ADJUDICATION"
    else:
        dispositions = [str(entry["disposition"]) for entry in adjudication["entries"]]
        if "UNRESOLVED" in dispositions:
            status = "NEEDS_ADJUDICATION"
        elif any(value in {"REVISE_ITEM", "REVISE_POLICY"} for value in dispositions):
            status = "REVISION_REQUIRED"
        else:
            status = "PASS"
    counts = {value: 0 for value in sorted(DISPOSITIONS)}
    if adjudication is not None:
        for entry in adjudication["entries"]:
            counts[str(entry["disposition"])] += 1
    return {
        "status": status,
        "metrics_pass": metrics_pass,
        "disagreement_count": disagreement_count,
        "disposition_counts": counts,
    }


def validate_adjudication(
    dataset_dir: Path,
    package_dir: Path,
    report_path: Path,
    adjudication_path: Path,
) -> dict[str, Any]:
    """Recompute the report, validate adjudication coverage, and return the final gate."""

    computed = analyze_review_package(dataset_dir, package_dir)
    committed = _load_report(report_path)
    if canonical_json(committed) != canonical_json(computed):
        raise DatasetIntegrityError("committed review analysis differs from recomputation")
    value = load_json(adjudication_path)
    if not isinstance(value, dict):
        raise DatasetIntegrityError("review adjudication must be an object")
    adjudication = _validate_adjudication_value(
        dataset_dir,
        committed,
        value,
        str(adjudication_path),
    )
    final_gate = evaluate_final_gate(committed, adjudication)
    return {
        "status": "PASS",
        "report_id": committed["report_id"],
        "adjudication_sha256": sha256_file(adjudication_path),
        "final_gate": final_gate,
    }


def validate_analysis_package(
    dataset_dir: Path,
    package_dir: Path,
) -> dict[str, Any]:
    """Validate a published package, deterministic report, and complete adjudication."""

    computed = analyze_review_package(dataset_dir, package_dir)
    if computed["reviewer_count"] < MINIMUM_REVIEWERS:
        raise DatasetIntegrityError("published review package requires at least two reviewers")
    report_path = package_dir / REPORT_FILENAME
    if not report_path.is_file():
        raise DatasetIntegrityError("published review package is missing review-report.json")
    committed = _load_report(report_path)
    if canonical_json(committed) != canonical_json(computed):
        raise DatasetIntegrityError("published review report differs from recomputation")

    adjudication_path = package_dir / ADJUDICATION_FILENAME
    adjudication: dict[str, Any] | None = None
    if committed["disagreements"]:
        if not adjudication_path.is_file():
            raise DatasetIntegrityError("published disagreements require adjudication.json")
        value = load_json(adjudication_path)
        if not isinstance(value, dict):
            raise DatasetIntegrityError("published adjudication must be an object")
        adjudication = _validate_adjudication_value(
            dataset_dir,
            committed,
            value,
            str(adjudication_path),
        )
    elif adjudication_path.exists():
        raise DatasetIntegrityError("adjudication.json is forbidden when no disagreement exists")

    final_gate = evaluate_final_gate(committed, adjudication)
    return {
        "status": "PASS",
        "packet_id": committed["packet_id"],
        "report_id": committed["report_id"],
        "reviewers": committed["reviewer_count"],
        "items": committed["item_count"],
        "final_gate": final_gate,
    }


def validate_analysis_root(
    dataset_dir: Path,
    reviews_root: Path,
    *,
    allow_empty: bool,
) -> dict[str, Any]:
    """Validate every published analysis package while preserving negative results."""

    if not reviews_root.is_dir():
        raise DatasetIntegrityError(f"review root does not exist: {reviews_root}")
    manifests = sorted(reviews_root.glob(f"*/{MANIFEST_FILENAME}"))
    if not manifests:
        if not allow_empty:
            raise DatasetIntegrityError("review root contains no analyzed package")
        return {
            "status": "PENDING",
            "packages": 0,
            "gate_counts": {
                "PASS": 0,
                "PENDING": 0,
                "NEEDS_ADJUDICATION": 0,
                "REVISION_REQUIRED": 0,
            },
        }
    reports = [validate_analysis_package(dataset_dir, path.parent) for path in manifests]
    gate_counts = {
        "PASS": 0,
        "PENDING": 0,
        "NEEDS_ADJUDICATION": 0,
        "REVISION_REQUIRED": 0,
    }
    for report in reports:
        gate_counts[str(report["final_gate"]["status"])] += 1
    return {
        "status": "PASS",
        "packages": len(reports),
        "gate_counts": gate_counts,
        "reports": reports,
    }


def _emit(report: dict[str, Any], out_path: Path | None) -> None:
    if out_path is not None:
        _write_json(out_path, report)
        summary = {
            key: value
            for key, value in report.items()
            if key not in {"reviewers", "inter_reviewer", "disagreements", "reports"}
        }
        summary["out"] = str(out_path)
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    """Run review agreement reporting and adjudication validation."""

    parser = argparse.ArgumentParser(prog="cpb-review-report", description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze_parser = subparsers.add_parser("analyze")
    analyze_parser.add_argument("--dataset", type=Path, default=Path("data/alpha"))
    analyze_parser.add_argument("--package", type=Path, required=True)
    analyze_parser.add_argument("--out", type=Path, required=True)

    initialize_parser = subparsers.add_parser("init-adjudication")
    initialize_parser.add_argument("--report", type=Path, required=True)
    initialize_parser.add_argument("--adjudicator-id", required=True)
    initialize_parser.add_argument("--out", type=Path, required=True)

    adjudication_parser = subparsers.add_parser("validate-adjudication")
    adjudication_parser.add_argument("--dataset", type=Path, default=Path("data/alpha"))
    adjudication_parser.add_argument("--package", type=Path, required=True)
    adjudication_parser.add_argument("--report", type=Path, required=True)
    adjudication_parser.add_argument("--adjudication", type=Path, required=True)
    adjudication_parser.add_argument("--out", type=Path)

    package_parser = subparsers.add_parser("validate-package")
    package_parser.add_argument("--dataset", type=Path, default=Path("data/alpha"))
    package_parser.add_argument("--package", type=Path, required=True)
    package_parser.add_argument("--out", type=Path)

    root_parser = subparsers.add_parser("validate-root")
    root_parser.add_argument("--dataset", type=Path, default=Path("data/alpha"))
    root_parser.add_argument("--root", type=Path, default=Path("reviews"))
    root_parser.add_argument("--allow-empty", action="store_true")
    root_parser.add_argument("--out", type=Path)

    args = parser.parse_args(argv)
    try:
        if args.command == "analyze":
            report = analyze_review_package(args.dataset, args.package)
            _emit(report, args.out)
        elif args.command == "init-adjudication":
            report = initialize_adjudication(
                args.report,
                args.adjudicator_id,
                args.out,
            )
            _emit(report, None)
        elif args.command == "validate-adjudication":
            report = validate_adjudication(
                args.dataset,
                args.package,
                args.report,
                args.adjudication,
            )
            _emit(report, args.out)
        elif args.command == "validate-package":
            report = validate_analysis_package(args.dataset, args.package)
            _emit(report, args.out)
        elif args.command == "validate-root":
            report = validate_analysis_root(
                args.dataset,
                args.root,
                allow_empty=bool(args.allow_empty),
            )
            _emit(report, args.out)
        else:
            raise DatasetIntegrityError(f"unknown review analysis command: {args.command}")
    except (ClaimPromoteBenchError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
