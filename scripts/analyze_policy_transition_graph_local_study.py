#!/usr/bin/env python3
"""Analyze the frozen local policy-transition graph with failure-aware metrics."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from policy_transition_graph_local import register_only_transition_graph  # noqa: E402

register_only_transition_graph()

import analyze_local_model_replication as analysis  # noqa: E402
from validate_policy_transition_graph_local_study import validate_all  # noqa: E402

analysis.validate_all = validate_all


if __name__ == "__main__":
    raise SystemExit(analysis.main())
