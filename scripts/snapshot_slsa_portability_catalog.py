#!/usr/bin/env python3
"""Write a credential-authenticated, account-free OpenCode Go catalog snapshot."""

from __future__ import annotations

import argparse
import json
import os
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

Json = dict[str, Any]
SELECTED = ("qwen3.7-max", "deepseek-v4-flash")


def fail(message: str) -> None:
    raise SystemExit(f"slsa-catalog-snapshot: {message}")


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def snapshot(out: Path) -> Json:
    if out.exists():
        fail(f"refusing to overwrite catalog snapshot: {out}")
    api_key = os.environ.get("OPENCODE_GO_API_KEY")
    if not api_key or api_key != api_key.strip():
        fail("OPENCODE_GO_API_KEY is absent or malformed")
    request = urllib.request.Request(
        "https://opencode.ai/zen/go/v1/models",
        headers={
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "ClaimPromoteBench-SLSA-Freeze/1",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
        status = int(response.status)
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, list):
        fail("catalog response lacks a data list")
    model_ids = sorted(
        str(row["id"]) for row in data if isinstance(row, dict) and isinstance(row.get("id"), str)
    )
    if missing := sorted(set(SELECTED) - set(model_ids)):
        fail(f"selected repeated configurations are absent: {missing}")
    result: Json = {
        "schema_version": "1.0.0",
        "status": "CREDENTIAL_AUTHENTICATED_MODEL_CATALOG_SNAPSHOT",
        "recorded_at_utc": utc_now(),
        "endpoint": "https://opencode.ai/zen/go/v1/models",
        "http_status": status,
        "model_count": len(model_ids),
        "model_ids": model_ids,
        "selected_model_ids": list(SELECTED),
        "selection_rule": (
            "Repeat the two configurations with usable coverage on the prior policy challenge "
            "so policy changes can be described within configuration. Selection uses no "
            "new-study outputs."
        ),
        "account_identifiers_retained": False,
        "provider_response_identifiers_retained": False,
        "credentials_retained": False,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = snapshot(args.out.resolve())
    print(
        json.dumps(
            {
                "status": result["status"],
                "models": result["model_count"],
                "selected": result["selected_model_ids"],
                "credentials_retained": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
