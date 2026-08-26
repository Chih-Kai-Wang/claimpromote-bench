from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from analyze_balanced_public_challenge import derive_reporting_metrics  # noqa: E402
from build_policy_switch_study import (  # noqa: E402
    BASE_POLICY_PATH,
    SWITCH_POLICY_PATH,
    changed_paths,
    public_switch_contract,
)
from freeze_slsa_portability_study import request_body  # noqa: E402
from policy_switch import evaluate_policy_switch, load_switch_policy  # noqa: E402
from slsa_policy import load_slsa_policy  # noqa: E402
from train_policy_switch_baselines import train  # noqa: E402
from validate_policy_switch_study import validate_dataset, validate_freeze  # noqa: E402

from claimpromotebench.dataset import load_json, load_jsonl  # noqa: E402
from claimpromotebench.hashing import canonical_json, sha256_file  # noqa: E402

STUDY_ROOT = ROOT / "v2" / "policy-switch-v1" / "frozen"
DATASET = STUDY_ROOT / "dataset"
BASELINE = STUDY_ROOT / "baseline"
PLAN = STUDY_ROOT / "study-plan.json"
SCHEDULE = STUDY_ROOT / "request-schedule.json"


def as_records(predictions: list[dict[str, object]]) -> list[dict[str, object]]:
    return [
        {
            "item_id": row["item_id"],
            "pair_id": row["pair_id"],
            "parse_status": "OK",
            "raw_decision": {"action": row["predicted_action"]},
        }
        for row in predictions
    ]


def test_policy_switch_dataset_recomputes_without_credentials() -> None:
    report = validate_dataset(DATASET)
    assert report["status"] == "POLICY_SWITCH_DATASET_VALID"
    assert report["development_items"] == 72
    assert report["evaluation_items"] == 120
    assert report["evaluation_pairs"] == 60


def test_policy_switch_pairs_change_only_active_profile() -> None:
    items = {
        str(row["id"]): row["model_visible"]
        for row in load_jsonl(DATASET / "evaluation-items.jsonl")
    }
    pairs = load_json(DATASET / "evaluation-pairs.json")
    assert isinstance(pairs, list)
    for pair in pairs:
        left, right = (items[str(item_id)] for item_id in pair["member_ids"])
        assert changed_paths(left, right) == ["/active_policy_profile"]


def test_policy_switch_gold_is_the_definitional_policy_ceiling() -> None:
    base_policy = load_slsa_policy(BASE_POLICY_PATH)
    switch_policy = load_switch_policy(SWITCH_POLICY_PATH, base_policy)
    items = {
        str(row["id"]): row["model_visible"]
        for row in load_jsonl(DATASET / "evaluation-items.jsonl")
    }
    for row in load_jsonl(DATASET / "evaluation-gold.jsonl"):
        assert (
            evaluate_policy_switch(items[str(row["id"])], switch_policy, base_policy)
            == row["decision"]
        )


def test_policy_switch_prompt_exposes_profiles_without_pair_metadata() -> None:
    base_policy = load_slsa_policy(BASE_POLICY_PATH)
    switch_policy = load_switch_policy(SWITCH_POLICY_PATH, base_policy)
    public_contract = canonical_json(public_switch_contract(switch_policy))
    packet = load_json(DATASET / "evaluation-prompt-packet.json")
    assert len(packet["records"]) == 120
    for record in packet["records"]:
        prompt = record["prompt"]
        assert public_contract in prompt
        assert "COUNTERFACTUAL_PROFILE_CONTRACT\n" in prompt
        assert "active_policy_profile" in prompt
        assert record["item_id"] not in prompt
        assert record["pair_id"] not in prompt
        assert "factor_id" not in prompt
        assert "binding_profile" not in prompt


def test_policy_switch_baselines_are_byte_reproducible(tmp_path: Path) -> None:
    output = tmp_path / "baseline"
    report = train(DATASET, output)
    assert report["evaluation_gold_loaded"] is False
    assert report["model_outputs_loaded"] is False
    assert sha256_file(output / "report.json") == sha256_file(BASELINE / "report.json")
    for comparator_id in ("policy_aware", "profile_blind"):
        assert sha256_file(output / f"{comparator_id}-predictions.jsonl") == sha256_file(
            BASELINE / f"{comparator_id}-predictions.jsonl"
        )


def test_policy_switch_baselines_expose_the_registered_shortcut() -> None:
    gold = load_jsonl(DATASET / "evaluation-gold.jsonl")
    pairs = load_json(DATASET / "evaluation-pairs.json")
    assert isinstance(pairs, list)
    aware = derive_reporting_metrics(
        gold,
        pairs,
        as_records(load_jsonl(BASELINE / "policy_aware-predictions.jsonl")),
    )
    blind = derive_reporting_metrics(
        gold,
        pairs,
        as_records(load_jsonl(BASELINE / "profile_blind-predictions.jsonl")),
    )
    assert (aware["correct_items"], aware["correct_pairs"]) == (120, 60)
    assert (blind["correct_items"], blind["correct_pairs"]) == (60, 0)


def test_policy_switch_execution_freeze_validates_without_credentials() -> None:
    report = validate_freeze(PLAN, SCHEDULE, DATASET, BASELINE)
    assert report["status"] == "POLICY_SWITCH_EXECUTION_FREEZE_VALID"
    assert report["credentials_loaded"] is False
    assert report["items"] == 120
    assert report["lanes"] == 2
    assert report["cells"] == 240


def test_policy_switch_repeated_configurations_keep_output_interfaces() -> None:
    plan = load_json(PLAN)
    packet = load_json(DATASET / "evaluation-prompt-packet.json")
    prompt = packet["records"][0]["prompt"]
    qwen, flash = plan["formal_lanes"]
    qwen_body = request_body(qwen, prompt)
    flash_body = request_body(flash, prompt)
    assert "response_format" not in qwen_body
    assert flash_body["response_format"]["type"] == "json_schema"
    assert qwen_body["messages"] == flash_body["messages"]


def test_policy_switch_schedule_rotates_lanes_and_covers_each_cell_once() -> None:
    schedule = load_json(SCHEDULE)
    lanes = schedule["base_lane_order"]
    cells = schedule["cells"]
    assert len(cells) == 240
    assert len({row["cell_id"] for row in cells}) == 240
    for item_index in range(120):
        block = cells[item_index * 2 : item_index * 2 + 2]
        rotation = item_index % 2
        assert [row["lane_id"] for row in block] == lanes[rotation:] + lanes[:rotation]
        assert len({row["item_id"] for row in block}) == 1
