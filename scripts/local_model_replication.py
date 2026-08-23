#!/usr/bin/env python3
"""Shared contracts for the prospectively frozen local-model replications."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "v2" / "local-model-replication-v1" / "model-catalog.json"
REQUIREMENTS_PATH = ROOT / "v2" / "local-model-replication-v1" / "requirements.txt"

Json = dict[str, Any]
HEX40 = re.compile(r"^[0-9a-f]{40}$")

DATASETS: dict[str, Json] = {
    "slsa": {
        "study_id": "claimpromotebench-slsa-local-model-replication-2026-08-v1",
        "design": "LOCAL_MODEL_REPLICATION_OF_PROSPECTIVELY_FROZEN_SLSA_POLICY_STUDY",
        "dataset_root": ROOT / "v2" / "slsa-portability-v1" / "replacement-v2" / "dataset",
        "baseline_root": ROOT / "v2" / "slsa-portability-v1" / "replacement-v2" / "baseline",
        "expected_dataset_fingerprint": (
            "sha256:25297fbfb7aa80c77022568c51d336b53e6c05e97f1e51c661b5f59f7d1fdce9"
        ),
        "purpose": (
            "Replicate the fixed SLSA-grounded evidence-contrast evaluation on two pinned local "
            "open-weight model routes."
        ),
        "interpretation_boundary": (
            "The study tests conformance to an author-defined artifact-admission policy on one "
            "fixed synthetic corpus. It is not a SLSA certification, a natural-distribution "
            "estimate, or a causal comparison with hosted routes."
        ),
    },
    "policy-switch": {
        "study_id": "claimpromotebench-policy-switch-local-model-replication-2026-08-v1",
        "design": "LOCAL_MODEL_REPLICATION_OF_PROSPECTIVELY_FROZEN_POLICY_SWITCH_STUDY",
        "dataset_root": ROOT / "v2" / "policy-switch-v1" / "frozen" / "dataset",
        "baseline_root": ROOT / "v2" / "policy-switch-v1" / "frozen" / "baseline",
        "expected_dataset_fingerprint": (
            "sha256:fe675a81fb959d122aa751a6b49c5c5e8e67f39e6382c346fd38f4cc6225bbaf"
        ),
        "purpose": (
            "Replicate the active-policy switch evaluation on two pinned local open-weight model "
            "routes."
        ),
        "interpretation_boundary": (
            "Within each pair, evidence, states, artifact, and request are fixed while only the "
            "author-defined active policy profile changes. The study is not a SLSA certification, "
            "an unseen-policy generalization estimate, or a causal comparison with hosted routes."
        ),
    },
}


def load_object(path: Path) -> Json:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value


def load_catalog(path: Path = CATALOG_PATH) -> Json:
    catalog = load_object(path)
    lanes = catalog.get("lanes")
    shared = catalog.get("shared_generation")
    if (
        catalog.get("status") != "PREINFERENCE_LOCAL_MODEL_CATALOG"
        or not isinstance(lanes, list)
        or len(lanes) != 2
        or not isinstance(shared, dict)
        or shared.get("sampler") != "GREEDY"
        or shared.get("temperature") != 0.0
        or shared.get("top_p") != 0.0
        or shared.get("client_retries") != 0
        or shared.get("max_output_tokens") != 1536
    ):
        raise ValueError("local-model catalog contract changed")
    lane_stems: set[str] = set()
    families: set[str] = set()
    for lane in lanes:
        if not isinstance(lane, dict):
            raise ValueError("local-model catalog lane is malformed")
        stem = str(lane.get("lane_stem", ""))
        family = str(lane.get("model_family", ""))
        if not stem or stem in lane_stems or not family or family in families:
            raise ValueError("local-model lane stems and families must be unique")
        if not HEX40.fullmatch(str(lane.get("model_revision", ""))):
            raise ValueError(f"local-model revision is not a full commit: {stem}")
        if not str(lane.get("model_repo", "")).startswith("mlx-community/"):
            raise ValueError(f"unexpected local-model repository: {stem}")
        tokenizer_options = lane.get("tokenizer_config")
        if (
            not isinstance(tokenizer_options, dict)
            or set(tokenizer_options) - {"fix_mistral_regex", "trust_remote_code"}
            or not isinstance(lane.get("trust_remote_code"), bool)
            or tokenizer_options.get("trust_remote_code") is not lane["trust_remote_code"]
            or (family == "Mistral" and tokenizer_options.get("fix_mistral_regex") is not True)
        ):
            raise ValueError(f"local-model tokenizer configuration changed: {stem}")
        lane_stems.add(stem)
        families.add(family)
    boundary = catalog.get("selection_boundary")
    if (
        not isinstance(boundary, dict)
        or boundary.get("models_selected_before_any_benchmark_inference") is not True
        or boundary.get("benchmark_accuracy_or_labels_consulted") is not False
    ):
        raise ValueError("local-model selection boundary changed")
    return catalog


def lane_id(lane: Json, dataset_key: str) -> str:
    return f"{lane['lane_stem']}-{dataset_key}-v1"


def format_chat_prompt(tokenizer: Any, prompt: str) -> str:
    formatted = tokenizer.apply_chat_template(
        [{"role": "user", "content": prompt}],
        add_generation_prompt=True,
        tokenize=False,
    )
    if not isinstance(formatted, str) or not formatted.strip():
        raise ValueError("chat template returned an empty or non-text prompt")
    return formatted


def tokenizer_config(lane: Json) -> Json:
    value = lane.get("tokenizer_config")
    if not isinstance(value, dict):
        raise ValueError("local-model tokenizer configuration is absent")
    return dict(value)


def generation_request(lane: Json, formatted_prompt: str, shared: Json) -> Json:
    return {
        "backend": "mlx-lm",
        "backend_version": "0.31.3",
        "formatted_prompt": formatted_prompt,
        "max_output_tokens": shared["max_output_tokens"],
        "model_repo": lane["model_repo"],
        "model_revision": lane["model_revision"],
        "sampler": shared["sampler"],
        "temperature": shared["temperature"],
        "tokenizer_config": tokenizer_config(lane),
        "top_p": shared["top_p"],
    }
