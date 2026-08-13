from __future__ import annotations

import json
from pathlib import Path

from claimpromotebench.cli import main
from claimpromotebench.dataset import load_jsonl
from claimpromotebench.hashing import sha256_bytes


def test_cli_validate(dataset_dir: Path, capsys) -> None:
    assert main(["validate", str(dataset_dir)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["instances"] == 40


def test_cli_render_hashes_complete_prompts(dataset_dir: Path, tmp_path: Path, capsys) -> None:
    rendered = tmp_path / "prompts.jsonl"
    assert (
        main(
            [
                "render",
                "--arm",
                "narrative",
                "--inputs",
                str(dataset_dir / "inputs.jsonl"),
                "--out",
                str(rendered),
            ]
        )
        == 0
    )
    capsys.readouterr()
    records = load_jsonl(rendered)
    assert len(records) == 40
    assert all(
        record["prompt_sha256"] == sha256_bytes(record["prompt"].encode("utf-8"))
        for record in records
    )


def test_cli_baseline_and_evaluate(dataset_dir: Path, tmp_path: Path, capsys) -> None:
    predictions = tmp_path / "oracle.jsonl"
    assert (
        main(
            [
                "baseline",
                "policy_oracle",
                "--inputs",
                str(dataset_dir / "inputs.jsonl"),
                "--out",
                str(predictions),
            ]
        )
        == 0
    )
    capsys.readouterr()
    assert len(load_jsonl(predictions)) == 40
    assert (
        main(
            [
                "evaluate",
                "--gold",
                str(dataset_dir / "gold.jsonl"),
                "--runs",
                str(predictions),
                "--bootstrap-samples",
                "25",
            ]
        )
        == 0
    )
    report = json.loads(capsys.readouterr().out)
    assert report["primary"]["paired_transition_accuracy"]["value"] == 1.0


def test_cli_missing_prediction_is_format_error(dataset_dir: Path, tmp_path: Path, capsys) -> None:
    empty = tmp_path / "empty.jsonl"
    empty.write_text("", encoding="utf-8")
    assert (
        main(
            [
                "evaluate",
                "--gold",
                str(dataset_dir / "gold.jsonl"),
                "--runs",
                str(empty),
            ]
        )
        == 1
    )
    assert "coverage mismatch" in capsys.readouterr().err


def test_cli_evaluates_complete_run_records(dataset_dir: Path, tmp_path: Path, capsys) -> None:
    baseline = tmp_path / "oracle.jsonl"
    assert (
        main(
            [
                "baseline",
                "policy_oracle",
                "--inputs",
                str(dataset_dir / "inputs.jsonl"),
                "--out",
                str(baseline),
            ]
        )
        == 0
    )
    capsys.readouterr()
    run_records = []
    for record in load_jsonl(baseline):
        run_records.append(
            {
                "item_id": record["id"],
                "model_id": "deterministic-smoke",
                "model_artifact_sha256": "sha256:" + "1" * 64,
                "quantization": None,
                "runtime_commit": None,
                "arm": "ledger_verifier_gate",
                "seed": 104729,
                "prompt_sha256": sha256_bytes(record["id"].encode()),
                "parse_status": "OK",
                "raw_decision": record["decision"],
                "final_decision": record["decision"],
                "latency_ms": 1,
                "output_tokens": 10,
                "verifier_calls": 1,
                "hardware": "test",
            }
        )
    runs = tmp_path / "runs.jsonl"
    from claimpromotebench.dataset import write_jsonl

    write_jsonl(runs, run_records)
    assert (
        main(
            [
                "evaluate-runs",
                "--gold",
                str(dataset_dir / "gold.jsonl"),
                "--runs",
                str(runs),
                "--bootstrap-samples",
                "25",
            ]
        )
        == 0
    )
    report = json.loads(capsys.readouterr().out)
    assert report["raw_intent"]["primary"]["paired_transition_accuracy"]["value"] == 1.0
    assert report["effective_system"]["primary"]["false_promotion_rate"]["value"] == 0.0
    assert report["parse_status"] == {"ok": 40, "format_error": 0}


def test_cli_format_error_run_is_not_silent_hold(dataset_dir: Path, tmp_path: Path, capsys) -> None:
    inputs = load_jsonl(dataset_dir / "inputs.jsonl")
    gold = load_jsonl(dataset_dir / "gold.jsonl")
    decisions = {
        record["id"]: {
            key: value
            for key, value in record["decision"].items()
            if key != "minimal_missing_evidence"
        }
        for record in gold
    }
    runs_data = []
    for index, item in enumerate(inputs):
        is_error = index == 0
        runs_data.append(
            {
                "item_id": item["id"],
                "model_id": "broken",
                "model_artifact_sha256": "sha256:" + "1" * 64,
                "arm": "ledger",
                "seed": 1,
                "prompt_sha256": "sha256:" + "2" * 64,
                "parse_status": "FORMAT_ERROR" if is_error else "OK",
                "raw_decision": None if is_error else decisions[item["id"]],
                "final_decision": None if is_error else decisions[item["id"]],
                "latency_ms": 1,
                "output_tokens": 0,
                "verifier_calls": 0,
            }
        )
    runs = tmp_path / "format-error.jsonl"
    from claimpromotebench.dataset import write_jsonl

    write_jsonl(runs, runs_data)
    assert (
        main(
            [
                "evaluate-runs",
                "--gold",
                str(dataset_dir / "gold.jsonl"),
                "--runs",
                str(runs),
            ]
        )
        == 0
    )
    report = json.loads(capsys.readouterr().out)
    assert report["parse_status"] == {"ok": 39, "format_error": 1}
    assert report["raw_intent"]["secondary"]["calibration_coverage"] == 39 / 40
    assert report["gate"]["format_error_count"] == 1
