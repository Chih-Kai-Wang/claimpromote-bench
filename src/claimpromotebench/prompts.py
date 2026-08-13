"""Leakage-resistant renderers for the four intervention arms."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from .hashing import canonical_json, resolve_artifact, sha256_file

ARMS = ("narrative", "ledger", "ledger_verifier", "ledger_verifier_gate")
PROMPT_EXCLUDED_FIELDS = {"id", "pair_id", "split", "family", "gold"}


def prompt_payload(item: dict[str, Any]) -> dict[str, Any]:
    """Remove benchmark-only metadata before any model-facing rendering."""

    return {
        key: deepcopy(value) for key, value in item.items() if key not in PROMPT_EXCLUDED_FIELDS
    }


def _flatten(value: Any, pointer: str = "") -> list[str]:
    lines: list[str] = []
    if isinstance(value, dict):
        for key in sorted(value):
            lines.extend(_flatten(value[key], f"{pointer}/{key}"))
    elif isinstance(value, list):
        if not value:
            lines.append(f"{pointer} has the empty list as its value.")
        else:
            for index, child in enumerate(value):
                lines.extend(_flatten(child, f"{pointer}/{index}"))
    else:
        lines.append(f"{pointer} has value {json.dumps(value, ensure_ascii=False)}.")
    return lines


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


def render_prompt(item: dict[str, Any], arm: str, dataset_dir: Path | None = None) -> str:
    """Render one item without family, pair, gold, or oracle-action leakage."""

    if arm not in ARMS:
        raise ValueError(f"unknown arm: {arm}")
    payload = prompt_payload(item)
    header = (
        "Decide whether the requested mathematical research claim-state transition is "
        "admissible under the stated versioned policy. Treat computation, formal "
        "certification, independent review, and mathematical resolution as separate axes."
    )
    if arm == "narrative":
        body = "Evidence record expressed as complete field statements:\n" + "\n".join(
            _flatten(payload)
        )
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
    return "\n\n".join([header, body, *additions, contract]) + "\n"
