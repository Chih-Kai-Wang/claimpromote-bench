from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from claimpromotebench.baselines import baseline_decision
from claimpromotebench.contributions import (
    main,
    make_contribution_id,
    prepare_contribution,
    validate_contribution,
    validate_contribution_tree,
)
from claimpromotebench.dataset import repository_root, write_jsonl
from claimpromotebench.errors import DatasetIntegrityError
from claimpromotebench.hashing import sha256_bytes, sha256_file
from claimpromotebench.prompts import render_prompt

IDENTITY = {
    "model_id": "contributor/local-smoke",
    "model_artifact_sha256": "sha256:" + "1" * 64,
    "quantization": "Q4_K_M",
    "runtime_commit": "runtime-commit",
    "arm": "ledger",
    "seed": 104729,
    "hardware": "community-test-hardware",
}


def _exact_prompt(rendered: str) -> str:
    decoding = json.loads(
        (repository_root() / "configs" / "decoding-v1.json").read_text(encoding="utf-8")
    )
    return f"{rendered.rstrip()}\n\n{decoding['control_instruction']}\n"


def _write_run(
    path: Path,
    *,
    inputs,
    policy,
    evaluation_time: str,
    dataset_dir: Path,
    identity: dict[str, object] | None = None,
) -> None:
    run_identity = identity or IDENTITY
    records = []
    for item in inputs:
        decision = baseline_decision(
            "policy_oracle",
            item,
            policy,
            evaluation_time,
        )
        rendered = render_prompt(
            item,
            str(run_identity["arm"]),
            dataset_dir,
            policy=policy,
            evaluation_time=evaluation_time,
        )
        prompt = _exact_prompt(rendered)
        records.append(
            {
                "item_id": item["id"],
                **run_identity,
                "prompt_sha256": sha256_bytes(prompt.encode("utf-8")),
                "parse_status": "OK",
                "raw_decision": decision,
                "final_decision": decision,
                "latency_ms": 1,
                "output_tokens": 10,
                "verifier_calls": 0,
            }
        )
    write_jsonl(path, records)


def _write_manifest(
    path: Path,
    *,
    root: Path,
    run_path: Path,
    expected_run: dict[str, object] | None = None,
) -> dict[str, object]:
    manifest: dict[str, object] = {
        "schema_version": "1.0.0",
        "contribution_id": "sha256:" + "0" * 64,
        "contributor": {
            "github_login": "community-contributor",
            "display_name": "Community Contributor",
            "attestation": True,
        },
        "dataset_gold_file": "data/alpha/gold.jsonl",
        "dataset_manifest_sha256": sha256_file(root / "data" / "alpha" / "manifest.json"),
        "run_file": run_path.name,
        "run_file_sha256": sha256_file(run_path),
        "expected_run": deepcopy(expected_run or IDENTITY),
        "license": "MIT",
        "consent": {
            "redistribution": True,
            "public_attribution": True,
            "contains_secrets": False,
            "contains_personal_data": False,
            "terms_accepted": True,
        },
        "reproduction": {
            "command": ["llama-cli", "--seed", "104729"],
            "runtime": "llama.cpp pinned test runtime",
            "source_revision": "model-revision",
            "network_access": False,
            "notes": "Synthetic test contribution.",
        },
    }
    manifest["contribution_id"] = make_contribution_id(manifest)
    path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


@pytest.fixture
def contribution_package(
    root: Path,
    dataset_dir: Path,
    inputs,
    policy,
    manifest,
    tmp_path: Path,
) -> tuple[Path, Path]:
    directory = tmp_path / "one"
    directory.mkdir()
    run_path = directory / "run.jsonl"
    _write_run(
        run_path,
        inputs=inputs,
        policy=policy,
        evaluation_time=str(manifest["evaluation_time"]),
        dataset_dir=dataset_dir,
    )
    manifest_path = directory / "contribution.json"
    _write_manifest(
        manifest_path,
        root=root,
        run_path=run_path,
    )
    return manifest_path, run_path


def test_prepare_contribution_derives_immutable_fields(
    root: Path,
    contribution_package: tuple[Path, Path],
    capsys,
) -> None:
    manifest_path, _run_path = contribution_package
    value = json.loads(manifest_path.read_text(encoding="utf-8"))
    for field in (
        "contribution_id",
        "dataset_manifest_sha256",
        "run_file_sha256",
        "expected_run",
    ):
        value.pop(field)
    manifest_path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    prepared = prepare_contribution(manifest_path, root=root)
    assert prepared["expected_run"] == IDENTITY
    assert prepared["contribution_id"] == make_contribution_id(prepared)

    assert main(["--prepare", str(manifest_path), "--write"]) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["status"] == "PREPARED"
    assert validate_contribution(manifest_path, root=root)["status"] == "PASS"


def test_valid_contribution_is_hash_bound(
    root: Path,
    contribution_package: tuple[Path, Path],
) -> None:
    manifest_path, _run_path = contribution_package
    report = validate_contribution(manifest_path, root=root)
    assert report["status"] == "PASS"
    assert report["identity"] == IDENTITY
    assert report["summary"]["instances"] == 40
    assert report["summary"]["format_errors"] == 0
    assert report["summary"]["raw_auprc_stepwise"] == 1.0
    assert report["summary"]["effective_false_promotion_rate"] == 0.0


def test_contribution_rejects_run_tampering(
    root: Path,
    contribution_package: tuple[Path, Path],
) -> None:
    manifest_path, run_path = contribution_package
    run_path.write_text(
        run_path.read_text(encoding="utf-8") + "\n",
        encoding="utf-8",
    )
    with pytest.raises(DatasetIntegrityError, match="run_file_sha256"):
        validate_contribution(manifest_path, root=root)


def test_contribution_rejects_manifest_identity_mismatch(
    root: Path,
    contribution_package: tuple[Path, Path],
) -> None:
    manifest_path, _run_path = contribution_package
    value = json.loads(manifest_path.read_text(encoding="utf-8"))
    value["expected_run"]["model_id"] = "different/model"
    value["contribution_id"] = make_contribution_id(value)
    manifest_path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(DatasetIntegrityError, match="expected_run"):
        validate_contribution(manifest_path, root=root)


def test_contribution_rejects_run_path_escape(
    root: Path,
    contribution_package: tuple[Path, Path],
) -> None:
    manifest_path, run_path = contribution_package
    outside = manifest_path.parent.parent / "outside.jsonl"
    outside.write_bytes(run_path.read_bytes())
    value = json.loads(manifest_path.read_text(encoding="utf-8"))
    value["run_file"] = "../outside.jsonl"
    manifest_path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(DatasetIntegrityError, match="escapes"):
        validate_contribution(manifest_path, root=root)


def test_contribution_tree_and_cli_validate_all(
    root: Path,
    contribution_package: tuple[Path, Path],
    tmp_path: Path,
    capsys,
) -> None:
    manifest_path, _run_path = contribution_package
    tree = validate_contribution_tree(manifest_path.parent.parent, root=root)
    assert tree["status"] == "PASS"
    assert tree["contributions"] == 1

    output = tmp_path / "contribution-report.json"
    assert (
        main(
            [
                "--manifest",
                str(manifest_path),
                "--out",
                str(output),
            ]
        )
        == 0
    )
    summary = json.loads(capsys.readouterr().out)
    report = json.loads(output.read_text(encoding="utf-8"))
    assert summary["status"] == "PASS"
    assert summary["out"] == str(output)
    assert report["run_id"] == tree["run_ids"][0]


def test_contribution_tree_rejects_duplicate_run(
    root: Path,
    contribution_package: tuple[Path, Path],
) -> None:
    manifest_path, run_path = contribution_package
    duplicate_dir = manifest_path.parent.parent / "duplicate"
    duplicate_dir.mkdir()
    duplicate_run = duplicate_dir / "run.jsonl"
    duplicate_run.write_bytes(run_path.read_bytes())
    duplicate_manifest = duplicate_dir / "contribution.json"
    _write_manifest(
        duplicate_manifest,
        root=root,
        run_path=duplicate_run,
    )
    with pytest.raises(DatasetIntegrityError, match="duplicate contribution_id"):
        validate_contribution_tree(manifest_path.parent.parent, root=root)
