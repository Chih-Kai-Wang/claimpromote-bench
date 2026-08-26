"""Regression tests for the precommitted balanced public robustness challenge."""

from __future__ import annotations

import importlib.util
import json
from collections import Counter, defaultdict
from pathlib import Path

from claimpromotebench.dataset import load_jsonl
from claimpromotebench.hashing import sha256_file

ROOT = Path(__file__).resolve().parents[1]
CONSTRUCTION_PLAN = ROOT / "configs" / "balanced-public-challenge-plan.json"
STUDY_PLAN = ROOT / "v2" / "balanced-public-challenge-study-plan.json"
SEED = ROOT / "configs" / "balanced-public-challenge-seed.hex"
DATASET = ROOT / "v2" / "balanced-public-challenge" / "dataset"
PACKET = ROOT / "v2" / "balanced-public-challenge" / "prompt-packet.json"


def load_script(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_balanced_challenge_dataset_rebuilds_byte_identically(tmp_path: Path) -> None:
    builder = load_script("build_v1_dataset")
    rebuilt = tmp_path / "dataset"
    report = builder.build(
        "test",
        rebuilt,
        SEED,
        confirmatory_rekey=True,
        plan_path=CONSTRUCTION_PLAN,
        identifier_prefix="v1-test-bal",
    )

    assert report["pairs"] == 90
    assert report["instances"] == 180
    assert report["invalid_action_counts"] == {"DEMOTE": 30, "ESCALATE": 30, "HOLD": 30}
    assert report["manifest_sha256"] == sha256_file(DATASET / "manifest.json")
    assert (rebuilt / "manifest.json").read_bytes() == (DATASET / "manifest.json").read_bytes()


def test_rare_actions_cross_five_independent_factors() -> None:
    pairs = json.loads((DATASET / "pairs.json").read_text(encoding="utf-8"))
    gold = {
        str(row["id"]): str(row["decision"]["action"]) for row in load_jsonl(DATASET / "gold.jsonl")
    }
    factors: dict[str, set[str]] = defaultdict(set)
    counts: Counter[str] = Counter()
    for pair in pairs:
        action = gold[str(pair["invalid_id"])]
        factors[action].add(str(pair["factor_id"]))
        counts[action] += 1

    assert counts == Counter({"HOLD": 30, "DEMOTE": 30, "ESCALATE": 30})
    assert len(factors["HOLD"]) == 5
    assert len(factors["DEMOTE"]) == 5
    assert len(factors["ESCALATE"]) == 5


def test_balanced_challenge_packet_is_exactly_frozen_and_factor_metadata_is_hidden() -> None:
    packet_builder = load_script("build_stronger_model_packet")
    observed = packet_builder.build_packet(DATASET, STUDY_PLAN)
    committed = json.loads(PACKET.read_text(encoding="utf-8"))

    assert observed == committed
    assert len(observed["records"]) == 180
    assert observed["pilot_item_ids"] == []
    assert all('"factor_id"' not in str(record["prompt"]) for record in observed["records"])
    assert all("Benchmark factor:" not in str(record["prompt"]) for record in observed["records"])
