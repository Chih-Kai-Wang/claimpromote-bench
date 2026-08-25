#!/usr/bin/env python3
"""Run the frozen analysis with a documented account-ID regex false-positive fix."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import analyze_review_gap_experiments as frozen  # noqa: E402

from claimpromotebench.hashing import sha256_file  # noqa: E402

Json = dict[str, Any]
FROZEN_ANALYZER = ROOT / "scripts" / "analyze_review_gap_experiments.py"
ORIGINAL_FORBIDDEN = frozen.FORBIDDEN
ACCOUNT_ID = (
    r"\b(?i:org|user|acct|account)_"
    r"(?=[A-Za-z0-9_-]{12,64}\b)"
    r"(?=[A-Za-z0-9_-]*[A-Z])"
    r"(?=[A-Za-z0-9_-]*[a-z])"
    r"(?=[A-Za-z0-9_-]*[0-9])"
    r"[A-Za-z0-9_-]+\b"
)
CORRECTED_FORBIDDEN = re.compile(
    r"(?i:/Users/|[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}|"
    r"(?:sk|key|token)-[A-Za-z0-9_-]{16,})|" + ACCOUNT_ID,
)


def patch_receipt(out_dir: Path, frozen_digest: str) -> None:
    original_matches: set[str] = set()
    for path in sorted(out_dir.rglob("*")):
        if path.is_file() and path.name != "privacy-receipt.json":
            text = path.read_text(encoding="utf-8")
            original_matches.update(match.group(0) for match in ORIGINAL_FORBIDDEN.finditer(text))
            if CORRECTED_FORBIDDEN.search(text):
                raise SystemExit(f"privacy patch: corrected scan failed: {path.name}")
    if original_matches != {"USER_ONLY_PUBLICATION"}:
        raise SystemExit("privacy patch: frozen scanner had an unexpected match set")
    receipt: Json = {
        "schema_version": "1.0.0",
        "status": "POSTHOC_PRIVACY_REGEX_FALSE_POSITIVE_FIX",
        "frozen_analyzer_sha256": frozen_digest,
        "scope": "ACCOUNT_IDENTIFIER_DETECTION_ONLY",
        "original_false_positive_literals": ["USER_ONLY_PUBLICATION"],
        "scoring_or_metrics_code_changed": False,
        "raw_prompts_or_responses_retained": False,
        "provider_response_identifiers_retained": False,
        "hidden_reasoning_retained": False,
    }
    patch_path = out_dir / "analysis-patch-receipt.json"
    patch_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    privacy_path = out_dir / "privacy-receipt.json"
    privacy = json.loads(privacy_path.read_text(encoding="utf-8"))
    privacy["files_scanned"] = int(privacy["files_scanned"]) + 1
    privacy["file_sha256"][patch_path.name] = sha256_file(patch_path)
    privacy["posthoc_privacy_patch_receipt"] = patch_path.name
    privacy_path.write_text(json.dumps(privacy, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--private-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    frozen_digest = sha256_file(FROZEN_ANALYZER)
    frozen.FORBIDDEN = CORRECTED_FORBIDDEN
    frozen.analyze(args.root.resolve(), args.private_dir.resolve(), args.out_dir.resolve())
    patch_receipt(args.out_dir.resolve(), frozen_digest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
