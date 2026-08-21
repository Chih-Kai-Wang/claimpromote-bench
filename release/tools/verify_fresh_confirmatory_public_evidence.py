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
    SENTINEL,
    THINKING_BLOCK_TYPES,
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
        for key, child in value.items():
            if key in HIDDEN_REASONING_KEYS and child != SENTINEL:
                fail(f"{label}: hidden reasoning survived in {key}")
            if thought_block and key in {"content", "text"} and child != SENTINEL:
                fail(f"{label}: thinking-block content survived in {key}")
            _verify_redaction(child, label)
    elif isinstance(value, list):
        for child in value:
            _verify_redaction(child, label)


def verify_public_release(
    public_root: Path,
    source_analysis_path: Path,
    public_analysis_path: Path,
) -> Json:
    public_root = public_root.resolve()
    receipt_path = public_root / "public-release-redaction-receipt.json"
    receipt = _load(receipt_path)
    observed_receipt_sha = receipt.pop("redaction_receipt_sha256", None)
    expected_receipt_sha = sha256_bytes(canonical_json(receipt).encode("utf-8"))
    if observed_receipt_sha != expected_receipt_sha:
        fail("public-release redaction receipt self-digest mismatch")

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
        "public_analysis_file_sha256": sha256_file(public_analysis_path),
        "public_analysis_sha256": public_analysis["aggregate_sha256"],
        "redaction_receipt_sha256": observed_receipt_sha,
        "schema_version": "1.0.0",
        "scientific_analysis_payload_byte_identical": True,
        "scientific_analysis_payload_sha256": sha256_bytes(
            canonical_json(source_science).encode("utf-8")
        ),
        "source_analysis_file_sha256": sha256_file(source_analysis_path),
        "source_analysis_sha256": source_analysis["aggregate_sha256"],
        "status": "POST_C2_PUBLIC_RELEASE_SCIENTIFIC_EQUIVALENCE_PASS",
    }
    result["equivalence_receipt_sha256"] = sha256_bytes(canonical_json(result).encode("utf-8"))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--public-root", type=Path, required=True)
    parser.add_argument("--source-analysis", type=Path, required=True)
    parser.add_argument("--public-analysis", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = verify_public_release(
        args.public_root,
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
