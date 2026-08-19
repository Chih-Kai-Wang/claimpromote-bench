#!/usr/bin/env python3
"""Validate a pointer-only v2 naturalistic candidate pool.

The candidate pool is deliberately unlabeled. This validator prevents source drift, duplicate
selection, accidental inclusion of benchmark answers/model outputs, and silent conversion of
source candidates into scored ClaimPromoteBench items.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "v2" / "naturalistic-sources.json"

Json = dict[str, Any]
SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
FORBIDDEN_CANDIDATE_KEYS = {
    "action",
    "decision",
    "gold",
    "gold_action",
    "model_output",
    "model_response",
    "results",
    "score",
    "success",
}
ALLOWED_CANDIDATE_KEYS = {
    "candidate_id",
    "source_id",
    "sampling_rank_sha256",
    "capsule_id",
    "capsule_title",
    "capsule_doi",
    "language",
    "task_prompt",
    "source_repository",
    "source_commit",
    "source_path",
    "redistribution_mode",
    "label_status",
    "include_status",
    "note",
}


def fail(message: str) -> None:
    raise SystemExit(f"v2-naturalistic-candidates: {message}")


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def load_object(path: Path) -> Json:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        fail(f"{path} must contain a JSON object")
    return value


def validate(registry: Json, pool: Json) -> Json:
    if registry.get("schema_version") != "1.0.0":
        fail("unsupported registry schema version")
    if pool.get("schema_version") != "1.0.0":
        fail("unsupported pool schema version")
    if pool.get("status") != "CANDIDATE_POOL_ONLY":
        fail("pool status must remain CANDIDATE_POOL_ONLY")
    if pool.get("selection_salt") != registry.get("selection_salt"):
        fail("selection salt differs from the frozen registry")
    if pool.get("registry_sha256") != digest(registry):
        fail("pool is not bound to the current registry bytes")

    sources = registry.get("sources")
    if not isinstance(sources, list) or not all(isinstance(source, dict) for source in sources):
        fail("registry.sources must be a list of objects")
    source_by_id = {str(source.get("source_id")): source for source in sources}
    if len(source_by_id) != len(sources):
        fail("registry contains duplicate source_id values")

    snapshots = pool.get("source_snapshots")
    if not isinstance(snapshots, list) or not all(isinstance(row, dict) for row in snapshots):
        fail("pool.source_snapshots must be a list of objects")
    snapshot_by_id = {str(row.get("source_id")): row for row in snapshots}
    if set(snapshot_by_id) != set(source_by_id):
        fail("source snapshot IDs do not match the registry")

    approved = {
        source_id
        for source_id, source in source_by_id.items()
        if source.get("status") == "APPROVED_FOR_CANDIDATE_SAMPLING"
    }
    target = registry.get("candidate_target_per_source")
    if not isinstance(target, int) or isinstance(target, bool) or target <= 0:
        fail("candidate_target_per_source must be a positive integer")

    for source_id, source in source_by_id.items():
        snapshot = snapshot_by_id[source_id]
        sampled = snapshot.get("sampled")
        if source_id in approved:
            if sampled != target:
                fail(f"{source_id} sampled count must equal the frozen target")
            for key in ("repository", "commit", "path"):
                if snapshot.get(key) != source.get(key):
                    fail(f"{source_id} snapshot {key} differs from registry")
            source_hash = snapshot.get("source_bytes_sha256")
            if not isinstance(source_hash, str) or not SHA256_PATTERN.fullmatch(source_hash):
                fail(f"{source_id} lacks a valid source-bytes SHA-256")
        elif sampled != 0:
            fail(f"non-approved source {source_id} must not be sampled")

    candidates = pool.get("candidates")
    if not isinstance(candidates, list) or not all(isinstance(row, dict) for row in candidates):
        fail("pool.candidates must be a list of objects")
    expected_count = len(approved) * target
    if pool.get("candidate_count") != expected_count or len(candidates) != expected_count:
        fail("candidate count does not match approved sources and frozen target")

    seen_ids: set[str] = set()
    ranks_by_source: dict[str, list[str]] = {source_id: [] for source_id in approved}
    for index, candidate in enumerate(candidates):
        keys = set(candidate)
        forbidden = sorted(keys & FORBIDDEN_CANDIDATE_KEYS)
        if forbidden:
            fail(f"candidate {index} contains result/label keys: {forbidden}")
        extra = sorted(keys - ALLOWED_CANDIDATE_KEYS)
        if extra:
            fail(f"candidate {index} contains unregistered keys: {extra}")

        candidate_id = candidate.get("candidate_id")
        if not isinstance(candidate_id, str) or not candidate_id:
            fail(f"candidate {index} lacks candidate_id")
        if candidate_id in seen_ids:
            fail(f"duplicate candidate_id: {candidate_id}")
        seen_ids.add(candidate_id)

        source_id = candidate.get("source_id")
        if source_id not in approved:
            fail(f"candidate {candidate_id} uses a non-approved source")
        source = source_by_id[str(source_id)]
        expected_fields = {
            "source_repository": source.get("repository"),
            "source_commit": source.get("commit"),
            "source_path": source.get("path"),
            "redistribution_mode": source.get("redistribution_mode"),
        }
        for key, expected in expected_fields.items():
            if candidate.get(key) != expected:
                fail(f"candidate {candidate_id} has incorrect {key}")
        if candidate.get("label_status") != "UNLABELED_CANDIDATE":
            fail(f"candidate {candidate_id} must remain unlabeled")
        if candidate.get("include_status") != "PENDING_SOURCE_LEVEL_REVIEW":
            fail(f"candidate {candidate_id} was included before source-level review")

        rank = candidate.get("sampling_rank_sha256")
        if not isinstance(rank, str) or not SHA256_PATTERN.fullmatch(rank):
            fail(f"candidate {candidate_id} lacks a valid sampling rank")
        ranks_by_source[str(source_id)].append(rank)

    for source_id, ranks in ranks_by_source.items():
        if ranks != sorted(ranks):
            fail(f"candidates for {source_id} are not in deterministic sampling order")

    boundary = pool.get("interpretation_boundary")
    if not isinstance(boundary, str) or "unlabeled" not in boundary.lower():
        fail("candidate-pool interpretation boundary is missing")

    return {
        "status": "PASS",
        "candidate_count": len(candidates),
        "approved_sources": sorted(approved),
        "registry_sha256": pool["registry_sha256"],
        "candidate_ids_sha256": digest(sorted(seen_ids)),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--pool", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    report = validate(load_object(args.registry), load_object(args.pool))
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
