from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

import claimpromotebench.invariance as invariance
from claimpromotebench.dataset import load_jsonl
from claimpromotebench.hashing import canonical_json
from claimpromotebench.invariance import (
    Transform,
    Variant,
    audit_invariance,
    main,
)
from claimpromotebench.oracle import evaluate
from claimpromotebench.policy import load_policy
from claimpromotebench.prompts import ARMS, render_prompt


def _dataset_context(dataset_dir: Path) -> tuple[list[dict[str, Any]], dict[str, Any], str]:
    items = load_jsonl(dataset_dir / "inputs.jsonl")
    policy = load_policy(
        Path(__file__).resolve().parents[1]
        / "policies"
        / "math-evidence-transition-1.0.2-alpha.json"
    )
    return items, policy, "2026-08-13T00:00:00Z"


def _transform(transform_id: str) -> Transform:
    return next(value for value in invariance.TRANSFORMS if value.transform_id == transform_id)


def test_complete_invariance_audit_passes(dataset_dir: Path) -> None:
    report = audit_invariance(dataset_dir)
    assert report["status"] == "PASS"
    assert report["base_items"] == 40
    assert report["total_variants"] > 320
    assert report["oracle_equivalent_variants"] == report["total_variants"]
    assert report["schema_validated_variants"] == report["total_variants"]
    assert report["artifact_validated_variants"] == report["total_variants"]
    assert report["prompt_renderings"] == report["total_variants"] * len(ARMS)
    assert report["failures"] == []

    by_id = {value["transform_id"]: value for value in report["transformations"]}
    key_order = by_id["reverse_json_object_key_order"]
    assert key_order["variants"] == 40
    assert key_order["prompt_identical_variants"] == 40
    assert key_order["prompt_changed_variants"] == 0
    assert all(value == 0 for value in key_order["changed_prompt_arms"].values())

    reversed_evidence = by_id["reverse_evidence_array"]
    assert 0 < reversed_evidence["variants"] < 40
    for transform_id, value in by_id.items():
        assert value["variants"] == value["applicable_items"]
        if transform_id != "reverse_json_object_key_order":
            assert value["prompt_changed_variants"] == value["variants"]
            assert value["prompt_identical_variants"] == 0


def test_key_order_reversal_preserves_every_prompt_byte(dataset_dir: Path) -> None:
    items, policy, evaluation_time = _dataset_context(dataset_dir)
    item = items[0]
    variant = _transform("reverse_json_object_key_order").apply(item)
    assert variant is not None
    assert list(variant.item) == list(reversed(list(item)))
    for arm in ARMS:
        assert render_prompt(
            variant.item,
            arm,
            dataset_dir,
            policy=policy,
            evaluation_time=evaluation_time,
        ) == render_prompt(
            item,
            arm,
            dataset_dir,
            policy=policy,
            evaluation_time=evaluation_time,
        )


def test_identifier_renaming_preserves_oracle_semantics(dataset_dir: Path) -> None:
    items, policy, evaluation_time = _dataset_context(dataset_dir)
    item = next(value for value in items if value["id"] == "alpha-dep-02-b")
    variant = _transform("rename_evidence_identifiers").apply(item)
    assert variant is not None
    assert {value["id"] for value in variant.item["evidence"]} != {
        value["id"] for value in item["evidence"]
    }
    base = invariance._normalize_decision(
        evaluate(item, policy, evaluation_time),
        invariance._identity_inverse(item),
    )
    transformed = invariance._normalize_decision(
        evaluate(variant.item, policy, evaluation_time),
        variant.inverse_evidence_ids,
    )
    assert canonical_json(transformed) == canonical_json(base)


def test_principal_and_environment_renaming_preserve_equality_relations(
    dataset_dir: Path,
) -> None:
    items, policy, evaluation_time = _dataset_context(dataset_dir)

    actor_item = next(value for value in items if value["id"] == "alpha-prov-01-a")
    actor_variant = _transform("rename_principal_identifiers").apply(actor_item)
    assert actor_variant is not None
    assert (
        actor_variant.item["evidence"][0]["provenance"]["actor_id"]
        == actor_variant.item["claim_context"]["author_id"]
    )
    assert (
        evaluate(actor_variant.item, policy, evaluation_time)["reason_codes"]
        == evaluate(actor_item, policy, evaluation_time)["reason_codes"]
    )

    environment_item = next(value for value in items if value["id"] == "alpha-prov-02-b")
    environment_variant = _transform("rename_environment_identifiers").apply(environment_item)
    assert environment_variant is not None
    assert (
        environment_variant.item["evidence"][0]["provenance"]["environment_sha256"]
        == environment_variant.item["claim_context"]["author_environment_sha256"]
    )
    assert (
        evaluate(environment_variant.item, policy, evaluation_time)["reason_codes"]
        == evaluate(environment_item, policy, evaluation_time)["reason_codes"]
    )


def test_unreferenced_failures_and_resolved_contradictions_are_inert(
    dataset_dir: Path,
) -> None:
    items, policy, evaluation_time = _dataset_context(dataset_dir)
    item = next(value for value in items if value["id"] == "alpha-num-01-a")
    base = evaluate(item, policy, evaluation_time)

    stale = _transform("prepend_stale_failed_unreferenced_artifact").apply(item)
    assert stale is not None
    stale_decision = evaluate(stale.item, policy, evaluation_time)
    assert stale.item["evidence"][0]["tool_exit"] == 1
    assert stale.item["evidence"][0]["timestamp"].startswith("2000-")
    assert stale.item["evidence"][0]["id"] not in stale_decision["used_evidence_ids"]
    assert canonical_json(stale_decision) == canonical_json(base)

    contradiction = _transform("append_resolved_contradiction").apply(item)
    assert contradiction is not None
    added = contradiction.item["evidence"][-1]
    assert added["type"] == "CONTRADICTION"
    assert added["scope"]["contradiction_status"] == "RESOLVED"
    assert canonical_json(evaluate(contradiction.item, policy, evaluation_time)) == canonical_json(
        base
    )


def test_audit_reports_a_semantic_break_as_failure(
    dataset_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def break_root_runtime(item: dict[str, Any]) -> Variant:
        variant = deepcopy(item)
        root_id = variant["requested_transition"]["basis_evidence_ids"][0]
        root = next(value for value in variant["evidence"] if value["id"] == root_id)
        root["tool_exit"] = 77
        return Variant(variant, invariance._identity_inverse(variant), False)

    monkeypatch.setattr(
        invariance,
        "TRANSFORMS",
        (
            Transform(
                "break_root_runtime",
                "Deliberately break a policy-relevant field for the negative test.",
                break_root_runtime,
            ),
        ),
    )
    report = audit_invariance(dataset_dir)
    assert report["status"] == "FAIL"
    assert report["failures"]
    assert {value["stage"] for value in report["failures"]} & {"ARTIFACT", "ORACLE"}


def test_invariance_cli_writes_report(
    dataset_dir: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "invariance.json"
    assert (
        main(
            [
                "--dataset",
                str(dataset_dir),
                "--out",
                str(output),
            ]
        )
        == 0
    )
    summary = json.loads(capsys.readouterr().out)
    report = json.loads(output.read_text(encoding="utf-8"))
    assert summary["status"] == "PASS"
    assert summary["failures"] == 0
    assert summary["total_variants"] == report["total_variants"]
    assert report["report_id"].startswith("sha256:")
