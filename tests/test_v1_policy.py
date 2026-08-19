"""Stable v1 policy identity must not silently change alpha-tested semantics."""

from __future__ import annotations

import json
from pathlib import Path

from claimpromotebench.policy import load_policy

ROOT = Path(__file__).resolve().parents[1]
ALPHA = ROOT / "policies" / "math-evidence-transition-1.0.2-alpha.json"
V1 = ROOT / "policies" / "math-evidence-transition-1.0.0.json"


def test_v1_policy_is_semantically_identical_to_alpha_contract() -> None:
    alpha = load_policy(ALPHA)
    v1 = load_policy(V1)
    assert alpha["policy_version"] == "1.0.2-alpha"
    assert v1["policy_version"] == "1.0.0"

    normalized_alpha = json.loads(json.dumps(alpha))
    normalized_v1 = json.loads(json.dumps(v1))
    normalized_alpha["policy_version"] = "<VERSION>"
    normalized_v1["policy_version"] = "<VERSION>"
    assert normalized_v1 == normalized_alpha
