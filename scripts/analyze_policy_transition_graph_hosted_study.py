#!/usr/bin/env python3
"""Analyze the complete hosted policy-transition graph study."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import analyze_policy_switch_study as frozen_analysis  # noqa: E402
from validate_policy_transition_graph_hosted_study import validate_freeze  # noqa: E402

from claimpromotebench.hashing import canonical_json, sha256_file  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--schedule", type=Path, required=True)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--baseline-root", type=Path, required=True)
    parser.add_argument("--execution-receipt", type=Path, required=True)
    parser.add_argument("--run", type=Path, action="append", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    plan_path = args.plan.resolve()
    original_validator = frozen_analysis.validate_freeze
    frozen_analysis.validate_freeze = validate_freeze
    try:
        result = frozen_analysis.analyze(
            plan_path,
            args.schedule.resolve(),
            args.dataset_root.resolve(),
            args.baseline_root.resolve(),
            args.execution_receipt.resolve(),
            [path.resolve() for path in args.run],
        )
    finally:
        frozen_analysis.validate_freeze = original_validator
    result["design"] = "PROSPECTIVELY_FROZEN_REACHABLE_POLICY_TRANSITION_GRAPH_HOSTED_STUDY"
    result["interpretation"] = (
        "Within each route, pair members hold evidence and states fixed and change only the "
        "published active policy profile. The synthetic graph covers all ten semantically "
        "reachable directed nonself action transitions under one author-defined executor. "
        "Between-route differences remain descriptive."
    )
    result["transition_graph_boundary"] = {
        "reachable_directed_transitions": 10,
        "covered_directed_transitions": 10,
        "contexts_per_transition": 6,
        "structurally_unreachable_transitions": ["HOLD->DEMOTE", "DEMOTE->HOLD"],
        "model_outputs_used_to_choose_edges_or_contexts": False,
        "plan_sha256": sha256_file(plan_path),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(canonical_json({"status": result["status"], "lanes": len(result["lanes"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
