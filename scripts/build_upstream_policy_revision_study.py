#!/usr/bin/env python3
"""Build a frozen, OPA-scored study from two traceable Gatekeeper policy revisions."""

from __future__ import annotations

import argparse
import difflib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from upstream_policy_revision import (  # noqa: E402
    Revision,
    UpstreamPolicyCase,
    expected_decision,
    render_prompt,
    upstream_policy_cases,
)

from claimpromotebench.dataset import validate_with_schema, write_jsonl  # noqa: E402
from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402
from claimpromotebench.policy_difference import (  # noqa: E402
    PolicyDifference,
    adequacy,
    minimum_complete_suite,
)

Json = dict[str, Any]
STUDY_ROOT = ROOT / "v2" / "upstream-policy-revisions-v1"
DATASET_ROOT = STUDY_ROOT / "dataset"
SOURCE_ROOT = STUDY_ROOT / "sources"
REGISTRY_PATH = SOURCE_ROOT / "registry.json"
SCHEMA_PATH = ROOT / "v2" / "schemas" / "upstream-policy-decision.schema.json"
GENERATED_PATHS = (
    "dataset/evaluation-gold.jsonl",
    "dataset/evaluation-items.jsonl",
    "dataset/evaluation-pairs.json",
    "dataset/evaluation-prompt-packet.json",
    "coverage.json",
    "dataset-plan.json",
    "minimum-suite.json",
    "source-validation-receipt.json",
    "artifact-manifest.json",
)


def fail(message: str) -> None:
    raise SystemExit(f"upstream-policy-revision-build: {message}")


def load_object(path: Path) -> Json:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        fail(f"{path} must contain a JSON object")
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def repo_path(value: str) -> Path:
    path = (ROOT / value).resolve()
    try:
        path.relative_to(ROOT)
    except ValueError:
        fail(f"registry path escapes the repository: {value}")
    return path


def validate_sources(registry: Json) -> dict[str, dict[str, Path]]:
    revisions = registry.get("revisions")
    if not isinstance(revisions, list) or len(revisions) != 2:
        fail("source registry must contain two revisions")
    sources: dict[str, dict[str, Path]] = {}
    for row in revisions:
        if not isinstance(row, dict):
            fail("source registry contains a malformed revision")
        migration_id = str(row["migration_id"])
        if migration_id in sources:
            fail(f"source registry repeats {migration_id}")
        paths: dict[str, Path] = {}
        for revision in ("old", "new"):
            path = repo_path(str(row[f"{revision}_source"]))
            expected = str(row[f"{revision}_sha256"])
            if sha256_file(path) != expected:
                fail(f"source digest differs for {migration_id}/{revision}")
            paths[revision] = path
        sources[migration_id] = paths
    for key in ("license", "notice"):
        path = repo_path(str(registry[f"{key}_path"]))
        if sha256_file(path) != str(registry[f"{key}_sha256"]):
            fail(f"{key} digest differs")
    return sources


def opa_metadata(opa: Path) -> Json:
    completed = subprocess.run(
        [str(opa), "version"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        fail(f"OPA version failed: {completed.stderr.strip()}")
    fields: dict[str, str] = {}
    for line in completed.stdout.splitlines():
        if ":" in line:
            key, value = line.split(":", maxsplit=1)
            fields[key.strip()] = value.strip()
    version = fields.get("Version")
    if version != "1.19.1":
        fail(f"expected OPA 1.19.1, found {version!r}")
    return {
        "binary_sha256": sha256_file(opa),
        "build_commit": fields.get("Build Commit"),
        "go_version": fields.get("Go Version"),
        "platform": fields.get("Platform"),
        "rego_version": fields.get("Rego Version"),
        "version": version,
    }


def opa_violation_count(
    opa: Path,
    policy_path: Path,
    case: UpstreamPolicyCase,
) -> int:
    with tempfile.TemporaryDirectory(prefix="cpb-upstream-opa-") as directory:
        data_path = Path(directory) / "data.json"
        data_path.write_text(canonical_json(case.data_document) + "\n", encoding="utf-8")
        completed = subprocess.run(
            [
                str(opa),
                "eval",
                "--v0-compatible",
                "--format=json",
                "--stdin-input",
                "--data",
                str(policy_path),
                "--data",
                str(data_path),
                case.query,
            ],
            input=canonical_json(case.input_document),
            check=False,
            capture_output=True,
            text=True,
        )
    if completed.returncode != 0:
        fail(
            f"OPA evaluation failed for {case.pair_id}/{policy_path.name}: "
            f"{completed.stderr.strip()}"
        )
    payload = json.loads(completed.stdout)
    try:
        value = payload["result"][0]["expressions"][0]["value"]
    except (KeyError, IndexError, TypeError) as exc:
        fail(f"OPA returned a malformed result for {case.pair_id}: {exc}")
    if not isinstance(value, list):
        fail(f"OPA query did not return a violation collection for {case.pair_id}")
    return len(value)


def revision_members(pair_id: str) -> dict[Revision, str]:
    digest = sha256_bytes(pair_id.encode("utf-8"))
    old_suffix, new_suffix = ("a", "b") if int(digest[-1], 16) % 2 == 0 else ("b", "a")
    return {"old": f"{pair_id}-{old_suffix}", "new": f"{pair_id}-{new_suffix}"}


def source_diff_coordinates(old_source: str, new_source: str) -> Json:
    old_lines = old_source.splitlines()
    new_lines = new_source.splitlines()
    matcher = difflib.SequenceMatcher(a=old_lines, b=new_lines, autojunk=False)
    changed_old: list[int] = []
    changed_new: list[int] = []
    operations: list[Json] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        changed_old.extend(range(i1 + 1, i2 + 1))
        changed_new.extend(range(j1 + 1, j2 + 1))
        operations.append(
            {
                "operation": tag,
                "old_lines_1_based": list(range(i1 + 1, i2 + 1)),
                "new_lines_1_based": list(range(j1 + 1, j2 + 1)),
            }
        )
    return {
        "changed_old_lines": changed_old,
        "changed_new_lines": changed_new,
        "operations": operations,
    }


def artifact_rows(root: Path, paths: tuple[str, ...]) -> Json:
    return {path: sha256_file(root / path) for path in paths}


def build(opa: Path, output_root: Path) -> None:
    registry = load_object(REGISTRY_PATH)
    sources = validate_sources(registry)
    runtime = opa_metadata(opa)
    cases = upstream_policy_cases()
    if len(cases) != 12 or len({case.pair_id for case in cases}) != 12:
        fail("finite context grammar must contain twelve unique pairs")

    items: list[Json] = []
    gold: list[Json] = []
    pairs: list[Json] = []
    packet_records: list[Json] = []
    difference_rows: list[PolicyDifference] = []
    oracle_rows: list[Json] = []
    transition_counts: Counter[str] = Counter()
    migration_counts: Counter[str] = Counter()
    factor_support: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))

    for case in cases:
        members = revision_members(case.pair_id)
        decisions: dict[Revision, Json] = {}
        source_texts: dict[Revision, str] = {}
        for revision in ("old", "new"):
            typed_revision: Revision = revision
            source_path = sources[case.migration_id][revision]
            source_text = source_path.read_text(encoding="utf-8")
            source_texts[typed_revision] = source_text
            count = opa_violation_count(opa, source_path, case)
            decision = expected_decision(
                case,
                typed_revision,
                observed_violation_count=count,
            )
            validate_with_schema(
                decision,
                SCHEMA_PATH,
                f"{case.pair_id}/{typed_revision} OPA decision",
            )
            decisions[typed_revision] = decision
            item_id = members[typed_revision]
            model_visible: Json = {
                "base_data": case.data_document,
                "input": case.input_document,
                "policy_language": "Rego v0",
                "policy_source": source_text,
                "query": case.query,
            }
            prompt = render_prompt(case, source_text)
            prompt_hash = sha256_bytes(prompt.encode("utf-8"))
            items.append(
                {
                    "id": item_id,
                    "migration_id": case.migration_id,
                    "model_visible": model_visible,
                    "pair_id": case.pair_id,
                }
            )
            gold.append(
                {
                    "decision": decision,
                    "id": item_id,
                    "migration_id": case.migration_id,
                    "pair_id": case.pair_id,
                    "revision": typed_revision,
                }
            )
            packet_records.append(
                {
                    "item_id": item_id,
                    "pair_id": case.pair_id,
                    "prompt": prompt,
                    "prompt_sha256": prompt_hash,
                }
            )
            oracle_rows.append(
                {
                    "action": decision["action"],
                    "item_id": item_id,
                    "pair_id": case.pair_id,
                    "revision": typed_revision,
                    "violation_count": count,
                }
            )

        old_action = str(decisions["old"]["action"])
        new_action = str(decisions["new"]["action"])
        if old_action == new_action:
            fail(f"{case.pair_id} is outside the behavioral difference set")
        edge = f"{old_action}->{new_action}"
        transition_counts[edge] += 1
        migration_counts[case.migration_id] += 1
        for factor, value in case.factors.items():
            rendered = canonical_json(value)
            factor_support[case.migration_id][factor].add(rendered)
        pairs.append(
            {
                "action_transition": edge,
                "changed_rule": case.rule_id,
                "controlled_json_pointers": ["/model_visible/policy_source"],
                "factors": case.factors,
                "member_ids": sorted(members.values()),
                "migration_id": case.migration_id,
                "new_id": members["new"],
                "old_id": members["old"],
                "pair_id": case.pair_id,
            }
        )
        difference_rows.append(
            PolicyDifference(
                context_id=case.pair_id,
                left_action=old_action,
                right_action=new_action,
                witnessed_rules=frozenset({case.rule_id}),
            )
        )
        if source_texts["old"] == source_texts["new"]:
            fail(f"{case.migration_id} source bytes do not change")

    items.sort(key=lambda row: str(row["id"]))
    gold.sort(key=lambda row: str(row["id"]))
    pairs.sort(key=lambda row: str(row["pair_id"]))
    packet_records.sort(key=lambda row: str(row["item_id"]))
    oracle_rows.sort(key=lambda row: str(row["item_id"]))
    required_rules = sorted({rule for row in difference_rows for rule in row.witnessed_rules})
    required_edges = sorted({row.edge for row in difference_rows})
    selected = minimum_complete_suite(
        difference_rows,
        required_rules=required_rules,
        required_edges=required_edges,
    )
    if selected is None:
        fail("finite grammar has no jointly adequate minimum suite")
    report = adequacy(
        selected,
        required_rules=required_rules,
        required_edges=required_edges,
    )
    if len(selected) != 2 or not report.complete:
        fail("expected a two-pair joint-adequacy witness")

    output_root.mkdir(parents=True, exist_ok=True)
    dataset_root = output_root / "dataset"
    write_jsonl(dataset_root / "evaluation-items.jsonl", items)
    write_jsonl(dataset_root / "evaluation-gold.jsonl", gold)
    write_json(dataset_root / "evaluation-pairs.json", pairs)
    packet: Json = {
        "contains_gold": False,
        "pair_count": len(pairs),
        "records": packet_records,
        "schema_version": "1.0.0",
    }
    packet["packet_sha256"] = sha256_bytes(canonical_json(packet).encode("utf-8"))
    write_json(dataset_root / "evaluation-prompt-packet.json", packet)

    coverage: Json = {
        "candidate_pairs": len(pairs),
        "changed_rules": required_rules,
        "contexts_per_transition": dict(sorted(transition_counts.items())),
        "factor_level_support": {
            migration: {
                factor: sorted(values) for factor, values in sorted(migration_factors.items())
            }
            for migration, migration_factors in sorted(factor_support.items())
        },
        "migrations": dict(sorted(migration_counts.items())),
        "reachable_action_edges": [f"{left}->{right}" for left, right in required_edges],
        "scope": (
            "Complete relative to the committed twelve-context finite grammar, two upstream "
            "revision rules, and two observed old-to-new action edges."
        ),
        "schema_version": "1.0.0",
    }
    write_json(output_root / "coverage.json", coverage)

    minimum: Json = {
        "candidate_pairs": len(pairs),
        "coverage": {
            "action_edges": {"covered": len(report.covered_edges), "total": len(required_edges)},
            "changed_rules": {
                "covered": len(report.covered_rules),
                "total": len(required_rules),
            },
        },
        "lower_bound_pairs": len(required_edges),
        "lower_bound_reason": (
            "Each pair realizes one old-to-new action edge, so two distinct required edges need "
            "at least two pairs."
        ),
        "schema_version": "1.0.0",
        "selected_pair_ids": [row.context_id for row in selected],
        "status": "PROVABLY_MINIMUM_RELATIVE_TO_COMMITTED_GRAMMAR",
        "witness_pairs": len(selected),
    }
    write_json(output_root / "minimum-suite.json", minimum)

    registry_by_id = {
        str(row["migration_id"]): row for row in registry["revisions"] if isinstance(row, dict)
    }
    source_rows: list[Json] = []
    for migration_id, paths in sorted(sources.items()):
        old_text = paths["old"].read_text(encoding="utf-8")
        new_text = paths["new"].read_text(encoding="utf-8")
        source_rows.append(
            {
                "diff_coordinates": source_diff_coordinates(old_text, new_text),
                "migration_id": migration_id,
                "new_sha256": sha256_file(paths["new"]),
                "old_sha256": sha256_file(paths["old"]),
                "upstream_change_commit": registry_by_id[migration_id]["change_commit"],
                "upstream_change_url": registry_by_id[migration_id]["change_url"],
                "upstream_regression_test": registry_by_id[migration_id]["upstream_test"],
            }
        )
    source_receipt: Json = {
        "credentials_retained": False,
        "finite_grammar_oracle_evaluations": oracle_rows,
        "model_calls": 0,
        "opa_runtime": runtime,
        "registry_sha256": sha256_file(REGISTRY_PATH),
        "schema_version": "1.0.0",
        "source_bytes_match_registry": True,
        "sources": source_rows,
        "status": "OPA_EXECUTION_REPRODUCED_BOTH_UPSTREAM_BEHAVIOR_CHANGES",
    }
    write_json(output_root / "source-validation-receipt.json", source_receipt)

    plan: Json = {
        "action_vocabulary": ["ALLOW", "HOLD"],
        "author_constructed_contexts": len(cases),
        "candidate_pairs": len(pairs),
        "candidate_items": len(items),
        "controlled_coordinate": "/model_visible/policy_source",
        "external_revision_count": len(migration_counts),
        "gold_source": "OPA 1.19.1 execution of exact commit-pinned upstream Rego bytes",
        "human_annotator_count": 0,
        "interpretation": (
            "The two policy revisions are independently authored upstream operational changes. "
            "The twelve admission contexts are author-constructed finite-grammar probes. Results "
            "measure route conformance on those probes and do not estimate production frequency."
        ),
        "model_calls_before_freeze": 0,
        "pair_balance": dict(sorted(transition_counts.items())),
        "response_schema": SCHEMA_PATH.relative_to(ROOT).as_posix(),
        "schema_version": "1.0.0",
        "status": "DATASET_READY_FOR_PREINFERENCE_COMMIT",
    }
    write_json(output_root / "dataset-plan.json", plan)

    tracked = tuple(path for path in GENERATED_PATHS if path != "artifact-manifest.json")
    manifest: Json = {
        "files": artifact_rows(output_root, tracked),
        "schema_version": "1.0.0",
        "source_files": {
            path.relative_to(ROOT).as_posix(): sha256_file(path)
            for migration in sources.values()
            for path in migration.values()
        },
        "status": "COMPLETE_DETERMINISTIC_BUILD",
    }
    manifest["response_schema_sha256"] = sha256_file(SCHEMA_PATH)
    manifest["self_digest"] = sha256_bytes(canonical_json(manifest).encode("utf-8"))
    write_json(output_root / "artifact-manifest.json", manifest)


def compare_build(expected_root: Path, candidate_root: Path) -> None:
    differences: list[str] = []
    for relative in GENERATED_PATHS:
        expected = expected_root / relative
        candidate = candidate_root / relative
        if not expected.is_file() or expected.read_bytes() != candidate.read_bytes():
            differences.append(relative)
    if differences:
        fail(f"deterministic rebuild differs: {differences}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--opa", type=Path, default=Path(shutil.which("opa") or "opa"))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    opa = args.opa.resolve()
    if not opa.is_file() or not re.fullmatch(r"opa(?:\.v[0-9.]+)?", opa.name):
        fail(f"OPA executable is unavailable or unexpectedly named: {opa}")
    if args.check:
        with tempfile.TemporaryDirectory(prefix="cpb-upstream-build-") as directory:
            candidate = Path(directory) / "upstream-policy-revisions-v1"
            build(opa, candidate)
            compare_build(STUDY_ROOT, candidate)
    else:
        existing = [relative for relative in GENERATED_PATHS if (STUDY_ROOT / relative).exists()]
        if existing:
            fail(f"refusing to overwrite generated artifacts: {existing}")
        build(opa, STUDY_ROOT)
    print(
        "upstream-policy-revision-build: "
        f"pairs=12 items=24 opa={opa_metadata(opa)['version']} check={args.check}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
