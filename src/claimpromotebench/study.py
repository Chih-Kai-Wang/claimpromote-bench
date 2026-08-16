"""Cumulative run evaluation and exact matched-arm comparisons."""

from __future__ import annotations

from collections import defaultdict
from itertools import combinations
from typing import Any, TypedDict

from .hashing import canonical_json, sha256_bytes
from .metrics import evaluate_gate_records, evaluate_records, operational_metrics
from .prompts import ARMS
from .statistics import holm_adjust, mcnemar_exact


class RunBundle(TypedDict):
    """One validated run-record file plus immutable provenance."""

    identity: dict[str, Any]
    source: str
    source_sha256: str
    records: list[dict[str, Any]]


GROUP_FIELDS = (
    "model_id",
    "model_artifact_sha256",
    "quantization",
    "runtime_commit",
    "seed",
    "hardware",
)

METRIC_PATHS = {
    "false_promotion_rate": ("primary", "false_promotion_rate"),
    "valid_promotion_recall": ("primary", "valid_promotion_recall"),
    "paired_transition_accuracy": ("primary", "paired_transition_accuracy"),
    "auprc_stepwise": (
        "secondary",
        "precision_recall",
        "auprc_stepwise",
    ),
}


def make_run_id(
    identity: dict[str, Any], source_sha256: str, dataset: dict[str, Any]
) -> str:
    """Return a path-independent digest for one validated run."""

    fingerprint = {
        "dataset": dataset,
        "identity": identity,
        "source_sha256": source_sha256,
    }
    return sha256_bytes(canonical_json(fingerprint).encode("utf-8"))


def _scored_decision(record: dict[str, Any], field: str) -> dict[str, Any]:
    if record["parse_status"] == "OK":
        return dict(record[field])
    return {
        "action": "FORMAT_ERROR",
        "proposed_state": record["current_state"],
        "p_admissible": None,
        "used_evidence_ids": [],
        "reason_codes": ["FORMAT_ERROR"],
        "missing_evidence_ids": [],
    }


def _prediction_records(
    records: list[dict[str, Any]], field: str
) -> list[dict[str, Any]]:
    return [
        {**record, "prediction": _scored_decision(record, field)}
        for record in records
    ]


def evaluate_run_records(
    records: list[dict[str, Any]], *, bootstrap_samples: int = 10_000
) -> dict[str, Any]:
    """Score raw intent, effective decisions, the gate, and runtime fields."""

    raw_records = _prediction_records(records, "raw_decision")
    final_records = _prediction_records(records, "final_decision")
    gate_records = [
        {
            **record,
            "raw_decision": _scored_decision(record, "raw_decision"),
            "final_decision": _scored_decision(record, "final_decision"),
        }
        for record in records
    ]
    format_errors = sum(record["parse_status"] == "FORMAT_ERROR" for record in records)
    return {
        "parse_status": {
            "ok": len(records) - format_errors,
            "format_error": format_errors,
        },
        "raw_intent": evaluate_records(
            raw_records, bootstrap_samples=bootstrap_samples
        ),
        "effective_system": evaluate_records(
            final_records, bootstrap_samples=bootstrap_samples
        ),
        "gate": evaluate_gate_records(gate_records),
        "operations": operational_metrics(records),
    }


def _group_key(identity: dict[str, Any]) -> tuple[str, ...]:
    return tuple(
        "" if identity.get(field) is None else str(identity[field])
        for field in GROUP_FIELDS
    )


def _run_key(identity: dict[str, Any]) -> tuple[str, ...]:
    return (*_group_key(identity), str(identity["arm"]))


def _ordered_correctness(
    records: list[dict[str, Any]], field: str
) -> tuple[list[str], list[bool]]:
    identifiers: list[str] = []
    correctness: list[bool] = []
    for record in sorted(records, key=lambda value: str(value["id"])):
        identifiers.append(str(record["id"]))
        decision = record.get(field)
        correctness.append(
            record["parse_status"] == "OK"
            and isinstance(decision, dict)
            and decision.get("action") == record["gold"]["action"]
        )
    return identifiers, correctness


def _metric_value(report: dict[str, Any], path: tuple[str, ...]) -> float | None:
    value: Any = report
    for key in path:
        value = value[key]
    if isinstance(value, dict) and "value" in value:
        value = value["value"]
    return None if value is None else float(value)


def _metric_deltas(
    left: dict[str, Any], right: dict[str, Any]
) -> dict[str, float | None]:
    deltas: dict[str, float | None] = {}
    for name, path in METRIC_PATHS.items():
        left_value = _metric_value(left, path)
        right_value = _metric_value(right, path)
        deltas[name] = (
            None
            if left_value is None or right_value is None
            else right_value - left_value
        )
    return deltas


def _matched_comparison(
    run_a: dict[str, Any], run_b: dict[str, Any], arm_a: str, arm_b: str
) -> dict[str, Any]:
    ids_a, raw_a = _ordered_correctness(run_a["records"], "raw_decision")
    ids_b, raw_b = _ordered_correctness(run_b["records"], "raw_decision")
    final_ids_a, final_a = _ordered_correctness(
        run_a["records"], "final_decision"
    )
    final_ids_b, final_b = _ordered_correctness(
        run_b["records"], "final_decision"
    )
    if ids_a != ids_b or final_ids_a != final_ids_b or ids_a != final_ids_a:
        raise ValueError("matched runs do not contain identical item IDs")

    return {
        "arm_a": arm_a,
        "arm_b": arm_b,
        "raw_intent": {
            "mcnemar_exact": mcnemar_exact(raw_a, raw_b),
            "delta_b_minus_a": _metric_deltas(
                run_a["report"]["raw_intent"],
                run_b["report"]["raw_intent"],
            ),
        },
        "effective_system": {
            "mcnemar_exact": mcnemar_exact(final_a, final_b),
            "delta_b_minus_a": _metric_deltas(
                run_a["report"]["effective_system"],
                run_b["report"]["effective_system"],
            ),
        },
    }


def _holm_adjust_comparisons(comparisons: list[dict[str, Any]]) -> None:
    if not comparisons:
        return
    raw_adjusted = holm_adjust(
        [
            float(comparison["raw_intent"]["mcnemar_exact"]["p"])
            for comparison in comparisons
        ]
    )
    effective_adjusted = holm_adjust(
        [
            float(comparison["effective_system"]["mcnemar_exact"]["p"])
            for comparison in comparisons
        ]
    )
    for comparison, raw_p, effective_p in zip(
        comparisons,
        raw_adjusted,
        effective_adjusted,
        strict=True,
    ):
        comparison["raw_intent"]["mcnemar_exact"]["p_holm"] = raw_p
        comparison["effective_system"]["mcnemar_exact"]["p_holm"] = effective_p


def compare_run_bundles(
    bundles: list[RunBundle],
    *,
    dataset: dict[str, Any],
    bootstrap_samples: int = 0,
) -> dict[str, Any]:
    """Build a hash-bound cumulative study report and matched arm comparisons."""

    if not bundles:
        raise ValueError("study comparison requires at least one run")
    if bootstrap_samples < 0:
        raise ValueError("bootstrap samples must be non-negative")

    seen_sources: set[str] = set()
    seen_runs: set[tuple[str, ...]] = set()
    evaluated: list[dict[str, Any]] = []
    groups: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)

    for bundle in bundles:
        source_sha256 = bundle["source_sha256"]
        identity = bundle["identity"]
        if source_sha256 in seen_sources:
            raise ValueError(f"duplicate run content: {source_sha256}")
        run_key = _run_key(identity)
        if run_key in seen_runs:
            raise ValueError(
                "duplicate model/artifact/runtime/seed/hardware/arm run identity"
            )
        seen_sources.add(source_sha256)
        seen_runs.add(run_key)

        report = evaluate_run_records(
            bundle["records"], bootstrap_samples=bootstrap_samples
        )
        evaluated_run: dict[str, Any] = {
            "run_id": make_run_id(identity, source_sha256, dataset),
            "identity": identity,
            "source": bundle["source"],
            "source_sha256": source_sha256,
            "records": bundle["records"],
            "report": report,
        }
        evaluated.append(evaluated_run)
        groups[_group_key(identity)].append(evaluated_run)

    arm_order = {arm: index for index, arm in enumerate(ARMS)}
    evaluated.sort(
        key=lambda run: (
            _group_key(run["identity"]),
            arm_order[str(run["identity"]["arm"])],
            str(run["source_sha256"]),
        )
    )

    group_reports: list[dict[str, Any]] = []
    for group_key in sorted(groups):
        runs = sorted(
            groups[group_key],
            key=lambda run: arm_order[str(run["identity"]["arm"])],
        )
        by_arm = {str(run["identity"]["arm"]): run for run in runs}
        present = [arm for arm in ARMS if arm in by_arm]
        comparisons_report = [
            _matched_comparison(
                by_arm[arm_a],
                by_arm[arm_b],
                arm_a,
                arm_b,
            )
            for arm_a, arm_b in combinations(present, 2)
        ]
        _holm_adjust_comparisons(comparisons_report)

        identity = {
            field: runs[0]["identity"].get(field)
            for field in GROUP_FIELDS
        }
        group_reports.append(
            {
                "identity": identity,
                "arms_present": present,
                "arms_missing": [arm for arm in ARMS if arm not in by_arm],
                "complete": len(present) == len(ARMS),
                "comparisons": comparisons_report,
            }
        )

    public_runs = [
        {
            "run_id": run["run_id"],
            "identity": run["identity"],
            "source": run["source"],
            "source_sha256": run["source_sha256"],
            **run["report"],
        }
        for run in evaluated
    ]
    fingerprint = {
        "dataset": dataset,
        "run_ids": [run["run_id"] for run in evaluated],
    }
    return {
        "study_id": sha256_bytes(canonical_json(fingerprint).encode("utf-8")),
        "dataset": dataset,
        "summary": {
            "runs": len(public_runs),
            "groups": len(group_reports),
            "complete_groups": sum(group["complete"] for group in group_reports),
            "comparisons": sum(
                len(group["comparisons"]) for group in group_reports
            ),
        },
        "runs": public_runs,
        "groups": group_reports,
    }
