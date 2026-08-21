#!/usr/bin/env python3
"""Build ClaimPromoteBench v1 dev or private test data from one frozen constructor."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import shutil
import sys
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from claimpromotebench.dataset import validate_dataset  # noqa: E402
from claimpromotebench.executable import build_exact_grid_artifact  # noqa: E402
from claimpromotebench.formal import (  # noqa: E402
    TOOLCHAIN_SHA256,
    build_formal_artifact,
    formal_artifact_path,
    formal_claim_text,
    write_formal_package,
)
from claimpromotebench.hashing import sha256_bytes, sha256_file  # noqa: E402
from claimpromotebench.oracle import evaluate  # noqa: E402

Json = dict[str, Any]
PLAN_PATH = ROOT / "configs" / "v1-benchmark-plan.json"
POLICY_PATH = ROOT / "policies" / "math-evidence-transition-1.0.0.json"
INPUT_SCHEMA = ROOT / "schemas" / "benchmark-input-v1.schema.json"
GOLD_SCHEMA = ROOT / "schemas" / "gold-label.schema.json"
PUBLIC_DEV_SEED = hashlib.sha256(b"claimpromotebench-v1-public-dev-v1").digest()

FAMILY_CODES = {
    "DEPENDENCY": "dep",
    "NUMERICAL": "num",
    "RUNTIME": "run",
    "STALE_CONTRADICTION": "stale",
    "PROVENANCE": "prov",
    "FORMAL": "formal",
}

POINTERS = {
    "direct_dependency": ["/evidence"],
    "transitive_dependency": ["/evidence"],
    "dependency_verifier": ["/evidence/1/verifier_result"],
    "dependency_statement": ["/evidence/1/scope/statement_sha256"],
    "repetitions": ["/evidence/0/scope/repetitions"],
    "domain": ["/evidence/0/scope/domain/variables/0/upper"],
    "preregistration": ["/evidence/0/scope/preregistered"],
    "precision": ["/evidence/0/scope/precision_bits"],
    "tool_exit": ["/evidence/0/tool_exit"],
    "verifier_execution": ["/evidence/0/verifier_result"],
    "run_completion": ["/evidence/0/tool_exit", "/evidence/0/verifier_result"],
    "age": ["/evidence/0/timestamp"],
    "current_binding": ["/current_state_basis/computation_status/bound_artifact_sha256"],
    "contradiction": ["/evidence/1/scope/contradiction_status"],
    "reviewer_identity": ["/evidence/0/provenance/actor_id"],
    "review_environment": ["/evidence/0/provenance/environment_sha256"],
    "cold_start": ["/evidence/0/provenance/cold_start"],
    "statement_identity": ["/evidence/0/scope/statement_sha256"],
    "claim_identity": ["/evidence/0/scope/claim_id"],
    "trust_base": ["/evidence/0/scope/toolchain_lock_sha256"],
}

SURFACE_TEXT = {
    "algebraic_identity": "The registered algebraic invariant holds for every admissible input.",
    "order_inequality": "The registered order inequality holds throughout the declared scope.",
    "finite_sequence": "The registered invariant holds for every entry of the finite sequence.",
    "polynomial_grid": "The registered polynomial condition holds on the declared finite grid.",
    "matrix_property": "The registered matrix property holds for the declared bounded object.",
    "graph_property": "The registered graph property holds for the declared finite structure.",
    "recurrence": "The registered recurrence invariant holds on the declared bounded range.",
    "probability_bound": "The registered probability bound holds under the declared assumptions.",
    "number_theory": "The registered arithmetic property holds for the declared finite instance.",
    "set_relation": "The registered set relation holds over the declared bounded universe.",
}


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def write_jsonl(path: Path, records: list[Json]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(f"{canonical(record)}\n" for record in records),
        encoding="utf-8",
        newline="\n",
    )


def label_digest(label: str) -> str:
    return sha256_bytes(label.encode("utf-8"))


def opaque(label: str, length: int = 16) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()[:length]


def keyed_bytes(seed: bytes, label: str) -> bytes:
    return hmac.new(seed, label.encode("utf-8"), hashlib.sha256).digest()


def pick(seed: bytes, label: str, values: list[str]) -> str:
    if not values:
        raise ValueError("cannot pick from an empty list")
    index = int.from_bytes(keyed_bytes(seed, label)[:8], "big") % len(values)
    return values[index]


def load_seed(split: str, seed_file: Path | None) -> bytes:
    if split == "dev":
        if seed_file is not None:
            raise ValueError("public dev construction does not accept a private seed")
        return PUBLIC_DEV_SEED
    if seed_file is None:
        raise ValueError("private test construction requires --seed-file")
    raw = seed_file.read_bytes()
    if len(raw) == 32:
        return raw
    stripped = raw.strip()
    if len(stripped) == 64:
        try:
            seed = bytes.fromhex(stripped.decode("ascii"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise ValueError("test seed must be 32 raw bytes or 64 hex digits") from exc
        if len(seed) == 32:
            return seed
    raise ValueError("test seed must be 32 raw bytes or 64 hex digits")


def state(
    research: str = "OPEN",
    computation: str = "NONE",
    formal: str = "NONE",
    review: str = "UNREVIEWED",
) -> Json:
    return {
        "research_status": research,
        "computation_status": computation,
        "formal_status": formal,
        "review_status": review,
    }


def domain(upper: str = "1") -> Json:
    return {
        "variables": [
            {
                "name": "x",
                "lower": "0",
                "upper": upper,
                "lower_inclusive": True,
                "upper_inclusive": True,
            }
        ]
    }


def evidence(
    pair_id: str,
    role: str,
    evidence_type: str,
    claim_id: str,
    statement_sha256: str,
    artifact_path: str,
    artifact_hash: str,
    *,
    scope_extra: Json | None = None,
    dependencies: list[str] | None = None,
    tool_exit: int | None = 0,
    verifier_result: str = "PASS",
    timestamp: str = "2026-08-01T00:00:00Z",
    actor_id: str = "cpb-tool",
    actor_role: str = "TOOL",
    environment_sha256: str | None = None,
    cold_start: bool = True,
) -> Json:
    evidence_id = f"ev-{opaque(f'{pair_id}:{role}')}"
    scope: Json = {"claim_id": claim_id, "statement_sha256": statement_sha256}
    scope.update(scope_extra or {})
    return {
        "id": evidence_id,
        "type": evidence_type,
        "provenance": {
            "actor_id": actor_id,
            "actor_role": actor_role,
            "run_id": opaque(f"run:{pair_id}:{role}"),
            "environment_sha256": environment_sha256
            or label_digest(f"environment:{pair_id}:{role}"),
            "cold_start": cold_start,
        },
        "artifact_path": artifact_path,
        "artifact_hash": artifact_hash,
        "scope": scope,
        "dependencies": dependencies or [],
        "tool_exit": tool_exit,
        "verifier_result": verifier_result,
        "timestamp": timestamp,
    }


def claim_text(pair_id: str, family: str, surface: str) -> str:
    if family == "FORMAL":
        return formal_claim_text(pair_id)
    if family == "NUMERICAL":
        return (
            f"[{surface}] On the registered exact rational grid for this bounded object, "
            "the declared polynomial predicate holds at every grid point."
        )
    return f"[{surface}] {SURFACE_TEXT[surface]}"


def base_item(pair_id: str, family: str, surface: str) -> Json:
    text = claim_text(pair_id, family, surface)
    claim_id = f"claim-{opaque(f'claim:{pair_id}', 12)}"
    return {
        "schema_version": "1.0.0",
        "pair_id": pair_id,
        "split": pair_id.split("-")[1],
        "family": family,
        "claim_text": text,
        "policy_id": "math-evidence-transition",
        "policy_version": "1.0.0",
        "claim_context": {
            "claim_id": claim_id,
            "author_id": f"author-{opaque(f'author:{pair_id}', 12)}",
            "author_environment_sha256": label_digest(f"author-environment:{pair_id}"),
            "statement_sha256": label_digest(f"statement:{text}"),
        },
        "current_state": state(),
        "current_state_basis": {},
        "requested_transition": {"target_state": state(), "basis_evidence_ids": []},
        "evidence": [],
    }


def artifact_for(
    dataset_dir: Path,
    pair_id: str,
    family: str,
    item: Json,
    seed: bytes,
) -> tuple[str, str]:
    token = opaque(f"artifact:{pair_id}")
    if family == "NUMERICAL":
        offset = 2 + int.from_bytes(keyed_bytes(seed, f"numeric:{pair_id}")[:2], "big") % 7
        relative = f"artifacts/artifact-{token}.json"
        artifact = build_exact_grid_artifact(
            coefficients=[str(offset), "-1", "1"],
            grid=["0", "1/4", "1/2", "3/4", "1"],
            relation=">=",
            threshold="0",
            repetitions=3,
        )
        content = (
            json.dumps(artifact, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        ).encode()
    elif family == "FORMAL":
        relative = formal_artifact_path(pair_id)
        content = build_formal_artifact(
            pair_id,
            str(item["claim_context"]["claim_id"]),
            str(item["claim_context"]["statement_sha256"]),
        ).encode("utf-8")
    else:
        relative = f"artifacts/artifact-{token}.txt"
        content = (
            "ClaimPromoteBench v1 synthetic evidence fixture.\n"
            f"object={opaque(f'object:{pair_id}', 20)}\n"
            "This artifact is benchmark evidence, not an asserted research result.\n"
        ).encode()
    path = dataset_dir / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return relative, sha256_bytes(content)


def numerical_evidence(item: Json, pair_id: str, artifact_path: str, artifact_hash: str) -> Json:
    return evidence(
        pair_id,
        "computation",
        "COMPUTATION",
        item["claim_context"]["claim_id"],
        item["claim_context"]["statement_sha256"],
        artifact_path,
        artifact_hash,
        scope_extra={
            "domain": domain(),
            "protocol_id": "cpb-numeric-v1",
            "protocol_version": "1.0.0",
            "repetitions": 3,
            "preregistered": True,
            "precision_bits": 64,
        },
    )


def formal_evidence(
    item: Json,
    pair_id: str,
    artifact_path: str,
    artifact_hash: str,
    *,
    dependencies: list[str] | None = None,
) -> Json:
    return evidence(
        pair_id,
        "certificate",
        "FORMAL_CERTIFICATE",
        item["claim_context"]["claim_id"],
        item["claim_context"]["statement_sha256"],
        artifact_path,
        artifact_hash,
        scope_extra={"verifier": "lean", "toolchain_lock_sha256": TOOLCHAIN_SHA256},
        dependencies=dependencies,
    )


def review_evidence(item: Json, pair_id: str, artifact_path: str, artifact_hash: str) -> Json:
    return evidence(
        pair_id,
        "review",
        "REVIEW",
        item["claim_context"]["claim_id"],
        item["claim_context"]["statement_sha256"],
        artifact_path,
        artifact_hash,
        actor_id=f"reviewer-{opaque(f'reviewer:{pair_id}', 12)}",
        actor_role="INDEPENDENT_REVIEWER",
        environment_sha256=label_digest(f"review-environment:{pair_id}"),
        cold_start=True,
    )


def configure_valid(
    factor: str,
    family: str,
    item: Json,
    pair_id: str,
    artifact_path: str,
    artifact_hash: str,
) -> None:
    context = item["claim_context"]
    if family in {"NUMERICAL", "RUNTIME"} or factor == "age":
        context["required_domain"] = domain()
        computation = numerical_evidence(item, pair_id, artifact_path, artifact_hash)
        item["requested_transition"] = {
            "target_state": state(computation="COMPUTATIONAL"),
            "basis_evidence_ids": [computation["id"]],
        }
        item["evidence"] = [computation]
        return
    if family == "PROVENANCE":
        review = review_evidence(item, pair_id, artifact_path, artifact_hash)
        item["requested_transition"] = {
            "target_state": state(review="INDEPENDENTLY_VERIFIED"),
            "basis_evidence_ids": [review["id"]],
        }
        item["evidence"] = [review]
        return
    if family == "FORMAL":
        certificate = formal_evidence(item, pair_id, artifact_path, artifact_hash)
        item["requested_transition"] = {
            "target_state": state(formal="FORMALLY_CERTIFIED"),
            "basis_evidence_ids": [certificate["id"]],
        }
        item["evidence"] = [certificate]
        return
    if family == "DEPENDENCY":
        middle_id = f"ev-{opaque(f'{pair_id}:dependency')}"
        leaf_id = f"ev-{opaque(f'{pair_id}:leaf')}"
        root_dependencies = [middle_id]
        if factor == "direct_dependency":
            root_dependencies = [leaf_id]
        root = formal_evidence(
            item,
            pair_id,
            artifact_path,
            artifact_hash,
            dependencies=root_dependencies,
        )
        item["requested_transition"] = {
            "target_state": state(formal="FORMALLY_CERTIFIED"),
            "basis_evidence_ids": [root["id"]],
        }
        leaf = evidence(
            pair_id,
            "leaf",
            "DEPENDENCY",
            context["claim_id"],
            context["statement_sha256"],
            artifact_path,
            artifact_hash,
        )
        if factor == "direct_dependency":
            item["evidence"] = [root, leaf]
        else:
            middle = evidence(
                pair_id,
                "dependency",
                "DEPENDENCY",
                context["claim_id"],
                context["statement_sha256"],
                artifact_path,
                artifact_hash,
                dependencies=[leaf_id] if factor == "transitive_dependency" else [],
            )
            item["evidence"] = [root, middle]
            if factor == "transitive_dependency":
                item["evidence"].append(leaf)
        return
    if factor == "current_binding":
        item["current_state"] = state(computation="COMPUTATIONAL")
        basis = numerical_evidence(item, pair_id, artifact_path, artifact_hash)
        item["current_state_basis"] = {
            "computation_status": {
                "evidence_ids": [basis["id"]],
                "bound_artifact_sha256": artifact_hash,
            }
        }
        review = review_evidence(item, pair_id, artifact_path, artifact_hash)
        item["requested_transition"] = {
            "target_state": state(computation="COMPUTATIONAL", review="INDEPENDENTLY_VERIFIED"),
            "basis_evidence_ids": [review["id"]],
        }
        item["evidence"] = [basis, review]
        return
    if factor == "contradiction":
        root = formal_evidence(item, pair_id, artifact_path, artifact_hash)
        contradiction = evidence(
            pair_id,
            "contradiction",
            "CONTRADICTION",
            context["claim_id"],
            context["statement_sha256"],
            artifact_path,
            artifact_hash,
            scope_extra={"contradiction_status": "RESOLVED"},
            actor_id=f"reviewer-{opaque(f'contradiction-reviewer:{pair_id}', 12)}",
            actor_role="INDEPENDENT_REVIEWER",
            environment_sha256=label_digest(f"contradiction-environment:{pair_id}"),
            cold_start=True,
        )
        item["requested_transition"] = {
            "target_state": state(formal="FORMALLY_CERTIFIED"),
            "basis_evidence_ids": [root["id"]],
        }
        item["evidence"] = [root, contradiction]
        return
    raise AssertionError(f"unhandled valid fixture: {factor}")


def invalidate(factor: str, item: Json) -> None:
    root = item["evidence"][0]
    if factor in {"direct_dependency", "transitive_dependency"}:
        item["evidence"].pop()
    elif factor == "dependency_verifier":
        item["evidence"][1]["verifier_result"] = "FAIL"
    elif factor == "dependency_statement":
        item["evidence"][1]["scope"]["statement_sha256"] = label_digest("wrong-statement")
    elif factor == "repetitions":
        root["scope"]["repetitions"] = 1
    elif factor == "domain":
        root["scope"]["domain"] = domain("0.9")
    elif factor == "preregistration":
        root["scope"]["preregistered"] = False
    elif factor == "precision":
        root["scope"]["precision_bits"] = 32
    elif factor == "tool_exit":
        root["tool_exit"] = 1
    elif factor == "verifier_execution":
        root["verifier_result"] = "NOT_RUN"
    elif factor == "run_completion":
        root["tool_exit"] = None
        root["verifier_result"] = "UNKNOWN"
    elif factor == "age":
        root["timestamp"] = "2026-07-13T00:00:00Z"
    elif factor == "current_binding":
        item["current_state_basis"]["computation_status"]["bound_artifact_sha256"] = label_digest(
            "stale-binding"
        )
    elif factor == "contradiction":
        item["evidence"][1]["scope"]["contradiction_status"] = "OPEN"
    elif factor == "reviewer_identity":
        root["provenance"]["actor_id"] = item["claim_context"]["author_id"]
    elif factor == "review_environment":
        root["provenance"]["environment_sha256"] = item["claim_context"][
            "author_environment_sha256"
        ]
    elif factor == "cold_start":
        root["provenance"]["cold_start"] = False
    elif factor == "statement_identity":
        root["scope"]["statement_sha256"] = label_digest("wrong-formal-statement")
    elif factor == "claim_identity":
        root["scope"]["claim_id"] = "wrong-claim-id"
    elif factor == "trust_base":
        root["scope"]["toolchain_lock_sha256"] = label_digest("untrusted-toolchain")
    else:
        raise AssertionError(f"unhandled invalid fixture: {factor}")


def selected_variants(plan: Json, split: str) -> list[tuple[int, Json, int]]:
    selected: list[tuple[int, Json, int]] = []
    for factor_index, row in enumerate(plan["factors"]):
        dev = {int(value) for value in row["dev_variants"]}
        for variant in range(int(row["pairs"])):
            in_split = variant in dev if split == "dev" else variant not in dev
            if in_split:
                selected.append((factor_index, row, variant))
    return selected


def pair_specs(
    plan: Json, split: str, seed: bytes, *, confirmatory_rekey: bool = False
) -> list[Json]:
    counters: defaultdict[str, int] = defaultdict(int)
    profiles = [str(value) for value in plan["surface_profiles"]]
    specs: list[Json] = []
    for factor_index, row, variant in selected_variants(plan, split):
        family = str(row["family"])
        counters[family] += 1
        number = counters[family]
        code = FAMILY_CODES[family]
        pair_id = f"v1-{split}-{code}-{number:03d}"
        invalid_side = "a" if (factor_index + variant) % 2 == 0 else "b"
        surface = pick(seed, f"surface:{row['factor_id']}:{variant}", profiles)
        specs.append(
            {
                "pair_id": pair_id,
                "family": family,
                "factor": str(row["factor_id"]),
                "variant": variant,
                "invalid": invalid_side,
                "action": str(row["invalid_action"]),
                "pointers": POINTERS[str(row["factor_id"])],
                "surface": surface,
            }
        )
    if confirmatory_rekey:
        if split != "test":
            raise ValueError("confirmatory rekey is restricted to the private test split")
        ordered = sorted(
            specs,
            key=lambda row: keyed_bytes(seed, f"confirmatory-pair-order:{row['pair_id']}"),
        )
        for number, row in enumerate(ordered, start=1):
            row["pair_id"] = f"v1-test-cfo-{number:03d}"
            row["template_id"] = (
                f"formal-logic-template-{(number - 1) % 24 + 1:02d}"
                if row["family"] == "FORMAL"
                else f"surface-profile-{row['surface']}"
            )
        specs = ordered
    return specs


def build(
    split: str,
    out_dir: Path,
    seed_file: Path | None,
    *,
    confirmatory_rekey: bool = False,
) -> Json:
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    seed = load_seed(split, seed_file)
    specs = pair_specs(plan, split, seed, confirmatory_rekey=confirmatory_rekey)
    expected_pairs = int(plan["splits"][split]["pairs"])
    if len(specs) != expected_pairs:
        raise ValueError(f"constructed {len(specs)} {split} specs, expected {expected_pairs}")

    if out_dir.exists():
        shutil.rmtree(out_dir)
    artifacts_dir = out_dir / "artifacts"
    artifacts_dir.mkdir(parents=True)
    formal_pair_ids = [spec["pair_id"] for spec in specs if spec["family"] == "FORMAL"]
    formal_package_files = write_formal_package(out_dir, formal_pair_ids)

    author_items: list[Json] = []
    pairs: list[Json] = []
    family_counts: Counter[str] = Counter()
    invalid_sides: Counter[str] = Counter()
    invalid_actions: Counter[str] = Counter()

    for spec in specs:
        pair_id = spec["pair_id"]
        valid = base_item(pair_id, spec["family"], spec["surface"])
        artifact_path, artifact_hash = artifact_for(
            out_dir,
            pair_id,
            spec["family"],
            valid,
            seed,
        )
        configure_valid(
            spec["factor"],
            spec["family"],
            valid,
            pair_id,
            artifact_path,
            artifact_hash,
        )
        invalid = deepcopy(valid)
        invalidate(spec["factor"], invalid)

        side_items = {"a": deepcopy(valid), "b": deepcopy(valid)}
        side_items[spec["invalid"]] = invalid
        pair_rows: dict[str, Json] = {}
        for side in ("a", "b"):
            item = side_items[side]
            item["id"] = f"{pair_id}-{side}"
            item["gold"] = evaluate(item, policy, policy["evaluation_time"])
            author_items.append(item)
            pair_rows[side] = item

        invalid_id = f"{pair_id}-{spec['invalid']}"
        valid_side = "b" if spec["invalid"] == "a" else "a"
        valid_id = f"{pair_id}-{valid_side}"
        if pair_rows[spec["invalid"]]["gold"]["action"] != spec["action"]:
            raise AssertionError(f"unexpected invalid action for {pair_id}")
        if pair_rows[valid_side]["gold"]["action"] != "ALLOW":
            raise AssertionError(f"valid member did not ALLOW for {pair_id}")
        pair_record: Json = {
            "pair_id": pair_id,
            "family": spec["family"],
            "member_ids": [f"{pair_id}-a", f"{pair_id}-b"],
            "invalid_id": invalid_id,
            "valid_id": valid_id,
            "factor_id": spec["factor"],
            "controlled_json_pointers": spec["pointers"],
        }
        if "template_id" in spec:
            pair_record["template_id"] = spec["template_id"]
        pairs.append(pair_record)
        family_counts[spec["family"]] += 1
        invalid_sides[spec["invalid"].upper()] += 1
        invalid_actions[spec["action"]] += 1

    inputs: list[Json] = []
    gold: list[Json] = []
    for item in author_items:
        public = deepcopy(item)
        decision = public.pop("gold")
        inputs.append(public)
        gold.append(
            {
                "id": item["id"],
                "pair_id": item["pair_id"],
                "family": item["family"],
                "decision": decision,
            }
        )

    write_jsonl(out_dir / "author-items.jsonl", author_items)
    write_jsonl(out_dir / "inputs.jsonl", inputs)
    write_jsonl(out_dir / "gold.jsonl", gold)
    write_json(out_dir / "pairs.json", pairs)

    generated = [
        "author-items.jsonl",
        "inputs.jsonl",
        "gold.jsonl",
        "pairs.json",
        *formal_package_files,
    ]
    generated.extend(
        sorted(
            str(path.relative_to(out_dir)).replace("\\", "/")
            for path in artifacts_dir.rglob("*")
            if path.is_file()
        )
    )
    generated = sorted(set(generated))
    split_plan = plan["splits"][split]
    if family_counts != Counter(
        {
            str(row["family"]): sum(
                1
                for _factor_index, selected_row, _variant in selected_variants(plan, split)
                if selected_row["family"] == row["family"]
            )
            for row in plan["factors"]
        }
    ):
        raise AssertionError("internal family count mismatch")
    if invalid_sides != Counter(split_plan["invalid_side_counts"]):
        raise AssertionError(f"invalid-side count mismatch: {dict(invalid_sides)}")
    expected_actions = Counter(
        plan["dev_invalid_action_counts"] if split == "dev" else plan["test_invalid_action_counts"]
    )
    if invalid_actions != expected_actions:
        raise AssertionError(f"invalid-action count mismatch: {dict(invalid_actions)}")

    manifest = {
        "schema_version": "1.0.0",
        "dataset_id": (
            "claimpromotebench-v1-confirmatory-test"
            if confirmatory_rekey
            else f"claimpromotebench-v1-{split}"
        ),
        "release_status": (
            "PRIVATE_CONFIRMATORY_TEST_UNCOMMITTED"
            if confirmatory_rekey
            else ("PUBLIC_DEV" if split == "dev" else "PRIVATE_TEST_UNCOMMITTED")
        ),
        "evaluation_time": policy["evaluation_time"],
        "policy_id": policy["policy_id"],
        "policy_version": policy["policy_version"],
        "policy_file": POLICY_PATH.name,
        "policy_sha256": sha256_file(POLICY_PATH),
        "input_schema": "benchmark-input-v1.schema.json",
        "gold_schema": "gold-label.schema.json",
        "schema_sha256": {
            "benchmark-input-v1.schema.json": sha256_file(INPUT_SCHEMA),
            "gold-label.schema.json": sha256_file(GOLD_SCHEMA),
        },
        "instances": len(inputs),
        "pairs": len(pairs),
        "family_pair_counts": dict(sorted(family_counts.items())),
        "invalid_side_counts": dict(sorted(invalid_sides.items())),
        "invalid_action_counts": dict(sorted(invalid_actions.items())),
        "benchmark_plan_sha256": sha256_file(PLAN_PATH),
        "construction_seed_sha256": sha256_bytes(seed),
        "test_manifest_commitment": "NOT_APPLICABLE" if split == "dev" else "PENDING",
        "model_experiments": "PENDING",
        "files": {relative: sha256_file(out_dir / relative) for relative in generated},
    }
    if confirmatory_rekey:
        manifest["confirmatory_rekey_enabled"] = True
        manifest["identifier_namespace"] = "PRIVATE_SEED_KEYED_OPAQUE_CFM_R5"
    write_json(out_dir / "manifest.json", manifest)
    summary = validate_dataset(out_dir, ROOT)
    return {
        "status": "PASS",
        "split": split,
        "pairs": len(pairs),
        "instances": len(inputs),
        "family_pair_counts": dict(sorted(family_counts.items())),
        "invalid_side_counts": dict(sorted(invalid_sides.items())),
        "invalid_action_counts": dict(sorted(invalid_actions.items())),
        "manifest_sha256": sha256_file(out_dir / "manifest.json"),
        "validator": summary,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=("dev", "test"), required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seed-file", type=Path)
    parser.add_argument("--confirmatory-rekey", action="store_true")
    args = parser.parse_args()
    report = build(
        args.split,
        args.out.resolve(),
        args.seed_file.resolve() if args.seed_file is not None else None,
        confirmatory_rekey=args.confirmatory_rekey,
    )
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
