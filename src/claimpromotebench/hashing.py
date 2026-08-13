"""Canonical serialization and local artifact integrity checks."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .errors import DatasetIntegrityError


def canonical_json(value: Any) -> str:
    """Return the benchmark's stable JSON representation."""

    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(data: bytes) -> str:
    """Return a prefixed lowercase SHA-256 digest."""

    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def sha256_file(path: Path) -> str:
    """Hash a file without interpreting its contents."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def resolve_artifact(dataset_dir: Path, artifact_path: str) -> Path:
    """Resolve an artifact path while rejecting escape from the dataset directory."""

    root = dataset_dir.resolve()
    candidate = (root / artifact_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise DatasetIntegrityError(f"artifact path escapes dataset: {artifact_path}") from exc
    if not candidate.is_file():
        raise DatasetIntegrityError(f"artifact does not exist: {artifact_path}")
    return candidate


def verify_artifact(dataset_dir: Path, evidence: dict[str, Any]) -> None:
    """Verify one evidence object's local artifact digest."""

    path = resolve_artifact(dataset_dir, str(evidence["artifact_path"]))
    actual = sha256_file(path)
    expected = str(evidence["artifact_hash"])
    if actual != expected:
        raise DatasetIntegrityError(
            f"artifact hash mismatch for {evidence['id']}: expected {expected}, got {actual}"
        )
