"""Static and request-byte tests for the gold-free confirmatory service runner."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

from claimpromotebench.dataset import load_json

ROOT = Path(__file__).resolve().parents[1]


def _load_script(name: str) -> ModuleType:
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_confirmatory_worker_has_no_gold_or_gate_dependency() -> None:
    source = (ROOT / "scripts" / "run_confirmatory_service_study.py").read_text(encoding="utf-8")
    assert "postgate_decision" not in source
    assert "gold.jsonl" not in source
    assert "--dataset" not in source
    assert "HTTPRedirectHandler" in source
    assert "client_retry_count" in source


def test_frozen_request_bodies_match_the_two_selected_service_adapters() -> None:
    runner = _load_script("run_confirmatory_service_study")
    schema = runner.portable_decision_schema(
        load_json(ROOT / "schemas" / "agent-decision.schema.json")
    )
    qwen = {
        "api_kind": "anthropic_messages",
        "response_format": "prompt_only_json",
        "model": "qwen3.7-max",
        "max_output_tokens": 1536,
    }
    qwen_body = runner.request_body_for_lane(qwen, "prompt", schema)
    assert qwen_body == {
        "model": "qwen3.7-max",
        "max_tokens": 1536,
        "messages": [{"role": "user", "content": "prompt"}],
        "stream": False,
    }
    flash = {
        "api_kind": "openai_compatible",
        "response_format": "json_schema",
        "model": "deepseek-v4-flash",
        "max_output_tokens": 1536,
    }
    flash_body = runner.request_body_for_lane(flash, "prompt", schema)
    assert flash_body["max_tokens"] == 1536
    assert flash_body["stream"] is False
    assert flash_body["response_format"]["type"] == "json_schema"
    assert flash_body["response_format"]["json_schema"]["strict"] is True
    for body in (qwen_body, flash_body):
        assert "temperature" not in body
        assert "top_p" not in body
        assert "seed" not in body


def test_reasoning_is_redacted_but_parse_independent_envelope_fields_remain() -> None:
    runner = _load_script("run_confirmatory_service_study")
    sanitized = runner._sanitize_envelope(
        {
            "id": "response-1",
            "reasoning_content": "private chain of thought",
            "content": [
                {"type": "text", "thought": True, "text": "private thought"},
                {"type": "text", "text": '{"action":"ALLOW"}'},
            ],
        }
    )
    assert sanitized["id"] == "response-1"
    assert sanitized["reasoning_content"] == "<REDACTED_HIDDEN_REASONING>"
    assert sanitized["content"][0]["text"] == "<REDACTED_HIDDEN_REASONING>"
    assert sanitized["content"][1]["text"] == '{"action":"ALLOW"}'
