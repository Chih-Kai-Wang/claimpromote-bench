"""Build, bind, and execute narrow Lean 4 formal evidence artifacts."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from .dataset import load_json, load_jsonl
from .errors import ClaimPromoteBenchError, DatasetIntegrityError
from .hashing import sha256_bytes, sha256_file

TOOLCHAIN_CONTENT = "leanprover/lean4:v4.33.0\n"
TOOLCHAIN_SHA256 = sha256_bytes(TOOLCHAIN_CONTENT.encode("utf-8"))
LAKEFILE_CONTENT = """name = \"claimpromote_formal_alpha\"
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
  "name": "claimpromote_formal_alpha",
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

_V1_PAIR = re.compile(r"^v1-(dev|test)-formal-([0-9]{3})$")
_CONFIRMATORY_PAIR = re.compile(r"^v1-test-(?:cfm|cfn|cfo)-([0-9]{3})$")
_V1_FORMAL_TEMPLATES: tuple[tuple[str, str], ...] = (
    (
        "For every natural number n, n + 0 = n.",
        "theorem {name} (n : Nat) : n + 0 = n := Nat.add_zero n",
    ),
    (
        "For every natural number n, 0 + n = n.",
        "theorem {name} (n : Nat) : 0 + n = n := Nat.zero_add n",
    ),
    (
        "For all propositions p and q, p and q holds exactly when q and p holds.",
        """theorem {name} (p q : Prop) : p ∧ q ↔ q ∧ p :=
  ⟨fun h => ⟨h.2, h.1⟩, fun h => ⟨h.2, h.1⟩⟩""",
    ),
    (
        "For all propositions p and q, p or q holds exactly when q or p holds.",
        """theorem {name} (p q : Prop) : Or p q ↔ Or q p :=
  ⟨fun h => h.elim Or.inr Or.inl, fun h => h.elim Or.inr Or.inl⟩""",
    ),
    (
        "For every proposition p, p and True holds exactly when p holds.",
        """theorem {name} (p : Prop) : p ∧ True ↔ p :=
  ⟨fun h => h.1, fun h => ⟨h, True.intro⟩⟩""",
    ),
    (
        "For every proposition p, p or False holds exactly when p holds.",
        """theorem {name} (p : Prop) : Or p False ↔ p :=
  ⟨fun h => h.elim (fun hp => hp) False.elim, fun h => Or.inl h⟩""",
    ),
    (
        "For every natural number n, n multiplied by one equals n.",
        "theorem {name} (n : Nat) : n * 1 = n := Nat.mul_one n",
    ),
    (
        "For every natural number n, one multiplied by n equals n.",
        "theorem {name} (n : Nat) : 1 * n = n := Nat.one_mul n",
    ),
    (
        "Every natural number is equal to itself.",
        "theorem {name} (n : Nat) : n = n := rfl",
    ),
    (
        "For natural numbers a and b, if a equals b then b equals a.",
        "theorem {name} (a b : Nat) : a = b → b = a := fun h => h.symm",
    ),
)

_CONFIRMATORY_FORMAL_TEMPLATES: tuple[tuple[str, str], ...] = (
    (
        "Every proposition implies itself.",
        "theorem {name} (p : Prop) : p → p := fun h => h",
    ),
    (
        "A conjunction implies its left proposition.",
        "theorem {name} (p q : Prop) : p ∧ q → p := fun h => h.1",
    ),
    (
        "A conjunction implies its right proposition.",
        "theorem {name} (p q : Prop) : p ∧ q → q := fun h => h.2",
    ),
    (
        "Two established propositions establish their conjunction.",
        "theorem {name} (p q : Prop) : p → q → p ∧ q := fun hp hq => ⟨hp, hq⟩",
    ),
    (
        "A proposition implies its disjunction with any second proposition.",
        "theorem {name} (p q : Prop) : p → Or p q := fun hp => Or.inl hp",
    ),
    (
        "A second proposition implies its disjunction with any first proposition.",
        "theorem {name} (p q : Prop) : q → Or p q := fun hq => Or.inr hq",
    ),
    (
        "If either of two propositions implies a third, their disjunction implies the third.",
        "theorem {name} (p q r : Prop) : (p → r) → (q → r) → Or p q → r := "
        "fun hp hq h => h.elim hp hq",
    ),
    (
        "A left-associated triple conjunction implies the corresponding right-associated one.",
        "theorem {name} (p q r : Prop) : (p ∧ q) ∧ r → p ∧ (q ∧ r) := "
        "fun h => ⟨h.1.1, ⟨h.1.2, h.2⟩⟩",
    ),
    (
        "A right-associated triple conjunction implies the corresponding left-associated one.",
        "theorem {name} (p q r : Prop) : p ∧ (q ∧ r) → (p ∧ q) ∧ r := "
        "fun h => ⟨⟨h.1, h.2.1⟩, h.2.2⟩",
    ),
    (
        "A left-associated triple disjunction implies the corresponding right-associated one.",
        """theorem {name} (p q r : Prop) : Or (Or p q) r → Or p (Or q r) :=
  fun h => h.elim (fun hpq => hpq.elim Or.inl (fun hq => Or.inr (Or.inl hq)))
    (fun hr => Or.inr (Or.inr hr))""",
    ),
    (
        "A right-associated triple disjunction implies the corresponding left-associated one.",
        """theorem {name} (p q r : Prop) : Or p (Or q r) → Or (Or p q) r :=
  fun h => h.elim (fun hp => Or.inl (Or.inl hp))
    (fun hqr => hqr.elim (fun hq => Or.inl (Or.inr hq)) Or.inr)""",
    ),
    (
        "Implication is transitive across an intermediate proposition.",
        "theorem {name} (p q r : Prop) : (p → q) → (q → r) → p → r := "
        "fun hpq hqr hp => hqr (hpq hp)",
    ),
    (
        "Falsehood implies every proposition.",
        "theorem {name} (p : Prop) : False → p := False.elim",
    ),
    (
        "Every proposition implies truth.",
        "theorem {name} (p : Prop) : p → True := fun _ => True.intro",
    ),
    (
        "A proposition conjoined with itself is equivalent to that proposition.",
        "theorem {name} (p : Prop) : p ∧ p ↔ p := ⟨fun h => h.1, fun h => ⟨h, h⟩⟩",
    ),
    (
        "A proposition disjoined with itself is equivalent to that proposition.",
        "theorem {name} (p : Prop) : Or p p ↔ p := "
        "⟨fun h => h.elim (fun hp => hp) (fun hp => hp), fun h => Or.inl h⟩",
    ),
    (
        "A proposition conjoined with falsehood is equivalent to falsehood.",
        "theorem {name} (p : Prop) : p ∧ False ↔ False := ⟨fun h => h.2, fun h => False.elim h⟩",
    ),
    (
        "A proposition disjoined with truth is equivalent to truth.",
        "theorem {name} (p : Prop) : Or p True ↔ True := "
        "⟨fun _ => True.intro, fun _ => Or.inr True.intro⟩",
    ),
    (
        "Equal natural numbers have equal successors.",
        "theorem {name} (a b : Nat) : a = b → Nat.succ a = Nat.succ b := "
        "fun h => congrArg Nat.succ h",
    ),
    (
        "Equal successors of natural numbers have equal predecessors.",
        "theorem {name} (a b : Nat) : Nat.succ a = Nat.succ b → a = b := fun h => Nat.succ.inj h",
    ),
    (
        "Equality of natural numbers composes through an intermediate number.",
        "theorem {name} (a b c : Nat) : a = b → b = c → a = c := fun hab hbc => Eq.trans hab hbc",
    ),
    (
        "Equality of natural numbers can be reversed.",
        "theorem {name} (a b : Nat) : a = b → b = a := fun h => Eq.symm h",
    ),
    (
        "A conjunction of two consecutive equalities implies their composite equality.",
        "theorem {name} (a b c : Nat) : a = b ∧ b = c → a = c := fun h => Eq.trans h.1 h.2",
    ),
    (
        "Equality of natural numbers is equivalent to its reverse equality.",
        "theorem {name} (a b : Nat) : a = b ↔ b = a := ⟨fun h => Eq.symm h, fun h => Eq.symm h⟩",
    ),
)

_MARKER = re.compile(r"^CPB_([A-Z0-9_]+)=(.+)$", re.MULTILINE)
Runner = Callable[[Path, Path], dict[str, Any]]


def _v1_spec(pair_id: str) -> tuple[str, str, str] | None:
    match = _V1_PAIR.fullmatch(pair_id)
    if match is None:
        return None
    split, number_text = match.groups()
    number = int(number_text)
    if number < 1:
        raise DatasetIntegrityError(f"invalid v1 formal pair number: {pair_id}")
    claim, declaration_template = _V1_FORMAL_TEMPLATES[(number - 1) % len(_V1_FORMAL_TEMPLATES)]
    split_label = "Dev" if split == "dev" else "Test"
    module = f"V1{split_label}Formal{number_text}"
    theorem_name = f"v1{split}formal{number_text}"
    return claim, module, declaration_template.format(name=theorem_name)


def _confirmatory_spec(pair_id: str) -> tuple[str, str, str] | None:
    match = _CONFIRMATORY_PAIR.fullmatch(pair_id)
    if match is None:
        return None
    number_text = match.group(1)
    number = int(number_text)
    if number < 1:
        raise DatasetIntegrityError(f"invalid confirmatory formal pair number: {pair_id}")
    claim, declaration_template = _CONFIRMATORY_FORMAL_TEMPLATES[
        (number - 1) % len(_CONFIRMATORY_FORMAL_TEMPLATES)
    ]
    module = f"V1Confirmatory{number_text}"
    theorem_name = f"v1confirmatory{number_text}"
    return claim, module, declaration_template.format(name=theorem_name)


def _formal_spec(pair_id: str) -> tuple[str, str, str]:
    if pair_id in FORMAL_CLAIMS:
        return FORMAL_CLAIMS[pair_id]
    v1 = _v1_spec(pair_id)
    if v1 is not None:
        return v1
    confirmatory = _confirmatory_spec(pair_id)
    if confirmatory is not None:
        return confirmatory
    raise DatasetIntegrityError(f"unknown formal pair: {pair_id}")


def formal_claim_text(pair_id: str) -> str:
    """Return the exact natural-language claim paired with one generated theorem."""

    return _formal_spec(pair_id)[0]


def formal_module_name(pair_id: str) -> str:
    """Return the Lean module name registered for one pair."""

    return _formal_spec(pair_id)[1]


def formal_artifact_path(pair_id: str) -> str:
    """Return the stable dataset-relative Lean module path for one formal pair."""

    return f"artifacts/ClaimPromoteFormal/{formal_module_name(pair_id)}.lean"


def build_formal_artifact(pair_id: str, claim_id: str, statement_sha256: str) -> str:
    """Generate one source file whose metadata and theorem are both deterministic."""

    _claim, _module, declaration = _formal_spec(pair_id)
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


def write_formal_package(dataset_dir: Path, pair_ids: Iterable[str] | None = None) -> list[str]:
    """Write pinned Lake package files and a deterministic root import module."""

    toolchain = dataset_dir / "lean-toolchain"
    lakefile = dataset_dir / "lakefile.toml"
    lake_manifest = dataset_dir / "lake-manifest.json"
    root_module = dataset_dir / "artifacts" / "ClaimPromoteFormal.lean"
    root_module.parent.mkdir(parents=True, exist_ok=True)
    toolchain.write_text(TOOLCHAIN_CONTENT, encoding="utf-8", newline="\n")
    lakefile.write_text(LAKEFILE_CONTENT, encoding="utf-8", newline="\n")
    lake_manifest.write_text(LAKE_MANIFEST_CONTENT, encoding="utf-8", newline="\n")
    if pair_ids is None:
        root_content = ROOT_MODULE_CONTENT
    else:
        modules = sorted({formal_module_name(pair_id) for pair_id in pair_ids})
        root_content = "".join(f"import ClaimPromoteFormal.{module}\n" for module in modules)
    root_module.write_text(root_content, encoding="utf-8", newline="\n")
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
        raise DatasetIntegrityError("formal lean-toolchain file is missing")
    if toolchain_path.read_text(encoding="utf-8") != TOOLCHAIN_CONTENT:
        raise DatasetIntegrityError("formal lean-toolchain content is not registered")
    actual_toolchain_hash = sha256_file(toolchain_path)
    if actual_toolchain_hash != TOOLCHAIN_SHA256:
        raise DatasetIntegrityError("formal lean-toolchain hash is inconsistent")

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


def verify_dataset_formal_sources(
    dataset_dir: Path,
    *,
    runner: Runner = _run_lean,
) -> dict[str, Any]:
    """Compile every unique formal artifact after checking all dataset bindings."""

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
            raise DatasetIntegrityError(f"formal item needs one certificate: {item['id']}")
        evidence = formal_evidence[0]
        verify_formal_artifact_binding(
            dataset_dir,
            item,
            evidence,
            require_scope_match=gold[item["id"]]["decision"]["action"] == "ALLOW",
        )
        paths.add(str(evidence["artifact_path"]))
        evidence_count += 1

    executions: list[dict[str, Any]] = []
    for relative in sorted(paths):
        source = _artifact_file(dataset_dir, relative)
        execution = runner(dataset_dir, source)
        if execution["exit_code"] != 0:
            raise DatasetIntegrityError(f"Lean rejected formal artifact: {relative}")
        executions.append({"artifact_path": relative, **execution})
    return {
        "status": "PASS",
        "artifacts": len(paths),
        "evidence_records": evidence_count,
        "toolchain_sha256": TOOLCHAIN_SHA256,
        "executions": executions,
    }


def verify_alpha_formal_sources(
    dataset_dir: Path,
    *,
    runner: Runner = _run_lean,
) -> dict[str, Any]:
    """Preserve the alpha-specific six-record/three-artifact regression gate."""

    report = verify_dataset_formal_sources(dataset_dir, runner=runner)
    if report["artifacts"] != 3 or report["evidence_records"] != 6:
        raise DatasetIntegrityError("formal alpha must bind six items to three Lean artifacts")
    return report


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
        dataset = (
            verify_alpha_formal_sources(args.dataset)
            if args.dataset.name == "alpha"
            else verify_dataset_formal_sources(args.dataset)
        )
        fixtures = verify_formal_fixture_suite(
            args.fixtures,
            package_dir=args.dataset,
        )
        report = {
            "status": "PASS",
            "dataset": dataset,
            "fixtures": fixtures,
        }
        if args.out:
            _write_json(args.out, report)
            output: dict[str, Any] = {
                "status": "PASS",
                "out": str(args.out),
                "formal_artifacts": dataset["artifacts"],
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
