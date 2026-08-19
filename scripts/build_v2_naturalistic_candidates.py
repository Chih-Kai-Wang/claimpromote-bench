#!/usr/bin/env python3
"""Build pointer-only v2 naturalistic candidates from pinned public metadata.

This script does not create ClaimPromoteBench labels. It samples a candidate pool before model
scoring so later curation cannot cherry-pick based on model behavior. Only source metadata and
stable pointers are emitted; third-party capsule contents are never copied.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "v2" / "naturalistic-sources.json"
Json = dict[str, Any]


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def load_registry(path: Path = REGISTRY) -> Json:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("naturalistic source registry must be an object")
    return value


def raw_github_url(repository: str, commit: str, path: str) -> str:
    return f"https://raw.githubusercontent.com/{repository}/{commit}/{path}"


def download_json(url: str, timeout: float) -> tuple[Any, str]:
    request = urllib.request.Request(url, headers={"User-Agent": "ClaimPromoteBench-v2-curation"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read()
    return json.loads(raw), sha256_bytes(raw)


def sample_core_bench(rows: list[Json], *, salt: str, count: int, source: Json) -> list[Json]:
    eligible = [row for row in rows if row.get("field") == source.get("eligible_field")]
    ranked: list[tuple[str, Json]] = []
    for row in eligible:
        capsule_id = str(row.get("capsule_id", ""))
        if not capsule_id:
            continue
        rank = hashlib.sha256(f"{salt}:{capsule_id}".encode("utf-8")).hexdigest()
        ranked.append((rank, row))
    ranked.sort(key=lambda value: (value[0], str(value[1].get("capsule_id", ""))))

    selected: list[Json] = []
    for rank, row in ranked[:count]:
        capsule_id = str(row["capsule_id"])
        selected.append(
            {
                "candidate_id": f"core-bench:{capsule_id}",
                "source_id": source["source_id"],
                "sampling_rank_sha256": f"sha256:{rank}",
                "capsule_id": capsule_id,
                "capsule_title": row.get("capsule_title"),
                "capsule_doi": row.get("capsule_doi"),
                "language": row.get("language"),
                "task_prompt": row.get("task_prompt"),
                "source_repository": source["repository"],
                "source_commit": source["commit"],
                "source_path": source["path"],
                "redistribution_mode": source["redistribution_mode"],
                "label_status": "UNLABELED_CANDIDATE",
                "include_status": "PENDING_SOURCE_LEVEL_REVIEW",
                "note": (
                    "Candidate sampling does not imply that the capsule contents may be copied, "
                    "that a ClaimPromoteBench transition can be defined, or that the case will be scored."
                ),
            }
        )
    return selected


def build(registry: Json, *, timeout: float) -> Json:
    salt = str(registry["selection_salt"])
    target = int(registry["candidate_target_per_source"])
    candidates: list[Json] = []
    source_snapshots: list[Json] = []

    for source in registry["sources"]:
        if source.get("status") != "APPROVED_FOR_CANDIDATE_SAMPLING":
            source_snapshots.append(
                {
                    "source_id": source["source_id"],
                    "status": source["status"],
                    "sampled": 0,
                }
            )
            continue
        repository = str(source["repository"])
        commit = str(source["commit"])
        path = str(source["path"])
        url = raw_github_url(repository, commit, path)
        payload, payload_sha256 = download_json(url, timeout)
        if not isinstance(payload, list) or not all(isinstance(row, dict) for row in payload):
            raise RuntimeError(f"unexpected candidate source structure: {source['source_id']}")
        if source["source_id"] != "core-bench-train":
            raise RuntimeError(f"no deterministic sampler registered for {source['source_id']}")
        selected = sample_core_bench(payload, salt=salt, count=target, source=source)
        if len(selected) != target:
            raise RuntimeError(
                f"source {source['source_id']} produced {len(selected)} candidates; expected {target}"
            )
        candidates.extend(selected)
        source_snapshots.append(
            {
                "source_id": source["source_id"],
                "repository": repository,
                "commit": commit,
                "path": path,
                "download_url": url,
                "source_bytes_sha256": payload_sha256,
                "sampled": len(selected),
            }
        )

    result: Json = {
        "schema_version": "1.0.0",
        "status": "CANDIDATE_POOL_ONLY",
        "selection_salt": salt,
        "registry_sha256": sha256_bytes(canonical(registry).encode("utf-8")),
        "source_snapshots": source_snapshots,
        "candidate_count": len(candidates),
        "candidates": candidates,
        "interpretation_boundary": (
            "These records are unlabeled source candidates. They are not benchmark items, do not "
            "carry ClaimPromoteBench gold actions, and must not be selected using model outputs."
        ),
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", type=Path, default=REGISTRY)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()

    registry = load_registry(args.registry)
    result = build(registry, timeout=args.timeout)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "candidates": result["candidate_count"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
