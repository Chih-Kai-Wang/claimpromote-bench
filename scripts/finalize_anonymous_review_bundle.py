#!/usr/bin/env python3
"""Finalize the staged anonymous reviewer bundle with self-contained public checks."""

from __future__ import annotations

import argparse
import importlib.util
import shutil
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "build_anonymous_review_bundle.py"


def load_builder() -> ModuleType:
    spec = importlib.util.spec_from_file_location("anonymous_bundle_builder", BUILDER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load anonymous bundle builder")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def copy_public_check(relative: str, bundle: Path) -> None:
    source = ROOT / relative
    target = bundle / relative
    if not source.is_file():
        raise RuntimeError(f"missing public check: {relative}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def patch_runner(bundle: Path) -> None:
    path = bundle / "scripts" / "run_review_checks.py"
    text = path.read_text(encoding="utf-8")
    marker = '    [sys.executable, "-m", "claimpromotebench", "validate", "data/alpha"],\n'
    command = '''    [
        sys.executable,
        "scripts/audit_public_pair_contracts.py",
        "--dataset",
        "data/alpha",
        "--out",
        "work/public-pair-contract-audit.json",
    ],
'''
    if command in text:
        return
    if marker not in text:
        raise RuntimeError("anonymous review runner insertion point not found")
    path.write_text(text.replace(marker, marker + command, 1), encoding="utf-8", newline="\n")


def patch_readme(bundle: Path) -> None:
    path = bundle / "README.md"
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        "hidden seed, raw human-review submission, or public workflow/provenance identifier.",
        "hidden seed, human-subject study record, or public workflow/provenance identifier.",
    )
    old = (
        "The checks rebuild and validate the public alpha benchmark, run "
        "shortcut/invariance/executable\nchecks, validate the compact v1 and v2 paper-result "
        "summaries, validate the unlabeled naturalistic\n"
    )
    new = (
        "The checks rebuild and validate the public alpha benchmark, verify all 20 "
        "controlled-pair\ncontracts, run shortcut/invariance/executable checks, validate the "
        "compact v1 and v2 paper-result\nsummaries, and validate the unlabeled naturalistic\n"
    )
    if old not in text:
        raise RuntimeError("anonymous review README patch target not found")
    path.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")


def patch_manifest_scope(bundle: Path) -> None:
    path = bundle / "MANIFEST.json"
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        '"raw_human_review_submissions_included": false',
        '"human_subject_study_records_included": false',
    )
    path.write_text(text, encoding="utf-8", newline="\n")


def finalize(bundle: Path) -> None:
    for relative in (
        "scripts/audit_public_pair_contracts.py",
        "scripts/build_v2_naturalistic_candidates.py",
    ):
        copy_public_check(relative, bundle)
    patch_runner(bundle)
    patch_readme(bundle)

    builder = load_builder()
    builder.scan_identity(bundle)
    builder.write_manifest(bundle)
    patch_manifest_scope(bundle)
    builder.write_manifest(bundle)
    patch_manifest_scope(bundle)
    builder.scan_identity(bundle)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", type=Path, required=True)
    args = parser.parse_args()
    bundle = args.bundle.resolve()
    if not bundle.is_dir():
        raise RuntimeError(f"bundle directory does not exist: {bundle}")
    finalize(bundle)
    print(f"anonymous-review-finalize: PASS ({bundle})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
