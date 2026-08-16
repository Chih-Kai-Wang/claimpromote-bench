"""Cross-fitted audits for non-semantic and shallow structural shortcuts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .dataset import load_jsonl, verify_manifest
from .errors import ClaimPromoteBenchError
from .shortcut_report import audit_shortcuts

__all__ = ["audit_shortcuts", "main"]


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _summary(report: dict[str, Any]) -> dict[str, Any]:
    tiers: dict[str, Any] = {}
    for tier, tier_report in report["tiers"].items():
        evaluation = tier_report["evaluation"]
        tiers[tier] = {
            "auprc_stepwise": evaluation["secondary"]["precision_recall"]["auprc_stepwise"][
                "value"
            ],
            "paired_score_strict_accuracy": evaluation["secondary"]["paired_score_ranking"][
                "strict_accuracy"
            ]["value"],
            "pair_exposure_rate": tier_report["pair_differences"]["pair_exposure_rate"],
        }
    return {
        "instances": report["instances"],
        "pairs": report["pairs"],
        "tiers": tiers,
    }


def main(argv: list[str] | None = None) -> int:
    """Run a deterministic shortcut audit over one complete dataset."""

    parser = argparse.ArgumentParser(
        prog="cpb-audit-shortcuts",
        description=__doc__,
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("data/alpha"),
    )
    parser.add_argument("--out", type=Path)
    parser.add_argument("--bootstrap-samples", type=int, default=0)
    args = parser.parse_args(argv)

    try:
        verify_manifest(args.dataset)
        report = audit_shortcuts(
            load_jsonl(args.dataset / "inputs.jsonl"),
            load_jsonl(args.dataset / "gold.jsonl"),
            bootstrap_samples=args.bootstrap_samples,
        )
        if args.out:
            _write_json(args.out, report)
            result = {"out": str(args.out), **_summary(report)}
        else:
            result = report
    except (ClaimPromoteBenchError, OSError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
