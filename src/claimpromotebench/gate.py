"""One-way deterministic veto gate."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def apply_gate(raw_decision: dict[str, Any], oracle_result: dict[str, Any]) -> dict[str, Any]:
    """Veto an invalid ALLOW without ever promoting on an agent's behalf."""

    final = deepcopy(raw_decision)
    caught = raw_decision["action"] == "ALLOW" and oracle_result["action"] != "ALLOW"
    if caught:
        final = {
            "action": oracle_result["action"],
            "proposed_state": deepcopy(oracle_result["proposed_state"]),
            "p_admissible": raw_decision["p_admissible"],
            "used_evidence_ids": list(raw_decision["used_evidence_ids"]),
            "reason_codes": _merge_codes(
                raw_decision["reason_codes"], ["GATE_VETO", *oracle_result["reason_codes"]]
            ),
            "missing_evidence_ids": list(oracle_result["missing_evidence_ids"]),
        }
    return {"caught": caught, "raw_decision": deepcopy(raw_decision), "final_decision": final}


def _merge_codes(left: list[str], right: list[str]) -> list[str]:
    return list(dict.fromkeys([*left, *right]))
