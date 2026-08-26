from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from derive_minimal_policy_migration_hosted_eligibility import classify_records  # noqa: E402
from freeze_minimal_policy_migration_hosted_study import (  # noqa: E402
    BASELINE_ROOT,
    DATASET_ROOT,
    EXPECTED_ROOT,
    MINIMAL_SUITE_PATH,
    RESOURCE_EXHAUSTION_RULE,
    build_schedule,
    hosted_lanes,
)
from validate_minimal_policy_migration_hosted_study import validate_freeze  # noqa: E402

Json = dict[str, Any]


def load_object(path: Path) -> Json:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def terminal_rows(*, detail: str | None = None, start: int = 0) -> list[Json]:
    rows: list[Json] = []
    for sequence in range(40):
        failed = sequence >= start and detail is not None
        rows.append(
            {
                "sequence": sequence,
                "record": {
                    "transport_status": "ERROR" if failed else "OK",
                    "transport_error": detail if failed else None,
                    "parse_status": "TRANSPORT_ERROR" if failed else "OK",
                },
            }
        )
    return rows


def test_minimum_hosted_schedule_covers_only_the_frozen_witness() -> None:
    suite = load_object(MINIMAL_SUITE_PATH)
    packet = load_object(DATASET_ROOT / "evaluation-prompt-packet.json")
    lanes = hosted_lanes()
    plan: Json = {
        "study_id": "test-minimal-policy-migration",
        "formal_lanes": lanes,
        "execution": {"base_lane_order": [str(row["lane_id"]) for row in lanes]},
    }
    schedule = build_schedule(plan, packet, suite)
    assert schedule["planned_cells"] == 40
    assert {str(row["item_id"]) for row in schedule["cells"]} == set(suite["selected_item_ids"])
    assert Counter(str(row["lane_id"]) for row in schedule["cells"]) == Counter(
        {str(row["lane_id"]): 20 for row in lanes}
    )
    assert [int(row["sequence"]) for row in schedule["cells"]] == list(range(40))


def test_minimum_hosted_resource_exclusion_requires_an_explicit_persistent_tail() -> None:
    exhausted = classify_records(
        terminal_rows(detail="Shared subscription quota exhausted", start=0)
    )
    assert exhausted["eligible_for_route_conformance_reporting"] is False
    assert exhausted["persistent_exhaustion_trigger_sequence"] == 0

    ordinary = classify_records(terminal_rows(detail="HTTP 503 server error", start=0))
    assert ordinary["eligible_for_route_conformance_reporting"] is True
    assert ordinary["persistent_exhaustion_trigger_sequence"] is None

    late = classify_records(terminal_rows(detail="Shared subscription quota exhausted", start=20))
    assert late["eligible_for_route_conformance_reporting"] is True
    assert late["persistent_exhaustion_trigger_sequence"] is None


def test_frozen_minimum_hosted_study_validates_without_credentials() -> None:
    report = validate_freeze(
        EXPECTED_ROOT / "study-plan.json",
        EXPECTED_ROOT / "request-schedule.json",
        DATASET_ROOT,
        BASELINE_ROOT,
    )
    assert report["status"] == "MINIMAL_POLICY_MIGRATION_HOSTED_FREEZE_VALID"
    assert report["credentials_loaded"] is False
    assert (report["items"], report["pairs"], report["cells"]) == (20, 10, 40)
    plan = load_object(EXPECTED_ROOT / "study-plan.json")
    assert plan["execution"]["resource_exhaustion_eligibility_rule"] == RESOURCE_EXHAUSTION_RULE
    assert plan["statistics"]["strict_smoke_pass_rule"].startswith("A lane passes only")
