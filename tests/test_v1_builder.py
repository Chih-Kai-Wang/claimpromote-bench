"""End-to-end construction gate for the public ClaimPromoteBench v1 dev split."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_public_v1_dev_split_builds_and_matches_preregistration(tmp_path: Path) -> None:
    dataset = tmp_path / "v1-dev"
    built = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_v1_dataset.py"),
            "--split",
            "dev",
            "--out",
            str(dataset),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert built.returncode == 0, built.stderr or built.stdout
    report = json.loads(built.stdout)
    assert report["status"] == "PASS"
    assert report["pairs"] == 50
    assert report["instances"] == 100

    audited = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "validate_v1_plan.py"),
            "--dev-dir",
            str(dataset),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert audited.returncode == 0, audited.stderr or audited.stdout
    audit = json.loads(audited.stdout)
    assert audit["plan"]["status"] == "PLAN_PASS"
    assert audit["dev"]["status"] == "DATASET_PASS"
