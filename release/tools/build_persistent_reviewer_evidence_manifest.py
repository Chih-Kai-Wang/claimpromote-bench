"""Build or verify the permanent manifest for committed reviewer evidence."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file

Json = dict[str, Any]


def fail(message: str) -> None:
    raise ValueError(message)


def _file_map(root: Path, manifest_path: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): sha256_file(path)
        for path in sorted(root.rglob("*"))
        if path.is_file() and path != manifest_path
    }


def build_manifest(
    root: Path,
    out: Path,
    *,
    workflow_run_id: int,
    artifact_id: int,
    artifact_zip_sha256: str,
    head_commit: str,
) -> Json:
    root = root.resolve()
    out = out.resolve()
    if not root.is_dir() or out.parent != root:
        fail("persistent manifest must be created at the reviewer-evidence root")
    if out.exists():
        fail(f"refusing to overwrite persistent manifest: {out}")
    files = _file_map(root, out)
    if not files:
        fail("reviewer-evidence root is empty")
    manifest: Json = {
        "file_count": len(files),
        "files": files,
        "public_release_artifact": {
            "artifact_id": artifact_id,
            "artifact_zip_sha256": artifact_zip_sha256,
            "head_commit": head_commit,
            "workflow_run_id": workflow_run_id,
        },
        "schema_version": "1.0.0",
        "scope": {
            "hidden_reasoning_present": False,
            "original_reasoning_bearing_artifacts_included": False,
            "post_c2_allowlist_derivative": True,
            "scientific_analysis_payload_byte_identical": True,
            "source_to_derived_row_hashes_verified": True,
        },
        "status": "PERSISTENT_FRESH_CONFIRMATORY_PUBLIC_EVIDENCE",
    }
    manifest["manifest_sha256"] = sha256_bytes(canonical_json(manifest).encode("utf-8"))
    out.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return manifest


def verify_manifest(root: Path, manifest_path: Path) -> Json:
    root = root.resolve()
    manifest_path = manifest_path.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        fail("persistent manifest is not an object")
    payload = copy.deepcopy(manifest)
    observed = payload.pop("manifest_sha256", None)
    if observed != sha256_bytes(canonical_json(payload).encode("utf-8")):
        fail("persistent manifest self-digest mismatch")
    files = _file_map(root, manifest_path)
    if manifest.get("files") != files or manifest.get("file_count") != len(files):
        fail("persistent manifest file coverage or digest mismatch")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--verify", type=Path)
    parser.add_argument("--workflow-run-id", type=int)
    parser.add_argument("--artifact-id", type=int)
    parser.add_argument("--artifact-zip-sha256")
    parser.add_argument("--head-commit")
    args = parser.parse_args()
    if (args.out is None) == (args.verify is None):
        fail("choose exactly one of --out or --verify")
    if args.verify is not None:
        result = verify_manifest(args.root, args.verify)
    else:
        required = (
            args.workflow_run_id,
            args.artifact_id,
            args.artifact_zip_sha256,
            args.head_commit,
        )
        if any(value is None for value in required):
            fail("manifest creation requires workflow, artifact, digest, and head metadata")
        result = build_manifest(
            args.root,
            args.out,
            workflow_run_id=args.workflow_run_id,
            artifact_id=args.artifact_id,
            artifact_zip_sha256=args.artifact_zip_sha256,
            head_commit=args.head_commit,
        )
    print(
        canonical_json(
            {
                "file_count": result["file_count"],
                "manifest_sha256": result["manifest_sha256"],
                "status": result["status"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
