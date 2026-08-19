#!/usr/bin/env python3
"""Validate the public v1 paper-results release against the frozen study summary.

This script does not recompute model inference. It checks that the compact, public-safe release
file is internally complete and agrees with the submission-facing frozen quantities derived from
the validated recovered study.
"""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "release" / "v1-paper-results.json"
FREEZE = ROOT / "technical-report" / "results-freeze.json"

MODELS = ("0.6B", "1.7B")
ARMS = ("narrative", "ledger", "ledger_verifier", "ledger_verifier_gate")
SEEDS = (104729, 130363, 169087)
INSTANCES_PER_RUN = 300
EXPECTED_FORMAT_ERRORS = {
    ("0.6B", "narrative"): 900,
    ("0.6B", "ledger"): 261,
    ("0.6B", "ledger_verifier"): 335,
    ("0.6B", "ledger_verifier_gate"): 585,
    ("1.7B", "narrative"): 900,
    ("1.7B", "ledger"): 900,
    ("1.7B", "ledger_verifier"): 900,
    ("1.7B", "ledger_verifier_gate"): 546,
}

Json = dict[str, Any]


def fail(message: str) -> None:
    raise SystemExit(f"v1-release-results: {message}")


def load_object(path: Path) -> Json:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        fail(f"{path.relative_to(ROOT)} must contain a JSON object")
    return value


def close(left: Any, right: float, *, label: str) -> None:
    if not isinstance(left, (int, float)) or isinstance(left, bool):
        fail(f"{label} must be numeric")
    if not math.isclose(float(left), right, rel_tol=0.0, abs_tol=1e-12):
        fail(f"{label} mismatch: expected {right}, got {left}")


def require_value(row: Json, key: str, expected: float | None, identity: tuple[str, str, int]) -> None:
    value = row.get(key)
    label = f"{identity}.{key}"
    if expected is None:
        if value is not None:
            fail(f"{label} must be null when the rate is undefined")
        return
    close(value, expected, label=label)


def model_freeze(freeze: Json, suffix: str) -> Json:
    key = f"Qwen/Qwen3-{suffix}"
    models = freeze.get("models")
    if not isinstance(models, dict) or not isinstance(models.get(key), dict):
        fail(f"results freeze lacks model {key}")
    return models[key]


def main() -> int:
    release = load_object(RELEASE)
    freeze = load_object(FREEZE)

    if release.get("schema_version") != "1.0.0":
        fail("unexpected release schema_version")
    for key in (
        "source_study_sha256",
        "source_scored_workflow_run_id",
        "source_recovery_workflow_run_id",
    ):
        if release.get(key) != freeze.get(key):
            fail(f"release {key} does not match results-freeze.json")

    dataset = release.get("dataset")
    if not isinstance(dataset, dict):
        fail("dataset identity is missing")
    if dataset.get("manifest_sha256") != (
        "sha256:fe838548389ee1516d9cf9442201a22c291add0ddb6cabf4f39de99b6489caba"
    ):
        fail("dataset manifest is not the frozen hidden-study manifest")

    runs = release.get("runs")
    if not isinstance(runs, list) or len(runs) != 24:
        fail("release must contain exactly 24 run summaries")

    expected_identities = {
        (model, arm, seed) for model in MODELS for arm in ARMS for seed in SEEDS
    }
    seen: set[tuple[str, str, int]] = set()
    errors_by_cell: Counter[tuple[str, str]] = Counter()
    python_versions: Counter[str] = Counter()
    total_errors = 0
    total_parseable = 0
    gate_coverage: dict[str, list[float]] = defaultdict(list)
    gate_pair_coverage: dict[str, list[float]] = defaultdict(list)

    for index, raw_row in enumerate(runs):
        if not isinstance(raw_row, dict):
            fail(f"runs[{index}] must be an object")
        row: Json = raw_row
        model = row.get("m")
        arm = row.get("a")
        seed = row.get("s")
        if model not in MODELS or arm not in ARMS or seed not in SEEDS:
            fail(f"runs[{index}] has an unknown model/arm/seed identity")
        identity = (str(model), str(arm), int(seed))
        if identity in seen:
            fail(f"duplicate run identity: {identity}")
        seen.add(identity)

        format_errors = row.get("fe")
        if not isinstance(format_errors, int) or isinstance(format_errors, bool):
            fail(f"{identity}.fe must be an integer")
        if not 0 <= format_errors <= INSTANCES_PER_RUN:
            fail(f"{identity}.fe is outside [0, {INSTANCES_PER_RUN}]")
        parseable = INSTANCES_PER_RUN - format_errors
        close(row.get("cov"), parseable / INSTANCES_PER_RUN, label=f"{identity}.cov")
        pair_coverage = row.get("pcov")
        if not isinstance(pair_coverage, (int, float)) or isinstance(pair_coverage, bool):
            fail(f"{identity}.pcov must be numeric")
        if not 0.0 <= float(pair_coverage) <= 1.0:
            fail(f"{identity}.pcov is outside [0, 1]")

        total_errors += format_errors
        total_parseable += parseable
        errors_by_cell[(str(model), str(arm))] += format_errors
        python = row.get("py")
        if python not in {"3.11.15", "3.11.16"}:
            fail(f"{identity}.py has an unexpected Python identity")
        python_versions[str(python)] += 1

        if parseable == 0:
            for key in ("fpr", "vpr", "pta", "flip", "efpr", "evpr", "epta", "catch", "fb"):
                require_value(row, key, None, identity)
            continue

        require_value(row, "fpr", 1.0, identity)
        require_value(row, "vpr", 1.0, identity)
        require_value(row, "pta", 0.0, identity)
        require_value(row, "flip", 0.0, identity)
        if arm == "ledger_verifier_gate":
            require_value(row, "efpr", 0.0, identity)
            require_value(row, "evpr", 1.0, identity)
            require_value(row, "epta", 1.0, identity)
            require_value(row, "catch", 1.0, identity)
            require_value(row, "fb", 0.0, identity)
            gate_coverage[str(model)].append(float(row["cov"]))
            gate_pair_coverage[str(model)].append(float(row["pcov"]))
        else:
            require_value(row, "efpr", 1.0, identity)
            require_value(row, "evpr", 1.0, identity)
            require_value(row, "epta", 0.0, identity)
            require_value(row, "catch", 0.0, identity)
            require_value(row, "fb", 0.0, identity)

    if seen != expected_identities:
        missing = sorted(expected_identities - seen)
        extra = sorted(seen - expected_identities)
        fail(f"run matrix mismatch: missing={missing}, extra={extra}")
    if dict(errors_by_cell) != EXPECTED_FORMAT_ERRORS:
        fail(f"per-model/arm format-error totals changed: {dict(errors_by_cell)}")
    if total_errors != freeze.get("format_error_count"):
        fail("total format-error count does not match results freeze")
    if total_parseable != freeze.get("parseable_raw_decisions"):
        fail("total parseable count does not match results freeze")
    if total_errors + total_parseable != freeze.get("total_decisions"):
        fail("release totals do not reconstruct the full decision matrix")
    if python_versions != Counter({"3.11.15": 21, "3.11.16": 3}):
        fail(f"Python patch identity distribution changed: {dict(python_versions)}")

    for suffix in MODELS:
        frozen_model = model_freeze(freeze, suffix)
        observed_cov = [min(gate_coverage[suffix]), max(gate_coverage[suffix])]
        observed_pair = [min(gate_pair_coverage[suffix]), max(gate_pair_coverage[suffix])]
        expected_cov = frozen_model.get("gate_decision_coverage_range")
        expected_pair = frozen_model.get("gate_complete_pair_coverage_range")
        if observed_cov != expected_cov:
            fail(f"{suffix} gate decision-coverage range changed")
        if observed_pair != expected_pair:
            fail(f"{suffix} gate complete-pair-coverage range changed")

    print(
        "v1-release-results: PASS "
        f"(24 runs, {total_errors} format errors, {total_parseable} parseable, "
        f"study {release['source_study_sha256']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
