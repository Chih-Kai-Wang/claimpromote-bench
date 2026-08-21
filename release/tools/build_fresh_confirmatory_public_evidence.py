"""Derive a public-safe post-C2 copy of fresh confirmatory evidence.

The scored artifacts remain immutable.  This publication-only transform removes
provider-returned hidden reasoning while preserving every field used for scoring.
"""

from __future__ import annotations

import argparse
import copy
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file

Json = dict[str, Any]

SENTINEL = "<REDACTED_HIDDEN_REASONING>"
HIDDEN_REASONING_KEYS = {
    "reasoning_content",
    "thinking",
    "thinking_content",
    "thoughts",
}
THINKING_BLOCK_TYPES = {"reasoning", "thinking"}
SCORING_INDEPENDENT_FIELDS = {
    "pre_redaction_sanitized_provider_envelope_sha256",
    "public_release_redaction",
    "sanitized_provider_envelope",
    "sanitized_provider_envelope_sha256",
}


def fail(message: str) -> None:
    raise ValueError(message)


def write_json(path: Path, value: Json) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def write_jsonl(path: Path, rows: list[Json]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(canonical_json(row))
            handle.write("\n")


@dataclass
class RedactionStats:
    fields: int = 0
    utf8_bytes: int = 0

    def record(self, value: Any) -> None:
        self.fields += 1
        self.utf8_bytes += len(canonical_json(value).encode("utf-8"))


def redact_hidden_reasoning(value: Any, stats: RedactionStats) -> Any:
    """Recursively replace reasoning payloads with one fixed public sentinel."""

    if isinstance(value, dict):
        block_type = str(value.get("type", "")).lower()
        thought_block = value.get("thought") is True or block_type in THINKING_BLOCK_TYPES
        redacted: Json = {}
        for key, child in value.items():
            if key in HIDDEN_REASONING_KEYS or (thought_block and key in {"content", "text"}):
                if child != SENTINEL:
                    stats.record(child)
                redacted[key] = SENTINEL
            else:
                redacted[key] = redact_hidden_reasoning(child, stats)
        return redacted
    if isinstance(value, list):
        return [redact_hidden_reasoning(child, stats) for child in value]
    return value


def _scientific_projection(row: Json) -> Json:
    projected = copy.deepcopy(row)
    for field in SCORING_INDEPENDENT_FIELDS:
        projected.pop(field, None)
    return projected


def redact_record(row: Json) -> tuple[Json, RedactionStats]:
    derived = copy.deepcopy(row)
    stats = RedactionStats()
    envelope = row.get("sanitized_provider_envelope")
    if envelope is None:
        return derived, stats

    original_envelope_sha = row.get("sanitized_provider_envelope_sha256")
    expected_original_sha = sha256_bytes(canonical_json(envelope).encode("utf-8"))
    if original_envelope_sha != expected_original_sha:
        fail("source record has a malformed sanitized-provider-envelope digest")

    public_envelope = redact_hidden_reasoning(envelope, stats)
    if stats.fields == 0:
        return derived, stats

    derived["pre_redaction_sanitized_provider_envelope_sha256"] = original_envelope_sha
    derived["sanitized_provider_envelope"] = public_envelope
    derived["sanitized_provider_envelope_sha256"] = sha256_bytes(
        canonical_json(public_envelope).encode("utf-8")
    )
    derived["public_release_redaction"] = {
        "redacted_fields": stats.fields,
        "redacted_utf8_bytes": stats.utf8_bytes,
        "sentinel": SENTINEL,
        "status": "POST_C2_HIDDEN_REASONING_REDACTED",
    }
    if _scientific_projection(row) != _scientific_projection(derived):
        fail("publication redaction changed a scoring-relevant field")
    return derived, stats


def _is_scored_jsonl(relative_path: Path) -> bool:
    name = relative_path.name
    return name.endswith("-run.jsonl") or name.endswith("-c2-complete.jsonl")


def _load_jsonl(path: Path) -> list[tuple[bytes, Json]]:
    loaded: list[tuple[bytes, Json]] = []
    for line_number, raw_line in enumerate(path.read_bytes().splitlines(), start=1):
        if not raw_line:
            continue
        value = json.loads(raw_line)
        if not isinstance(value, dict):
            fail(f"{path}: JSONL row {line_number} is not an object")
        if raw_line != canonical_json(value).encode("utf-8"):
            fail(f"{path}: JSONL row {line_number} is not canonical JSON")
        loaded.append((raw_line, value))
    return loaded


def _file_map(root: Path, *, exclude: set[str] | None = None) -> dict[str, str]:
    excluded = exclude or set()
    return {
        path.relative_to(root).as_posix(): sha256_file(path)
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.relative_to(root).as_posix() not in excluded
    }


def build_public_release(
    source_root: Path,
    out_root: Path,
    *,
    github_run_id: int,
    artifact_registry_path: Path | None = None,
) -> Json:
    source_root = source_root.resolve()
    out_root = out_root.resolve()
    if not source_root.is_dir():
        fail(f"source reviewer-evidence directory does not exist: {source_root}")
    if out_root.exists():
        fail(f"refusing to overwrite public-evidence directory: {out_root}")
    out_root.mkdir(parents=True)

    source_files = _file_map(source_root)
    if not source_files:
        fail("source reviewer-evidence directory is empty")

    transformed_files: list[Json] = []
    row_map: list[Json] = []
    redacted_unique_cells: set[tuple[str, str]] = set()
    copied_files = 0
    total_redacted_fields = 0
    total_redacted_bytes = 0

    for source in sorted(source_root.rglob("*")):
        if not source.is_file():
            continue
        relative = source.relative_to(source_root)
        target = out_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if not _is_scored_jsonl(relative):
            shutil.copyfile(source, target)
            copied_files += 1
            continue

        output_rows: list[Json] = []
        file_redacted_rows = 0
        file_redacted_fields = 0
        file_redacted_bytes = 0
        for raw_line, row in _load_jsonl(source):
            derived, stats = redact_record(row)
            derived_line = canonical_json(derived).encode("utf-8")
            changed = stats.fields > 0
            if changed:
                file_redacted_rows += 1
                file_redacted_fields += stats.fields
                file_redacted_bytes += stats.utf8_bytes
                redacted_unique_cells.add((str(row.get("lane_id")), str(row.get("item_id"))))
            row_map.append(
                {
                    "derived_row_sha256": sha256_bytes(derived_line),
                    "item_id": row.get("item_id"),
                    "lane_id": row.get("lane_id"),
                    "redacted_fields": stats.fields,
                    "redacted_utf8_bytes": stats.utf8_bytes,
                    "relative_path": relative.as_posix(),
                    "scientific_fields_unchanged": (
                        _scientific_projection(row) == _scientific_projection(derived)
                    ),
                    "sequence": row.get("sequence"),
                    "source_row_sha256": sha256_bytes(raw_line),
                }
            )
            output_rows.append(derived)
        write_jsonl(target, output_rows)
        total_redacted_fields += file_redacted_fields
        total_redacted_bytes += file_redacted_bytes
        transformed_files.append(
            {
                "derived_file_sha256": sha256_file(target),
                "records": len(output_rows),
                "redacted_fields": file_redacted_fields,
                "redacted_records": file_redacted_rows,
                "redacted_utf8_bytes": file_redacted_bytes,
                "relative_path": relative.as_posix(),
                "source_file_sha256": sha256_file(source),
            }
        )

    registry_sha256: str | None = None
    if artifact_registry_path is not None:
        registry_path = artifact_registry_path.resolve()
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        if not isinstance(registry, dict) or registry.get("github_run_id") != github_run_id:
            fail("source-artifact registry is not bound to the scored GitHub run")
        registry_payload = copy.deepcopy(registry)
        observed_registry_sha = registry_payload.pop("source_artifact_registry_sha256", None)
        if observed_registry_sha != sha256_bytes(canonical_json(registry_payload).encode("utf-8")):
            fail("source-artifact registry self-digest mismatch")
        registry_target = out_root / "provenance" / "source-artifacts.json"
        registry_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(registry_path, registry_target)
        registry_sha256 = sha256_file(registry_target)

    row_map_path = out_root / "public-release-row-hash-map.jsonl"
    write_jsonl(row_map_path, row_map)
    derived_files = _file_map(
        out_root,
        exclude={"public-release-redaction-receipt.json"},
    )
    receipt: Json = {
        "copied_byte_identical_files": copied_files,
        "derived_files_sha256": derived_files,
        "github_run_id": github_run_id,
        "hidden_reasoning_present_in_public_release": False,
        "original_scored_artifacts_modified": False,
        "post_c2_transform": True,
        "redacted_fields_including_raw_and_c2_copies": total_redacted_fields,
        "redacted_unique_model_item_cells": len(redacted_unique_cells),
        "redacted_utf8_bytes_including_raw_and_c2_copies": total_redacted_bytes,
        "redaction_rule": {
            "hidden_reasoning_keys": sorted(HIDDEN_REASONING_KEYS),
            "sentinel": SENTINEL,
            "thinking_block_types": sorted(THINKING_BLOCK_TYPES),
        },
        "row_hash_map": {
            "file_sha256": sha256_file(row_map_path),
            "path": row_map_path.relative_to(out_root).as_posix(),
            "rows": len(row_map),
        },
        "schema_version": "1.0.0",
        "scientific_fields_unchanged": all(
            bool(row["scientific_fields_unchanged"]) for row in row_map
        ),
        "source_artifact_registry_sha256": registry_sha256,
        "source_files_sha256": source_files,
        "status": "POST_C2_PUBLIC_RELEASE_REDACTION",
        "transformed_files": transformed_files,
    }
    receipt["redaction_receipt_sha256"] = sha256_bytes(canonical_json(receipt).encode("utf-8"))
    write_json(out_root / "public-release-redaction-receipt.json", receipt)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--github-run-id", type=int, required=True)
    parser.add_argument("--source-artifact-registry", type=Path)
    args = parser.parse_args()
    receipt = build_public_release(
        args.source_root,
        args.out,
        github_run_id=args.github_run_id,
        artifact_registry_path=args.source_artifact_registry,
    )
    print(
        canonical_json(
            {
                "redacted_fields": receipt["redacted_fields_including_raw_and_c2_copies"],
                "redacted_unique_model_item_cells": receipt["redacted_unique_model_item_cells"],
                "receipt_sha256": receipt["redaction_receipt_sha256"],
                "status": receipt["status"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
