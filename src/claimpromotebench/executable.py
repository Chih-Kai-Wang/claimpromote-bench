"""Safe exact-arithmetic executable evidence fixtures."""

from __future__ import annotations

import argparse
import json
import re
import sys
from fractions import Fraction
from pathlib import Path
from typing import Any, NoReturn

from .dataset import load_json, repository_root, validate_with_schema
from .errors import ClaimPromoteBenchError, DatasetIntegrityError, ExecutableFixtureError
from .hashing import canonical_json, sha256_bytes

ARTIFACT_KIND = "CPB_EXACT_RATIONAL_GRID"
PROTOCOL_ID = "cpb-exact-grid-v1"
PROTOCOL_VERSION = "1.0.0"
MAX_COEFFICIENTS = 32
MAX_GRID_POINTS = 4096
MAX_RATIONAL_CHARS = 96
MAX_REPETITIONS = 32
_RATIONAL = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:/[1-9][0-9]*)?$")


def _fail(code: str, message: str) -> NoReturn:
    raise ExecutableFixtureError(code, message)


def _fraction(value: Any, label: str) -> Fraction:
    if not isinstance(value, str):
        _fail("INVALID_RATIONAL", f"{label} must be a rational string")
    if len(value) > MAX_RATIONAL_CHARS or not _RATIONAL.fullmatch(value):
        _fail("INVALID_RATIONAL", f"{label} is not a bounded rational")
    try:
        return Fraction(value)
    except (ValueError, ZeroDivisionError) as exc:
        raise ExecutableFixtureError("INVALID_RATIONAL", f"{label}: {exc}") from exc


def _format_fraction(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"


def _evaluate_polynomial(coefficients: list[Fraction], x: Fraction) -> Fraction:
    total = Fraction(0)
    power = Fraction(1)
    for coefficient in coefficients:
        total += coefficient * power
        power *= x
    return total


def _predicate_holds(values: list[Fraction], relation: str, threshold: Fraction) -> bool:
    if relation == ">=":
        return all(value >= threshold for value in values)
    if relation == "<=":
        return all(value <= threshold for value in values)
    if relation == "==":
        return all(value == threshold for value in values)
    _fail("UNSUPPORTED_PREDICATE", f"unsupported predicate relation: {relation}")


def _repetition_digest(
    artifact: dict[str, Any],
    values: list[str],
    repetition: int,
) -> str:
    payload = {
        "artifact_kind": artifact["artifact_kind"],
        "protocol_id": artifact["protocol_id"],
        "protocol_version": artifact["protocol_version"],
        "program": artifact["program"],
        "repetition": repetition,
        "values": values,
    }
    return sha256_bytes(canonical_json(payload).encode("utf-8"))


def verify_exact_grid_artifact(artifact: dict[str, Any]) -> dict[str, Any]:
    """Recompute one finite-grid polynomial artifact without shell execution."""

    if artifact.get("artifact_kind") != ARTIFACT_KIND:
        _fail("UNSUPPORTED_ARTIFACT", "artifact kind is not registered")
    if (
        artifact.get("protocol_id") != PROTOCOL_ID
        or artifact.get("protocol_version") != PROTOCOL_VERSION
    ):
        _fail("UNSUPPORTED_PROTOCOL", "protocol identifier or version is not registered")
    if artifact.get("claim_scope") != "FINITE_GRID_ONLY":
        _fail("SCOPE_MISMATCH", "executable fixture must declare finite-grid-only scope")
    if artifact.get("arithmetic") != "EXACT_RATIONAL":
        _fail("UNSUPPORTED_ARITHMETIC", "only exact rational arithmetic is registered")
    if artifact.get("preregistered") is not True:
        _fail("PREREGISTRATION_REQUIRED", "fixture must declare preregistration")

    repetition_value = artifact.get("repetitions")
    if (
        isinstance(repetition_value, bool)
        or not isinstance(repetition_value, int)
        or not 1 <= repetition_value <= MAX_REPETITIONS
    ):
        _fail("RESOURCE_LIMIT", "repetition count is outside the registered limit")
    repetitions = repetition_value

    program = artifact["program"]
    coefficient_text = list(program["coefficients"])
    grid_text = list(program["grid"])
    if not 1 <= len(coefficient_text) <= MAX_COEFFICIENTS:
        _fail("RESOURCE_LIMIT", "coefficient count is outside the registered limit")
    if not 2 <= len(grid_text) <= MAX_GRID_POINTS:
        _fail("RESOURCE_LIMIT", "grid size is outside the registered limit")

    coefficients = [
        _fraction(value, f"coefficient[{index}]")
        for index, value in enumerate(coefficient_text)
    ]
    grid = [_fraction(value, f"grid[{index}]") for index, value in enumerate(grid_text)]
    lower = _fraction(program["domain"]["lower"], "domain.lower")
    upper = _fraction(program["domain"]["upper"], "domain.upper")
    if lower >= upper:
        _fail("INVALID_GRID", "domain lower bound must be below upper bound")
    if grid != sorted(set(grid)):
        _fail("INVALID_GRID", "grid points must be unique and strictly increasing")
    if grid[0] != lower or grid[-1] != upper:
        _fail("INVALID_GRID", "grid must include both declared domain endpoints")
    if any(value < lower or value > upper for value in grid):
        _fail("INVALID_GRID", "grid point lies outside the declared domain")

    values = [_evaluate_polynomial(coefficients, value) for value in grid]
    value_text = [_format_fraction(value) for value in values]
    predicate = program["predicate"]
    threshold = _fraction(predicate["threshold"], "predicate.threshold")
    holds = _predicate_holds(values, str(predicate["relation"]), threshold)
    minimum = _format_fraction(min(values))
    maximum = _format_fraction(max(values))

    observed = artifact["observed"]
    if (
        observed["values"] != value_text
        or observed["minimum"] != minimum
        or observed["maximum"] != maximum
        or observed["predicate_holds"] is not holds
    ):
        _fail("OBSERVATION_MISMATCH", "observed values do not match exact recomputation")

    expected_digests = [
        _repetition_digest(artifact, value_text, repetition)
        for repetition in range(repetitions)
    ]
    if observed["repetition_digests"] != expected_digests:
        _fail(
            "REPETITION_DIGEST_MISMATCH",
            "repetition digests do not match exact recomputation",
        )

    return {
        "status": "PASS",
        "artifact_sha256": sha256_bytes(canonical_json(artifact).encode("utf-8")),
        "grid_points": len(grid),
        "minimum": minimum,
        "maximum": maximum,
        "predicate_holds": holds,
        "repetitions": repetitions,
    }


def verify_fixture_case(case: dict[str, Any]) -> dict[str, Any]:
    """Verify that one positive or negative fixture has its declared outcome."""

    root = repository_root()
    validate_with_schema(
        case,
        root / "schemas" / "executable-fixture-case.schema.json",
        str(case.get("case_id", "fixture")),
    )
    expected = str(case["expected_status"])
    try:
        result = verify_exact_grid_artifact(case["artifact"])
    except ExecutableFixtureError as exc:
        if expected != "REJECT":
            raise DatasetIntegrityError(
                f"fixture {case['case_id']} unexpectedly rejected: {exc.code}"
            ) from exc
        if exc.code != case.get("expected_error_code"):
            raise DatasetIntegrityError(
                f"fixture {case['case_id']} rejected with {exc.code}, "
                f"expected {case.get('expected_error_code')}"
            ) from exc
        return {
            "case_id": case["case_id"],
            "expected_status": expected,
            "observed_status": "REJECT",
            "error_code": exc.code,
        }

    if expected != "PASS":
        raise DatasetIntegrityError(f"fixture {case['case_id']} unexpectedly passed")
    return {
        "case_id": case["case_id"],
        "expected_status": expected,
        "observed_status": "PASS",
        "result": result,
    }


def verify_fixture_suite(directory: Path) -> dict[str, Any]:
    """Verify every JSON fixture in a directory with deterministic ordering."""

    paths = sorted(directory.glob("*.json"))
    if not paths:
        raise DatasetIntegrityError(f"no executable fixtures found in {directory}")
    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in paths:
        case = load_json(path)
        if not isinstance(case, dict):
            raise DatasetIntegrityError(f"fixture is not an object: {path}")
        case_id = str(case.get("case_id", ""))
        if not case_id or case_id in seen:
            raise DatasetIntegrityError(f"missing or duplicate fixture case_id: {case_id!r}")
        seen.add(case_id)
        results.append(verify_fixture_case(case))

    return {
        "status": "PASS",
        "fixtures": len(results),
        "positive_cases": sum(result["observed_status"] == "PASS" for result in results),
        "negative_cases": sum(result["observed_status"] == "REJECT" for result in results),
        "results": results,
    }


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    """Run the safe executable-fixture suite."""

    parser = argparse.ArgumentParser(prog="cpb-verify-fixtures", description=__doc__)
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=Path("fixtures/executable"),
    )
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)

    try:
        report = verify_fixture_suite(args.fixtures)
        if args.out:
            _write_json(args.out, report)
            output: dict[str, Any] = {
                "out": str(args.out),
                "status": report["status"],
                "fixtures": report["fixtures"],
                "positive_cases": report["positive_cases"],
                "negative_cases": report["negative_cases"],
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
