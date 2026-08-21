"""Verify redacted confirmatory evidence and invariant scientific results."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file
from release.tools.build_fresh_confirmatory_public_evidence import (
    HIDDEN_REASONING_KEYS,
    THINKING_BLOCK_TYPES,
    RedactionStats,
    _load_jsonl,
    _scientific_projection,
    derive_public_provider_envelope,
    write_json,
)

Json = dict[str, Any]


def fail(message: str) -> None:
    raise ValueError(message)


def _load(path: Path) -> Json:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        fail(f"JSON root is not an object: {path}")
    return value


def _scientific_analysis(value: Json) -> Json:
    projected = copy.deepcopy(value)
    projected.pop("aggregate_sha256", None)
    scores = projected.get("scores")
    if isinstance(scores, dict):
        for score in scores.values():
            if isinstance(score, dict):
                score.pop("run_sha256", None)
    return projected


def _verify_redaction(value: Any, label: str) -> None:
    if isinstance(value, dict):
        block_type = str(value.get("type", "")).lower()
        thought_block = value.get("thought") is True or block_type in THINKING_BLOCK_TYPES
        if thought_block:
            fail(f"{label}: thinking content block survived")
        for key, child in value.items():
            if key in HIDDEN_REASONING_KEYS:
                fail(f"{label}: hidden-reasoning field survived in {key}")
            _verify_redaction(child, label)
    elif isinstance(value, list):
        for child in value:
            _verify_redaction(child, label)


def _verify_source_to_derived_rows(
    source_root: Path,
    public_root: Path,
    receipt: Json,
) -> None:
    row_map_path = public_root / receipt["row_hash_map"]["path"]
    if sha256_file(row_map_path) != receipt["row_hash_map"]["file_sha256"]:
        fail("public-release row-hash map digest mismatch")
    row_map = [row for _, row in _load_jsonl(row_map_path)]
    if len(row_map) != receipt["row_hash_map"]["rows"]:
        fail("public-release row-hash map count mismatch")

    entries_by_path: dict[str, list[Json]] = {}
    for entry in row_map:
        entries_by_path.setdefault(str(entry["relative_path"]), []).append(entry)

    verified_rows = 0
    for transformed in receipt["transformed_files"]:
        relative = str(transformed["relative_path"])
        source_rows = _load_jsonl(source_root / relative)
        public_rows = _load_jsonl(public_root / relative)
        entries = entries_by_path.pop(relative, [])
        if not (len(source_rows) == len(public_rows) == len(entries)):
            fail(f"source/derived row count mismatch: {relative}")
        for (source_raw, source), (public_raw, public), entry in zip(
            source_rows,
            public_rows,
            entries,
            strict=True,
        ):
            if sha256_bytes(source_raw) != entry["source_row_sha256"]:
                fail(f"source row digest mismatch: {relative}")
            if sha256_bytes(public_raw) != entry["derived_row_sha256"]:
                fail(f"derived row digest mismatch: {relative}")
            if source.get("sanitized_provider_envelope_sha256") != entry.get(
                "source_envelope_sha256"
            ):
                fail(f"source envelope digest mismatch: {relative}")
            if public.get("sanitized_provider_envelope_sha256") != entry.get(
                "derived_envelope_sha256"
            ):
                fail(f"derived envelope digest mismatch: {relative}")
            if _scientific_projection(source) != _scientific_projection(public):
                fail(f"publication transform changed a scientific row field: {relative}")
            if entry.get("scientific_fields_unchanged") is not True:
                fail(f"row map does not attest unchanged scientific fields: {relative}")
            envelope = public.get("sanitized_provider_envelope")
            if envelope is not None:
                stats = RedactionStats()
                if derive_public_provider_envelope(envelope, stats) != envelope:
                    fail(f"public provider envelope is not canonical: {relative}")
                if stats.changed:
                    fail(f"public provider envelope still needs redaction: {relative}")
            verified_rows += 1
    if entries_by_path:
        fail(f"row-hash map names unknown transformed files: {sorted(entries_by_path)}")
    if verified_rows != receipt["row_hash_map"]["rows"]:
        fail("not every row-hash entry was independently verified")

    for relative, expected in receipt["source_files_sha256"].items():
        path = source_root / relative
        if not path.is_file() or sha256_file(path) != expected:
            fail(f"source reviewer-evidence file digest mismatch: {relative}")

    c2 = receipt["source_c2_receipt"]
    c2_path = source_root / c2["path"]
    if not c2_path.is_file() or sha256_file(c2_path) != c2["file_sha256"]:
        fail("source C2 receipt file digest mismatch")


def verify_public_release(
    public_root: Path,
    source_root: Path,
    source_analysis_path: Path,
    public_analysis_path: Path,
) -> Json:
    public_root = public_root.resolve()
    source_root = source_root.resolve()
    receipt_path = public_root / "public-release-redaction-receipt.json"
    receipt = _load(receipt_path)
    observed_receipt_sha = receipt.pop("redaction_receipt_sha256", None)
    expected_receipt_sha = sha256_bytes(canonical_json(receipt).encode("utf-8"))
    if observed_receipt_sha != expected_receipt_sha:
        fail("public-release redaction receipt self-digest mismatch")

    _verify_source_to_derived_rows(source_root, public_root, receipt)

    for relative, expected in receipt["derived_files_sha256"].items():
        path = public_root / relative
        if not path.is_file() or sha256_file(path) != expected:
            fail(f"public-release file digest mismatch: {relative}")

    for path in sorted(public_root.rglob("*.json")):
        _verify_redaction(
            json.loads(path.read_text(encoding="utf-8")),
            path.relative_to(public_root).as_posix(),
        )
    for path in sorted(public_root.rglob("*.jsonl")):
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line:
                continue
            _verify_redaction(
                json.loads(line),
                f"{path.relative_to(public_root).as_posix()}:{line_number}",
            )

    source_analysis = _load(source_analysis_path)
    public_analysis = _load(public_analysis_path)
    source_science = _scientific_analysis(source_analysis)
    public_science = _scientific_analysis(public_analysis)
    if source_science != public_science:
        fail("public redaction changed the confirmatory scientific analysis payload")

    result: Json = {
        "hidden_reasoning_present_in_public_release": False,
        "public_provider_envelopes_allowlisted": True,
        "public_analysis_file_sha256": sha256_file(public_analysis_path),
        "public_analysis_sha256": public_analysis["aggregate_sha256"],
        "redaction_receipt_sha256": observed_receipt_sha,
        "redaction_rule_sha256": receipt["redaction_rule_sha256"],
        "schema_version": "1.1.0",
        "scientific_analysis_payload_byte_identical": True,
        "scientific_analysis_payload_sha256": sha256_bytes(
            canonical_json(source_science).encode("utf-8")
        ),
        "source_analysis_file_sha256": sha256_file(source_analysis_path),
        "source_analysis_sha256": source_analysis["aggregate_sha256"],
        "source_c2_receipt_self_digest": receipt["source_c2_receipt"]["self_digest"],
        "source_to_derived_row_hashes_verified": True,
        "status": "POST_C2_PUBLIC_RELEASE_SCIENTIFIC_EQUIVALENCE_PASS",
    }
    result["equivalence_receipt_sha256"] = sha256_bytes(canonical_json(result).encode("utf-8"))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--public-root", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--source-analysis", type=Path, required=True)
    parser.add_argument("--public-analysis", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = verify_public_release(
        args.public_root,
        args.source_root,
        args.source_analysis.resolve(),
        args.public_analysis.resolve(),
    )
    write_json(args.out.resolve(), result)
    print(
        canonical_json(
            {
                "equivalence_receipt_sha256": result["equivalence_receipt_sha256"],
                "status": result["status"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
