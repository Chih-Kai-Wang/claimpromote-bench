"""Command-line interface for deterministic alpha operations."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .baselines import BASELINES, baseline_decision
from .dataset import (
    check_pairs,
    compile_author_items,
    load_json,
    load_jsonl,
    repository_root,
    validate_dataset,
    validate_with_schema,
    verify_manifest,
    write_jsonl,
)
from .errors import ClaimPromoteBenchError, DatasetIntegrityError, PredictionFormatError
from .metrics import evaluate_records
from .oracle import evaluate
from .policy import load_policy
from .prompts import ARMS, render_prompt
from .state import validate_decision_semantics


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _dataset_dir(source: Path) -> Path:
    return source if source.is_dir() else source.parent


def _context(dataset_dir: Path) -> tuple[dict[str, Any], dict[str, Any], str]:
    root = repository_root()
    manifest = load_json(dataset_dir / "manifest.json")
    if not isinstance(manifest, dict):
        raise DatasetIntegrityError("manifest must be an object")
    policy = load_policy(root / "policies" / str(manifest["policy_file"]))
    return manifest, policy, str(manifest["evaluation_time"])


def _load_joined(gold_path: Path, runs_path: Path) -> list[dict[str, Any]]:
    root = repository_root()
    gold_records = load_jsonl(gold_path)
    run_records = load_jsonl(runs_path)
    gold_by_id = {str(record["id"]): record for record in gold_records}
    runs_by_id: dict[str, dict[str, Any]] = {}
    inputs_by_id = {str(item["id"]): item for item in load_jsonl(gold_path.parent / "inputs.jsonl")}
    for record in run_records:
        record_id = str(record.get("id", ""))
        if not record_id or record_id in runs_by_id:
            raise PredictionFormatError(f"missing or duplicate prediction ID: {record_id!r}")
        decision = record.get("decision")
        if not isinstance(decision, dict):
            raise PredictionFormatError(f"prediction {record_id} has no decision object")
        validate_with_schema(
            decision,
            root / "schemas" / "agent-decision.schema.json",
            f"prediction {record_id}",
        )
        if record_id not in inputs_by_id:
            raise PredictionFormatError(f"prediction has unknown ID: {record_id}")
        validate_decision_semantics(inputs_by_id[record_id], decision)
        runs_by_id[record_id] = record
    if set(runs_by_id) != set(gold_by_id):
        missing = sorted(set(gold_by_id) - set(runs_by_id))
        extra = sorted(set(runs_by_id) - set(gold_by_id))
        raise PredictionFormatError(
            f"prediction coverage mismatch: missing={missing}, extra={extra}"
        )
    return [
        {
            "id": record_id,
            "pair_id": gold_by_id[record_id]["pair_id"],
            "family": gold_by_id[record_id]["family"],
            "gold": gold_by_id[record_id]["decision"],
            "prediction": runs_by_id[record_id]["decision"],
        }
        for record_id in sorted(gold_by_id)
    ]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cpb", description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    compile_parser = subparsers.add_parser(
        "compile", help="split author items into inputs and gold"
    )
    compile_parser.add_argument("source", type=Path)

    validate_parser = subparsers.add_parser("validate", help="validate a complete dataset")
    validate_parser.add_argument("dataset", type=Path)

    manifest_parser = subparsers.add_parser("verify-manifest", help="verify committed file hashes")
    manifest_parser.add_argument("manifest", type=Path)

    pairs_parser = subparsers.add_parser("check-pairs", help="check counterfactual invariants")
    pairs_parser.add_argument("dataset", type=Path)

    gold_parser = subparsers.add_parser("check-gold", help="recompute oracle labels")
    gold_parser.add_argument("dataset", type=Path)

    oracle_parser = subparsers.add_parser("oracle", help="generate deterministic oracle decisions")
    oracle_parser.add_argument("inputs", type=Path)
    oracle_parser.add_argument("--out", type=Path, required=True)

    baseline_parser = subparsers.add_parser("baseline", help="generate a non-model baseline")
    baseline_parser.add_argument("name", choices=BASELINES)
    baseline_parser.add_argument("--inputs", type=Path, default=Path("data/alpha/inputs.jsonl"))
    baseline_parser.add_argument("--out", type=Path, required=True)

    render_parser = subparsers.add_parser("render", help="render model-facing prompts")
    render_parser.add_argument("--arm", choices=ARMS, required=True)
    render_parser.add_argument("--inputs", type=Path, default=Path("data/alpha/inputs.jsonl"))
    render_parser.add_argument("--out", type=Path, required=True)

    evaluate_parser = subparsers.add_parser("evaluate", help="score one complete decision file")
    evaluate_parser.add_argument("--gold", type=Path, required=True)
    evaluate_parser.add_argument("--runs", type=Path, required=True)
    evaluate_parser.add_argument("--out", type=Path)
    evaluate_parser.add_argument("--bootstrap-samples", type=int, default=10_000)
    return parser


def _run(args: argparse.Namespace) -> Any:
    command = args.command
    if command == "compile":
        dataset_dir = _dataset_dir(args.source)
        compile_author_items(dataset_dir)
        return {"compiled": str(dataset_dir)}
    if command == "validate":
        return validate_dataset(args.dataset)
    if command == "verify-manifest":
        manifest = verify_manifest(args.manifest.parent)
        return {"verified_files": len(manifest["files"])}
    if command == "check-pairs":
        return {"families": check_pairs(args.dataset)}
    if command == "check-gold":
        report = validate_dataset(args.dataset)
        return {"gold_matches_oracle": True, **report}
    if command in {"oracle", "baseline"}:
        inputs_path = args.inputs
        dataset_dir = inputs_path.parent
        _manifest, policy, evaluation_time = _context(dataset_dir)
        records = []
        for item in load_jsonl(inputs_path):
            if command == "oracle":
                result = evaluate(item, policy, evaluation_time)
                decision = {
                    key: result[key]
                    for key in (
                        "action",
                        "proposed_state",
                        "p_admissible",
                        "used_evidence_ids",
                        "reason_codes",
                        "missing_evidence_ids",
                    )
                }
            else:
                decision = baseline_decision(args.name, item, policy, evaluation_time)
            records.append({"id": item["id"], "pair_id": item["pair_id"], "decision": decision})
        write_jsonl(args.out, records)
        return {"records": len(records), "out": str(args.out)}
    if command == "render":
        dataset_dir = args.inputs.parent
        records = [
            {
                "id": item["id"],
                "arm": args.arm,
                "prompt": render_prompt(item, args.arm, dataset_dir),
            }
            for item in load_jsonl(args.inputs)
        ]
        write_jsonl(args.out, records)
        return {"prompts": len(records), "arm": args.arm, "out": str(args.out)}
    if command == "evaluate":
        records = _load_joined(args.gold, args.runs)
        report = evaluate_records(records, bootstrap_samples=args.bootstrap_samples)
        if args.out:
            _write_json(args.out, report)
        return report
    raise AssertionError(f"unhandled command: {command}")


def main(argv: list[str] | None = None) -> int:
    """Run the CLI with stable exit codes: 0 success, 1 validation, 2 usage."""

    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
        result = _run(args)
    except (ClaimPromoteBenchError, OSError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
