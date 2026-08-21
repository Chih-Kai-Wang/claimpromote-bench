"""Tests for the fixed client-side subscription authorization gate."""

from __future__ import annotations

import importlib.util
from copy import deepcopy
from pathlib import Path
from types import ModuleType

import pytest

from claimpromotebench.dataset import load_json
from claimpromotebench.hashing import canonical_json, sha256_bytes

ROOT = Path(__file__).resolve().parents[1]


def _script(name: str) -> ModuleType:
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _module() -> ModuleType:
    return _script("confirmatory_subscription_authorization")


def _schedule(module: ModuleType, plan: dict[str, object]) -> dict[str, object]:
    cells = []
    for lane_id in module.LANES:
        for sequence in range(module.POSTS_PER_LANE):
            item_id = f"item-{sequence:03d}"
            body = {
                "model": (
                    "qwen3.7-max" if lane_id == "opencode-go-qwen3.7-max" else "deepseek-v4-flash"
                ),
                "messages": [{"role": "user", "content": f"prompt-{sequence}"}],
                "max_tokens": 1536,
                "stream": False,
            }
            if lane_id == "opencode-go-deepseek-v4-flash-matched":
                body["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "agent_decision",
                        "strict": True,
                        "schema": module._portable_decision_schema(),
                    },
                }
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "ClaimPromoteBench-Confirmatory/1",
                "Authorization": "<REDACTED_CREDENTIAL>",
            }
            if lane_id == "opencode-go-qwen3.7-max":
                headers.update(
                    {
                        "x-api-key": "<REDACTED_CREDENTIAL>",
                        "anthropic-version": "2023-06-01",
                    }
                )
            cells.append(
                {
                    "cell_id": f"{lane_id}/{item_id}",
                    "lane_id": lane_id,
                    "sequence": sequence,
                    "item_id": item_id,
                    "pair_id": f"pair-{sequence:03d}",
                    "prompt_sha256": sha256_bytes(f"prompt-{sequence}".encode()),
                    "request_body": body,
                    "request_body_sha256": sha256_bytes(canonical_json(body).encode()),
                    "request_headers_template": headers,
                }
            )
    return {
        "study_id": plan["study_id"],
        "lane_order": list(module.LANES),
        "planned_cells": 600,
        "application_posts_per_cell": 1,
        "client_retry_count": 0,
        "cells": cells,
    }


def test_exact_600_cell_subscription_authorization_passes() -> None:
    module = _module()
    plan = load_json(ROOT / "v2" / "fresh-confirmatory-study-plan.json")
    report = module.validate_schedule_authorization(plan, _schedule(module, plan))
    assert report["status"] == "SUBSCRIPTION_AUTHORIZATION_GATE_PASS"
    assert report["schedule_cells_verified"] == 600
    assert report["per_lane_cells_verified"] == {
        "opencode-go-qwen3.7-max": 300,
        "opencode-go-deepseek-v4-flash-matched": 300,
    }
    assert report["max_output_tokens_per_post"] == 1536
    assert report["incremental_cash_cap_usd"] == 0.0
    assert report["per_lane_token_usd_cap"] is None


def test_one_extra_output_token_fails_before_credentials() -> None:
    module = _module()
    plan = load_json(ROOT / "v2" / "fresh-confirmatory-study-plan.json")
    schedule = _schedule(module, plan)
    schedule["cells"][0]["request_body"]["max_tokens"] = 1537
    with pytest.raises(ValueError, match="max_tokens changed"):
        module.validate_schedule_authorization(plan, schedule)


def test_cash_or_provider_fallback_cannot_be_enabled() -> None:
    module = _module()
    plan = load_json(ROOT / "v2" / "fresh-confirmatory-study-plan.json")
    for field in ("cash_balance_fallback", "alternate_provider_fallback"):
        changed = deepcopy(plan)
        changed["budget"][field] = True
        with pytest.raises(ValueError, match=field):
            module.validate_plan_authorization(changed)


def test_token_usd_cap_cannot_be_reintroduced_after_r5() -> None:
    module = _module()
    plan = load_json(ROOT / "v2" / "fresh-confirmatory-study-plan.json")
    changed = deepcopy(plan)
    changed["formal_lanes"][0]["spend_cap_usd"] = 12.0
    with pytest.raises(ValueError, match="reintroduced a token-USD cap"):
        module.validate_plan_authorization(changed)


def test_missing_cell_fails_closed() -> None:
    module = _module()
    plan = load_json(ROOT / "v2" / "fresh-confirmatory-study-plan.json")
    schedule = _schedule(module, plan)
    schedule["cells"].pop()
    with pytest.raises(ValueError, match="schedule cells are incomplete"):
        module.validate_schedule_authorization(plan, schedule)


def test_prompt_bytes_full_schema_and_order_are_bound() -> None:
    module = _module()
    plan = load_json(ROOT / "v2" / "fresh-confirmatory-study-plan.json")

    changed_prompt = _schedule(module, plan)
    changed_prompt["cells"][0]["request_body"]["messages"][0]["content"] += " changed"
    with pytest.raises(ValueError, match="prompt digest changed"):
        module.validate_schedule_authorization(plan, changed_prompt)

    changed_schema = _schedule(module, plan)
    flash = changed_schema["cells"][module.POSTS_PER_LANE]
    flash["request_body"]["response_format"]["json_schema"]["strict"] = False
    flash["request_body_sha256"] = sha256_bytes(canonical_json(flash["request_body"]).encode())
    with pytest.raises(ValueError, match="response schema changed"):
        module.validate_schedule_authorization(plan, changed_schema)

    changed_order = _schedule(module, plan)
    changed_order["cells"][1]["sequence"] = 0
    with pytest.raises(ValueError, match="cell order changed"):
        module.validate_schedule_authorization(plan, changed_order)


def test_real_c1_builder_embeds_the_exact_recomputed_gate(tmp_path: Path) -> None:
    dataset_builder = _script("build_v1_dataset")
    packet_builder = _script("build_stronger_model_packet")
    baseline_builder = _script("predict_confirmatory_baselines")
    c1_builder = _script("build_confirmatory_c1")
    plan_path = ROOT / "v2" / "fresh-confirmatory-study-plan.json"
    plan = load_json(plan_path)
    seed = tmp_path / "public-rehearsal-seed.bin"
    seed.write_bytes(bytes(range(32)))
    dataset = tmp_path / "public-rehearsal-hidden"
    dataset_builder.build("test", dataset, seed, confirmatory_rekey=True)
    packet = packet_builder.build_packet(dataset, plan_path)
    model = load_json(ROOT / "v2" / "confirmatory" / "public-dev-text-nb-v1.json")
    baselines = baseline_builder.build_predictions(model, packet, plan)
    schedule, receipt = c1_builder.build_c1(packet, baselines, plan, plan_path)
    authorization = receipt["subscription_authorization"]
    assert schedule["planned_cells"] == 600
    assert authorization["status"] == "SUBSCRIPTION_AUTHORIZATION_GATE_PASS"
    assert authorization["schedule_recomputed_from_exact_request_bodies"] is True
    assert authorization["schedule_cells_verified"] == 600
    assert authorization["per_lane_cells_verified"] == {
        "opencode-go-qwen3.7-max": 300,
        "opencode-go-deepseek-v4-flash-matched": 300,
    }
