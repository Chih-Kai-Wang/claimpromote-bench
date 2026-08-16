"""Prepare, initialize, and validate blinded independent-review packages."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import secrets
import sys
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

from .dataset import (
    load_json,
    load_jsonl,
    repository_root,
    validate_dataset,
    validate_with_schema,
)
from .errors import ClaimPromoteBenchError, DatasetIntegrityError
from .hashing import canonical_json, sha256_bytes, sha256_file
from .policy import load_policy

SCHEMA_VERSION = "1.0.0"
BLINDING_METHOD = "HMAC-SHA256-128"
PACKET_FILENAME = "packet.jsonl"
MANIFEST_FILENAME = "packet-manifest.json"
PRIVATE_KEY_FILENAME = "private-key.json"
SUBMISSIONS_DIRECTORY = "submissions"
HIDDEN_PACKET_FIELDS = {"id", "pair_id", "split", "family", "gold"}
ACTIONS = {"ALLOW", "HOLD", "DEMOTE", "ESCALATE"}


def _schema(name: str) -> Path:
    return repository_root() / "schemas" / name


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _write_jsonl(path: Path, values: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(f"{canonical_json(value)}\n" for value in values),
        encoding="utf-8",
        newline="\n",
    )


def _safe_child(root: Path, relative: str, label: str) -> Path:
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise DatasetIntegrityError(f"{label} path escapes its package: {relative}") from exc
    return candidate


def _review_payload(item: dict[str, Any]) -> dict[str, Any]:
    payload = deepcopy(item)
    for field in HIDDEN_PACKET_FIELDS:
        payload.pop(field, None)
    return payload


def _blind_id(secret: bytes, item_id: str) -> str:
    digest = hmac.new(secret, item_id.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"review-{digest[:32]}"


def _packet_identity(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        key: manifest[key]
        for key in (
            "schema_version",
            "dataset_manifest_sha256",
            "policy_sha256",
            "evaluation_time",
            "item_count",
            "packet_file",
            "packet_sha256",
            "blinding_method",
        )
    }


def _load_packet_manifest(package_dir: Path) -> dict[str, Any]:
    manifest_path = package_dir / MANIFEST_FILENAME
    manifest = load_json(manifest_path)
    if not isinstance(manifest, dict):
        raise DatasetIntegrityError("review packet manifest must be an object")
    validate_with_schema(
        manifest,
        _schema("review-packet-manifest.schema.json"),
        str(manifest_path),
    )
    expected_id = sha256_bytes(canonical_json(_packet_identity(manifest)).encode("utf-8"))
    if manifest["packet_id"] != expected_id:
        raise DatasetIntegrityError("review packet_id does not match its immutable identity")
    return manifest


def _load_packet_records(
    package_dir: Path,
    manifest: dict[str, Any],
) -> list[dict[str, Any]]:
    packet_path = _safe_child(
        package_dir,
        str(manifest["packet_file"]),
        "review packet",
    )
    if not packet_path.is_file():
        raise DatasetIntegrityError("review packet file is missing")
    if sha256_file(packet_path) != manifest["packet_sha256"]:
        raise DatasetIntegrityError("review packet hash does not match its manifest")
    records = load_jsonl(packet_path)
    if len(records) != manifest["item_count"]:
        raise DatasetIntegrityError("review packet item count does not match its manifest")
    seen: set[str] = set()
    for record in records:
        validate_with_schema(
            record,
            _schema("review-packet-item.schema.json"),
            str(record.get("review_item_id", "review-item")),
        )
        review_item_id = str(record["review_item_id"])
        if review_item_id in seen:
            raise DatasetIntegrityError(f"duplicate review_item_id: {review_item_id}")
        seen.add(review_item_id)
        payload = record["payload"]
        if not isinstance(payload, dict):
            raise DatasetIntegrityError("review packet payload must be an object")
        leaked = HIDDEN_PACKET_FIELDS & set(payload)
        if leaked:
            raise DatasetIntegrityError(f"review packet exposes hidden fields: {sorted(leaked)}")
    return records


def _load_private_key(package_dir: Path) -> dict[str, Any]:
    key_path = package_dir / PRIVATE_KEY_FILENAME
    key = load_json(key_path)
    if not isinstance(key, dict):
        raise DatasetIntegrityError("review private key must be an object")
    validate_with_schema(
        key,
        _schema("review-private-key.schema.json"),
        str(key_path),
    )
    return key


def _dataset_context(dataset_dir: Path) -> tuple[dict[str, Any], list[dict[str, Any]], Path]:
    validate_dataset(dataset_dir)
    manifest = load_json(dataset_dir / "manifest.json")
    if not isinstance(manifest, dict):
        raise DatasetIntegrityError("dataset manifest must be an object")
    inputs = load_jsonl(dataset_dir / "inputs.jsonl")
    policy_path = repository_root() / "policies" / str(manifest["policy_file"])
    return manifest, inputs, policy_path


def prepare_review_package(
    dataset_dir: Path,
    out_dir: Path,
    *,
    secret: bytes | None = None,
) -> dict[str, Any]:
    """Create a blinded packet and private mapping in a new local directory."""

    if out_dir.exists() and any(out_dir.iterdir()):
        raise DatasetIntegrityError(f"review output directory is not empty: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)

    dataset_manifest, inputs, policy_path = _dataset_context(dataset_dir)
    active_secret = secret or secrets.token_bytes(32)
    if len(active_secret) != 32:
        raise DatasetIntegrityError("review blinding secret must contain exactly 32 bytes")

    mapping = [
        {
            "review_item_id": _blind_id(active_secret, str(item["id"])),
            "item_id": str(item["id"]),
        }
        for item in inputs
    ]
    mapping.sort(key=lambda value: value["review_item_id"])
    inputs_by_id = {str(item["id"]): item for item in inputs}
    packet = [
        {
            "review_item_id": value["review_item_id"],
            "payload": _review_payload(inputs_by_id[value["item_id"]]),
        }
        for value in mapping
    ]
    packet_path = out_dir / PACKET_FILENAME
    _write_jsonl(packet_path, packet)

    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "dataset_manifest_sha256": sha256_file(dataset_dir / "manifest.json"),
        "policy_sha256": sha256_file(policy_path),
        "evaluation_time": dataset_manifest["evaluation_time"],
        "item_count": len(packet),
        "packet_file": PACKET_FILENAME,
        "packet_sha256": sha256_file(packet_path),
        "blinding_method": BLINDING_METHOD,
    }
    manifest["packet_id"] = sha256_bytes(canonical_json(_packet_identity(manifest)).encode("utf-8"))
    _write_json(out_dir / MANIFEST_FILENAME, manifest)

    key = {
        "schema_version": SCHEMA_VERSION,
        "packet_id": manifest["packet_id"],
        "packet_sha256": manifest["packet_sha256"],
        "dataset_manifest_sha256": manifest["dataset_manifest_sha256"],
        "policy_sha256": manifest["policy_sha256"],
        "blinding_secret_hex": active_secret.hex(),
        "mapping": mapping,
    }
    _write_json(out_dir / PRIVATE_KEY_FILENAME, key)
    (out_dir / SUBMISSIONS_DIRECTORY).mkdir(exist_ok=True)

    validate_review_package_material(dataset_dir, out_dir)
    return {
        "status": "PREPARED",
        "packet_id": manifest["packet_id"],
        "items": len(packet),
        "out": str(out_dir),
    }


def validate_review_package_material(
    dataset_dir: Path,
    package_dir: Path,
) -> dict[str, Any]:
    """Validate packet, manifest, private mapping, and dataset binding."""

    dataset_manifest, inputs, policy_path = _dataset_context(dataset_dir)
    manifest = _load_packet_manifest(package_dir)
    records = _load_packet_records(package_dir, manifest)
    key = _load_private_key(package_dir)

    expected_dataset_hash = sha256_file(dataset_dir / "manifest.json")
    expected_policy_hash = sha256_file(policy_path)
    for label, expected in (
        ("dataset_manifest_sha256", expected_dataset_hash),
        ("policy_sha256", expected_policy_hash),
    ):
        if manifest[label] != expected or key[label] != expected:
            raise DatasetIntegrityError(f"review package {label} is stale")
    if manifest["evaluation_time"] != dataset_manifest["evaluation_time"]:
        raise DatasetIntegrityError("review packet evaluation_time is stale")
    for label in ("packet_id", "packet_sha256"):
        if key[label] != manifest[label]:
            raise DatasetIntegrityError(f"review private key {label} is stale")

    secret = bytes.fromhex(str(key["blinding_secret_hex"]))
    mapping = key["mapping"]
    if not isinstance(mapping, list):
        raise DatasetIntegrityError("review private mapping must be an array")
    review_ids: set[str] = set()
    item_ids: set[str] = set()
    mapping_by_review_id: dict[str, str] = {}
    for value in mapping:
        if not isinstance(value, dict):
            raise DatasetIntegrityError("review private mapping entry must be an object")
        review_item_id = str(value["review_item_id"])
        item_id = str(value["item_id"])
        if review_item_id in review_ids or item_id in item_ids:
            raise DatasetIntegrityError("review private mapping contains a duplicate")
        if _blind_id(secret, item_id) != review_item_id:
            raise DatasetIntegrityError("review private mapping fails its HMAC binding")
        review_ids.add(review_item_id)
        item_ids.add(item_id)
        mapping_by_review_id[review_item_id] = item_id

    expected_items = {str(item["id"]): item for item in inputs}
    if item_ids != set(expected_items):
        raise DatasetIntegrityError("review private mapping does not cover the dataset exactly")
    records_by_id = {str(record["review_item_id"]): record for record in records}
    if review_ids != set(records_by_id):
        raise DatasetIntegrityError("review packet and private mapping IDs differ")
    for review_item_id, item_id in mapping_by_review_id.items():
        payload = records_by_id[review_item_id]["payload"]
        if canonical_json(payload) != canonical_json(_review_payload(expected_items[item_id])):
            raise DatasetIntegrityError("review packet payload differs from the bound dataset")

    return {
        "status": "PASS",
        "packet_id": manifest["packet_id"],
        "items": len(records),
        "dataset_manifest_sha256": expected_dataset_hash,
        "policy_sha256": expected_policy_hash,
    }


def initialize_submission(
    package_dir: Path,
    reviewer_id: str,
    out_path: Path,
) -> dict[str, Any]:
    """Create an unbiased, deliberately incomplete review-submission draft."""

    manifest = _load_packet_manifest(package_dir)
    records = _load_packet_records(package_dir, manifest)
    draft = {
        "schema_version": SCHEMA_VERSION,
        "reviewer_id": reviewer_id,
        "packet_id": manifest["packet_id"],
        "packet_sha256": manifest["packet_sha256"],
        "policy_sha256": manifest["policy_sha256"],
        "completed_at": None,
        "attestation": {
            "independent": False,
            "no_gold_access": False,
            "no_model_outputs": False,
            "no_collaboration": False,
            "public_release_after_unblinding": False,
        },
        "decisions": [
            {
                "review_item_id": record["review_item_id"],
                "action": None,
                "reason_codes": [],
                "confidence": None,
                "rationale": "",
            }
            for record in records
        ],
    }
    _write_json(out_path, draft)
    return {
        "status": "DRAFT_CREATED",
        "reviewer_id": reviewer_id,
        "items": len(records),
        "out": str(out_path),
    }


def _parse_completed_at(value: str) -> None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DatasetIntegrityError("review completed_at is not a valid date-time") from exc
    if parsed.tzinfo is None:
        raise DatasetIntegrityError("review completed_at must include a timezone")


def _allowed_reason_codes(policy_path: Path) -> set[str]:
    policy = load_policy(policy_path)
    reasons = policy.get("reason_precedence")
    if not isinstance(reasons, list) or not all(isinstance(value, str) for value in reasons):
        raise DatasetIntegrityError("policy reason vocabulary is malformed")
    return set(reasons)


def validate_review_submission(
    dataset_dir: Path,
    package_dir: Path,
    submission_path: Path,
) -> dict[str, Any]:
    """Validate one completed reviewer submission against its blinded packet."""

    material = validate_review_package_material(dataset_dir, package_dir)
    manifest = _load_packet_manifest(package_dir)
    records = _load_packet_records(package_dir, manifest)
    submission = load_json(submission_path)
    if not isinstance(submission, dict):
        raise DatasetIntegrityError("review submission must be an object")
    validate_with_schema(
        submission,
        _schema("review-submission.schema.json"),
        str(submission_path),
    )
    for label in ("packet_id", "packet_sha256", "policy_sha256"):
        if submission[label] != manifest[label]:
            raise DatasetIntegrityError(f"review submission {label} is stale")
    _parse_completed_at(str(submission["completed_at"]))

    decisions = submission["decisions"]
    if not isinstance(decisions, list):
        raise DatasetIntegrityError("review submission decisions must be an array")
    expected_ids = {str(record["review_item_id"]) for record in records}
    observed_ids: set[str] = set()
    allowed_reasons = _allowed_reason_codes(
        repository_root()
        / "policies"
        / str(load_json(dataset_dir / "manifest.json")["policy_file"])
    )
    for decision in decisions:
        if not isinstance(decision, dict):
            raise DatasetIntegrityError("review decision must be an object")
        review_item_id = str(decision["review_item_id"])
        if review_item_id in observed_ids:
            raise DatasetIntegrityError(f"duplicate review decision: {review_item_id}")
        observed_ids.add(review_item_id)
        action = str(decision["action"])
        reason_codes = decision["reason_codes"]
        if action not in ACTIONS:
            raise DatasetIntegrityError(f"unknown review action: {action}")
        if not isinstance(reason_codes, list):
            raise DatasetIntegrityError("review reason_codes must be an array")
        unknown = set(str(value) for value in reason_codes) - allowed_reasons
        if unknown:
            raise DatasetIntegrityError(f"unknown review reason codes: {sorted(unknown)}")
        if action == "ALLOW" and reason_codes != ["POLICY_SATISFIED"]:
            raise DatasetIntegrityError("ALLOW review decisions require POLICY_SATISFIED only")
        if action != "ALLOW" and "POLICY_SATISFIED" in reason_codes:
            raise DatasetIntegrityError("non-ALLOW review decisions cannot use POLICY_SATISFIED")
    if observed_ids != expected_ids:
        missing = sorted(expected_ids - observed_ids)
        extra = sorted(observed_ids - expected_ids)
        raise DatasetIntegrityError(
            f"review submission coverage mismatch; missing={missing}, extra={extra}"
        )

    return {
        "status": "PASS",
        "reviewer_id": submission["reviewer_id"],
        "packet_id": material["packet_id"],
        "decisions": len(decisions),
        "submission_sha256": sha256_file(submission_path),
    }


def validate_review_package(
    dataset_dir: Path,
    package_dir: Path,
) -> dict[str, Any]:
    """Validate one completed, unblinded package and all public submissions."""

    material = validate_review_package_material(dataset_dir, package_dir)
    submissions_dir = package_dir / SUBMISSIONS_DIRECTORY
    if not submissions_dir.is_dir():
        raise DatasetIntegrityError("review package submissions directory is missing")
    paths = sorted(submissions_dir.glob("*.json"))
    if not paths:
        raise DatasetIntegrityError("completed review package has no submissions")
    reports = [validate_review_submission(dataset_dir, package_dir, path) for path in paths]
    reviewer_ids = [str(report["reviewer_id"]) for report in reports]
    if len(reviewer_ids) != len(set(reviewer_ids)):
        raise DatasetIntegrityError("review package contains duplicate reviewer IDs")
    return {
        "status": "PASS",
        "packet_id": material["packet_id"],
        "items": material["items"],
        "reviewers": len(reports),
        "submissions": reports,
    }


def validate_review_root(
    dataset_dir: Path,
    reviews_root: Path,
    *,
    allow_empty: bool,
) -> dict[str, Any]:
    """Validate every completed review package published beneath one root."""

    if not reviews_root.is_dir():
        raise DatasetIntegrityError(f"review root does not exist: {reviews_root}")
    manifests = sorted(reviews_root.glob(f"*/{MANIFEST_FILENAME}"))
    if not manifests:
        if not allow_empty:
            raise DatasetIntegrityError("review root contains no completed package")
        return {"status": "PENDING", "packages": 0, "reviewers": 0}
    reports = [validate_review_package(dataset_dir, path.parent) for path in manifests]
    packet_ids = [str(report["packet_id"]) for report in reports]
    if len(packet_ids) != len(set(packet_ids)):
        raise DatasetIntegrityError("review root contains duplicate packet IDs")
    return {
        "status": "PASS",
        "packages": len(reports),
        "reviewers": sum(int(report["reviewers"]) for report in reports),
        "reports": reports,
    }


def _read_secret(path: Path | None) -> bytes | None:
    if path is None:
        return None
    try:
        value = path.read_text(encoding="utf-8").strip()
        secret = bytes.fromhex(value)
    except (OSError, ValueError) as exc:
        raise DatasetIntegrityError(
            "secret file must contain exactly 64 hexadecimal digits"
        ) from exc
    if len(secret) != 32:
        raise DatasetIntegrityError("secret file must contain exactly 64 hexadecimal digits")
    return secret


def _emit(report: dict[str, Any], out_path: Path | None) -> None:
    if out_path is not None:
        _write_json(out_path, report)
        summary = {
            key: value for key, value in report.items() if key not in {"reports", "submissions"}
        }
        summary["out"] = str(out_path)
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    """Run the blinded independent-review package workflow."""

    parser = argparse.ArgumentParser(prog="cpb-review", description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("--dataset", type=Path, default=Path("data/alpha"))
    prepare.add_argument("--out", type=Path, required=True)
    prepare.add_argument("--secret-file", type=Path)

    initialize = subparsers.add_parser("init-submission")
    initialize.add_argument("--package", type=Path, required=True)
    initialize.add_argument("--reviewer-id", required=True)
    initialize.add_argument("--out", type=Path, required=True)

    validate_submission_parser = subparsers.add_parser("validate-submission")
    validate_submission_parser.add_argument("--dataset", type=Path, default=Path("data/alpha"))
    validate_submission_parser.add_argument("--package", type=Path, required=True)
    validate_submission_parser.add_argument("--submission", type=Path, required=True)
    validate_submission_parser.add_argument("--out", type=Path)

    validate_package_parser = subparsers.add_parser("validate-package")
    validate_package_parser.add_argument("--dataset", type=Path, default=Path("data/alpha"))
    validate_package_parser.add_argument("--package", type=Path, required=True)
    validate_package_parser.add_argument("--out", type=Path)

    validate_root_parser = subparsers.add_parser("validate-root")
    validate_root_parser.add_argument("--dataset", type=Path, default=Path("data/alpha"))
    validate_root_parser.add_argument("--root", type=Path, default=Path("reviews"))
    validate_root_parser.add_argument("--allow-empty", action="store_true")
    validate_root_parser.add_argument("--out", type=Path)

    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            report = prepare_review_package(
                args.dataset,
                args.out,
                secret=_read_secret(args.secret_file),
            )
            _emit(report, None)
        elif args.command == "init-submission":
            report = initialize_submission(args.package, args.reviewer_id, args.out)
            _emit(report, None)
        elif args.command == "validate-submission":
            report = validate_review_submission(args.dataset, args.package, args.submission)
            _emit(report, args.out)
        elif args.command == "validate-package":
            report = validate_review_package(args.dataset, args.package)
            _emit(report, args.out)
        elif args.command == "validate-root":
            report = validate_review_root(
                args.dataset,
                args.root,
                allow_empty=bool(args.allow_empty),
            )
            _emit(report, args.out)
        else:
            raise DatasetIntegrityError(f"unknown review command: {args.command}")
    except (ClaimPromoteBenchError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
