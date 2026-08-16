"""Dataset loading, schema validation, pair checks, and manifest verification."""

from __future__ import annotations

import json
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .errors import DatasetIntegrityError
from .hashing import canonical_json, sha256_file, verify_artifact
from .oracle import evaluate
from .policy import load_policy

EXPECTED_FAMILY_COUNTS = {
    "DEPENDENCY": 4,
    "NUMERICAL": 4,
    "RUNTIME": 3,
    "STALE_CONTRADICTION": 3,
    "PROVENANCE": 3,
    "FORMAL": 3,
}


def repository_root() -> Path:
    """Return the source-checkout root for the installed editable package."""

    return Path(__file__).resolve().parents[2]


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"), parse_constant=_reject_constant)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise DatasetIntegrityError(f"cannot load JSON {path}: {exc}") from exc


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON number is forbidden: {value}")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load object-only JSON Lines with useful line diagnostics."""

    records: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise DatasetIntegrityError(f"cannot read JSONL {path}: {exc}") from exc
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line, parse_constant=_reject_constant)
        except (json.JSONDecodeError, ValueError) as exc:
            raise DatasetIntegrityError(f"invalid JSON at {path}:{line_number}: {exc}") from exc
        if not isinstance(record, dict):
            raise DatasetIntegrityError(f"record at {path}:{line_number} is not an object")
        records.append(record)
    return records


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    """Write deterministic UTF-8/LF JSON Lines."""

    path.parent.mkdir(parents=True, exist_ok=True)
    content = "".join(f"{canonical_json(record)}\n" for record in records)
    path.write_text(content, encoding="utf-8", newline="\n")


def validate_with_schema(value: Any, schema_path: Path, label: str) -> None:
    """Validate a value against one self-contained 2020-12 schema."""

    schema = load_json(schema_path)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(value), key=lambda error: list(error.absolute_path))
    if errors:
        first = errors[0]
        location = "/".join(str(part) for part in first.absolute_path) or "<root>"
        raise DatasetIntegrityError(f"{label} violates schema at {location}: {first.message}")


def _schema(root: Path, name: str) -> Path:
    return root / "schemas" / name


def compile_author_items(dataset_dir: Path, root: Path | None = None) -> None:
    """Split author records into public inputs and scorer-only gold labels."""

    root = root or repository_root()
    author_items = load_jsonl(dataset_dir / "author-items.jsonl")
    inputs: list[dict[str, Any]] = []
    gold: list[dict[str, Any]] = []
    for item in author_items:
        validate_with_schema(
            item, _schema(root, "benchmark-author-item.schema.json"), str(item.get("id"))
        )
        public = deepcopy(item)
        decision = public.pop("gold")
        inputs.append(public)
        gold.append(
            {
                "id": item["id"],
                "pair_id": item["pair_id"],
                "family": item["family"],
                "decision": decision,
            }
        )
    write_jsonl(dataset_dir / "inputs.jsonl", inputs)
    write_jsonl(dataset_dir / "gold.jsonl", gold)


def verify_manifest(dataset_dir: Path) -> dict[str, Any]:
    """Verify all committed files named by the manifest."""

    manifest_path = dataset_dir / "manifest.json"
    manifest = load_json(manifest_path)
    if not isinstance(manifest, dict):
        raise DatasetIntegrityError("manifest must be an object")
    files = manifest.get("files")
    if not isinstance(files, dict):
        raise DatasetIntegrityError("manifest.files must be an object")
    for relative, expected in sorted(files.items()):
        path = (dataset_dir / str(relative)).resolve()
        try:
            path.relative_to(dataset_dir.resolve())
        except ValueError as exc:
            raise DatasetIntegrityError(f"manifest path escapes dataset: {relative}") from exc
        if not path.is_file():
            raise DatasetIntegrityError(f"manifest file is missing: {relative}")
        actual = sha256_file(path)
        if actual != expected:
            raise DatasetIntegrityError(
                f"manifest mismatch for {relative}: expected {expected}, got {actual}"
            )
    return manifest


def _walk_diff(left: Any, right: Any, pointer: str = "") -> set[str]:
    if type(left) is not type(right):
        return {pointer or "/"}
    if isinstance(left, dict):
        paths: set[str] = set()
        for key in sorted(set(left) | set(right)):
            child = f"{pointer}/{key}"
            if key not in left or key not in right:
                paths.add(child)
            else:
                paths |= _walk_diff(left[key], right[key], child)
        return paths
    if isinstance(left, list):
        paths = set()
        if len(left) != len(right):
            paths.add(f"{pointer}/length")
        for index, (left_value, right_value) in enumerate(zip(left, right, strict=False)):
            paths |= _walk_diff(left_value, right_value, f"{pointer}/{index}")
        return paths
    return set() if left == right else {pointer or "/"}


def check_pairs(dataset_dir: Path) -> dict[str, int]:
    """Check controlled-pair invariants without consulting a model."""

    items = {str(item["id"]): item for item in load_jsonl(dataset_dir / "author-items.jsonl")}
    pairs = load_json(dataset_dir / "pairs.json")
    if not isinstance(pairs, list) or len(pairs) != 20:
        raise DatasetIntegrityError("alpha must contain exactly 20 pair descriptors")
    family_counts: Counter[str] = Counter()
    invalid_sides: Counter[str] = Counter()
    seen_members: set[str] = set()
    for pair in pairs:
        family_counts[str(pair["family"])] += 1
        member_ids = [str(value) for value in pair["member_ids"]]
        if len(member_ids) != 2 or len(set(member_ids)) != 2:
            raise DatasetIntegrityError(f"{pair['pair_id']} must name two unique members")
        if not all(member_id in items for member_id in member_ids):
            raise DatasetIntegrityError(f"{pair['pair_id']} references an unknown item")
        if seen_members & set(member_ids):
            raise DatasetIntegrityError(f"an item appears in multiple pairs: {pair['pair_id']}")
        seen_members.update(member_ids)
        invalid_id = str(pair["invalid_id"])
        valid_id = str(pair["valid_id"])
        if {invalid_id, valid_id} != set(member_ids):
            raise DatasetIntegrityError(f"{pair['pair_id']} invalid/valid members are inconsistent")
        invalid_sides[invalid_id.rsplit("-", 1)[-1].upper()] += 1

        left = deepcopy(items[member_ids[0]])
        right = deepcopy(items[member_ids[1]])
        for value in (left, right):
            value.pop("id", None)
            value.pop("gold", None)
        differences = _walk_diff(left, right)
        controlled = set(str(value) for value in pair["controlled_json_pointers"])
        unexpected = {
            path
            for path in differences
            if not any(path == allowed or path.startswith(f"{allowed}/") for allowed in controlled)
        }
        if unexpected:
            raise DatasetIntegrityError(
                f"{pair['pair_id']} changes uncontrolled fields: {sorted(unexpected)}"
            )
        if not differences:
            raise DatasetIntegrityError(f"{pair['pair_id']} has no counterfactual difference")
        for field in ("claim_text", "current_state", "requested_transition"):
            if left[field] != right[field]:
                raise DatasetIntegrityError(f"{pair['pair_id']} changes invariant field {field}")
        invalid_action = items[invalid_id]["gold"]["action"]
        valid_action = items[valid_id]["gold"]["action"]
        if invalid_action == "ALLOW" or valid_action != "ALLOW":
            raise DatasetIntegrityError(f"{pair['pair_id']} is not invalid-to-valid")

    if family_counts != Counter(EXPECTED_FAMILY_COUNTS):
        raise DatasetIntegrityError(f"unexpected family distribution: {dict(family_counts)}")
    if invalid_sides != Counter({"A": 10, "B": 10}):
        raise DatasetIntegrityError(f"invalid sides are not balanced: {dict(invalid_sides)}")
    if seen_members != set(items) or len(items) != 40:
        raise DatasetIntegrityError("alpha must contain 40 items, each in exactly one pair")
    return dict(sorted(family_counts.items()))


def validate_dataset(dataset_dir: Path, root: Path | None = None) -> dict[str, Any]:
    """Run schemas, integrity, pairs, artifact bindings, and oracle/gold checks."""

    root = root or repository_root()
    manifest = verify_manifest(dataset_dir)
    inputs = load_jsonl(dataset_dir / "inputs.jsonl")
    gold_records = load_jsonl(dataset_dir / "gold.jsonl")
    if len(inputs) != 40 or len(gold_records) != 40:
        raise DatasetIntegrityError("alpha inputs and gold must each contain 40 records")
    input_ids = [str(item["id"]) for item in inputs]
    if len(input_ids) != len(set(input_ids)):
        raise DatasetIntegrityError("input IDs must be unique")
    gold_by_id = {str(record["id"]): record for record in gold_records}
    if set(input_ids) != set(gold_by_id):
        raise DatasetIntegrityError("input and gold IDs differ")

    policy_path = root / "policies" / str(manifest["policy_file"])
    if sha256_file(policy_path) != manifest.get("policy_sha256"):
        raise DatasetIntegrityError("loaded policy does not match manifest policy_sha256")
    policy = load_policy(policy_path)
    if policy.get("evaluation_time") != manifest.get("evaluation_time"):
        raise DatasetIntegrityError("policy and manifest evaluation_time differ")
    schema_hashes = manifest.get("schema_sha256")
    if not isinstance(schema_hashes, dict):
        raise DatasetIntegrityError("manifest.schema_sha256 must bind the public schemas")
    for name, expected in sorted(schema_hashes.items()):
        if sha256_file(root / "schemas" / str(name)) != expected:
            raise DatasetIntegrityError(f"schema does not match manifest: {name}")

    from .executable import verify_dataset_artifact
    from .formal import verify_formal_artifact_binding

    executable_artifacts: set[str] = set()
    executable_evidence = 0
    formal_artifacts: set[str] = set()
    formal_evidence = 0
    for item in inputs:
        validate_with_schema(item, _schema(root, "benchmark-input.schema.json"), str(item["id"]))
        gold_record = gold_by_id[str(item["id"])]
        validate_with_schema(gold_record, _schema(root, "gold-label.schema.json"), str(item["id"]))
        require_scope_match = gold_record["decision"]["action"] == "ALLOW"
        item_has_executable = False
        item_has_formal = False
        for evidence in item["evidence"]:
            verify_artifact(dataset_dir, evidence)
            artifact_path = str(evidence["artifact_path"])
            if evidence["type"] == "COMPUTATION" and artifact_path.endswith(".json"):
                verify_dataset_artifact(
                    dataset_dir,
                    evidence,
                    require_scope_match=require_scope_match,
                )
                executable_artifacts.add(artifact_path)
                executable_evidence += 1
                item_has_executable = True
            if item["family"] == "FORMAL" and evidence["type"] == "FORMAL_CERTIFICATE":
                verify_formal_artifact_binding(
                    dataset_dir,
                    item,
                    evidence,
                    require_scope_match=require_scope_match,
                )
                formal_artifacts.add(artifact_path)
                formal_evidence += 1
                item_has_formal = True
        if item["family"] == "NUMERICAL" and not item_has_executable:
            raise DatasetIntegrityError(
                f"numerical alpha item lacks executable computation evidence: {item['id']}"
            )
        if item["family"] == "FORMAL" and not item_has_formal:
            raise DatasetIntegrityError(
                f"formal alpha item lacks a bound Lean certificate: {item['id']}"
            )

        actual = evaluate(item, policy, str(manifest["evaluation_time"]))
        expected = gold_record["decision"]
        if canonical_json(actual) != canonical_json(expected):
            raise DatasetIntegrityError(
                f"oracle/gold mismatch for {item['id']}: {actual} != {expected}"
            )
    distribution = check_pairs(dataset_dir)
    return {
        "instances": len(inputs),
        "pairs": 20,
        "families": distribution,
        "evaluation_time": manifest["evaluation_time"],
        "executable_computation_artifacts": len(executable_artifacts),
        "executable_computation_evidence": executable_evidence,
        "formal_lean_artifacts": len(formal_artifacts),
        "formal_lean_evidence": formal_evidence,
        "model_experiments": "PENDING",
    }
