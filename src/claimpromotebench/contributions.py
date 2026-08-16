"""Validate externally contributed, hash-bound model run packages."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .cli import _build_run_context, _load_run_bundle
from .dataset import load_json, repository_root, validate_with_schema
from .errors import ClaimPromoteBenchError, DatasetIntegrityError
from .hashing import canonical_json, sha256_bytes, sha256_file
from .study import evaluate_run_records, make_run_id

CONTRIBUTION_FILENAME = "contribution.json"


def _resolve_file(base: Path, relative: str, label: str) -> Path:
    value = Path(relative)
    if value.is_absolute():
        raise DatasetIntegrityError(f"{label} must be a relative path")
    root = base.resolve()
    candidate = (root / value).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise DatasetIntegrityError(f"{label} escapes its allowed directory") from exc
    if not candidate.is_file():
        raise DatasetIntegrityError(f"{label} does not exist: {relative}")
    return candidate


def make_contribution_id(manifest: dict[str, Any]) -> str:
    """Return the stable ID for one contributor, dataset, run, and identity tuple."""

    fingerprint = {
        "schema_version": manifest["schema_version"],
        "contributor_github_login": str(manifest["contributor"]["github_login"]).lower(),
        "dataset_manifest_sha256": manifest["dataset_manifest_sha256"],
        "run_file_sha256": manifest["run_file_sha256"],
        "expected_run": manifest["expected_run"],
        "license": manifest["license"],
    }
    return sha256_bytes(canonical_json(fingerprint).encode("utf-8"))


def _metric_value(report: dict[str, Any], *path: str) -> float | None:
    value: Any = report
    for key in path:
        value = value[key]
    if isinstance(value, dict) and "value" in value:
        value = value["value"]
    return None if value is None else float(value)


def _evaluation_summary(report: dict[str, Any]) -> dict[str, Any]:
    raw = report["raw_intent"]
    effective = report["effective_system"]
    return {
        "instances": raw["instances"],
        "format_errors": report["parse_status"]["format_error"],
        "raw_false_promotion_rate": _metric_value(
            raw, "primary", "false_promotion_rate"
        ),
        "effective_false_promotion_rate": _metric_value(
            effective, "primary", "false_promotion_rate"
        ),
        "raw_auprc_stepwise": _metric_value(
            raw,
            "secondary",
            "precision_recall",
            "auprc_stepwise",
        ),
        "effective_auprc_stepwise": _metric_value(
            effective,
            "secondary",
            "precision_recall",
            "auprc_stepwise",
        ),
    }


def validate_contribution(
    manifest_path: Path,
    *,
    root: Path | None = None,
) -> dict[str, Any]:
    """Validate one contribution manifest and its complete run-record file."""

    repository = (root or repository_root()).resolve()
    manifest = load_json(manifest_path)
    if not isinstance(manifest, dict):
        raise DatasetIntegrityError("contribution manifest must be an object")
    validate_with_schema(
        manifest,
        repository / "schemas" / "run-contribution.schema.json",
        str(manifest_path),
    )

    run_path = _resolve_file(
        manifest_path.parent,
        str(manifest["run_file"]),
        "run_file",
    )
    gold_path = _resolve_file(
        repository,
        str(manifest["dataset_gold_file"]),
        "dataset_gold_file",
    )
    dataset_manifest_path = gold_path.parent / "manifest.json"
    if not dataset_manifest_path.is_file():
        raise DatasetIntegrityError("dataset manifest does not exist")
    actual_dataset_hash = sha256_file(dataset_manifest_path)
    if actual_dataset_hash != manifest["dataset_manifest_sha256"]:
        raise DatasetIntegrityError(
            "dataset_manifest_sha256 does not match the selected dataset"
        )

    actual_run_hash = sha256_file(run_path)
    if actual_run_hash != manifest["run_file_sha256"]:
        raise DatasetIntegrityError("run_file_sha256 does not match the run file")

    expected_contribution_id = make_contribution_id(manifest)
    if manifest["contribution_id"] != expected_contribution_id:
        raise DatasetIntegrityError(
            "contribution_id does not match contributor, dataset, run, and identity"
        )

    context = _build_run_context(gold_path)
    bundle = _load_run_bundle(context, run_path)
    if bundle["identity"] != manifest["expected_run"]:
        raise DatasetIntegrityError(
            "expected_run does not match the immutable identity in the run file"
        )

    evaluation = evaluate_run_records(bundle["records"], bootstrap_samples=0)
    run_id = make_run_id(
        bundle["identity"],
        bundle["source_sha256"],
        context.dataset_fingerprint,
    )
    return {
        "status": "PASS",
        "contribution_id": expected_contribution_id,
        "run_id": run_id,
        "contributor": manifest["contributor"],
        "license": manifest["license"],
        "identity": bundle["identity"],
        "dataset": context.dataset_fingerprint,
        "source": {
            "manifest": str(manifest_path),
            "run_file": str(run_path),
            "run_file_sha256": actual_run_hash,
        },
        "reproduction": manifest["reproduction"],
        "summary": _evaluation_summary(evaluation),
    }


def validate_contribution_tree(
    contributions_root: Path,
    *,
    root: Path | None = None,
) -> dict[str, Any]:
    """Validate every contribution.json below one directory."""

    if not contributions_root.is_dir():
        raise DatasetIntegrityError(
            f"contribution root does not exist: {contributions_root}"
        )
    manifests = sorted(contributions_root.rglob(CONTRIBUTION_FILENAME))
    reports = [
        validate_contribution(manifest_path, root=root)
        for manifest_path in manifests
    ]

    contribution_ids = [str(report["contribution_id"]) for report in reports]
    if len(contribution_ids) != len(set(contribution_ids)):
        raise DatasetIntegrityError("duplicate contribution_id in contribution tree")
    run_ids = [str(report["run_id"]) for report in reports]
    if len(run_ids) != len(set(run_ids)):
        raise DatasetIntegrityError("duplicate validated run in contribution tree")

    return {
        "status": "PASS",
        "contributions": len(reports),
        "contribution_ids": contribution_ids,
        "run_ids": run_ids,
        "reports": reports,
    }


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _summary(report: dict[str, Any]) -> dict[str, Any]:
    if "reports" in report:
        return {
            "status": report["status"],
            "contributions": report["contributions"],
            "contribution_ids": report["contribution_ids"],
        }
    return {
        "status": report["status"],
        "contribution_id": report["contribution_id"],
        "run_id": report["run_id"],
        "summary": report["summary"],
    }


def main(argv: list[str] | None = None) -> int:
    """Validate one externally contributed run or the full contribution tree."""

    parser = argparse.ArgumentParser(
        prog="cpb-validate-contribution",
        description=__doc__,
    )
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--manifest", type=Path)
    target.add_argument("--root", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)

    try:
        if args.manifest:
            report = validate_contribution(args.manifest)
        else:
            report = validate_contribution_tree(args.root)
        if args.out:
            _write_json(args.out, report)
            result = {"out": str(args.out), **_summary(report)}
        else:
            result = report
    except (ClaimPromoteBenchError, OSError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
