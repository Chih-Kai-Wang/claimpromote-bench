from __future__ import annotations

from copy import deepcopy

from claimpromotebench.baselines import baseline_decision
from claimpromotebench.gate import apply_gate
from claimpromotebench.oracle import evaluate


def test_gate_vetoes_invalid_allow(inputs, policy, manifest) -> None:
    item = next(
        item
        for item in inputs
        if evaluate(item, policy, manifest["evaluation_time"])["action"] != "ALLOW"
    )
    raw = baseline_decision("always_allow", item, policy, manifest["evaluation_time"])
    oracle = evaluate(item, policy, manifest["evaluation_time"])
    result = apply_gate(raw, oracle)
    assert result["caught"] is True
    assert result["raw_decision"]["action"] == "ALLOW"
    assert result["final_decision"]["action"] == oracle["action"]
    assert "GATE_VETO" in result["final_decision"]["reason_codes"]


def test_gate_never_promotes_a_hold(inputs, policy, manifest) -> None:
    item = next(
        item
        for item in inputs
        if evaluate(item, policy, manifest["evaluation_time"])["action"] == "ALLOW"
    )
    raw = baseline_decision("always_hold", item, policy, manifest["evaluation_time"])
    result = apply_gate(raw, evaluate(item, policy, manifest["evaluation_time"]))
    assert result["caught"] is False
    assert result["final_decision"] == raw


def test_gate_does_not_mutate_raw_decision(inputs, policy, manifest) -> None:
    item = inputs[0]
    raw = baseline_decision("always_allow", item, policy, manifest["evaluation_time"])
    original = deepcopy(raw)
    apply_gate(raw, evaluate(item, policy, manifest["evaluation_time"]))
    assert raw == original
