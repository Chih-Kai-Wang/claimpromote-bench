#!/usr/bin/env python3
"""Build or verify the exact r6 runtime-source closure before C0."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from claimpromotebench.dataset import load_json  # noqa: E402
from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]
STUDY_ID = "claimpromotebench-v1-fresh-confirmatory-2026-08-r6"
MANIFEST_PATH = "configs/confirmatory-runtime-source-manifest-r6.json"

_DISCOVERY_RULES = (
    ("src", {".py"}, {"py.typed"}),
    ("scripts", {".py"}, set()),
    ("schemas", {".json"}, set()),
    ("policies", {".json"}, set()),
)
_EXPLICIT_PATHS = (
    ".github/workflows/apply-solo-pilot.yml",
    ".github/workflows/confirmatory-hidden-freeze.yml",
    ".github/workflows/confirmatory-hidden-study.yml",
    ".github/workflows/prepare-review-alpha.yml",
    "configs/decoding-v1.json",
    "configs/prior-hidden-prompt-hash-denylist-r6.json",
    "configs/v1-benchmark-plan.json",
    "configs/v1-hidden-test-commitment.json",
    "fixtures/formal/cases.json",
    "pyproject.toml",
    "tools/confirmatory-python311.lock",
    "tools/drand/fetch_verified_beacon.mjs",
    "tools/drand/package-lock.json",
    "tools/drand/package.json",
    "v2/confirmatory/c1-r4/confirmatory-hidden-commitment.json",
    "v2/confirmatory/c1-r5/confirmatory-hidden-commitment.json",
    "v2/confirmatory/c1-r5/prompt-hash-recovery-run-receipt.json",
    "v2/confirmatory/c1-r5/void-pre-post-receipt.json",
    "v2/confirmatory/power-analysis-r6.json",
    "v2/confirmatory/power-assumptions-r6.json",
    "v2/confirmatory/public-dev-text-nb-v1.json",
    "v2/confirmatory/r4-execution/execution-receipt.json",
    "v2/confirmatory/r5-to-r6-change-scope.json",
)
_POST_R6_NON_RUNTIME_PATHS = {
    # These scripts were introduced only after the immutable r6 scored run. They read or
    # aggregate already terminal evidence and cannot influence C1 or scored inference.
    "src/claimpromotebench/policy_difference.py",
    "scripts/analyze_balanced_public_challenge.py",
    "scripts/audit_manuscript_style.py",
    "scripts/analyze_public_model_breadth_study.py",
    "scripts/analyze_slsa_portability_study.py",
    "scripts/analyze_policy_switch_study.py",
    "scripts/analyze_local_model_replication.py",
    "scripts/analyze_minimal_policy_migration_gate.py",
    "scripts/analyze_minimal_policy_migration_hosted_study.py",
    "scripts/analyze_ox_alpha_minimal_route_study.py",
    "scripts/build_sigstore_policy_verifier_revision.py",
    "scripts/build_agent_governance_policy_interface_revision.py",
    "scripts/build_dual_endpoint_audit.py",
    "scripts/build_trivy_policy_revision.py",
    "scripts/build_upstream_policy_revision_study.py",
    "scripts/build_policy_switch_study.py",
    "scripts/build_slsa_portability_study.py",
    "scripts/build_local_release_kit.py",
    "scripts/build_public_model_breadth_study.py",
    "scripts/derive_public_model_breadth_failure_addendum.py",
    "scripts/derive_policy_switch_hosted_exclusion.py",
    "scripts/derive_policy_switch_hosted_replacement_eligibility.py",
    "scripts/derive_policy_difference_coverage.py",
    "scripts/derive_upstream_route_repetition_failure_modes.py",
    "scripts/derive_minimal_policy_migration_hosted_eligibility.py",
    "scripts/derive_minimal_policy_migration_suite.py",
    "scripts/derive_policy_migration_mutation_audit.py",
    "scripts/analyze_policy_switch_hosted_replacement.py",
    "scripts/freeze_policy_switch_hosted_replacement.py",
    "scripts/run_policy_switch_hosted_replacement.py",
    "scripts/validate_policy_switch_hosted_replacement.py",
    "scripts/derive_r6_reporting_addendum.py",
    "scripts/finalize_public_model_breadth_study.py",
    "scripts/finalize_local_model_results.py",
    "scripts/finalize_minimal_policy_migration_hosted_results.py",
    "scripts/finalize_synthetic_policy_results.py",
    "scripts/build_policy_transition_graph_study.py",
    "scripts/validate_policy_transition_graph_study.py",
    "scripts/policy_transition_graph_local.py",
    "scripts/freeze_policy_transition_graph_local_study.py",
    "scripts/validate_policy_transition_graph_local_study.py",
    "scripts/run_policy_transition_graph_local_study.py",
    "scripts/analyze_policy_transition_graph_local_study.py",
    "scripts/analyze_policy_transition_graph_hosted_study.py",
    "scripts/derive_policy_transition_graph_hosted_eligibility.py",
    "scripts/freeze_policy_transition_graph_hosted_study.py",
    "scripts/run_policy_transition_graph_hosted_study.py",
    "scripts/validate_policy_transition_graph_hosted_study.py",
    "scripts/freeze_local_model_replications.py",
    "scripts/freeze_minimal_policy_migration_hosted_study.py",
    "scripts/freeze_ox_alpha_minimal_route_study.py",
    "scripts/frozen_run_io.py",
    "scripts/freeze_slsa_portability_study.py",
    "scripts/freeze_policy_switch_study.py",
    "scripts/policy_switch.py",
    "scripts/local_model_replication.py",
    "scripts/qualify_local_model_environment.py",
    "scripts/run_public_model_breadth_study.py",
    "scripts/run_slsa_portability_study.py",
    "scripts/run_policy_switch_study.py",
    "scripts/run_local_model_replication.py",
    "scripts/run_minimal_policy_migration_hosted_study.py",
    "scripts/run_ox_alpha_minimal_route_study.py",
    "scripts/seal_local_model_void_attempt.py",
    "scripts/slsa_policy.py",
    "scripts/snapshot_slsa_portability_catalog.py",
    "scripts/synthetic_policy_output.py",
    "scripts/train_slsa_structured_baseline.py",
    "scripts/train_policy_switch_baselines.py",
    "scripts/validate_public_model_breadth_study.py",
    "scripts/validate_anonymous_current_evidence.py",
    "scripts/validate_slsa_portability_freeze.py",
    "scripts/validate_slsa_portability_study.py",
    "scripts/validate_policy_switch_study.py",
    "scripts/validate_local_model_replications.py",
    "scripts/validate_minimal_policy_migration_hosted_study.py",
    "scripts/validate_ox_alpha_minimal_route_study.py",
    "scripts/validate_sigstore_policy_verifier_revision.py",
    "scripts/validate_agent_governance_policy_interface_revision.py",
    "scripts/validate_external_evidence_audit.py",
    "scripts/validate_dual_endpoint_audit.py",
    "scripts/validate_trivy_policy_revision.py",
    "scripts/upstream_policy_revision.py",
    "scripts/upstream_route_repetition.py",
    "scripts/openai_compatible_call.py",
    "scripts/freeze_upstream_policy_route_repetition.py",
    "scripts/validate_upstream_policy_route_repetition.py",
    "scripts/run_upstream_policy_route_repetition.py",
    "scripts/analyze_upstream_policy_route_repetition.py",
    "scripts/validate_upstream_policy_route_repetition_results.py",
    "scripts/validate_upstream_policy_revision_study.py",
    "v2/schemas/upstream-policy-route-repetition-record.schema.json",
}


def discover_runtime_source_paths() -> tuple[str, ...]:
    """Return every code/config file allowed to influence C1 or scored execution."""

    paths = set(_EXPLICIT_PATHS)
    for directory, suffixes, names in _DISCOVERY_RULES:
        root = ROOT / directory
        if not root.is_dir():
            raise ValueError(f"runtime source directory is absent: {directory}")
        for path in root.rglob("*"):
            relative = path.relative_to(ROOT).as_posix()
            if (
                path.is_file()
                and relative not in _POST_R6_NON_RUNTIME_PATHS
                and (path.suffix in suffixes or path.name in names)
            ):
                paths.add(relative)
    missing = sorted(relative for relative in paths if not (ROOT / relative).is_file())
    if missing:
        raise ValueError(f"runtime source files are absent: {missing}")
    return tuple(sorted(paths))


def build_manifest() -> Json:
    paths = discover_runtime_source_paths()
    record: Json = {
        "schema_version": "1.0.0",
        "status": "EXACT_RUNTIME_SOURCE_CLOSURE",
        "study_id": STUDY_ID,
        "coverage": {
            "all_root_src_tree_python_and_typing_marker_files": True,
            "all_root_scripts_tree_python_files": True,
            "all_root_schemas_and_policies_trees": True,
            "both_canonical_and_dispatch_alias_workflows": True,
            "hash_locked_python311_runtime_dependencies": True,
            "manifest_and_plan_excluded_to_avoid_hash_cycles": True,
            "post_c0_source_diff_rule": (
                "Only the two public active commitment JSON files and JSON evidence under "
                "v2/confirmatory/c1-r6 may differ from the source commit before scoring."
            ),
        },
        "file_count": len(paths),
        "files_sha256": {relative: sha256_file(ROOT / relative) for relative in paths},
    }
    record["manifest_sha256"] = sha256_bytes(canonical_json(record).encode("utf-8"))
    return record


def validate_manifest(manifest: Json) -> Json:
    payload = dict(manifest)
    observed_digest = payload.pop("manifest_sha256", None)
    expected_digest = sha256_bytes(canonical_json(payload).encode("utf-8"))
    if observed_digest != expected_digest:
        raise ValueError("runtime source manifest self-digest mismatch")
    if (
        manifest.get("status") != "EXACT_RUNTIME_SOURCE_CLOSURE"
        or manifest.get("study_id") != STUDY_ID
    ):
        raise ValueError("runtime source manifest identity mismatch")
    expected_paths = discover_runtime_source_paths()
    files = manifest.get("files_sha256")
    if not isinstance(files, dict) or tuple(sorted(files)) != expected_paths:
        raise ValueError("runtime source manifest does not match the exact discovered file set")
    if manifest.get("file_count") != len(expected_paths):
        raise ValueError("runtime source manifest file count mismatch")
    for relative in expected_paths:
        if files.get(relative) != sha256_file(ROOT / relative):
            raise ValueError(f"runtime source manifest hash mismatch: {relative}")
    return {
        "status": "RUNTIME_SOURCE_MANIFEST_PASS",
        "study_id": STUDY_ID,
        "file_count": len(expected_paths),
        "manifest_sha256": expected_digest,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--out", type=Path)
    group.add_argument("--verify", type=Path)
    args = parser.parse_args()
    if args.out is not None:
        record = build_manifest()
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_bytes((json.dumps(record, indent=2, sort_keys=True) + "\n").encode("utf-8"))
        report = {
            "status": "RUNTIME_SOURCE_MANIFEST_WRITTEN",
            "file_count": record["file_count"],
            "manifest_sha256": record["manifest_sha256"],
        }
    else:
        report = validate_manifest(load_json(args.verify.resolve()))
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
