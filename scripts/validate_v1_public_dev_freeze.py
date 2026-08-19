#!/usr/bin/env python3
"""Validate a generated v1 public-dev dataset against its frozen release hashes."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FREEZE = ROOT / "configs" / "v1-public-dev-freeze.json"


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def validate(dataset_dir: Path, freeze_path: Path) -> dict[str, Any]:
    freeze = _load_json(freeze_path)
    manifest_path = dataset_dir / "manifest.json"
    manifest = _load_json(manifest_path)

    if manifest.get("dataset_id") != freeze.get("dataset_id"):
        raise RuntimeError("public-dev dataset_id differs from frozen release")
    if manifest.get("release_status") != freeze.get("release_status"):
        raise RuntimeError("public-dev release_status differs from frozen release")
    if manifest.get("evaluation_time") != freeze.get("evaluation_time"):
        raise RuntimeError("public-dev evaluation_time differs from frozen release")
    if manifest.get("pairs") != freeze.get("pairs"):
        raise RuntimeError("public-dev pair count differs from frozen release")
    if manifest.get("instances") != freeze.get("instances"):
        raise RuntimeError("public-dev instance count differs from frozen release")
    if manifest.get("policy_file") != freeze.get("policy_file"):
        raise RuntimeError("public-dev policy identity differs from frozen release")
    if _sha256(manifest_path) != freeze.get("manifest_sha256"):
        raise RuntimeError("public-dev manifest bytes differ from frozen release")

    expected: dict[str, str] = {}
    for section in ("canonical_files", "formal_files"):
        values = freeze.get(section)
        if not isinstance(values, dict):
            raise RuntimeError(f"freeze {section} must be an object")
        expected.update({str(path): str(digest) for path, digest in values.items()})

    failures: list[str] = []
    for relative, digest in sorted(expected.items()):
        path = dataset_dir / relative
        if not path.is_file():
            failures.append(f"missing:{relative}")
            continue
        observed = _sha256(path)
        if observed != digest:
            failures.append(f"hash:{relative}:{observed}")
    if failures:
        raise RuntimeError("public-dev freeze mismatch: " + "; ".join(failures))

    return {
        "status": "PASS",
        "dataset_id": manifest["dataset_id"],
        "pairs": manifest["pairs"],
        "instances": manifest["instances"],
        "manifest_sha256": _sha256(manifest_path),
        "frozen_files_checked": len(expected),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--freeze", type=Path, default=DEFAULT_FREEZE)
    args = parser.parse_args()
    report = validate(args.dataset, args.freeze)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
