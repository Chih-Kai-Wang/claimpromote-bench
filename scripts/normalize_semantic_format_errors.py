#!/usr/bin/env python3
"""Normalize schema-valid but semantically invalid model decisions to FORMAT_ERROR.

This recovery is intentionally narrow. It preserves every completed inference record and
all immutable run identity, prompt-hash, timing, token, verifier, model, runtime, and
hardware fields. Only a record whose raw model decision violates the already-frozen
cross-field decision semantics is reclassified as FORMAT_ERROR, matching the benchmark's
pre-registered malformed-output contract. A semantically invalid system-produced final
decision is never normalized and instead fails closed.
"""

from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from claimpromotebench.dataset import (  # noqa: E402
    load_jsonl,
    validate_with_schema,
    write_jsonl,
)
from claimpromotebench.errors import PredictionFormatError  # noqa: E402
from claimpromotebench.hashing import sha256_file  # noqa: E402
from claimpromotebench.state import validate_decision_semantics  # noqa: E402

Json = dict[str, Any]
EXPECTED_ARMS = ("narrative", "ledger", "ledger_verifier", "ledger_verifier_gate")
EXPECTED_SEEDS = (104729, 130363, 169087)
EXPECTED_MODELS = ("Qwen/Qwen3-0.6B", "Qwen/Qwen3-1.7B")


def _identity(record: Json) -> tuple[Any, ...]:
    return (
        record["model_id"],
        record["model_artifact_sha256"],
        record.get("quantization"),
        record.get("runtime_commit"),
        record["arm"],
        record["seed"],
        record.get("hardware"),
    )


def normalize_run(
    source: Path,
    destination: Path,
    *,
    inputs_by_id: dict[str, Json],
    run_schema: Path,
) -> Json:
    records = load_jsonl(source)
    if len(records) != len(inputs_by_id):
        raise RuntimeError(
            f"run coverage count mismatch for {source}: {len(records)} != {len(inputs_by_id)}"
        )

    seen: set[str] = set()
    identity: tuple[Any, ...] | None = None
    normalized: list[Json] = []
    reclassified = 0

    for original in records:
        validate_with_schema(original, run_schema, f"source run record {original.get('item_id')}")
        item_id = str(original["item_id"])
        if item_id not in inputs_by_id or item_id in seen:
            raise RuntimeError(f"unknown or duplicate item_id in {source}: {item_id}")
        seen.add(item_id)

        current_identity = _identity(original)
        if identity is None:
            identity = current_identity
        elif current_identity != identity:
            raise RuntimeError(f"mixed run identity in {source}")

        record = deepcopy(original)
        if record["parse_status"] == "OK":
            raw = record["raw_decision"]
            try:
                validate_decision_semantics(inputs_by_id[item_id], raw)
            except PredictionFormatError:
                record["parse_status"] = "FORMAT_ERROR"
                record["raw_decision"] = None
                record["final_decision"] = None
                reclassified += 1
            else:
                # The final decision is produced by the harness/gate, not by parsing the
                # model response. If it is invalid, recovery must stop rather than hide a
                # system-side bug as a model format error.
                validate_decision_semantics(inputs_by_id[item_id], record["final_decision"])

        validate_with_schema(record, run_schema, f"normalized run record {item_id}")
        normalized.append(record)

    if seen != set(inputs_by_id):
        raise RuntimeError(f"run coverage mismatch for {source}")
    if identity is None:
        raise RuntimeError(f"empty run file: {source}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(destination, normalized)
    return {
        "source": str(source),
        "source_sha256": sha256_file(source),
        "normalized": str(destination),
        "normalized_sha256": sha256_file(destination),
        "records": len(normalized),
        "semantic_format_errors_reclassified": reclassified,
        "identity": {
            "model_id": identity[0],
            "model_artifact_sha256": identity[1],
            "quantization": identity[2],
            "runtime_commit": identity[3],
            "arm": identity[4],
            "seed": identity[5],
            "hardware": identity[6],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--out-root", type=Path, required=True)
    parser.add_argument("--provenance", type=Path, required=True)
    parser.add_argument("--source-workflow-run-id", type=int, required=True)
    parser.add_argument("--source-scoring-head-sha", required=True)
    args = parser.parse_args()

    inputs = load_jsonl(args.dataset / "inputs.jsonl")
    inputs_by_id = {str(item["id"]): item for item in inputs}
    if len(inputs_by_id) != 300:
        raise RuntimeError("recovery requires exactly 300 committed hidden instances")

    run_schema = ROOT / "schemas" / "run-record.schema.json"
    sources = sorted(args.source_root.rglob("run.jsonl"))
    if len(sources) != 24:
        raise RuntimeError(f"recovery requires exactly 24 source run files, found {len(sources)}")

    reports: list[Json] = []
    identities: set[tuple[str, str, int]] = set()
    for source in sources:
        relative_parent = source.parent.relative_to(args.source_root)
        destination = args.out_root / relative_parent / "run.jsonl"
        report = normalize_run(
            source,
            destination,
            inputs_by_id=inputs_by_id,
            run_schema=run_schema,
        )
        identity = report["identity"]
        key = (str(identity["model_id"]), str(identity["arm"]), int(identity["seed"]))
        if key in identities:
            raise RuntimeError(f"duplicate model/arm/seed identity: {key}")
        identities.add(key)
        reports.append(report)

    expected = {
        (model, arm, seed)
        for model in EXPECTED_MODELS
        for arm in EXPECTED_ARMS
        for seed in EXPECTED_SEEDS
    }
    if identities != expected:
        missing = sorted(expected - identities)
        extra = sorted(identities - expected)
        raise RuntimeError(f"recovery identity matrix mismatch: missing={missing}, extra={extra}")

    decision_count = sum(int(report["records"]) for report in reports)
    if decision_count != 7200:
        raise RuntimeError(f"recovery decision count mismatch: {decision_count}")

    provenance: Json = {
        "schema_version": "1.0.0",
        "status": "SEMANTIC_FORMAT_ERROR_NORMALIZATION_COMPLETE",
        "source_workflow_run_id": args.source_workflow_run_id,
        "source_scoring_head_sha": args.source_scoring_head_sha,
        "normalization_rule": (
            "A schema-valid raw model decision that violates the frozen cross-field decision "
            "semantics is a malformed model output and is reclassified as FORMAT_ERROR. "
            "No valid model decision is altered; a semantically invalid system final "
            "decision fails closed."
        ),
        "runs": 24,
        "instances_per_run": 300,
        "decisions": 7200,
        "run_files": reports,
    }
    args.provenance.parent.mkdir(parents=True, exist_ok=True)
    args.provenance.write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": provenance["status"], "runs": 24, "decisions": 7200}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
