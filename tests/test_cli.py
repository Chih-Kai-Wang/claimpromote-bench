from __future__ import annotations

import json
from pathlib import Path

from claimpromotebench.cli import main
from claimpromotebench.dataset import load_jsonl


def test_cli_validate(dataset_dir: Path, capsys) -> None:
    assert main(["validate", str(dataset_dir)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["instances"] == 40


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
