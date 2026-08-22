#!/usr/bin/env python3
"""Analyze the frozen public model-breadth supplement with failure-aware metrics."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from analyze_balanced_public_challenge import analyze_challenge  # noqa: E402

from claimpromotebench.dataset import load_json  # noqa: E402


def fail(message: str) -> None:
    raise SystemExit(f"public-model-breadth-analysis: {message}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--run", type=Path, action="append", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    output = args.out.resolve()
    if output.exists():
        fail(f"refusing to overwrite existing output: {output}")
    plan = load_json(args.plan.resolve())
    result = analyze_challenge(
        args.dataset.resolve(),
        load_json(args.packet.resolve()),
        plan,
        args.plan.resolve(),
        [path.resolve() for path in args.run],
    )
    reporting = plan["reporting"]
    result["design"] = reporting["aggregate_design"]
    result["interpretation"] = reporting["aggregate_interpretation"]
    result["service_comparison"]["reason"] = reporting["service_comparison_reason"]
    result["scope_limits"] = {
        "public_known_challenge": True,
        "hidden_generalization_claimed": False,
        "naturalistic_cases": 0,
        "policy_count": 1,
        "ontology_count": 1,
        "breadth_dimension_added": "MODEL_FAMILY_ONLY",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": result["status"],
                "study_id": result["study_id"],
                "lanes": len(result["lanes"]),
                "out": str(output),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
