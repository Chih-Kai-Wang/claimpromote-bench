from __future__ import annotations

from claimpromotebench.prompts import ARMS, prompt_payload, render_prompt


def test_all_arms_hide_benchmark_metadata(inputs, dataset_dir) -> None:
    item = inputs[0]
    for arm in ARMS:
        prompt = render_prompt(item, arm, dataset_dir)
        assert item["id"] not in prompt
        assert item["pair_id"] not in prompt
        assert item["family"] not in prompt
        assert '"gold"' not in prompt
        assert "oracle final action" not in prompt.lower()


def test_payload_preserves_decision_relevant_fields(inputs) -> None:
    payload = prompt_payload(inputs[0])
    assert set(payload) == set(inputs[0]) - {"id", "pair_id", "split", "family", "gold"}
    assert payload["evidence"] == inputs[0]["evidence"]


def test_gate_arm_discloses_one_way_veto(inputs, dataset_dir) -> None:
    prompt = render_prompt(inputs[0], "ledger_verifier_gate", dataset_dir)
    assert "veto" in prompt
    assert "never promote" in prompt
