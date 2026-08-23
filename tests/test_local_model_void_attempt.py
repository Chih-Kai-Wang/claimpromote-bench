from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from seal_local_model_void_attempt import derive  # noqa: E402

ATTEMPT = ROOT / "v2" / "local-model-replication-v1" / "frozen" / "slsa"


def test_first_local_attempt_is_sealed_without_terminal_or_selected_output() -> None:
    expected = derive(
        ATTEMPT / "study-plan.json",
        ATTEMPT / "request-schedule.json",
        ATTEMPT / "journal",
        ATTEMPT / "results",
        ROOT / "v2" / "schemas" / "stronger-model-run-record.schema.json",
    )
    receipt = json.loads((ATTEMPT / "void-exclusion-receipt.json").read_text(encoding="utf-8"))
    assert receipt == expected
    assert receipt["observed_counts"]["application_invocations"] == 1
    assert receipt["observed_counts"]["durable_terminal_records"] == 0
    assert receipt["observed_counts"]["retained_model_outputs"] == 0
    assert receipt["decision"]["attempt_enters_manuscript"] is False
    assert receipt["decision"]["resume_or_overwrite_used"] is False
