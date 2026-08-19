"""Regression gate for the preregistered ClaimPromoteBench v1 design arithmetic."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v1_preregistered_plan_is_internally_consistent() -> None:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate_v1_plan.py")],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert '"status": "PLAN_PASS"' in completed.stdout
