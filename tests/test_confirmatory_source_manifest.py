"""Tests for the exact r6 runtime-source and dependency closure."""

from __future__ import annotations

import importlib.util
from copy import deepcopy
from pathlib import Path
from types import ModuleType

import pytest

from claimpromotebench.dataset import load_json
from claimpromotebench.hashing import canonical_json, sha256_bytes

ROOT = Path(__file__).resolve().parents[1]


def _module(name: str = "build_confirmatory_source_manifest") -> ModuleType:
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_runtime_manifest_is_preserved_at_the_recorded_source_commit() -> None:
    module = _module()
    commitment_module = _module("make_confirmatory_hidden_commitment")
    manifest = load_json(ROOT / module.MANIFEST_PATH)
    commitment = load_json(
        ROOT / "v2" / "confirmatory" / "c1-r6" / "confirmatory-hidden-commitment.json"
    )
    assert b"\r\n" not in (ROOT / module.MANIFEST_PATH).read_bytes()
    commitment_module.verify_recorded_source_commit(commitment)
    assert commitment["runtime_source_manifest_sha256"] == manifest["manifest_sha256"]
    files = set(manifest["files_sha256"])
    recorded_files = commitment["source_files_sha256"]
    assert {path: recorded_files[path] for path in manifest["files_sha256"]} == manifest[
        "files_sha256"
    ]
    assert "src/claimpromotebench/__init__.py" in files
    assert "src/claimpromotebench/statistics.py" in files
    assert "configs/decoding-v1.json" in files
    assert "tools/confirmatory-python311.lock" in files
    assert "scripts/analyze_balanced_public_challenge.py" not in files
    assert "scripts/analyze_public_model_breadth_study.py" not in files
    assert "scripts/build_local_release_kit.py" not in files
    assert "scripts/build_public_model_breadth_study.py" not in files
    assert "scripts/derive_r6_reporting_addendum.py" not in files
    assert "scripts/finalize_public_model_breadth_study.py" not in files
    assert "scripts/run_public_model_breadth_study.py" not in files
    assert "scripts/validate_public_model_breadth_study.py" not in files
    # Publication and anonymous-review tooling changed after the scored run. The immutable
    # manifest must keep matching its recorded Git source while refusing to describe HEAD.
    with pytest.raises(ValueError, match="runtime source manifest hash mismatch"):
        module.validate_manifest(manifest)


def test_runtime_manifest_rejects_missing_added_or_changed_entries() -> None:
    module = _module()
    manifest = load_json(ROOT / module.MANIFEST_PATH)

    missing = deepcopy(manifest)
    missing["files_sha256"].pop("src/claimpromotebench/__init__.py")
    missing["file_count"] -= 1
    missing.pop("manifest_sha256")
    missing["manifest_sha256"] = sha256_bytes(canonical_json(missing).encode("utf-8"))
    with pytest.raises(ValueError, match="exact discovered file set"):
        module.validate_manifest(missing)

    added = deepcopy(manifest)
    added["files_sha256"]["scripts/unregistered_runtime.py"] = "sha256:" + "0" * 64
    added["file_count"] += 1
    added.pop("manifest_sha256")
    added["manifest_sha256"] = sha256_bytes(canonical_json(added).encode("utf-8"))
    with pytest.raises(ValueError, match="exact discovered file set"):
        module.validate_manifest(added)

    changed = deepcopy(manifest)
    changed["files_sha256"]["src/claimpromotebench/statistics.py"] = "sha256:" + "0" * 64
    changed.pop("manifest_sha256")
    changed["manifest_sha256"] = sha256_bytes(canonical_json(changed).encode("utf-8"))
    with pytest.raises(ValueError, match="hash mismatch"):
        module.validate_manifest(changed)
