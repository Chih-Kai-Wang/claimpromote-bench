from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from external_agent_policy_revision import (  # noqa: E402
    CASES,
    CONFIGURATIONS,
    MAX_OUTPUT_TOKENS,
    REPLICATIONS,
    SOURCES,
    conservative_cost_upper_bound_usd,
    expanded_lanes,
    request_body,
    schedule_payload,
)
from factor_complete_route_breadth import (  # noqa: E402
    conservative_cost_upper_bound_usd as factor_complete_cost_upper_bound_usd,
)
from freeze_external_agent_policy_revision import prompt_for  # noqa: E402
from run_external_agent_policy_revision import diagnose  # noqa: E402

from claimpromotebench.hashing import sha256_bytes  # noqa: E402


def _packet() -> dict[str, object]:
    records: list[dict[str, object]] = []
    for case in CASES:
        for version in ("before", "after"):
            item_id = f"{case['case_id']}-{version}"
            prompt = f"frozen prompt for {item_id}"
            records.append(
                {
                    "item_id": item_id,
                    "pair_id": case["case_id"],
                    "prompt": prompt,
                    "prompt_sha256": sha256_bytes(prompt.encode("utf-8")),
                }
            )
    return {
        "packet_sha256": "sha256:" + "1" * 64,
        "dataset_manifest_sha256": "sha256:" + "2" * 64,
        "records": records,
    }


def test_external_policy_cases_cover_changes_controls_and_actions() -> None:
    assert len(SOURCES) == 2
    assert len(CASES) == 10
    assert sum(bool(case["changed"]) for case in CASES) == 6
    assert sum(not bool(case["changed"]) for case in CASES) == 4
    assert {str(case["source_id"]) for case in CASES} == {
        "opa-agent-security-policy",
        "woocommerce-agent-bc-policy",
    }
    actions = Counter(
        str(case[version]["action"]) for case in CASES for version in ("before", "after")
    )
    assert actions == Counter({"ALLOW": 14, "HOLD": 3, "ESCALATE": 2, "DEMOTE": 1})


def test_external_policy_routes_use_one_prompt_only_contract() -> None:
    lanes = expanded_lanes()
    assert len(lanes) == len(CONFIGURATIONS) * REPLICATIONS == 21
    by_kind = {str(row["api_kind"]): row for row in lanes}
    chat = request_body(by_kind["openai_compatible"], "prompt")
    messages = request_body(by_kind["anthropic_messages"], "prompt")
    responses = request_body(by_kind["openai_responses"], "prompt")
    assert chat["messages"] == messages["messages"] == [{"role": "user", "content": "prompt"}]
    assert chat["max_tokens"] == messages["max_tokens"] == MAX_OUTPUT_TOKENS
    assert responses["input"][0]["content"] == [{"type": "input_text", "text": "prompt"}]
    assert responses["max_output_tokens"] == MAX_OUTPUT_TOKENS
    assert all("response_format" not in body for body in (chat, messages, responses))


def test_external_policy_prompt_has_distinct_complete_action_semantics() -> None:
    prompt = prompt_for(CASES[0], "after", "Repository policy text.")
    assert "HOLD: do not proceed" in prompt
    assert "blocks it" in prompt
    assert "blocks or deprioritizes" not in prompt
    assert "ESCALATE, then HOLD, then DEMOTE, then ALLOW" in prompt


def test_external_policy_schedule_is_complete_balanced_and_below_quota() -> None:
    packet = _packet()
    schedule = schedule_payload({"formal_lanes": expanded_lanes()}, packet)
    assert schedule["planned_cells"] == 420
    assert schedule["planned_groups"] == 60
    assert schedule["planned_items_per_lane"] == 20
    assert len({str(row["cell_id"]) for row in schedule["cells"]}) == 420
    assert set(Counter(str(row["lane_id"]) for row in schedule["cells"]).values()) == {20}
    assert set(Counter(int(row["group_index"]) for row in schedule["cells"]).values()) == {
        len(CONFIGURATIONS)
    }
    new_bound = conservative_cost_upper_bound_usd()
    prior_bound = factor_complete_cost_upper_bound_usd()
    assert new_bound < 4.6
    assert prior_bound + new_bound < 12.0


def test_external_policy_parser_accepts_direct_and_single_embedded_json() -> None:
    item = {
        "case_id": "agent-policy-opa-unflagged-advisory",
        "policy_version": "AFTER",
    }
    decision = {
        **item,
        "action": "DEMOTE",
        "reason_codes": ["DEPENDENCY_NOT_EXPLOITABLE"],
    }
    direct = json.dumps(decision)
    assert diagnose(direct, item) == ("OK", decision, None)
    assert diagnose(f"```json\n{direct}\n```", item) == (
        "OK",
        decision,
        "DETERMINISTIC_SINGLE_JSON_OBJECT_EXTRACTION",
    )


def test_external_policy_parser_rejects_binding_and_reason_mismatches() -> None:
    item = {
        "case_id": "agent-policy-woo-unknown-bc-impact",
        "policy_version": "AFTER",
    }

    def status(value: dict[str, object]) -> str:
        return diagnose(json.dumps(value), item)[0]

    valid = {
        **item,
        "action": "ESCALATE",
        "reason_codes": ["BC_IMPACT_REVIEW_REQUIRED"],
    }
    assert status(valid) == "OK"
    assert status({**valid, "case_id": "agent-policy-woo-private-helper-control"}) == (
        "SEMANTIC_ERROR"
    )
    assert status({**valid, "policy_version": "BEFORE"}) == "SEMANTIC_ERROR"
    assert status({**valid, "action": "HOLD"}) == "SEMANTIC_ERROR"
    assert status({key: value for key, value in valid.items() if key != "reason_codes"}) == (
        "SCHEMA_ERROR"
    )
    assert diagnose("not JSON", item)[0] == "JSON_SYNTAX_ERROR"
