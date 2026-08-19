from __future__ import annotations

import json
from pathlib import Path

from claimpromotebench.baselines import baseline_decision
from claimpromotebench.cli import main
from claimpromotebench.dataset import load_jsonl, repository_root, write_jsonl
from claimpromotebench.hashing import sha256_bytes
from claimpromotebench.prompts import render_prompt


def _exact_prompt(rendered: str) -> str:
    decoding = json.loads(
        (repository_root() / "configs" / "decoding-v1.json").read_text(encoding="utf-8")
    )
    return f"{rendered.rstrip()}\n\n{decoding['control_instruction']}\n"


def _write_run(
    dataset_dir: Path,
    output: Path,
    *,
    arm: str,
    baseline: str,
    policy: dict[str, object],
    evaluation_time: str,
) -> None:
    records = []
    for item in load_jsonl(dataset_dir / "inputs.jsonl"):
        decision = baseline_decision(
            baseline,
            item,
            policy,
            evaluation_time,
        )
        rendered = render_prompt(
            item,
            arm,
            dataset_dir,
            policy=policy,
            evaluation_time=evaluation_time,
        )
        prompt = _exact_prompt(rendered)
        records.append(
            {
                "item_id": item["id"],
                "model_id": "deterministic-study-smoke",
                "model_artifact_sha256": "sha256:" + "1" * 64,
                "quantization": None,
                "runtime_commit": "study-runtime",
                "arm": arm,
                "seed": 104729,
                "prompt_sha256": sha256_bytes(prompt.encode("utf-8")),
                "parse_status": "OK",
                "raw_decision": decision,
                "final_decision": decision,
                "latency_ms": 1,
                "output_tokens": 10,
                "verifier_calls": 0,
                "hardware": "test",
            }
        )
    write_jsonl(output, records)


def test_compare_runs_builds_deterministic_cumulative_study(
    dataset_dir: Path,
    tmp_path: Path,
    policy: dict[str, object],
    manifest: dict[str, object],
    capsys,
) -> None:
    evaluation_time = str(manifest["evaluation_time"])
    narrative = tmp_path / "narrative.jsonl"
    ledger = tmp_path / "ledger.jsonl"
    _write_run(
        dataset_dir,
        narrative,
        arm="narrative",
        baseline="policy_oracle",
        policy=policy,
        evaluation_time=evaluation_time,
    )
    _write_run(
        dataset_dir,
        ledger,
        arm="ledger",
        baseline="always_allow",
        policy=policy,
        evaluation_time=evaluation_time,
    )

    report_path = tmp_path / "study.json"
    command = [
        "compare-runs",
        "--gold",
        str(dataset_dir / "gold.jsonl"),
        "--runs",
        str(narrative),
        str(ledger),
        "--out",
        str(report_path),
    ]
    assert main(command) == 0
    report = json.loads(capsys.readouterr().out)
    assert report == json.loads(report_path.read_text(encoding="utf-8"))
    assert report["study_id"].startswith("sha256:")
    assert report["summary"] == {
        "runs": 2,
        "groups": 1,
        "complete_groups": 0,
        "comparisons": 1,
    }
    assert len({run["run_id"] for run in report["runs"]}) == 2

    group = report["groups"][0]
    assert group["arms_present"] == ["narrative", "ledger"]
    assert group["arms_missing"] == [
        "ledger_verifier",
        "ledger_verifier_gate",
    ]
    comparison = group["comparisons"][0]
    assert (comparison["arm_a"], comparison["arm_b"]) == (
        "narrative",
        "ledger",
    )
    deltas = comparison["effective_system"]["delta_b_minus_a"]
    assert deltas["false_promotion_rate"] == 1.0
    assert deltas["auprc_stepwise"] == -0.5
    assert "p_holm" in comparison["effective_system"]["mcnemar_exact"]

    reverse_command = [
        "compare-runs",
        "--gold",
        str(dataset_dir / "gold.jsonl"),
        "--runs",
        str(ledger),
        str(narrative),
    ]
    assert main(reverse_command) == 0
    reverse = json.loads(capsys.readouterr().out)
    assert reverse["study_id"] == report["study_id"]


def test_compare_runs_rejects_duplicate_content(
    dataset_dir: Path,
    tmp_path: Path,
    policy: dict[str, object],
    manifest: dict[str, object],
    capsys,
) -> None:
    run_path = tmp_path / "run.jsonl"
    _write_run(
        dataset_dir,
        run_path,
        arm="narrative",
        baseline="policy_oracle",
        policy=policy,
        evaluation_time=str(manifest["evaluation_time"]),
    )
    assert (
        main(
            [
                "compare-runs",
                "--gold",
                str(dataset_dir / "gold.jsonl"),
                "--runs",
                str(run_path),
                str(run_path),
            ]
        )
        == 1
    )
    assert "duplicate run content" in capsys.readouterr().err


def test_evaluate_runs_emits_hash_bound_run_identity(
    dataset_dir: Path,
    tmp_path: Path,
    policy: dict[str, object],
    manifest: dict[str, object],
    capsys,
) -> None:
    run_path = tmp_path / "run.jsonl"
    _write_run(
        dataset_dir,
        run_path,
        arm="narrative",
        baseline="policy_oracle",
        policy=policy,
        evaluation_time=str(manifest["evaluation_time"]),
    )
    assert (
        main(
            [
                "evaluate-runs",
                "--gold",
                str(dataset_dir / "gold.jsonl"),
                "--runs",
                str(run_path),
                "--bootstrap-samples",
                "0",
            ]
        )
        == 0
    )
    report = json.loads(capsys.readouterr().out)
    assert report["run"]["run_id"].startswith("sha256:")
    assert report["run"]["source_sha256"].startswith("sha256:")
    assert report["dataset"]["manifest_sha256"].startswith("sha256:")
    assert (
        report["raw_intent"]["secondary"]["precision_recall"]["auprc_stepwise"][
            "ci95_pair_bootstrap"
        ]["samples_defined"]
        == 0
    )
