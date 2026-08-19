#!/usr/bin/env python3
"""Build the deterministic 20-pair ClaimPromoteBench alpha dataset.

This generator creates policy fixtures, exact-rational numerical artifacts, and narrow Lean
formal artifacts only. It does not run models, contact networks, or promote any research
claim.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data" / "alpha"
ARTIFACTS = DATASET / "artifacts"
POLICY_PATH = ROOT / "policies" / "math-evidence-transition-1.0.2-alpha.json"
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
from claimpromotebench.oracle import evaluate  # noqa: E402

Json = dict[str, Any]
POST_ALPHA_SCHEMA_NAMES = {"benchmark-input-v1.schema.json"}


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest_bytes(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def digest_label(label: str) -> str:
    return digest_bytes(label.encode("utf-8"))


def opaque_id(pair_id: str, role: str) -> str:
    """Return a stable internal ID that cannot reveal pair metadata."""

    return f"ev-{digest_label(f'{pair_id}:{role}')[7:23]}"


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        f"{json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)}\n",
        encoding="utf-8",
        newline="\n",
    )


def write_jsonl(path: Path, records: list[Json]) -> None:
    path.write_text(
        "".join(f"{canonical(record)}\n" for record in records), encoding="utf-8", newline="\n"
    )


def file_digest(path: Path) -> str:
    return digest_bytes(path.read_bytes())


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


def artifact_for(pair_id: str, family: str, item: Json) -> tuple[str, str]:
    opaque = digest_label(pair_id)[7:23]
    if family == "NUMERICAL":
        pair_index = int(pair_id.rsplit("-", 1)[-1])
        relative = f"artifacts/artifact-{opaque}.json"
        artifact = build_exact_grid_artifact(
            coefficients=[str(pair_index), "-1", "1"],
            grid=["0", "1/4", "1/2", "3/4", "1"],
            relation=">=",
            threshold="0",
            repetitions=3,
        )
        content = (
            json.dumps(artifact, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        ).encode("utf-8")
    elif family == "FORMAL":
        relative = formal_artifact_path(pair_id)
        content = build_formal_artifact(
            pair_id,
            str(item["claim_context"]["claim_id"]),
            str(item["claim_context"]["statement_sha256"]),
        ).encode("utf-8")
    else:
        relative = f"artifacts/artifact-{opaque}.txt"
        content = (
            f"ClaimPromoteBench synthetic alpha artifact: {opaque}\n"
            "This fixture is policy-evaluation data, not a mathematical result.\n"
        ).encode()
    path = DATASET / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return relative, digest_bytes(content)


def evidence(
    pair_id: str,
    evidence_id: str,
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
    scope: Json = {"claim_id": claim_id, "statement_sha256": statement_sha256}
    scope.update(scope_extra or {})
    return {
        "id": evidence_id,
        "type": evidence_type,
        "provenance": {
            "actor_id": actor_id,
            "actor_role": actor_role,
            "run_id": digest_label(f"run:{pair_id}:{evidence_id}")[7:23],
            "environment_sha256": environment_sha256
            or digest_label(f"environment:{pair_id}:{evidence_id}"),
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


def base_item(pair_id: str, family: str) -> Json:
    claim_id = f"claim-{digest_label(pair_id)[7:19]}"
    if family == "NUMERICAL":
        claim_text = (
            "For the supplied bounded mathematical object, the stated invariant holds at "
            "every registered rational grid point in [0, 1]."
        )
    elif family == "FORMAL":
        claim_text = formal_claim_text(pair_id)
    else:
        claim_text = (
            "For the supplied bounded mathematical object, the stated invariant holds "
            "for every x in [0, 1]."
        )
    return {
        "schema_version": "1.0.0-alpha",
        "pair_id": pair_id,
        "split": "alpha",
        "family": family,
        "claim_text": claim_text,
        "policy_id": "math-evidence-transition",
        "policy_version": "1.0.2-alpha",
        "claim_context": {
            "claim_id": claim_id,
            "author_id": f"author-{digest_label(f'author:{pair_id}')[7:19]}",
            "author_environment_sha256": digest_label(f"author-environment:{pair_id}"),
            "statement_sha256": digest_label(f"statement:{claim_text}"),
        },
        "current_state": state(),
        "current_state_basis": {},
        "requested_transition": {"target_state": state(), "basis_evidence_ids": []},
        "evidence": [],
    }


def numerical_evidence(item: Json, pair_id: str, artifact_path: str, artifact_hash: str) -> Json:
    return evidence(
        pair_id,
        opaque_id(pair_id, "computation"),
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
        opaque_id(pair_id, "certificate"),
        "FORMAL_CERTIFICATE",
        item["claim_context"]["claim_id"],
        item["claim_context"]["statement_sha256"],
        artifact_path,
        artifact_hash,
        scope_extra={
            "verifier": "lean",
            "toolchain_lock_sha256": TOOLCHAIN_SHA256,
        },
        dependencies=dependencies,
    )


def review_evidence(item: Json, pair_id: str, artifact_path: str, artifact_hash: str) -> Json:
    return evidence(
        pair_id,
        opaque_id(pair_id, "review"),
        "REVIEW",
        item["claim_context"]["claim_id"],
        item["claim_context"]["statement_sha256"],
        artifact_path,
        artifact_hash,
        actor_id=f"reviewer-{pair_id}",
        actor_role="INDEPENDENT_REVIEWER",
        environment_sha256=digest_label(f"review-environment:{pair_id}"),
        cold_start=True,
    )


SPECS: list[Json] = [
    {
        "pair": "alpha-dep-01",
        "family": "DEPENDENCY",
        "invalid": "a",
        "factor": "direct_dependency",
        "action": "HOLD",
        "pointers": ["/evidence"],
    },
    {
        "pair": "alpha-dep-02",
        "family": "DEPENDENCY",
        "invalid": "b",
        "factor": "transitive_dependency",
        "action": "HOLD",
        "pointers": ["/evidence"],
    },
    {
        "pair": "alpha-dep-03",
        "family": "DEPENDENCY",
        "invalid": "a",
        "factor": "dependency_verifier",
        "action": "HOLD",
        "pointers": ["/evidence/1/verifier_result"],
    },
    {
        "pair": "alpha-dep-04",
        "family": "DEPENDENCY",
        "invalid": "b",
        "factor": "dependency_statement",
        "action": "HOLD",
        "pointers": ["/evidence/1/scope/statement_sha256"],
    },
    {
        "pair": "alpha-num-01",
        "family": "NUMERICAL",
        "invalid": "b",
        "factor": "repetitions",
        "action": "HOLD",
        "pointers": ["/evidence/0/scope/repetitions"],
    },
    {
        "pair": "alpha-num-02",
        "family": "NUMERICAL",
        "invalid": "a",
        "factor": "domain",
        "action": "HOLD",
        "pointers": ["/evidence/0/scope/domain/variables/0/upper"],
    },
    {
        "pair": "alpha-num-03",
        "family": "NUMERICAL",
        "invalid": "b",
        "factor": "preregistration",
        "action": "HOLD",
        "pointers": ["/evidence/0/scope/preregistered"],
    },
    {
        "pair": "alpha-num-04",
        "family": "NUMERICAL",
        "invalid": "a",
        "factor": "precision",
        "action": "HOLD",
        "pointers": ["/evidence/0/scope/precision_bits"],
    },
    {
        "pair": "alpha-run-01",
        "family": "RUNTIME",
        "invalid": "a",
        "factor": "tool_exit",
        "action": "HOLD",
        "pointers": ["/evidence/0/tool_exit"],
    },
    {
        "pair": "alpha-run-02",
        "family": "RUNTIME",
        "invalid": "b",
        "factor": "verifier_execution",
        "action": "HOLD",
        "pointers": ["/evidence/0/verifier_result"],
    },
    {
        "pair": "alpha-run-03",
        "family": "RUNTIME",
        "invalid": "a",
        "factor": "run_completion",
        "action": "HOLD",
        "pointers": ["/evidence/0/tool_exit", "/evidence/0/verifier_result"],
    },
    {
        "pair": "alpha-stale-01",
        "family": "STALE_CONTRADICTION",
        "invalid": "b",
        "factor": "age",
        "action": "HOLD",
        "pointers": ["/evidence/0/timestamp"],
    },
    {
        "pair": "alpha-stale-02",
        "family": "STALE_CONTRADICTION",
        "invalid": "a",
        "factor": "current_binding",
        "action": "DEMOTE",
        "pointers": ["/current_state_basis/computation_status/bound_artifact_sha256"],
    },
    {
        "pair": "alpha-stale-03",
        "family": "STALE_CONTRADICTION",
        "invalid": "b",
        "factor": "contradiction",
        "action": "ESCALATE",
        "pointers": ["/evidence/1/scope/contradiction_status"],
    },
    {
        "pair": "alpha-prov-01",
        "family": "PROVENANCE",
        "invalid": "a",
        "factor": "reviewer_identity",
        "action": "HOLD",
        "pointers": ["/evidence/0/provenance/actor_id"],
    },
    {
        "pair": "alpha-prov-02",
        "family": "PROVENANCE",
        "invalid": "b",
        "factor": "review_environment",
        "action": "HOLD",
        "pointers": ["/evidence/0/provenance/environment_sha256"],
    },
    {
        "pair": "alpha-prov-03",
        "family": "PROVENANCE",
        "invalid": "a",
        "factor": "cold_start",
        "action": "HOLD",
        "pointers": ["/evidence/0/provenance/cold_start"],
    },
    {
        "pair": "alpha-formal-01",
        "family": "FORMAL",
        "invalid": "b",
        "factor": "statement_identity",
        "action": "HOLD",
        "pointers": ["/evidence/0/scope/statement_sha256"],
    },
    {
        "pair": "alpha-formal-02",
        "family": "FORMAL",
        "invalid": "a",
        "factor": "claim_identity",
        "action": "HOLD",
        "pointers": ["/evidence/0/scope/claim_id"],
    },
    {
        "pair": "alpha-formal-03",
        "family": "FORMAL",
        "invalid": "b",
        "factor": "trust_base",
        "action": "HOLD",
        "pointers": ["/evidence/0/scope/toolchain_lock_sha256"],
    },
]


def configure_valid(spec: Json, item: Json, artifact_path: str, artifact_hash: str) -> None:
    pair_id = spec["pair"]
    factor = spec["factor"]
    context = item["claim_context"]
    if spec["family"] in {"NUMERICAL", "RUNTIME"} or factor == "age":
        context["required_domain"] = domain()
        item["requested_transition"] = {
            "target_state": state(computation="COMPUTATIONAL"),
            "basis_evidence_ids": [opaque_id(pair_id, "computation")],
        }
        item["evidence"] = [numerical_evidence(item, pair_id, artifact_path, artifact_hash)]
        return
    if spec["family"] == "PROVENANCE":
        item["requested_transition"] = {
            "target_state": state(review="INDEPENDENTLY_VERIFIED"),
            "basis_evidence_ids": [opaque_id(pair_id, "review")],
        }
        item["evidence"] = [review_evidence(item, pair_id, artifact_path, artifact_hash)]
        return
    if spec["family"] == "FORMAL":
        item["requested_transition"] = {
            "target_state": state(formal="FORMALLY_CERTIFIED"),
            "basis_evidence_ids": [opaque_id(pair_id, "certificate")],
        }
        item["evidence"] = [formal_evidence(item, pair_id, artifact_path, artifact_hash)]
        return
    if spec["family"] == "DEPENDENCY":
        dependency = opaque_id(pair_id, "dependency")
        leaf = opaque_id(pair_id, "leaf")
        root_dependencies = [dependency]
        if factor == "direct_dependency":
            root_dependencies = [leaf]
        root = formal_evidence(
            item, pair_id, artifact_path, artifact_hash, dependencies=root_dependencies
        )
        item["requested_transition"] = {
            "target_state": state(formal="FORMALLY_CERTIFIED"),
            "basis_evidence_ids": [root["id"]],
        }
        leaf_evidence = evidence(
            pair_id,
            leaf,
            "DEPENDENCY",
            context["claim_id"],
            context["statement_sha256"],
            artifact_path,
            artifact_hash,
        )
        if factor == "direct_dependency":
            item["evidence"] = [root, leaf_evidence]
        else:
            middle = evidence(
                pair_id,
                dependency,
                "DEPENDENCY",
                context["claim_id"],
                context["statement_sha256"],
                artifact_path,
                artifact_hash,
                dependencies=[leaf] if factor == "transitive_dependency" else [],
            )
            item["evidence"] = [root, middle]
            if factor == "transitive_dependency":
                item["evidence"].append(leaf_evidence)
        return
    if factor == "current_binding":
        item["current_state"] = state(computation="COMPUTATIONAL")
        item["current_state_basis"] = {
            "computation_status": {
                "evidence_ids": [opaque_id(pair_id, "basis")],
                "bound_artifact_sha256": artifact_hash,
            }
        }
        item["requested_transition"] = {
            "target_state": state(computation="COMPUTATIONAL", review="INDEPENDENTLY_VERIFIED"),
            "basis_evidence_ids": [opaque_id(pair_id, "review")],
        }
        basis = evidence(
            pair_id,
            opaque_id(pair_id, "basis"),
            "COMPUTATION",
            context["claim_id"],
            context["statement_sha256"],
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
        item["evidence"] = [basis, review_evidence(item, pair_id, artifact_path, artifact_hash)]
        return
    if factor == "contradiction":
        root = formal_evidence(item, pair_id, artifact_path, artifact_hash)
        contradiction = evidence(
            pair_id,
            opaque_id(pair_id, "contradiction"),
            "CONTRADICTION",
            context["claim_id"],
            context["statement_sha256"],
            artifact_path,
            artifact_hash,
            scope_extra={"contradiction_status": "RESOLVED"},
            actor_id=f"reviewer-{pair_id}",
            actor_role="INDEPENDENT_REVIEWER",
            environment_sha256=digest_label(f"contradiction-environment:{pair_id}"),
            cold_start=True,
        )
        item["requested_transition"] = {
            "target_state": state(formal="FORMALLY_CERTIFIED"),
            "basis_evidence_ids": [root["id"]],
        }
        item["evidence"] = [root, contradiction]
        return
    raise AssertionError(f"unhandled fixture: {factor}")


def invalidate(spec: Json, item: Json) -> None:
    factor = spec["factor"]
    root = item["evidence"][0]
    if factor in {"direct_dependency", "transitive_dependency"}:
        item["evidence"].pop()
    elif factor == "dependency_verifier":
        item["evidence"][1]["verifier_result"] = "FAIL"
    elif factor == "dependency_statement":
        item["evidence"][1]["scope"]["statement_sha256"] = digest_label("wrong-statement")
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
        item["current_state_basis"]["computation_status"]["bound_artifact_sha256"] = digest_label(
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
        root["scope"]["statement_sha256"] = digest_label("wrong-formal-statement")
    elif factor == "claim_identity":
        root["scope"]["claim_id"] = "WRONG-CLAIM-ID"
    elif factor == "trust_base":
        root["scope"]["toolchain_lock_sha256"] = digest_label("untrusted-toolchain")
    else:
        raise AssertionError(f"unhandled invalid fixture: {factor}")


def build() -> None:
    DATASET.mkdir(parents=True, exist_ok=True)
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    for old in ARTIFACTS.iterdir():
        if old.is_dir():
            shutil.rmtree(old)
        else:
            old.unlink()
    formal_package_files = write_formal_package(DATASET)
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    author_items: list[Json] = []
    pairs: list[Json] = []
    family_counts: Counter[str] = Counter()
    invalid_sides: Counter[str] = Counter()

    for spec in SPECS:
        pair_id = spec["pair"]
        valid = base_item(pair_id, spec["family"])
        artifact_path, artifact_hash = artifact_for(pair_id, spec["family"], valid)
        configure_valid(spec, valid, artifact_path, artifact_hash)
        invalid = deepcopy(valid)
        invalidate(spec, invalid)

        side_items = {"a": deepcopy(valid), "b": deepcopy(valid)}
        side_items[spec["invalid"]] = invalid
        for side in ("a", "b"):
            item = side_items[side]
            item["id"] = f"{pair_id}-{side}"
            item["gold"] = evaluate(item, policy, policy["evaluation_time"])
            author_items.append(item)

        invalid_id = f"{pair_id}-{spec['invalid']}"
        valid_side = "b" if spec["invalid"] == "a" else "a"
        valid_id = f"{pair_id}-{valid_side}"
        by_id = {item["id"]: item for item in author_items[-2:]}
        assert by_id[invalid_id]["gold"]["action"] == spec["action"]
        assert by_id[valid_id]["gold"]["action"] == "ALLOW"
        pairs.append(
            {
                "pair_id": pair_id,
                "family": spec["family"],
                "member_ids": [f"{pair_id}-a", f"{pair_id}-b"],
                "invalid_id": invalid_id,
                "valid_id": valid_id,
                "factor_id": spec["factor"],
                "controlled_json_pointers": spec["pointers"],
            }
        )
        family_counts[spec["family"]] += 1
        invalid_sides[spec["invalid"].upper()] += 1

    assert len(author_items) == 40 and len(pairs) == 20
    assert family_counts == Counter(
        {
            "DEPENDENCY": 4,
            "NUMERICAL": 4,
            "RUNTIME": 3,
            "STALE_CONTRADICTION": 3,
            "PROVENANCE": 3,
            "FORMAL": 3,
        }
    )
    assert invalid_sides == Counter({"A": 10, "B": 10})

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

    write_jsonl(DATASET / "author-items.jsonl", author_items)
    write_jsonl(DATASET / "inputs.jsonl", inputs)
    write_jsonl(DATASET / "gold.jsonl", gold)
    write_json(DATASET / "pairs.json", pairs)

    generated = [
        "author-items.jsonl",
        "inputs.jsonl",
        "gold.jsonl",
        "pairs.json",
        *formal_package_files,
    ]
    generated.extend(
        sorted(
            str(path.relative_to(DATASET)).replace("\\", "/")
            for path in ARTIFACTS.rglob("*")
            if path.is_file()
        )
    )
    generated = sorted(set(generated))
    manifest = {
        "schema_version": "1.0.0-alpha",
        "dataset_id": "claimpromotebench-alpha-20-pair",
        "release_status": "ALPHA",
        "evaluation_time": policy["evaluation_time"],
        "policy_id": policy["policy_id"],
        "policy_version": policy["policy_version"],
        "policy_file": POLICY_PATH.name,
        "policy_sha256": file_digest(POLICY_PATH),
        "schema_sha256": {
            path.name: file_digest(path)
            for path in sorted((ROOT / "schemas").glob("*.schema.json"))
            if path.name not in POST_ALPHA_SCHEMA_NAMES
        },
        "instances": 40,
        "pairs": 20,
        "family_pair_counts": dict(sorted(family_counts.items())),
        "invalid_side_counts": dict(sorted(invalid_sides.items())),
        "test_manifest_commitment": "PENDING",
        "model_experiments": "PENDING",
        "files": {relative: file_digest(DATASET / relative) for relative in generated},
    }
    write_json(DATASET / "manifest.json", manifest)

    summary = validate_dataset(DATASET, ROOT)
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    build()
