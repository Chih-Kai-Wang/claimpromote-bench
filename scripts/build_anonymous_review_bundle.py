#!/usr/bin/env python3
"""Build an anonymized, public-data reviewer bundle for double-blind evaluation.

The bundle contains public benchmark code/data and compact v1/v2 result summaries. It excludes Git
history, author metadata, public repository links, workflow IDs, public provenance hashes, hidden
study data, and raw human-review submissions. The builder fails if a forbidden identity token
survives staging.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {
    ".cff",
    ".json",
    ".jsonl",
    ".lean",
    ".md",
    ".py",
    ".sh",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
SKIP_NAMES = {
    ".git",
    ".github",
    ".lake",
    ".mypy_cache",
    ".pytest_cache",
    "__pycache__",
    "work",
}
FORBIDDEN_TEXT = {
    "Chih-Kai Wang",
    "Wang, Chih-Kai",
    "National Taipei University of Education",
    "f0909172434",
    "f0909172434@gmail.com",
    "github.com/f0909172434",
    "paper/v1-submission-prep",
    "agent/iclr2027-v2-low-cost-study",
    "32255636879",
    "32274814703",
    "32291482079",
    "32297818154",
    "3eb5b534ab486dac774a62de3d623fa33009be3705d9e8d620bb9942e8bfe664",
    "83dbee4923bca6a0d1908083172190d7b81e2a5e9613c22e4929cfa25c0b264e",
    "f998a05fec36b84e59230fe241f1e9961647ad2e",
    "8d9b3f5c831f432cf6b321e6402724c4f52bb3e1",
    "aa5268dcde2aa44f8eabf0246631efbca27de7e5",
    "e2b09f30b0573cf7bcb244eef1917691755f2877",
}

Json = dict[str, Any]


def fail(message: str) -> None:
    raise SystemExit(f"anonymous-review-bundle: {message}")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def load_object(path: Path) -> Json:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        fail(f"expected JSON object: {path.relative_to(ROOT)}")
    return value


def strip_schema_ids(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: strip_schema_ids(child) for key, child in value.items() if key != "$id"}
    if isinstance(value, list):
        return [strip_schema_ids(child) for child in value]
    return value


def should_skip(path: Path) -> bool:
    return any(part in SKIP_NAMES for part in path.parts)


def copy_tree(source: Path, destination: Path) -> None:
    if not source.exists():
        fail(f"missing source path: {source.relative_to(ROOT)}")
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        if should_skip(relative):
            continue
        target = destination / relative
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix == ".json" and "schemas" in path.parts:
            value = strip_schema_ids(json.loads(path.read_text(encoding="utf-8")))
            target.write_text(
                json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        else:
            shutil.copyfile(path, target)


def copy_file(source: Path, destination: Path) -> None:
    if not source.is_file():
        fail(f"missing source file: {source.relative_to(ROOT)}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.suffix == ".json" and "schemas" in source.parts:
        value = strip_schema_ids(json.loads(source.read_text(encoding="utf-8")))
        destination.write_text(
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    else:
        shutil.copyfile(source, destination)


def rewrite_alpha_manifest(bundle: Path) -> None:
    manifest_path = bundle / "data" / "alpha" / "manifest.json"
    manifest = load_object(manifest_path)
    schema_hashes = manifest.get("schema_sha256")
    if not isinstance(schema_hashes, dict):
        fail("alpha manifest lacks schema_sha256")
    for name in sorted(schema_hashes):
        schema_path = bundle / "schemas" / name
        if not schema_path.is_file():
            fail(f"anonymous bundle lacks alpha schema: {name}")
        schema_hashes[name] = sha256_file(schema_path)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def anonymize_v1_results(source: Json) -> Json:
    runs = source.get("runs")
    if not isinstance(runs, list) or len(runs) != 24:
        fail("v1 public result source does not contain 24 runs")
    return {
        "schema_version": "1.0.0-review",
        "study_kind": "FROZEN_V1_HIDDEN_RESULT_SUMMARY",
        "source_identity": "WITHHELD_DURING_DOUBLE_BLIND_REVIEW",
        "dataset": {
            "evaluation_time": source.get("dataset", {}).get("evaluation_time"),
            "instances_per_run": 300,
        },
        "runs": runs,
        "interpretation_boundary": (
            "This compact summary permits paper-value validation but does not include the private "
            "hidden dataset or raw source artifacts."
        ),
    }


def remove_keys(value: Any, forbidden_keys: set[str]) -> Any:
    if isinstance(value, dict):
        return {
            key: remove_keys(child, forbidden_keys)
            for key, child in value.items()
            if key not in forbidden_keys
        }
    if isinstance(value, list):
        return [remove_keys(child, forbidden_keys) for child in value]
    return value


def anonymize_v2_results(source: Json) -> Json:
    cleaned = remove_keys(
        source,
        {
            "source_workflow_run_id",
            "study_sha256",
            "run_sha256",
            "run_path",
        },
    )
    if not isinstance(cleaned, dict):
        fail("unexpected v2 result structure")
    cleaned["schema_version"] = "1.0.0-review"
    cleaned["source_identity"] = "WITHHELD_DURING_DOUBLE_BLIND_REVIEW"
    return cleaned


def minimal_pyproject() -> str:
    return """[build-system]
requires = ["setuptools>=75", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "claimpromote-bench-anonymous-review"
version = "0.1.0"
description = "Anonymous public-data validation bundle"
requires-python = ">=3.11"
dependencies = ["jsonschema>=4.23,<5"]

[project.optional-dependencies]
test = ["pytest>=8.3,<10", "pytest-cov>=6,<8"]

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra"

[tool.coverage.run]
branch = true
source = ["claimpromotebench"]
"""


def review_readme() -> str:
    return """# ClaimPromoteBench anonymous reviewer bundle

This bundle contains the public controlled benchmark, executable fixtures, public Lean package,
selected validation code, compact v1/v2 paper-result summaries, and naturalistic-data boundary
checks. It contains no Git history, author metadata, public repository link, hidden v1 dataset,
hidden seed, raw human-review submission, or public workflow/provenance identifier.

## What can be checked

```bash
python -m pip install -e ".[test]"
python scripts/run_review_checks.py
```

The checks rebuild and validate the public alpha benchmark, run shortcut/invariance/executable
checks, validate the compact v1 and v2 paper-result summaries, validate the unlabeled naturalistic
candidate pool and case boundary, and run selected v2 tests.

For the public formal artifacts:

```bash
cd data/alpha
lake build
lake env leanchecker ClaimPromoteFormal
cd ../..
python -m claimpromotebench.formal \
  --dataset data/alpha \
  --fixtures fixtures/formal/cases.json \
  --out work/formal-fixtures.json
```

## Scope limitation

The private hidden dataset and its raw source artifacts are not included in this double-blind
bundle. `results/v1-paper-results.json` is a compact per-run summary suitable for checking the
reported matrix totals, conditional rates, and coverage ranges. The post-v1 public pilot aggregate
contains public pair/factor metrics but omits public provenance identifiers and raw response text.

Post-gate correctness applies the same fixed policy as the benchmark oracle. It must not be
interpreted as model learning or independent prediction accuracy.
"""


def review_validator() -> str:
    return r'''#!/usr/bin/env python3
"""Validate anonymous compact v1/v2 result summaries."""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
V1 = ROOT / "results" / "v1-paper-results.json"
V2 = ROOT / "results" / "v2-public-pilot-study.json"
MODELS = ("0.6B", "1.7B")
ARMS = ("narrative", "ledger", "ledger_verifier", "ledger_verifier_gate")
SEEDS = (104729, 130363, 169087)
EXPECTED_ERRORS = {
    ("0.6B", "narrative"): 900,
    ("0.6B", "ledger"): 261,
    ("0.6B", "ledger_verifier"): 335,
    ("0.6B", "ledger_verifier_gate"): 585,
    ("1.7B", "narrative"): 900,
    ("1.7B", "ledger"): 900,
    ("1.7B", "ledger_verifier"): 900,
    ("1.7B", "ledger_verifier_gate"): 546,
}


def fail(message: str) -> None:
    raise SystemExit(f"review-results: {message}")


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        fail(f"{path.name} is not a JSON object")
    return value


def close(observed: Any, expected: float, label: str) -> None:
    if not isinstance(observed, (int, float)) or isinstance(observed, bool):
        fail(f"{label} is not numeric")
    if not math.isclose(float(observed), expected, rel_tol=0.0, abs_tol=1e-12):
        fail(f"{label}: expected {expected}, got {observed}")


def validate_v1(value: dict[str, Any]) -> None:
    runs = value.get("runs")
    if not isinstance(runs, list) or len(runs) != 24:
        fail("v1 summary must contain 24 runs")
    seen: set[tuple[str, str, int]] = set()
    errors: Counter[tuple[str, str]] = Counter()
    python_versions: Counter[str] = Counter()
    total_errors = 0
    total_parseable = 0
    gate_cov: dict[str, list[float]] = defaultdict(list)
    gate_pair_cov: dict[str, list[float]] = defaultdict(list)
    for row in runs:
        identity = (str(row["m"]), str(row["a"]), int(row["s"]))
        if identity in seen:
            fail(f"duplicate v1 run: {identity}")
        seen.add(identity)
        format_errors = int(row["fe"])
        parseable = 300 - format_errors
        close(row["cov"], parseable / 300, f"{identity}.coverage")
        total_errors += format_errors
        total_parseable += parseable
        errors[(identity[0], identity[1])] += format_errors
        python_versions[str(row["py"])] += 1
        if parseable:
            close(row["fpr"], 1.0, f"{identity}.raw_fpr")
            close(row["vpr"], 1.0, f"{identity}.raw_vpr")
            close(row["pta"], 0.0, f"{identity}.raw_pta")
            if identity[1] == "ledger_verifier_gate":
                close(row["efpr"], 0.0, f"{identity}.effective_fpr")
                close(row["epta"], 1.0, f"{identity}.effective_pta")
                gate_cov[identity[0]].append(float(row["cov"]))
                gate_pair_cov[identity[0]].append(float(row["pcov"]))
        elif any(row.get(key) is not None for key in ("fpr", "vpr", "pta")):
            fail(f"undefined v1 rates are populated: {identity}")
    expected = {(model, arm, seed) for model in MODELS for arm in ARMS for seed in SEEDS}
    if seen != expected:
        fail("v1 run matrix is incomplete")
    if dict(errors) != EXPECTED_ERRORS:
        fail("v1 model/arm format-error totals changed")
    if (total_errors, total_parseable) != (5327, 1873):
        fail("v1 headline totals changed")
    if python_versions != Counter({"3.11.15": 21, "3.11.16": 3}):
        fail("v1 Python identity distribution changed")
    expected_ranges = {
        "0.6B": ((0.14, 0.49), (0.07333333333333333, 0.35333333333333333)),
        "1.7B": ((0.21666666666666667, 0.48333333333333334), (0.1, 0.38)),
    }
    for model, (coverage, pair_coverage) in expected_ranges.items():
        if (min(gate_cov[model]), max(gate_cov[model])) != coverage:
            fail(f"v1 {model} gate coverage range changed")
        if (min(gate_pair_cov[model]), max(gate_pair_cov[model])) != pair_coverage:
            fail(f"v1 {model} gate pair-coverage range changed")


def validate_v2(value: dict[str, Any]) -> None:
    if value.get("aggregate_status_counts") != {"OK": 108, "SCHEMA_ERROR": 52}:
        fail("v2 aggregate status counts changed")
    protocol = value.get("protocol")
    if not isinstance(protocol, dict) or protocol.get("total_decisions") != 160:
        fail("v2 protocol changed")
    runs = value.get("runs")
    if not isinstance(runs, list) or len(runs) != 4:
        fail("v2 must contain four run summaries")
    expected = {
        ("Qwen/Qwen3-0.6B", "free"): (0.75, 0.70, 30),
        ("Qwen/Qwen3-0.6B", "json_schema"): (1.0, 1.0, 40),
        ("Qwen/Qwen3-1.7B", "free"): (0.0, 0.0, 0),
        ("Qwen/Qwen3-1.7B", "json_schema"): (0.95, 0.90, 38),
    }
    constrained_ok = 0
    constrained_pairs = 0
    for row in runs:
        identity = (str(row["model_id"]), str(row["decoding_mode"]))
        if identity not in expected:
            fail(f"unexpected v2 run: {identity}")
        summary = row["summary"]
        coverage, pair_coverage, ok = expected[identity]
        close(summary["decision_coverage"], coverage, f"{identity}.coverage")
        close(summary["pair_coverage"], pair_coverage, f"{identity}.pair_coverage")
        if int(summary["status_counts"]["OK"]) != ok:
            fail(f"{identity} OK count changed")
        if ok:
            close(summary["raw_action_accuracy"], 0.5, f"{identity}.raw_accuracy")
            close(summary["raw_pair_accuracy"], 0.0, f"{identity}.pair_accuracy")
            close(summary["raw_flip_rate"], 0.0, f"{identity}.flip_rate")
            close(summary["raw_fpr"], 1.0, f"{identity}.raw_fpr")
            close(summary["raw_vpr"], 1.0, f"{identity}.raw_vpr")
        if identity[1] == "json_schema":
            constrained_ok += ok
            constrained_pairs += int(summary["covered_pairs"])
    if (constrained_ok, constrained_pairs) != (78, 38):
        fail("v2 constrained headline counts changed")


def main() -> int:
    validate_v1(load(V1))
    validate_v2(load(V2))
    print("review-results: PASS (v1 7,200 decisions; v2 160 decisions)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def review_runner() -> str:
    return r'''#!/usr/bin/env python3
"""Run public anonymous-review checks."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMANDS = [
    [sys.executable, "-m", "claimpromotebench", "validate", "data/alpha"],
    [
        sys.executable,
        "-m",
        "claimpromotebench.shortcuts",
        "--dataset",
        "data/alpha",
        "--out",
        "work/shortcut-audit.json",
    ],
    [
        sys.executable,
        "-m",
        "claimpromotebench.invariance",
        "--dataset",
        "data/alpha",
        "--out",
        "work/invariance-audit.json",
    ],
    [
        sys.executable,
        "-m",
        "claimpromotebench.executable",
        "--fixtures",
        "fixtures/executable",
        "--out",
        "work/executable-fixtures.json",
    ],
    [sys.executable, "scripts/validate_review_results.py"],
    [
        sys.executable,
        "scripts/validate_v2_naturalistic_candidates.py",
        "--pool",
        "v2/naturalistic-candidates.json",
        "--out",
        "work/naturalistic-candidate-validation.json",
    ],
    [
        sys.executable,
        "scripts/validate_v2_naturalistic_cases.py",
        "--root",
        "v2/naturalistic-cases",
        "--allow-empty",
        "--out",
        "work/naturalistic-case-validation.json",
    ],
    [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "tests/test_v2.py",
        "tests/test_v2_naturalistic.py",
        "tests/test_v2_naturalistic_cases.py",
    ],
]


def main() -> int:
    (ROOT / "work").mkdir(exist_ok=True)
    for command in COMMANDS:
        print("+", " ".join(command), flush=True)
        subprocess.run(command, cwd=ROOT, check=True)
    print("anonymous-review-checks: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def scan_identity(bundle: Path) -> None:
    findings: list[str] = []
    for path in sorted(bundle.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for token in sorted(FORBIDDEN_TEXT):
            if token.lower() in text.lower():
                findings.append(f"{path.relative_to(bundle)}: {token}")
    if findings:
        fail("identity/provenance leak detected:\n" + "\n".join(findings))


def write_manifest(bundle: Path) -> None:
    files = {
        str(path.relative_to(bundle)).replace("\\", "/"): sha256_file(path)
        for path in sorted(bundle.rglob("*"))
        if path.is_file() and path.name != "MANIFEST.json"
    }
    manifest = {
        "schema_version": "1.0.0-review",
        "status": "ANONYMOUS_PUBLIC_DATA_REVIEW_BUNDLE",
        "file_count": len(files),
        "files": files,
        "scope": {
            "public_alpha_included": True,
            "private_hidden_data_included": False,
            "raw_human_review_submissions_included": False,
            "public_repository_identity_included": False,
            "v1_compact_result_summary_included": True,
            "v2_public_pilot_summary_included": True,
        },
    }
    (bundle / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build(destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)

    for directory in ("src/claimpromotebench", "data/alpha", "policies", "schemas", "fixtures"):
        copy_tree(ROOT / directory, destination / directory)

    selected_files = (
        "scripts/build_alpha.py",
        "scripts/build_v1_dataset.py",
        "scripts/validate_v1_plan.py",
        "scripts/validate_v1_public_dev_freeze.py",
        "scripts/validate_v2_naturalistic_candidates.py",
        "scripts/validate_v2_naturalistic_cases.py",
        "tests/test_v2.py",
        "tests/test_v2_naturalistic.py",
        "tests/test_v2_naturalistic_cases.py",
        "v2/naturalistic-candidates.json",
        "v2/naturalistic-sources.json",
        "v2/schemas/run-record-v2.schema.json",
        "v2/schemas/naturalistic-case.schema.json",
    )
    for relative in selected_files:
        copy_file(ROOT / relative, destination / relative)

    rewrite_alpha_manifest(destination)

    (destination / "results").mkdir()
    v1 = anonymize_v1_results(load_object(ROOT / "release" / "v1-paper-results.json"))
    v2 = anonymize_v2_results(
        load_object(ROOT / "v2" / "pilot-results" / "v2-public-pilot-study.json")
    )
    (destination / "results" / "v1-paper-results.json").write_text(
        json.dumps(v1, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (destination / "results" / "v2-public-pilot-study.json").write_text(
        json.dumps(v2, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    (destination / "pyproject.toml").write_text(minimal_pyproject(), encoding="utf-8")
    (destination / "README.md").write_text(review_readme(), encoding="utf-8")
    (destination / "scripts" / "validate_review_results.py").write_text(
        review_validator(), encoding="utf-8"
    )
    (destination / "scripts" / "run_review_checks.py").write_text(review_runner(), encoding="utf-8")

    scan_identity(destination)
    write_manifest(destination)
    scan_identity(destination)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    destination = args.out.resolve()
    build(destination)
    print(
        json.dumps(
            {
                "status": "PASS",
                "output": str(destination),
                "manifest_sha256": sha256_file(destination / "MANIFEST.json"),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
