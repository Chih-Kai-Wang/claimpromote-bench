from __future__ import annotations

from claimpromotebench.prompts import ARMS, prompt_payload, render_prompt


def test_all_arms_hide_benchmark_metadata(inputs, dataset_dir, policy, manifest) -> None:
    item = inputs[0]
    for arm in ARMS:
        prompt = render_prompt(
            item,
            arm,
            dataset_dir,
            policy=policy,
            evaluation_time=manifest["evaluation_time"],
        )
        assert item["id"] not in prompt
        assert item["pair_id"] not in prompt
        assert f'"family":"{item["family"]}"' not in prompt
        assert '"gold"' not in prompt
        assert "oracle final action" not in prompt.lower()


def test_payload_preserves_decision_relevant_fields(inputs) -> None:
    payload = prompt_payload(inputs[0])
    assert set(payload) == set(inputs[0]) - {"id", "pair_id", "split", "family", "gold"}
    assert payload["evidence"] == inputs[0]["evidence"]


def test_gate_arm_discloses_one_way_veto(inputs, dataset_dir, policy, manifest) -> None:
    prompt = render_prompt(
        inputs[0],
        "ledger_verifier_gate",
        dataset_dir,
        policy=policy,
        evaluation_time=manifest["evaluation_time"],
    )
    assert "veto" in prompt
    assert "never promote" in prompt


def test_all_arms_receive_the_same_complete_policy(inputs, dataset_dir, policy, manifest) -> None:
    for arm in ARMS:
        prompt = render_prompt(
            inputs[0],
            arm,
            dataset_dir,
            policy=policy,
            evaluation_time=manifest["evaluation_time"],
        )
        assert str(policy["max_age_days"]) in prompt
        assert policy["formal"]["toolchain_lock_sha256"] in prompt
        assert policy["evaluation_time"] in prompt
        assert "RESEARCH_STATUS_TRANSITION_NOT_SUPPORTED_BY_ALPHA_POLICY" in prompt


def test_narrative_is_semantic_prose_not_json_pointers(
    inputs, dataset_dir, policy, manifest
) -> None:
    prompt = render_prompt(
        inputs[0],
        "narrative",
        dataset_dir,
        policy=policy,
        evaluation_time=manifest["evaluation_time"],
    )
    assert "Evidence 1, ID" in prompt
    assert "/evidence/0/" not in prompt
    assert "Typed evidence ledger" not in prompt
