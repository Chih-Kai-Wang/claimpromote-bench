"""Build, bind, and execute the narrow Lean 4 formal alpha artifacts."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .dataset import load_json, load_jsonl
from .errors import ClaimPromoteBenchError, DatasetIntegrityError
from .hashing import sha256_bytes, sha256_file

TOOLCHAIN_CONTENT = "leanprover/lean4:v4.33.0\n"
TOOLCHAIN_SHA256 = sha256_bytes(TOOLCHAIN_CONTENT.encode("utf-8"))
LAKEFILE_CONTENT = """name = \"claimpromote-formal-alpha\"
version = \"0.1.0\"
defaultTargets = [\"ClaimPromoteFormal\"]
srcDir = \"artifacts\"

[[lean_lib]]
name = \"ClaimPromoteFormal\"
"""
LAKE_MANIFEST_CONTENT = """{
  "version": "1.1.0",
  "packagesDir": ".lake/packages",
  "packages": [],
  "name": "claimpromote-formal-alpha",
  "lakeDir": ".lake"
}
"""
ROOT_MODULE_CONTENT = """import ClaimPromoteFormal.Formal01
import ClaimPromoteFormal.Formal02
import ClaimPromoteFormal.Formal03
"""

FORMAL_CLAIMS: dict[str, tuple[str, str, str]] = {
    "alpha-formal-01": (
        "For every natural number n, n + 0 = n.",
        "Formal01",
        "theorem formal01 (n : Nat) : n + 0 = n := Nat.add_zero n",
    ),
    "alpha-formal-02": (
        "For every natural number n, 0 + n = n.",
        "Formal02",
        "theorem formal02 (n : Nat) : 0 + n = n := Nat.zero_add n",
    ),
    "alpha-formal-03": (
        "For all propositions p and q, p and q holds exactly when q and p holds.",
        "Formal03",
        """theorem formal03 (p q : Prop) : p ∧ q ↔ q ∧ p :=
  ⟨fun h => ⟨h.2, h.1⟩, fun h => ⟨h.2, h.1⟩⟩""",
    ),
}

_MARKER = re.compile(r"^CPB_([A-Z0-9_]+)=(.+)$", re.MULTILINE)
Runner = Callable[[Path, Path], dict[str, Any]]


def formal_claim_text(pair_id: str) -> str:
    """Return the exact natural-language claim paired with one generated theorem."""

    try:
        return FORMAL_CLAIMS[pair_id][0]
    except KeyError as exc:
        raise DatasetIntegrityError(f"unknown formal alpha pair: {pair_id}") from exc


def formal_artifact_path(pair_id: str) -> str:
    """Return the stable dataset-relative Lean module path for one formal pair."""

    try:
        module = FORMAL_CLAIMS[pair_id][1]
    except KeyError as exc:
        raise DatasetIntegrityError(f"unknown formal alpha pair: {pair_id}") from exc
    return f"artifacts/ClaimPromoteFormal/{module}.lean"


def build_formal_artifact(pair_id: str, claim_id: str, statement_sha256: str) -> str:
    """Generate one source file whose metadata and theorem are both deterministic."""

    try:
        _claim, _module, declaration = FORMAL_CLAIMS[pair_id]
    except KeyError as exc:
        raise DatasetIntegrityError(f"unknown formal alpha pair: {pair_id}") from exc
    return f"""/-
CPB_PAIR_ID={pair_id}
CPB_CLAIM_ID={claim_id}
CPB_STATEMENT_SHA256={statement_sha256}
CPB_TOOLCHAIN_LOCK_SHA256={TOOLCHAIN_SHA256}
-/
import Init

set_option autoImplicit false

namespace ClaimPromoteFormal

{declaration}

end ClaimPromoteFormal
"""


def write_formal_package(dataset_dir: Path) -> list[str]:
    """Write the pinned Lake package files that are not item-specific artifacts."""

    toolchain = dataset_dir / "lean-toolchain"
    lakefile = dataset_dir / "lakefile.toml"
    lake_manifest = dataset_dir / "lake-manifest.json"
    root_module = dataset_dir / "artifacts" / "ClaimPromoteFormal.lean"
    root_module.parent.mkdir(parents=True, exist_ok=True)
    toolchain.write_text(TOOLCHAIN_CONTENT, encoding="utf-8", newline="\n")
    lakefile.write_text(LAKEFILE_CONTENT, encoding="utf-8", newline="\n")
    lake_manifest.write_text(LAKE_MANIFEST_CONTENT, encoding="utf-8", newline="\n")
    root_module.write_text(ROOT_MODULE_CONTENT, encoding="utf-8", newline="\n")
    return [
        "lean-toolchain",
        "lakefile.toml",
        "lake-manifest.json",
        "artifacts/ClaimPromoteFormal.lean",
    ]


def _artifact_file(dataset_dir: Path, relative: str) -> Path:
    path = (dataset_dir / relative).resolve()
    try:
        path.relative_to(dataset_dir.resolve())
    except ValueError as exc:
        raise DatasetIntegrityError(f"formal artifact path escapes dataset: {relative}") from exc
    if not path.is_file():
        raise DatasetIntegrityError(f"formal artifact is missing: {relative}")
    return path


def _markers(source: str, relative: str) -> dict[str, str]:
    values = {key: value.strip() for key, value in _MARKER.findall(source)}
    required = {
        "PAIR_ID",
        "CLAIM_ID",
        "STATEMENT_SHA256",
        "TOOLCHAIN_LOCK_SHA256",
    }
    if set(values) != required:
        raise DatasetIntegrityError(
            f"formal artifact markers differ from the registered set: {relative}"
        )
    return values


def verify_formal_artifact_binding(
    dataset_dir: Path,
    item: dict[str, Any],
    evidence: dict[str, Any],
    *,
    require_scope_match: bool,
) -> dict[str, Any]:
    """Verify source bytes, theorem metadata, and pinned toolchain binding."""

    relative = evidence.get("artifact_path")
    if not isinstance(relative, str) or not relative.endswith(".lean"):
        raise DatasetIntegrityError("formal evidence must reference a Lean source artifact")
    if relative != formal_artifact_path(str(item["pair_id"])):
        raise DatasetIntegrityError(f"formal artifact path is not registered for {item['pair_id']}")
    path = _artifact_file(dataset_dir, relative)
    if evidence.get("artifact_hash") != sha256_file(path):
        raise DatasetIntegrityError(f"formal artifact hash mismatch: {relative}")

    toolchain_path = dataset_dir / "lean-toolchain"
    if not toolchain_path.is_file():
        raise DatasetIntegrityError("formal alpha lean-toolchain file is missing")
    if toolchain_path.read_text(encoding="utf-8") != TOOLCHAIN_CONTENT:
        raise DatasetIntegrityError("formal alpha lean-toolchain content is not registered")
    actual_toolchain_hash = sha256_file(toolchain_path)
    if actual_toolchain_hash != TOOLCHAIN_SHA256:
        raise DatasetIntegrityError("formal alpha lean-toolchain hash is inconsistent")

    source = path.read_text(encoding="utf-8")
    markers = _markers(source, relative)
    context = item["claim_context"]
    if markers["PAIR_ID"] != item["pair_id"]:
        raise DatasetIntegrityError("formal artifact pair marker does not match the item")
    if markers["CLAIM_ID"] != context["claim_id"]:
        raise DatasetIntegrityError("formal artifact claim marker does not match the item")
    if markers["STATEMENT_SHA256"] != context["statement_sha256"]:
        raise DatasetIntegrityError("formal artifact statement marker does not match the item")
    if markers["TOOLCHAIN_LOCK_SHA256"] != actual_toolchain_hash:
        raise DatasetIntegrityError(
            "formal artifact toolchain marker is not pinned to lean-toolchain"
        )

    scope = evidence.get("scope")
    if not isinstance(scope, dict) or scope.get("verifier") != "lean":
        raise DatasetIntegrityError("formal evidence must declare the Lean verifier")
    if evidence.get("tool_exit") != 0 or evidence.get("verifier_result") != "PASS":
        raise DatasetIntegrityError("formal evidence must record a completed passing verifier")
    if require_scope_match and (
        scope.get("claim_id") != markers["CLAIM_ID"]
        or scope.get("statement_sha256") != markers["STATEMENT_SHA256"]
        or scope.get("toolchain_lock_sha256") != markers["TOOLCHAIN_LOCK_SHA256"]
    ):
        raise DatasetIntegrityError("formal evidence scope does not match the compiled artifact")

    return {
        "status": "BOUND",
        "pair_id": item["pair_id"],
        "artifact_path": relative,
        "artifact_sha256": sha256_file(path),
        "toolchain_sha256": actual_toolchain_hash,
    }


def _run_lean(package_dir: Path, source: Path) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            ["lake", "env", "lean", str(source.resolve())],
            cwd=package_dir,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except FileNotFoundError as exc:
        raise DatasetIntegrityError(
            "lake is unavailable; install the pinned Lean toolchain"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise DatasetIntegrityError(f"Lean verification timed out: {source}") from exc
    output = f"{completed.stdout}\0{completed.stderr}".encode("utf-8", errors="replace")
    return {
        "exit_code": completed.returncode,
        "output_sha256": sha256_bytes(output),
    }


def verify_formal_fixture_suite(
    cases_path: Path,
    *,
    package_dir: Path,
    runner: Runner = _run_lean,
) -> dict[str, Any]:
    """Execute positive and negative committed Lean fixtures under one toolchain."""

    value = load_json(cases_path)
    if not isinstance(value, list) or not value:
        raise DatasetIntegrityError("formal fixture manifest must be a non-empty array")
    seen: set[str] = set()
    results: list[dict[str, Any]] = []
    root = cases_path.parent.resolve()
    for case in value:
        if not isinstance(case, dict) or set(case) != {
            "case_id",
            "source",
            "expected_status",
        }:
            raise DatasetIntegrityError("formal fixture case has an unsupported shape")
        case_id = str(case["case_id"])
        if not case_id or case_id in seen:
            raise DatasetIntegrityError(f"missing or duplicate formal fixture case_id: {case_id!r}")
        seen.add(case_id)
        source = (root / str(case["source"])).resolve()
        try:
            source.relative_to(root)
        except ValueError as exc:
            raise DatasetIntegrityError(
                f"formal fixture path escapes its directory: {case_id}"
            ) from exc
        if not source.is_file() or source.suffix != ".lean":
            raise DatasetIntegrityError(f"formal fixture source is missing: {case_id}")
        execution = runner(package_dir, source)
        observed = "PASS" if execution["exit_code"] == 0 else "REJECT"
        if observed != case["expected_status"]:
            raise DatasetIntegrityError(
                f"formal fixture {case_id} observed {observed}, expected {case['expected_status']}"
            )
        results.append(
            {
                "case_id": case_id,
                "expected_status": case["expected_status"],
                "observed_status": observed,
                **execution,
            }
        )
    return {
        "status": "PASS",
        "fixtures": len(results),
        "positive_cases": sum(result["observed_status"] == "PASS" for result in results),
        "negative_cases": sum(result["observed_status"] == "REJECT" for result in results),
        "results": results,
    }


def verify_alpha_formal_sources(
    dataset_dir: Path,
    *,
    runner: Runner = _run_lean,
) -> dict[str, Any]:
    """Compile each unique formal alpha artifact after checking all six bindings."""

    inputs = load_jsonl(dataset_dir / "inputs.jsonl")
    gold = {record["id"]: record for record in load_jsonl(dataset_dir / "gold.jsonl")}
    paths: set[str] = set()
    evidence_count = 0
    for item in inputs:
        if item["family"] != "FORMAL":
            continue
        formal_evidence = [
            evidence for evidence in item["evidence"] if evidence["type"] == "FORMAL_CERTIFICATE"
        ]
        if len(formal_evidence) != 1:
            raise DatasetIntegrityError(f"formal alpha item needs one certificate: {item['id']}")
        evidence = formal_evidence[0]
        verify_formal_artifact_binding(
            dataset_dir,
            item,
            evidence,
            require_scope_match=gold[item["id"]]["decision"]["action"] == "ALLOW",
        )
        paths.add(str(evidence["artifact_path"]))
        evidence_count += 1
    if len(paths) != 3 or evidence_count != 6:
        raise DatasetIntegrityError("formal alpha must bind six items to three Lean artifacts")

    executions: list[dict[str, Any]] = []
    for relative in sorted(paths):
        source = _artifact_file(dataset_dir, relative)
        execution = runner(dataset_dir, source)
        if execution["exit_code"] != 0:
            raise DatasetIntegrityError(f"Lean rejected formal alpha artifact: {relative}")
        executions.append({"artifact_path": relative, **execution})
    return {
        "status": "PASS",
        "artifacts": len(paths),
        "evidence_records": evidence_count,
        "toolchain_sha256": TOOLCHAIN_SHA256,
        "executions": executions,
    }


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cpb-verify-formal", description=__doc__)
    parser.add_argument("--dataset", type=Path, default=Path("data/alpha"))
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=Path("fixtures/formal/cases.json"),
    )
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)

    try:
        alpha = verify_alpha_formal_sources(args.dataset)
        fixtures = verify_formal_fixture_suite(
            args.fixtures,
            package_dir=args.dataset,
        )
        report = {
            "status": "PASS",
            "alpha": alpha,
            "fixtures": fixtures,
        }
        if args.out:
            _write_json(args.out, report)
            output: dict[str, Any] = {
                "status": "PASS",
                "out": str(args.out),
                "alpha_artifacts": alpha["artifacts"],
                "fixture_cases": fixtures["fixtures"],
            }
        else:
            output = report
    except (ClaimPromoteBenchError, OSError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
