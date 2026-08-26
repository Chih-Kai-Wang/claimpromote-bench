"""Frozen feature extraction and inference for the public-only shallow baseline."""

from __future__ import annotations

import math
import re
from collections import Counter
from copy import deepcopy
from itertools import pairwise
from typing import Any

from .errors import DatasetIntegrityError
from .hashing import canonical_json, sha256_bytes

Json = dict[str, Any]
ACTIONS = ("ALLOW", "HOLD", "DEMOTE", "ESCALATE")
_SHA256 = re.compile(r"sha256:[0-9a-f]{64}", re.IGNORECASE)
_ENTITY_ID = re.compile(r"\b(?:ev|claim|author|run)-[0-9a-f]+\b", re.IGNORECASE)
_ARTIFACT = re.compile(r"artifacts/[a-z0-9_.-]+", re.IGNORECASE)
_TOKEN = re.compile(r"[a-z_][a-z0-9_]*|[0-9]+(?:\.[0-9]+)?")


def prompt_features(prompt: str) -> list[str]:
    """Return the frozen identifier-normalized unigram and bigram features."""

    normalized = _SHA256.sub(" hash_token ", prompt.lower())
    normalized = _ENTITY_ID.sub(" entity_id ", normalized)
    normalized = _ARTIFACT.sub(" artifact_path ", normalized)
    tokens = _TOKEN.findall(normalized)
    return [
        *(f"u:{token}" for token in tokens),
        *(f"b:{left}|{right}" for left, right in pairwise(tokens)),
    ]


def validate_model(model: Json) -> None:
    payload = deepcopy(model)
    observed = payload.pop("model_sha256", None)
    if observed != sha256_bytes(canonical_json(payload).encode("utf-8")):
        raise DatasetIntegrityError("confirmatory shallow-model digest mismatch")
    if model.get("schema_version") != "1.0.0" or model.get("actions") != list(ACTIONS):
        raise DatasetIntegrityError("confirmatory shallow-model identity changed")
    if model.get("alpha") != 1.0:
        raise DatasetIntegrityError("confirmatory shallow-model smoothing changed")
    vocabulary = model.get("vocabulary")
    if (
        not isinstance(vocabulary, list)
        or not vocabulary
        or len(vocabulary) != len(set(vocabulary))
    ):
        raise DatasetIntegrityError("confirmatory shallow-model vocabulary is malformed")
    for action in ACTIONS:
        if not isinstance(model.get("token_counts", {}).get(action), dict):
            raise DatasetIntegrityError(f"confirmatory shallow-model counts missing: {action}")


def predict_text_nb(model: Json, prompt: str) -> str:
    """Apply the frozen four-class multinomial Naive Bayes model."""

    alpha = float(model["alpha"])
    vocabulary_size = len(model["vocabulary"])
    document_total = int(model["documents"])
    features = Counter(prompt_features(prompt))
    scores: dict[str, float] = {}
    for action in ACTIONS:
        documents = int(model["document_counts"][action])
        score = math.log((documents + alpha) / (document_total + alpha * len(ACTIONS)))
        denominator = int(model["token_totals"][action]) + alpha * vocabulary_size
        counts = model["token_counts"][action]
        for feature, occurrences in features.items():
            score += occurrences * math.log((int(counts.get(feature, 0)) + alpha) / denominator)
        scores[action] = score
    return max(ACTIONS, key=lambda action: (scores[action], -ACTIONS.index(action)))
