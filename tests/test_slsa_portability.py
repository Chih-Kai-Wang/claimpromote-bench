from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from analyze_balanced_public_challenge import derive_reporting_metrics  # noqa: E402
from build_slsa_portability_study import changed_paths, public_contract  # noqa: E402
from freeze_slsa_portability_study import request_body  # noqa: E402
from slsa_policy import (  # noqa: E402
    diagnose_slsa_decision,
    evaluate_slsa,
    load_slsa_policy,
)
from train_slsa_structured_baseline import train  # noqa: E402
from validate_slsa_portability_freeze import validate_freeze  # noqa: E402
from validate_slsa_portability_study import validate_dataset  # noqa: E402

from claimpromotebench.dataset import load_json, load_jsonl  # noqa: E402
from claimpromotebench.hashing import canonical_json, sha256_file  # noqa: E402

STUDY_ROOT = ROOT / "v2" / "slsa-portability-v1"
DATASET = STUDY_ROOT / "dataset"
BASELINE = STUDY_ROOT / "baseline"
PLAN = STUDY_ROOT / "study-plan.json"
SCHEDULE = STUDY_ROOT / "request-schedule.json"
POLICY_PATH = STUDY_ROOT / "policy-contract.json"
SCHEMA = ROOT / "v2" / "schemas" / "slsa-agent-decision.schema.json"


def test_slsa_dataset_freeze_recomputes_without_credentials() -> None:
    report = validate_dataset(DATASET, verify_upstream=False)
    assert report["status"] == "SLSA_PORTABILITY_FREEZE_VALID"
    assert report["credentials_loaded"] is False
    assert report["development"] == {
        "items": 72,
        "pairs": 36,
        "factors": 12,
        "action_counts": {"ALLOW": 36, "DEMOTE": 12, "ESCALATE": 12, "HOLD": 12},
    }
    assert report["evaluation"] == {
        "items": 120,
        "pairs": 60,
        "factors": 12,
        "action_counts": {"ALLOW": 60, "DEMOTE": 20, "ESCALATE": 20, "HOLD": 20},
    }


def test_slsa_pairs_change_one_model_visible_field() -> None:
    items = {
        str(row["id"]): row["model_visible"]
        for row in load_jsonl(DATASET / "evaluation-items.jsonl")
    }
    pairs = load_json(DATASET / "evaluation-pairs.json")
    assert isinstance(pairs, list)
    for pair in pairs:
        left, right = (items[str(item_id)] for item_id in pair["member_ids"])
        assert changed_paths(left, right) == [pair["controlled_path"]]
        assert pair["controlled_path"].startswith("/evidence/0/observed/")


def test_slsa_gold_is_the_definitional_policy_ceiling() -> None:
    policy = load_slsa_policy(POLICY_PATH)
    items = {
        str(row["id"]): row["model_visible"]
        for row in load_jsonl(DATASET / "evaluation-items.jsonl")
    }
    gold = load_jsonl(DATASET / "evaluation-gold.jsonl")
    assert all(evaluate_slsa(items[str(row["id"])], policy) == row["decision"] for row in gold)


def test_slsa_prompt_contains_policy_but_not_pair_or_factor_metadata() -> None:
    policy = load_slsa_policy(POLICY_PATH)
    packet = load_json(DATASET / "evaluation-prompt-packet.json")
    assert len(packet["records"]) == 120
    public_policy = canonical_json(public_contract(policy))
    for record in packet["records"]:
        prompt = record["prompt"]
        assert public_policy in prompt
        assert record["item_id"] not in prompt
        assert record["pair_id"] not in prompt
        assert "factor_id" not in prompt


def test_slsa_gold_decisions_are_schema_and_semantically_valid() -> None:
    policy = load_slsa_policy(POLICY_PATH)
    items = {
        str(row["id"]): row["model_visible"]
        for row in load_jsonl(DATASET / "evaluation-items.jsonl")
    }
    for row in load_jsonl(DATASET / "evaluation-gold.jsonl"):
        decision = row["decision"]
        status, parsed, detail = diagnose_slsa_decision(
            json.dumps(decision), items[str(row["id"])], policy, schema_path=SCHEMA
        )
        assert (status, parsed, detail) == ("OK", decision, None)


def test_slsa_semantic_parser_rejects_action_state_disagreement() -> None:
    policy = load_slsa_policy(POLICY_PATH)
    item = load_jsonl(DATASET / "evaluation-items.jsonl")[0]["model_visible"]
    decision = evaluate_slsa(item, policy)
    decision["action"] = "HOLD" if decision["action"] != "HOLD" else "ALLOW"
    status, parsed, detail = diagnose_slsa_decision(
        json.dumps(decision), item, policy, schema_path=SCHEMA
    )
    assert status == "SEMANTIC_ERROR"
    assert parsed is None
    assert detail is not None and "proposed_state" in detail


def test_slsa_structured_baseline_is_byte_reproducible(tmp_path: Path) -> None:
    output = tmp_path / "baseline"
    report = train(DATASET, output)
    assert report["evaluation_gold_loaded"] is False
    assert report["model_outputs_loaded"] is False
    assert sha256_file(output / "report.json") == sha256_file(BASELINE / "report.json")
    assert sha256_file(output / "predictions.jsonl") == sha256_file(BASELINE / "predictions.jsonl")


def test_slsa_baseline_metrics_cover_all_actions() -> None:
    gold = load_jsonl(DATASET / "evaluation-gold.jsonl")
    pairs = load_json(DATASET / "evaluation-pairs.json")
    predictions = load_jsonl(BASELINE / "predictions.jsonl")
    records = [
        {
            "item_id": row["item_id"],
            "pair_id": row["pair_id"],
            "parse_status": "OK",
            "raw_decision": {"action": row["predicted_action"]},
        }
        for row in predictions
    ]
    metrics = derive_reporting_metrics(gold, pairs, records)
    assert metrics["items"] == 120
    assert metrics["pairs"] == 60
    assert metrics["decision_coverage"] == 1.0
    assert Counter(row["predicted_action"] for row in predictions).keys() == {
        "ALLOW",
        "HOLD",
        "DEMOTE",
        "ESCALATE",
    }


def test_slsa_execution_freeze_validates_without_credentials() -> None:
    report = validate_freeze(PLAN, SCHEDULE, DATASET, BASELINE)
    assert report["status"] == "SLSA_PORTABILITY_EXECUTION_FREEZE_VALID"
    assert report["credentials_loaded"] is False
    assert report["items"] == 120
    assert report["lanes"] == 2
    assert report["cells"] == 240


def test_slsa_repeated_configurations_keep_their_output_interfaces() -> None:
    plan = load_json(PLAN)
    packet = load_json(DATASET / "evaluation-prompt-packet.json")
    prompt = packet["records"][0]["prompt"]
    qwen, flash = plan["formal_lanes"]
    qwen_body = request_body(qwen, prompt)
    flash_body = request_body(flash, prompt)
    assert "response_format" not in qwen_body
    assert flash_body["response_format"]["type"] == "json_schema"
    assert qwen_body["messages"] == flash_body["messages"]


def test_slsa_schedule_rotates_lane_order_and_covers_each_cell_once() -> None:
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
