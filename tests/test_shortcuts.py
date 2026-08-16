from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from claimpromotebench.shortcuts import audit_shortcuts, main


def _state(*, formal: str = "NONE") -> dict[str, str]:
    return {
        "research_status": "OPEN",
        "computation_status": "NONE",
        "formal_status": formal,
        "review_status": "UNREVIEWED",
    }


def _item(
    item_id: str,
    pair_id: str,
    *,
    evidence_count: int,
    semantic_value: str = "PASS",
) -> dict[str, object]:
    evidence = [
        {
            "id": f"ev-{index:02d}",
            "type": "DEPENDENCY",
            "artifact_path": f"artifacts/a{index}.txt",
            "dependencies": [],
            "scope": {"flag": semantic_value},
            "provenance": {"actor_role": "TOOL"},
            "tool_exit": 0,
            "verifier_result": "PASS",
        }
        for index in range(evidence_count)
    ]
    return {
        "id": item_id,
        "pair_id": pair_id,
        "family": "SYNTHETIC",
        "split": "test",
        "schema_version": "test",
        "policy_id": "test",
        "policy_version": "test",
        "claim_text": "The bounded invariant holds.",
        "claim_context": {},
        "current_state": _state(),
        "current_state_basis": {},
        "requested_transition": {
            "target_state": _state(formal="FORMALLY_CERTIFIED"),
            "basis_evidence_ids": [evidence[0]["id"]] if evidence else [],
        },
        "evidence": evidence,
    }


def _gold(item: dict[str, object], *, allow: bool) -> dict[str, object]:
    current = deepcopy(item["current_state"])
    requested_transition = item["requested_transition"]
    assert isinstance(requested_transition, dict)
    target = deepcopy(requested_transition["target_state"])
    return {
        "id": item["id"],
        "pair_id": item["pair_id"],
        "family": item["family"],
        "decision": {
            "action": "ALLOW" if allow else "HOLD",
            "proposed_state": target if allow else current,
            "p_admissible": 1.0 if allow else 0.0,
            "used_evidence_ids": [],
            "reason_codes": ["POLICY_SATISFIED" if allow else "TEST_INVALID"],
            "missing_evidence_ids": [],
        },
    }


def _dataset(
    *,
    semantic_only: bool,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    inputs: list[dict[str, object]] = []
    gold: list[dict[str, object]] = []
    for index in range(4):
        pair_id = f"pair-{index}"
        valid = _item(
            f"{pair_id}-valid",
            pair_id,
            evidence_count=1 if semantic_only else 2,
            semantic_value="PASS",
        )
        invalid = _item(
            f"{pair_id}-invalid",
            pair_id,
            evidence_count=1,
            semantic_value="FAIL",
        )
        inputs.extend([valid, invalid])
        gold.extend([_gold(valid, allow=True), _gold(invalid, allow=False)])
    return inputs, gold


def test_cross_fitted_metadata_detects_count_shortcut() -> None:
    inputs, gold = _dataset(semantic_only=False)
    report = audit_shortcuts(inputs, gold)
    metadata = report["tiers"]["metadata_only"]["evaluation"]
    assert metadata["secondary"]["precision_recall"]["auprc_stepwise"]["value"] == 1.0
    assert metadata["secondary"]["paired_score_ranking"]["strict_accuracy"]["value"] == 1.0
    assert report["tiers"]["metadata_only"]["pair_differences"]["pair_exposure_rate"] == 1.0


def test_policy_blind_features_tie_on_equal_shape() -> None:
    inputs, gold = _dataset(semantic_only=True)
    report = audit_shortcuts(inputs, gold)
    for tier in ("metadata_only", "shallow_structure"):
        evaluation = report["tiers"][tier]["evaluation"]
        assert evaluation["secondary"]["precision_recall"]["auprc_stepwise"]["value"] == 0.5
        ranking = evaluation["secondary"]["paired_score_ranking"]
        assert ranking["strict_accuracy"]["value"] == 0.0
        assert ranking["tie_adjusted_accuracy"]["value"] == 0.5


def test_alpha_shortcut_audit_is_complete(inputs, gold) -> None:
    report = audit_shortcuts(inputs, gold)
    assert report["instances"] == 40
    assert report["pairs"] == 20
    assert set(report["tiers"]) == {"metadata_only", "shallow_structure"}
    assert report["protocol"]["cross_fit"] == "leave_one_controlled_pair_out"


def test_shortcut_cli_writes_report(
    dataset_dir: Path,
    tmp_path: Path,
    capsys,
) -> None:
    output = tmp_path / "shortcut-audit.json"
    assert main(["--dataset", str(dataset_dir), "--out", str(output)]) == 0
    summary = json.loads(capsys.readouterr().out)
    report = json.loads(output.read_text(encoding="utf-8"))
    assert summary["pairs"] == 20
    assert summary["out"] == str(output)
    assert report["pairs"] == 20
