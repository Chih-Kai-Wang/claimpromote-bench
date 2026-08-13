"""Leakage-resistant renderers for the four intervention arms."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from .hashing import canonical_json, resolve_artifact, sha256_bytes, sha256_file

ARMS = ("narrative", "ledger", "ledger_verifier", "ledger_verifier_gate")
PROMPT_EXCLUDED_FIELDS = {"id", "pair_id", "split", "family", "gold"}


def prompt_payload(item: dict[str, Any]) -> dict[str, Any]:
    """Remove benchmark-only metadata before any model-facing rendering."""

    return {
        key: deepcopy(value) for key, value in item.items() if key not in PROMPT_EXCLUDED_FIELDS
    }


def _state_sentence(label: str, state: dict[str, Any]) -> str:
    return (
        f"{label}: research is {state['research_status']}; computation is "
        f"{state['computation_status']}; formal certification is {state['formal_status']}; "
        f"independent review is {state['review_status']}."
    )


def _narrative(item: dict[str, Any]) -> str:
    context = item["claim_context"]
    transition = item["requested_transition"]
    lines = [
        f"Claim: {item['claim_text']}",
        f"The claim identifier is {context['claim_id']}; its exact formal-statement digest is "
        f"{context['statement_sha256']}. The author is {context['author_id']} in environment "
        f"{context['author_environment_sha256']}.",
        _state_sentence("Current state", item["current_state"]),
        _state_sentence("Requested target state", transition["target_state"]),
        "The requested transition cites this basis: "
        + (", ".join(transition["basis_evidence_ids"]) or "none"),
    ]
    if "required_domain" in context:
        lines.append(
            "The claim's required numerical domain is "
            f"{canonical_json(context['required_domain'])}."
        )
    if item["current_state_basis"]:
        lines.append(
            "Current elevated axes have these bound bases: "
            f"{canonical_json(item['current_state_basis'])}."
        )
    for index, evidence in enumerate(item["evidence"], start=1):
        provenance = evidence["provenance"]
        scope = evidence["scope"]
        lines.append(
            f"Evidence {index}, ID {evidence['id']}, is type {evidence['type']}. It was produced "
            f"by actor {provenance['actor_id']} with role {provenance['actor_role']} in run "
            f"{provenance['run_id']} and environment {provenance['environment_sha256']}; cold "
            f"start is {str(provenance['cold_start']).lower()}. Its artifact is "
            f"{evidence['artifact_path']} with digest {evidence['artifact_hash']}. Its complete "
            f"scope is {canonical_json(scope)}. Dependencies are "
            f"{canonical_json(evidence['dependencies'])}; tool exit is "
            f"{canonical_json(evidence['tool_exit'])}; verifier result is "
            f"{evidence['verifier_result']}; timestamp is {evidence['timestamp']}."
        )
    return "\n".join(lines)


def _policy_contract(policy: dict[str, Any], evaluation_time: str) -> str:
    public_policy = deepcopy(policy)
    public_policy["evaluation_time"] = evaluation_time
    serialized = canonical_json(public_policy)
    return (
        "Versioned policy contract (this complete contract is authoritative; apply its "
        "root-type rules, transitive dependency closure, contradiction authority, review "
        "independence, alpha research-status scope, reason ordering, and action precedence "
        "exactly).\n"
        f"Contract SHA-256: {sha256_bytes(serialized.encode('utf-8'))}\n"
        f"{serialized}"
    )


def _verifier_readout(item: dict[str, Any], dataset_dir: Path | None) -> list[str]:
    evidence_ids = {str(evidence["id"]) for evidence in item["evidence"]}
    lines = ["Passive verifier readout (raw checks only; this is not a transition decision):"]
    for evidence in sorted(item["evidence"], key=lambda value: str(value["id"])):
        dependencies = [str(value) for value in evidence.get("dependencies", [])]
        missing = sorted(set(dependencies) - evidence_ids)
        artifact_match: str | bool = "NOT_CHECKED"
        if dataset_dir is not None:
            try:
                path = resolve_artifact(dataset_dir, str(evidence["artifact_path"]))
                artifact_match = sha256_file(path) == evidence["artifact_hash"]
            except Exception:
                artifact_match = False
        lines.append(
            canonical_json(
                {
                    "artifact_hash_matches": artifact_match,
                    "evidence_id": evidence["id"],
                    "missing_direct_dependencies": missing,
                    "tool_exit": evidence.get("tool_exit"),
                    "verifier_result": evidence.get("verifier_result"),
                }
            )
        )
    return lines


def render_prompt(
    item: dict[str, Any],
    arm: str,
    dataset_dir: Path | None = None,
    *,
    policy: dict[str, Any] | None = None,
    evaluation_time: str | None = None,
) -> str:
    """Render one item without family, pair, gold, or oracle-action leakage."""

    if arm not in ARMS:
        raise ValueError(f"unknown arm: {arm}")
    if policy is None or evaluation_time is None:
        raise ValueError("all model-facing prompts require the complete policy and evaluation_time")
    payload = prompt_payload(item)
    header = (
        "Decide whether the requested mathematical research claim-state transition is "
        "admissible under the stated versioned policy. Treat computation, formal "
        "certification, independent review, and mathematical resolution as separate axes."
    )
    if arm == "narrative":
        body = "Evidence record expressed as semantic prose:\n" + _narrative(payload)
    else:
        body = f"Typed evidence ledger (canonical JSON):\n{canonical_json(payload)}"
    additions: list[str] = []
    if arm in {"ledger_verifier", "ledger_verifier_gate"}:
        additions.extend(_verifier_readout(item, dataset_dir))
    if arm == "ledger_verifier_gate":
        additions.append(
            "After this raw decision, a deterministic gate will be allowed to veto an "
            "invalid ALLOW. The gate will never promote a claim for you."
        )
    contract = (
        "Return one JSON object with exactly these fields: action (ALLOW, HOLD, DEMOTE, or "
        "ESCALATE), proposed_state, p_admissible in [0,1], used_evidence_ids, reason_codes, "
        "and missing_evidence_ids. Do not add prose."
    )
    return (
        "\n\n".join([header, _policy_contract(policy, evaluation_time), body, *additions, contract])
        + "\n"
    )
