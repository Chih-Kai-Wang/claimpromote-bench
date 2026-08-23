#!/usr/bin/env python3
"""Build an anonymized reviewer bundle for double-blind evaluation.

The bundle contains benchmark code/data plus reviewer-release empirical records. It excludes Git
history, author metadata, public repository links, workflow IDs, searchable provenance hashes, the
private construction seed, and human-subject records. The builder fails if an identity token
survives staging.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import shutil
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {
    ".cff",
    ".json",
    ".jsonl",
    ".lean",
    ".md",
    ".py",
    ".sh",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
TEXT_NAMES = {"LICENSE"}
FORBIDDEN_CREDENTIAL_PATTERNS = {
    "private-key header": re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"),
    "OpenAI-style secret": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
    "Google API key": re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"),
    "GitHub token": re.compile(r"\b(?:github_pat_|gh[pousr]_)[A-Za-z0-9_]{20,}\b"),
    "bearer credential": re.compile(r"\bBearer\s+[A-Za-z0-9._~-]{24,}\b", re.IGNORECASE),
}
FORBIDDEN_PROVIDER_RESPONSE_PATTERNS = {
    "Anthropic-style response ID": re.compile(r"\bmsg_[0-9a-f-]{16,}\b", re.IGNORECASE),
    "OpenAI-style response ID": re.compile(
        r"\b(?:chatcmpl-|resp_)[A-Za-z0-9_-]{10,}\b", re.IGNORECASE
    ),
}
SENSITIVE_PROVENANCE_REPLACEMENTS = {
    "provider account identifier": (
        re.compile(
            r"\buser_(?=[A-Za-z0-9_-]{20,64}\b)"
            r"(?=[A-Za-z0-9_-]*[A-Z])(?=[A-Za-z0-9_-]*[a-z])"
            r"(?=[A-Za-z0-9_-]*[0-9])[A-Za-z0-9_-]+\b"
        ),
        "anonymous-provider-account",
    ),
}
SKIP_NAMES = {
    ".git",
    ".github",
    ".lake",
    ".mypy_cache",
    ".pytest_cache",
    "__pycache__",
    "work",
}
SKIP_FILES = {
    "review.py",
    "review_analysis.py",
    "SHA256SUMS",
}
SKIP_SUFFIXES = {".log", ".pyc", ".pyo"}
LOCAL_WORKSPACE_ROOT = (
    "C:\\Users\\user\\Documents\\Codex\\2026-08-20\\files-pasted-by-the-user-github"
    "\\work\\claimpromote-bench"
)
GITHUB_RUNNER_ROOT = "/home/runner/work/claimpromote-bench/claimpromote-bench"
MAC_WORKSPACE_ROOT = "/Users/wangzhikai/Documents/ChatGPT/claimpromotebranch投稿/claimpromote-bench"
FORBIDDEN_TEXT = {
    "Chih-Kai Wang",
    "Wang, Chih-Kai",
    "National Taipei University of Education",
    "f0909172434",
    "wangzhikai",
    "f0909172434@gmail.com",
    "github.com/f0909172434",
    "paper/v1-submission-prep",
    "agent/iclr2027-v2-low-cost-study",
    "32255636879",
    "32274814703",
    "32291482079",
    "32297818154",
    "32402699174",
    "32402993463",
    "32403718086",
    "32405565039",
    "32453310192",
    "32509532820",
    "9460301513",
    "3eb5b534ab486dac774a62de3d623fa33009be3705d9e8d620bb9942e8bfe664",
    "83dbee4923bca6a0d1908083172190d7b81e2a5e9613c22e4929cfa25c0b264e",
    "eb2af5fcfce8466306a208a707e0046b389f2fd656d25d549f784acfc04199e5",
    "abfc25e9a01018bdc269b683cbf54ca423264f62cacbbfee0d504ef10beb6f91",
    "f998a05fec36b84e59230fe241f1e9961647ad2e",
    "8d9b3f5c831f432cf6b321e6402724c4f52bb3e1",
    "aa5268dcde2aa44f8eabf0246631efbca27de7e5",
    "e2b09f30b0573cf7bcb244eef1917691755f2877",
    "22126629f3584ec2fbbb8e7b77c34faea67d833c",
    "3634ce85785e9b516abc519711fff12388307331",
    "2212662",
    "3634ce8",
    "8dd8d4887f48f053202c0ae6e51ca492ef9a4bc07e93ea101c7a918b2c515e5a",
    "ba6ba3057d96443af989e5c6e28f405d891c0504cdb7d997a9c83453addda355",
    "0054a4d73bdbd81e0ba31871ab4e51140ebf5f2421feda7cce40d57639b53ef7",
    "41480fba50bccfb955007a487dd0370f23daa876e82cd55a8d6601d0df64a9c8",
    "f2bb2e976da6e5b3bf2a6b3739e628aa28578e48a90ce9c6a20ae7105bc3d4c4",
    "119e475953e50218fc62abd2163eef04cbad4e23",
    "b86ee1e1d28db8a390344d28582af88e26970560",
    "cc67096ba0a91866ab442647b9f82301dd6cb317",
    "300dc094852e74c8139344248b25a4d637a94c7c",
    "1901e471bdf94f434f9671708b93599a106b1543",
    "3746403ea8784a95ae2cb1c66ee1b95e4a67ad42",
    "057e785483eed14742e63817f81bea6add579c53",
    "f44b01eb97418d87aa6d7486fa785c0f49b9dda2",
    "8821e710f867df95a932e9ce7cc4f3514a4995a6576d53bc0b5a71a84ee99b9b",
    "e3823dbc2df2ac596df43ee4d6c3b5fb2ff16516",
    LOCAL_WORKSPACE_ROOT,
    GITHUB_RUNNER_ROOT,
    MAC_WORKSPACE_ROOT,
}

PROVENANCE_REPLACEMENTS = {
    "Chih-Kai Wang": "Anonymous Authors",
    "Wang, Chih-Kai": "Anonymous Authors",
    "National Taipei University of Education": "Anonymous Institution",
    "f0909172434@gmail.com": "anonymous@example.invalid",
    "github.com/f0909172434": "anonymous.invalid/repository",
    "f0909172434": "anonymous-owner",
    "wangzhikai": "anonymous-local-user",
    "paper/v1-submission-prep": "anonymous-base-branch",
    "agent/iclr2027-v2-low-cost-study": "anonymous-study-branch",
    "32255636879": "anonymous-v1-source-run",
    "32274814703": "anonymous-v1-recovery-run",
    "32291482079": "anonymous-public-pilot-run",
    "32297818154": "anonymous-public-pilot-recovery-run",
    "32402699174": "anonymous-capable-preflight-run",
    "32402993463": "anonymous-capable-transport-run",
    "32403718086": "anonymous-capable-first-qualified-run",
    "32405565039": "anonymous-capable-final-qualified-run",
    "32453310192": "anonymous-fresh-confirmatory-run",
    "32509532820": "anonymous-balanced-challenge-run",
    "9460301513": "anonymous-balanced-challenge-artifact",
    "8d9b3f5c831f432cf6b321e6402724c4f52bb3e1": "anonymous-hidden-commitment",
    "aa5268dcde2aa44f8eabf0246631efbca27de7e5": "anonymous-v1-scored-source",
    "e2b09f30b0573cf7bcb244eef1917691755f2877": "anonymous-v1-recovery-source",
    "22126629f3584ec2fbbb8e7b77c34faea67d833c": ("0000000000000000000000000000000000000003"),
    "3634ce85785e9b516abc519711fff12388307331": ("0000000000000000000000000000000000000004"),
    "2212662": "anonymous-followup-plan-a",
    "3634ce8": "anonymous-followup-plan-b",
    "119e475953e50218fc62abd2163eef04cbad4e23": ("0000000000000000000000000000000000000001"),
    "b86ee1e1d28db8a390344d28582af88e26970560": ("0000000000000000000000000000000000000002"),
    "cc67096ba0a91866ab442647b9f82301dd6cb317": ("anonymous-capable-collection-source"),
    "300dc094852e74c8139344248b25a4d637a94c7c": ("0000000000000000000000000000000000000000"),
    "1901e471bdf94f434f9671708b93599a106b1543": ("0000000000000000000000000000000000000005"),
    "3746403ea8784a95ae2cb1c66ee1b95e4a67ad42": ("0000000000000000000000000000000000000006"),
    "057e785483eed14742e63817f81bea6add579c53": "0000000000000000000000000000000000000007",
    "f44b01eb97418d87aa6d7486fa785c0f49b9dda2": ("0000000000000000000000000000000000000008"),
    "e3823dbc2df2ac596df43ee4d6c3b5fb2ff16516": ("0000000000000000000000000000000000000009"),
    LOCAL_WORKSPACE_ROOT: "/anonymous/workspace",
    GITHUB_RUNNER_ROOT: "/anonymous/workspace",
    MAC_WORKSPACE_ROOT: "/anonymous/workspace",
    "3eb5b534ab486dac774a62de3d623fa33009be3705d9e8d620bb9942e8bfe664": (
        "anonymous-v1-study-digest"
    ),
    "83dbee4923bca6a0d1908083172190d7b81e2a5e9613c22e4929cfa25c0b264e": (
        "anonymous-public-pilot-digest"
    ),
    "eb2af5fcfce8466306a208a707e0046b389f2fd656d25d549f784acfc04199e5": (
        "anonymous-public-pilot-reporting-digest"
    ),
    "abfc25e9a01018bdc269b683cbf54ca423264f62cacbbfee0d504ef10beb6f91": (
        "anonymous-capable-exploratory-reporting-digest"
    ),
    "f998a05fec36b84e59230fe241f1e9961647ad2e": "anonymous-public-pilot-source",
    "8dd8d4887f48f053202c0ae6e51ca492ef9a4bc07e93ea101c7a918b2c515e5a": (
        "anonymous-followup-digest-a"
    ),
    "ba6ba3057d96443af989e5c6e28f405d891c0504cdb7d997a9c83453addda355": (
        "anonymous-followup-digest-b"
    ),
    "0054a4d73bdbd81e0ba31871ab4e51140ebf5f2421feda7cce40d57639b53ef7": (
        "anonymous-followup-digest-c"
    ),
    "41480fba50bccfb955007a487dd0370f23daa876e82cd55a8d6601d0df64a9c8": (
        "anonymous-followup-digest-d"
    ),
    "f2bb2e976da6e5b3bf2a6b3739e628aa28578e48a90ce9c6a20ae7105bc3d4c4": (
        "anonymous-followup-digest-e"
    ),
    "8821e710f867df95a932e9ce7cc4f3514a4995a6576d53bc0b5a71a84ee99b9b": (
        "anonymous-balanced-challenge-artifact-digest"
    ),
}
NUMERIC_PROVENANCE_REPLACEMENTS = {
    int(source): replacement
    for source, replacement in PROVENANCE_REPLACEMENTS.items()
    if source.isdigit()
}

Json = dict[str, Any]

FRESH_CONFIRMATORY_ROW_FIELDS = (
    "actual_cost_usd",
    "application_post_count",
    "client_retry_count",
    "deterministic_gate_applied",
    "evidence_ceiling",
    "finish_reason",
    "http_status",
    "item_id",
    "lane_id",
    "latency_ms",
    "model_requested",
    "model_returned",
    "network_error",
    "pair_id",
    "parse_detail",
    "parse_status",
    "provider_service",
    "raw_decision",
    "raw_final_text",
    "raw_final_text_sha256",
    "redirect_followed",
    "sequence",
    "usage",
)


def fail(message: str) -> None:
    raise SystemExit(f"anonymous-review-bundle: {message}")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def sha256_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_jsonl(path: Path, rows: list[Json]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(f"{canonical_json(row)}\n" for row in rows),
        encoding="utf-8",
    )


def load_object(path: Path) -> Json:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        fail(f"expected JSON object: {path.relative_to(ROOT)}")
    return value


def apply_balanced_reporting_correction(aggregate: Json, correction: Json) -> Json:
    """Apply the receipted derived-metric correction without altering historical source files."""

    payload = deepcopy(correction)
    observed_receipt_sha = payload.pop("receipt_sha256", None)
    if observed_receipt_sha != sha256_text(canonical_json(payload)):
        fail("balanced challenge reporting-correction self-digest changed")
    if (
        correction.get("status") != "REPORTING_CORRECTION"
        or correction.get("metric_convention")
        != "FIXED_FOUR_CLASS_MACRO_F1_WITH_ZERO_DIVISION_EQUAL_TO_ZERO"
        or correction.get("scope", {}).get("model_calls_performed") != 0
        or correction.get("scope", {}).get("raw_or_terminal_records_changed") is not False
        or correction.get("scope", {}).get("primary_endpoints_changed") is not False
    ):
        fail("balanced challenge reporting-correction boundary changed")
    bindings = correction.get("source_bindings")
    if not isinstance(bindings, dict):
        fail("balanced challenge reporting-correction bindings are missing")
    for relative, expected in bindings.items():
        source = ROOT / str(relative)
        if not source.is_file() or sha256_file(source) != expected:
            fail(f"balanced challenge reporting-correction binding changed: {relative}")

    corrected = deepcopy(aggregate)
    lanes = {
        str(lane.get("lane_id")): lane.get("metrics")
        for lane in corrected.get("lanes", [])
        if isinstance(lane, dict) and isinstance(lane.get("metrics"), dict)
    }
    affected = correction.get("affected_lanes")
    if not isinstance(affected, dict) or set(affected) != {"opencode-go-deepseek-v4-flash-matched"}:
        fail("balanced challenge reporting-correction lane set changed")
    for lane_id, change in affected.items():
        metrics = lanes.get(lane_id)
        if not isinstance(metrics, dict) or not isinstance(change, dict):
            fail(f"balanced challenge reporting-correction lane is malformed: {lane_id}")
        historical = change.get("historical")
        replacement = change.get("corrected")
        if not isinstance(historical, dict) or not isinstance(replacement, dict):
            fail(f"balanced challenge reporting-correction values are malformed: {lane_id}")
        demote = metrics.get("per_action", {}).get("DEMOTE")
        if not isinstance(demote, dict):
            fail(f"balanced challenge DEMOTE metrics are missing: {lane_id}")
        observed = {
            "conditional_macro_f1": metrics.get("conditional_macro_f1"),
            "macro_f1": metrics.get("macro_f1"),
            "per_action.DEMOTE.conditional_f1": demote.get("conditional_f1"),
            "per_action.DEMOTE.end_to_end_f1": demote.get("end_to_end_f1"),
            "per_action.DEMOTE.precision": demote.get("precision"),
        }
        if observed != historical:
            fail(f"balanced challenge historical correction values changed: {lane_id}")
        metrics["conditional_macro_f1"] = replacement["conditional_macro_f1"]
        metrics["macro_f1"] = replacement["macro_f1"]
        demote["conditional_f1"] = replacement["per_action.DEMOTE.conditional_f1"]
        demote["end_to_end_f1"] = replacement["per_action.DEMOTE.end_to_end_f1"]
        demote["precision"] = replacement["per_action.DEMOTE.precision"]
    return corrected


def strip_schema_ids(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: strip_schema_ids(child) for key, child in value.items() if key != "$id"}
    if isinstance(value, list):
        return [strip_schema_ids(child) for child in value]
    return value


def anonymize_provenance(value: Any) -> Any:
    """Replace searchable repository provenance while preserving empirical payloads."""

    if isinstance(value, dict):
        hidden_reasoning_keys = {
            "reasoning_content",
            "thinking",
            "thinking_content",
            "thought",
            "thoughts",
        }
        cleaned: Json = {}
        for key, child in value.items():
            if key in hidden_reasoning_keys:
                continue
            if key in {"provider_response_id", "provider_request_id"}:
                cleaned[key] = None
            else:
                cleaned[key] = anonymize_provenance(child)
        return cleaned
    if isinstance(value, list):
        return [anonymize_provenance(child) for child in value]
    if isinstance(value, int) and value in NUMERIC_PROVENANCE_REPLACEMENTS:
        return NUMERIC_PROVENANCE_REPLACEMENTS[value]
    if isinstance(value, str):
        cleaned = value
        for source, replacement in sorted(
            PROVENANCE_REPLACEMENTS.items(), key=lambda row: len(row[0]), reverse=True
        ):
            cleaned = cleaned.replace(source, replacement)
        for pattern, replacement in SENSITIVE_PROVENANCE_REPLACEMENTS.values():
            cleaned = pattern.sub(replacement, cleaned)
        return cleaned
    return value


def copy_anonymized_tree(source: Path, destination: Path) -> None:
    """Copy a reviewer-evidence tree while removing searchable provenance values."""

    if not source.is_dir():
        fail(f"missing empirical evidence source: {source.relative_to(ROOT)}")
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        if should_skip(relative):
            continue
        anonymous_relative = Path(str(anonymize_provenance(relative.as_posix())))
        target = destination / anonymous_relative
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        source_digest = sha256_file(path).removeprefix("sha256:")
        force_digest_change = source_digest in FORBIDDEN_TEXT
        if path.suffix.lower() in TEXT_SUFFIXES or path.name in TEXT_NAMES:
            source_text = path.read_text(encoding="utf-8")
            if not force_digest_change and not any(
                token in source_text for token in PROVENANCE_REPLACEMENTS
            ):
                shutil.copyfile(path, target)
                continue
        if path.suffix == ".json":
            value = anonymize_provenance(json.loads(source_text))
            if force_digest_change and isinstance(value, dict):
                value["anonymous_source_identity"] = "WITHHELD_DURING_DOUBLE_BLIND_REVIEW"
            target.write_text(
                json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        elif path.suffix == ".jsonl":
            rows = [
                anonymize_provenance(json.loads(line))
                for line in source_text.splitlines()
                if line.strip()
            ]
            target.write_text(
                "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
                encoding="utf-8",
            )
        elif path.suffix.lower() in TEXT_SUFFIXES or path.name in TEXT_NAMES:
            text = str(anonymize_provenance(source_text))
            target.write_text(text, encoding="utf-8")
        else:
            shutil.copyfile(path, target)


def repair_capable_anonymous_evidence(root: Path) -> None:
    """Rebind canonical and attempt-history digests after provenance anonymization."""

    run_paths: dict[tuple[str, str], Path] = {}
    for path in sorted((root / "canonical" / "runs").glob("*.jsonl")):
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
        identities = {(str(row.get("lane_id")), str(row.get("phase"))) for row in rows}
        if len(identities) != 1:
            fail(f"capable evidence run has mixed identity: {path.relative_to(root)}")
        identity = identities.pop()
        if identity in run_paths:
            fail(f"duplicate capable evidence run identity: {identity}")
        run_paths[identity] = path

    analysis_paths: dict[tuple[str, str], Path] = {}
    for path in sorted((root / "canonical" / "analysis").glob("*.json")):
        value = load_object(path)
        identity = (str(value.get("lane_id")), str(value.get("phase")))
        if identity not in run_paths or identity in analysis_paths:
            fail(f"capable evidence analysis identity differs from runs: {identity}")
        value["run_sha256"] = sha256_file(run_paths[identity])
        path.write_text(
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        analysis_paths[identity] = path
    if set(analysis_paths) != set(run_paths):
        fail("capable evidence canonical analysis matrix differs from run matrix")

    attempt_run_paths = sorted((root / "attempt-history").glob("**/runs/*.jsonl"))
    if len(attempt_run_paths) != 16:
        fail("capable evidence must retain 14 pilot attempts and two full-pass copies")
    attempt_phase_counts = {"pilot": 0, "full": 0}
    attempt_digests: set[str] = set()
    for run_path in attempt_run_paths:
        analysis_path = run_path.parent.parent / "analysis" / f"{run_path.stem}.json"
        if not analysis_path.is_file():
            fail(f"capable attempt lacks analysis: {run_path.relative_to(root)}")
        rows = [
            json.loads(line) for line in run_path.read_text(encoding="utf-8").splitlines() if line
        ]
        phases = {str(row.get("phase")) for row in rows}
        if len(phases) != 1 or next(iter(phases)) not in attempt_phase_counts:
            fail(f"capable attempt has invalid phase: {run_path.relative_to(root)}")
        attempt_phase_counts[next(iter(phases))] += 1
        run_digest = sha256_file(run_path)
        attempt_digests.add(run_digest)
        value = load_object(analysis_path)
        value["run_sha256"] = run_digest
        analysis_path.write_text(
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if attempt_phase_counts != {"pilot": 14, "full": 2}:
        fail(f"capable attempt-history phase counts changed: {attempt_phase_counts}")
    if not {sha256_file(path) for path in run_paths.values()} <= attempt_digests:
        fail("capable canonical runs are not bound to the released attempt history")

    aggregate_path = root / "aggregate.json"
    aggregate = load_object(aggregate_path)
    qualification = aggregate.get("qualification")
    complete = aggregate.get("models_with_complete_hidden_pass")
    provenance = aggregate.get("provenance")
    if (
        not isinstance(qualification, dict)
        or not isinstance(qualification.get("pilots"), list)
        or not isinstance(complete, list)
        or not isinstance(provenance, dict)
    ):
        fail("capable evidence aggregate is malformed")

    for row in qualification["pilots"]:
        identity = (str(row.get("lane_id")), "pilot")
        if identity not in run_paths:
            fail(f"capable aggregate pilot lacks canonical run: {identity[0]}")
        row["run_sha256"] = sha256_file(run_paths[identity])
    for row in complete:
        identity = (str(row.get("lane_id")), "full")
        if identity not in run_paths:
            fail(f"capable aggregate full result lacks canonical run: {identity[0]}")
        row["run_sha256"] = sha256_file(run_paths[identity])

    for key, phase, paths in (
        ("pilot_run_sha256", "pilot", run_paths),
        ("full_run_sha256", "full", run_paths),
        ("pilot_analysis_sha256", "pilot", analysis_paths),
        ("full_analysis_sha256", "full", analysis_paths),
    ):
        original = provenance.get(key)
        if not isinstance(original, dict):
            fail(f"capable aggregate provenance lacks {key}")
        rebuilt = {
            lane: sha256_file(path)
            for (lane, observed_phase), path in sorted(paths.items())
            if observed_phase == phase
        }
        if set(rebuilt) != set(original):
            fail(f"capable aggregate provenance lane set changed for {key}")
        provenance[key] = rebuilt

    aggregate_path.write_text(
        json.dumps(aggregate, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def should_skip(path: Path) -> bool:
    return (
        any(part in SKIP_NAMES for part in path.parts)
        or path.name in SKIP_FILES
        or path.suffix.lower() in SKIP_SUFFIXES
    )


def copy_tree(source: Path, destination: Path) -> None:
    if not source.exists():
        fail(f"missing source path: {source.relative_to(ROOT)}")
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        if should_skip(relative):
            continue
        target = destination / relative
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix == ".json" and "schemas" in path.parts:
            value = strip_schema_ids(json.loads(path.read_text(encoding="utf-8")))
            target.write_text(
                json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        else:
            shutil.copyfile(path, target)


def copy_file(source: Path, destination: Path) -> None:
    if not source.is_file():
        fail(f"missing source file: {source.relative_to(ROOT)}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.suffix == ".json" and "schemas" in source.parts:
        value = strip_schema_ids(json.loads(source.read_text(encoding="utf-8")))
        destination.write_text(
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    else:
        shutil.copyfile(source, destination)


def rewrite_alpha_manifest(bundle: Path) -> None:
    manifest_path = bundle / "data" / "alpha" / "manifest.json"
    manifest = load_object(manifest_path)
    schema_hashes = manifest.get("schema_sha256")
    if not isinstance(schema_hashes, dict):
        fail("alpha manifest lacks schema_sha256")
    for name in sorted(schema_hashes):
        schema_path = bundle / "schemas" / name
        if not schema_path.is_file():
            fail(f"anonymous bundle lacks alpha schema: {name}")
        schema_hashes[name] = sha256_file(schema_path)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def anonymize_v1_results(source: Json) -> Json:
    runs = source.get("runs")
    if not isinstance(runs, list) or len(runs) != 24:
        fail("v1 public result source does not contain 24 runs")
    return {
        "schema_version": "1.0.0-review",
        "study_kind": "FROZEN_V1_HIDDEN_RESULT_SUMMARY",
        "source_identity": "WITHHELD_DURING_DOUBLE_BLIND_REVIEW",
        "dataset": {
            "evaluation_time": source.get("dataset", {}).get("evaluation_time"),
            "instances_per_run": 300,
        },
        "runs": runs,
        "interpretation_boundary": (
            "This compact summary is a convenience view. The reviewer-release hidden dataset, "
            "source records, normalized records, and normalization map are included separately "
            "under evidence/."
        ),
    }


def remove_keys(value: Any, forbidden_keys: set[str]) -> Any:
    if isinstance(value, dict):
        return {
            key: remove_keys(child, forbidden_keys)
            for key, child in value.items()
            if key not in forbidden_keys
        }
    if isinstance(value, list):
        return [remove_keys(child, forbidden_keys) for child in value]
    return value


def anonymize_v2_results(source: Json) -> Json:
    cleaned = remove_keys(
        source,
        {
            "source_workflow_run_id",
            "study_sha256",
            "run_sha256",
            "run_path",
        },
    )
    if not isinstance(cleaned, dict):
        fail("unexpected v2 result structure")
    cleaned["schema_version"] = "1.0.0-review"
    cleaned["source_identity"] = "WITHHELD_DURING_DOUBLE_BLIND_REVIEW"
    return cleaned


def repair_v2_public_anonymous_evidence(root: Path) -> None:
    aggregate_path = root / "aggregate.json"
    cleaned = anonymize_v2_results(load_object(aggregate_path))
    cleaned["interpretation_status"] = "RECOMPUTATION_VERIFIED_FOR_REPORTING"
    aggregate_path.write_text(
        json.dumps(cleaned, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _reject_hidden_reasoning(value: Any, label: str) -> None:
    if isinstance(value, dict):
        forbidden = {
            "reasoning_content",
            "thinking",
            "thinking_content",
            "thought",
            "thoughts",
        }
        overlap = forbidden & set(value)
        if overlap:
            fail(f"{label} contains hidden-reasoning fields: {sorted(overlap)}")
        block_type = str(value.get("type", "")).lower()
        if block_type in {"reasoning", "thinking"}:
            fail(f"{label} contains a hidden-reasoning content block")
        for child in value.values():
            _reject_hidden_reasoning(child, label)
    elif isinstance(value, list):
        for child in value:
            _reject_hidden_reasoning(child, label)


def _fresh_analysis_projection(value: Json) -> Json:
    projected = deepcopy(value)
    projected.pop("aggregate_sha256", None)
    projected.pop("source_identity", None)
    scores = projected.get("scores")
    if isinstance(scores, dict):
        for score in scores.values():
            if isinstance(score, dict):
                score.pop("run_sha256", None)
    return projected


def build_fresh_confirmatory_anonymous_evidence(source: Path, destination: Path) -> None:
    """Create a compact, replayable, identity-free derivative of the safe r6 release."""

    if not source.is_dir():
        fail(f"missing fresh-confirmatory source: {source.relative_to(ROOT)}")
    destination.mkdir(parents=True, exist_ok=True)

    copy_tree(source / "dataset", destination / "dataset")
    copy_file(ROOT / "v2" / "fresh-confirmatory-study-plan.json", destination / "study-plan.json")
    correction_source = load_object(
        ROOT / "v2" / "confirmatory" / "r6-execution" / "frozen-manifest-metadata-correction.json"
    )
    correction_source.pop("self_digest", None)
    correction_source["source_manifest_path"] = "dataset/manifest.json"
    correction_source["source_identity"] = "WITHHELD_DURING_DOUBLE_BLIND_REVIEW"
    correction_source["self_digest"] = sha256_text(canonical_json(correction_source))
    write_json(destination / "frozen-manifest-metadata-correction.json", correction_source)

    packet_paths = sorted(source.glob("collected/*/confirmatory-packet.json"))
    baseline_paths = sorted(source.glob("collected/*/confirmatory-baselines.json"))
    c2_receipt_paths = sorted(source.glob("collected/*/c2-receipt.json"))
    c2_run_paths = sorted(source.glob("collected/*/complete/*-c2-complete.jsonl"))
    if not (
        len(packet_paths) == len(baseline_paths) == len(c2_receipt_paths) == 1
        and len(c2_run_paths) == 2
    ):
        fail("fresh-confirmatory source has an unexpected packet/baseline/C2 layout")
    copy_file(packet_paths[0], destination / "prompt-packet.json")
    copy_file(baseline_paths[0], destination / "baselines.json")

    c2_source = load_object(c2_receipt_paths[0])
    c2_review = {
        "analysis_executed_before_receipt": c2_source.get("analysis_executed_before_receipt"),
        "commitment_stage": c2_source.get("commitment_stage"),
        "contains_gold_labels": c2_source.get("contains_gold_labels"),
        "gold_loaded_before_receipt": c2_source.get("gold_loaded_before_receipt"),
        "outcome_counts": c2_source.get("outcome_counts"),
        "planned_cells": c2_source.get("planned_cells"),
        "schema_version": "1.0.0-review",
        "sealed_cells": c2_source.get("sealed_cells"),
        "source_identity": "WITHHELD_DURING_DOUBLE_BLIND_REVIEW",
        "status": "C2_BEFORE_GOLD_UNBLINDING_OR_ANALYSIS",
        "study_id": c2_source.get("study_id"),
    }
    write_json(destination / "c2-receipt-review.json", c2_review)

    runs_destination = destination / "runs"
    runs_destination.mkdir()
    lane_files: dict[str, str] = {}
    for source_run in c2_run_paths:
        source_rows = [
            json.loads(line)
            for line in source_run.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        lane_ids = {str(row.get("lane_id")) for row in source_rows}
        if len(source_rows) != 300 or len(lane_ids) != 1:
            fail(f"fresh-confirmatory C2 run has invalid coverage: {source_run.name}")
        lane_id = lane_ids.pop()
        if not re.fullmatch(r"[a-z0-9][a-z0-9._-]+", lane_id) or lane_id in lane_files:
            fail(f"fresh-confirmatory lane identity is invalid or duplicated: {lane_id}")
        projected_rows: list[Json] = []
        for source_row in source_rows:
            projected = {
                key: deepcopy(source_row[key])
                for key in FRESH_CONFIRMATORY_ROW_FIELDS
                if key in source_row
            }
            if set(projected) != set(FRESH_CONFIRMATORY_ROW_FIELDS):
                missing = sorted(set(FRESH_CONFIRMATORY_ROW_FIELDS) - set(projected))
                fail(f"fresh-confirmatory row lacks reviewer fields: {missing}")
            _reject_hidden_reasoning(projected, f"fresh-confirmatory row {projected['item_id']}")
            raw_text = projected.get("raw_final_text")
            raw_sha = projected.get("raw_final_text_sha256")
            if raw_text is None:
                if raw_sha is not None:
                    fail("fresh-confirmatory null final text has a digest")
            elif raw_sha != sha256_text(str(raw_text)):
                fail("fresh-confirmatory final-text digest changed")
            projected_rows.append(projected)
        target_name = f"{lane_id}.jsonl"
        target_path = runs_destination / target_name
        target_path.write_text(
            "".join(f"{canonical_json(row)}\n" for row in projected_rows),
            encoding="utf-8",
        )
        lane_files[lane_id] = f"runs/{target_name}"

    source_analysis = load_object(source / "confirmatory-analysis-public.json")
    reported_analysis = _fresh_analysis_projection(source_analysis)
    reported_analysis["source_identity"] = "WITHHELD_DURING_DOUBLE_BLIND_REVIEW"
    write_json(destination / "reported-analysis.json", reported_analysis)

    source_result = load_object(ROOT / "v2" / "confirmatory" / "r6-execution" / "study-result.json")
    for key in ("public_release", "scored_execution", "study_result_sha256"):
        source_result.pop(key, None)
    source_result["source_identity"] = "WITHHELD_DURING_DOUBLE_BLIND_REVIEW"
    source_result["review_disposition"]["public_artifact"] = (
        "GO_REDACTED_PERSISTENT_ANONYMOUS_DERIVATIVE"
    )
    write_json(destination / "study-result.json", source_result)

    source_addendum = load_object(
        ROOT / "v2" / "confirmatory" / "r6-execution" / "reviewer-reporting-addendum.json"
    )
    source_addendum.pop("self_digest", None)
    source_addendum["sources"] = {
        "anonymous_recomputation": (
            "Recomputed from dataset/, runs/, and reported-analysis.json in this directory."
        ),
        "source_identity": "WITHHELD_DURING_DOUBLE_BLIND_REVIEW",
    }
    source_addendum["self_digest"] = sha256_text(canonical_json(source_addendum))
    write_json(destination / "reporting-addendum.json", source_addendum)

    source_redaction = load_object(source / "public-release-redaction-receipt.json")
    source_equivalence = load_object(source / "public-release-scientific-equivalence.json")
    anonymous_redaction = {
        "hidden_reasoning_present_in_public_release": source_equivalence.get(
            "hidden_reasoning_present_in_public_release"
        ),
        "original_scored_artifacts_modified": source_redaction.get(
            "original_scored_artifacts_modified"
        ),
        "post_c2_transform": source_redaction.get("post_c2_transform"),
        "public_provider_envelopes_allowlisted": source_equivalence.get(
            "public_provider_envelopes_allowlisted"
        ),
        "redacted_unique_model_item_cells": source_redaction.get(
            "redacted_unique_model_item_cells"
        ),
        "redaction_rule": source_redaction.get("redaction_rule"),
        "redaction_rule_sha256": source_redaction.get("redaction_rule_sha256"),
        "removed_content_blocks_including_raw_and_c2_copies": source_redaction.get(
            "removed_content_blocks_including_raw_and_c2_copies"
        ),
        "schema_version": "1.0.0-review",
        "scientific_analysis_payload_byte_identical": source_equivalence.get(
            "scientific_analysis_payload_byte_identical"
        ),
        "source_identity": "WITHHELD_DURING_DOUBLE_BLIND_REVIEW",
        "source_to_derived_row_hashes_verified_before_anonymization": source_equivalence.get(
            "source_to_derived_row_hashes_verified"
        ),
        "status": "POST_C2_PUBLIC_RELEASE_REDACTION_VERIFIED",
    }
    write_json(destination / "redaction-receipt-review.json", anonymous_redaction)

    readme = """# Fresh confirmatory reviewer evidence

This directory is a compact double-blind derivative of the immutable r6 execution. It contains the
released 300-item paired dataset, the frozen prompt packet and baseline predictions, two projected
C2-complete service-configuration runs, the preregistered study plan, and the complete scientific
analysis with only source-identifying provenance hashes removed.

The Qwen service configuration produced 272 valid decisions and achieved 86.00% end-to-end item
accuracy and 75.33% pair accuracy. Among covered outputs it achieved 258/272 item accuracy; 123/150
pairs had two valid decisions and 113/123 of those complete pairs were correct. The Flash lane
returned 300 HTTP 401 responses and no model output; it is an authentication or client-service
configuration failure, not an estimate of model accuracy. The Qwen result includes every failure as
incorrect without retry and has zero DEMOTE recall (0/8). `reporting-addendum.json` exposes the
full confusion matrix, factor-level pair outcomes, action-factor concentration, conditional metrics,
and deterministic policy ceiling.

Provider hidden-thinking blocks are not included. They were removed only in a deterministic
post-C2 publication derivative; the original C2 seal and scores were not altered. `MANIFEST.json`
binds every file in this directory. Recompute the reported analysis with
`scripts/validate_anonymous_empirical_evidence.py` from the bundle root.

The immutable dataset manifest retains one stale non-operative `CFM_R5` namespace label and three
construction-time `PENDING` values. The released IDs are all `v1-test-cfo-*`; the bound correction
overlay explains why the original manifest remains byte-identical and how current states are carried
by later receipts.
"""
    (destination / "README.md").write_text(readme, encoding="utf-8", newline="\n")

    files = {
        path.relative_to(destination).as_posix(): sha256_file(path)
        for path in sorted(destination.rglob("*"))
        if path.is_file() and path.name != "MANIFEST.json"
    }
    manifest: Json = {
        "file_count": len(files),
        "files": files,
        "lane_files": lane_files,
        "schema_version": "1.0.0-review",
        "scope": {
            "hidden_reasoning_included": False,
            "item_level_final_outputs_included": True,
            "original_reasoning_bearing_records_included": False,
            "private_construction_salt_included": False,
            "public_repository_identity_included": False,
            "source_artifact_or_workflow_ids_included": False,
        },
        "status": "ANONYMOUS_FRESH_CONFIRMATORY_EVIDENCE",
    }
    manifest["manifest_sha256"] = sha256_text(canonical_json(manifest))
    write_json(destination / "MANIFEST.json", manifest)


def build_balanced_public_anonymous_evidence(destination: Path) -> None:
    """Create a replayable anonymous derivative of the balanced public challenge."""

    source = ROOT / "v2" / "balanced-public-challenge"
    results = source / "results"
    destination.mkdir(parents=True, exist_ok=True)
    copy_tree(source / "dataset", destination / "dataset")
    copy_file(source / "prompt-packet.json", destination / "prompt-packet.json")
    copy_file(
        ROOT / "v2" / "balanced-public-challenge-study-plan.json",
        destination / "study-plan.json",
    )

    run_destination = destination / "runs"
    analysis_destination = destination / "analysis"
    run_destination.mkdir()
    analysis_destination.mkdir()
    lane_files: dict[str, str] = {}
    analysis_files: dict[str, str] = {}
    run_paths: dict[str, Path] = {}
    for source_run in sorted((results / "runs").glob("*.jsonl")):
        rows = [
            anonymize_provenance(json.loads(line))
            for line in source_run.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        lane_ids = {str(row.get("lane_id")) for row in rows}
        if len(rows) != 180 or len(lane_ids) != 1:
            fail(f"balanced challenge run has invalid coverage: {source_run.name}")
        lane_id = lane_ids.pop()
        if lane_id in lane_files:
            fail(f"balanced challenge lane is duplicated: {lane_id}")
        for row in rows:
            _reject_hidden_reasoning(row, f"balanced challenge row {row.get('item_id')}")
            if row.get("provider_response_id") is not None:
                fail(f"balanced challenge retained a provider response ID: {row.get('item_id')}")
            raw_text = row.get("raw_response_text")
            raw_digest = row.get("raw_response_sha256")
            if raw_text is None:
                if raw_digest is not None:
                    fail("balanced challenge null response has a digest")
            elif raw_digest != sha256_text(str(raw_text)):
                fail("balanced challenge response digest changed")
        target = run_destination / source_run.name
        target.write_text(
            "".join(f"{canonical_json(row)}\n" for row in rows),
            encoding="utf-8",
        )
        lane_files[lane_id] = f"runs/{target.name}"
        run_paths[lane_id] = target

    for source_analysis in sorted((results / "analysis").glob("*.json")):
        analysis = anonymize_provenance(load_object(source_analysis))
        lane_id = str(analysis.get("lane_id"))
        if lane_id not in run_paths or lane_id in analysis_files:
            fail(f"balanced challenge analysis lane differs from runs: {lane_id}")
        analysis["run_path"] = lane_files[lane_id]
        analysis["run_sha256"] = sha256_file(run_paths[lane_id])
        target = analysis_destination / source_analysis.name
        write_json(target, analysis)
        analysis_files[lane_id] = f"analysis/{target.name}"
    if set(analysis_files) != set(lane_files):
        fail("balanced challenge analysis matrix differs from run matrix")

    source_aggregate = load_object(results / "aggregate.json")
    source_correction = load_object(results / "reporting-correction-v1.json")
    aggregate = anonymize_provenance(
        apply_balanced_reporting_correction(source_aggregate, source_correction)
    )
    aggregate["source_identity"] = "WITHHELD_DURING_DOUBLE_BLIND_REVIEW"
    external = aggregate.get("external_commitment")
    lanes = aggregate.get("lanes")
    if not isinstance(external, dict) or not isinstance(lanes, list):
        fail("balanced challenge aggregate is malformed")
    external["plan_sha256"] = sha256_file(destination / "study-plan.json")
    external["workflow_run_url"] = "WITHHELD_DURING_DOUBLE_BLIND_REVIEW"
    for lane in lanes:
        lane_id = str(lane.get("lane_id"))
        if lane_id not in run_paths:
            fail(f"balanced challenge aggregate contains an unknown lane: {lane_id}")
        lane["run_sha256"] = sha256_file(run_paths[lane_id])
    write_json(destination / "reported-aggregate.json", aggregate)

    review_correction = {
        "affected_lanes": deepcopy(source_correction["affected_lanes"]),
        "anonymous_run_sha256": {
            lane_id: sha256_file(run_path) for lane_id, run_path in sorted(run_paths.items())
        },
        "authoritative_reporting_rule": source_correction["authoritative_reporting_rule"],
        "correction_id": source_correction["correction_id"],
        "issued_on": source_correction["issued_on"],
        "metric_convention": source_correction["metric_convention"],
        "reason": source_correction["reason"],
        "schema_version": "1.0.0-review",
        "scope": deepcopy(source_correction["scope"]),
        "source_identity": "WITHHELD_DURING_DOUBLE_BLIND_REVIEW",
        "status": "REPORTING_CORRECTION",
    }
    write_json(destination / "reporting-correction-review.json", review_correction)

    source_receipt = load_object(results / "github-artifact-receipt.json")
    validation = source_receipt.get("validation")
    interpretation = source_receipt.get("interpretation")
    if not isinstance(validation, dict) or not isinstance(interpretation, dict):
        fail("balanced challenge source receipt is malformed")
    receipt = {
        "schema_version": "1.0.0-review",
        "status": source_receipt.get("status"),
        "truth_status": source_receipt.get("truth_status"),
        "source_identity": "WITHHELD_DURING_DOUBLE_BLIND_REVIEW",
        "source_artifact_or_workflow_ids_included": False,
        "validation": deepcopy(validation),
        "interpretation": deepcopy(interpretation),
    }
    write_json(destination / "privacy-receipt-review.json", receipt)

    readme = """# Balanced public challenge reviewer evidence

This directory contains the frozen 90-pair / 180-item public challenge, its prompt packet, two
one-pass zero-retry service runs, lane analyses, a corrected reported aggregate, and the bound
reporting-correction receipt. The invalid members are balanced across HOLD, DEMOTE, and ESCALATE
(30 each), with 90 ALLOW members over 15 factors.

Every non-OK response remains incorrect in end-to-end item and pair metrics. The two service
stacks differ, so the lane comparison is descriptive and is not a causal model ablation or a
hidden-test generalization estimate. `privacy-receipt-review.json` records the independent
360-record validation and zero findings for provider account identifiers, retained provider
response IDs, and hidden reasoning. Source workflow, artifact, repository, and commit identities
are withheld during double-blind review.

Run `scripts/validate_anonymous_empirical_evidence.py` from the bundle root to recompute coverage,
conditional and end-to-end accuracy, per-action recall, and the complete confusion matrices.
The correction defines zero-prediction classes as zero for fixed-four-class Macro-F1; it performs
no model calls and changes no primary endpoint, confusion cell, recall, or item-level record.
"""
    (destination / "README.md").write_text(readme, encoding="utf-8", newline="\n")

    files = {
        path.relative_to(destination).as_posix(): sha256_file(path)
        for path in sorted(destination.rglob("*"))
        if path.is_file() and path.name != "MANIFEST.json"
    }
    manifest: Json = {
        "schema_version": "1.0.0-review",
        "status": "ANONYMOUS_BALANCED_PUBLIC_CHALLENGE_EVIDENCE",
        "file_count": len(files),
        "files": files,
        "lane_files": lane_files,
        "analysis_files": analysis_files,
        "scope": {
            "hidden_reasoning_included": False,
            "item_level_final_outputs_included": True,
            "provider_response_identifiers_included": False,
            "public_repository_identity_included": False,
            "source_artifact_or_workflow_ids_included": False,
        },
    }
    manifest["manifest_sha256"] = sha256_text(canonical_json(manifest))
    write_json(destination / "MANIFEST.json", manifest)


SYNTHETIC_POLICY_ROW_FIELDS = (
    "actual_cost_usd",
    "cost_status",
    "dataset_manifest_sha256",
    "evidence_ceiling",
    "finish_reason",
    "frozen_plan_commit",
    "item_id",
    "lane_id",
    "latency_ms",
    "model_family",
    "model_requested",
    "model_returned",
    "packet_sha256",
    "pair_id",
    "parse_error_detail",
    "parse_status",
    "phase",
    "postgate_decision",
    "prompt_sha256",
    "provider",
    "provider_response_id",
    "raw_decision",
    "raw_response_sha256",
    "raw_response_text",
    "request_sha256",
    "request_started_at_utc",
    "response_format_sha256",
    "response_received_at_utc",
    "routed_provider",
    "schema_version",
    "study_id",
    "system_fingerprint",
    "transport_error",
    "transport_status",
    "usage",
)


def _synthetic_policy_manifest(destination: Path, *, study_kind: str, lane_files: Json) -> None:
    files = {
        path.relative_to(destination).as_posix(): sha256_file(path)
        for path in sorted(destination.rglob("*"))
        if path.is_file() and path.name != "MANIFEST.json"
    }
    manifest: Json = {
        "schema_version": "1.0.0-review",
        "status": "ANONYMOUS_SYNTHETIC_POLICY_EVIDENCE",
        "study_kind": study_kind,
        "file_count": len(files),
        "files": files,
        "lane_files": lane_files,
        "scope": {
            "credentials_included": False,
            "hidden_reasoning_included": False,
            "provider_response_identifiers_included": False,
            "source_repository_or_commit_identity_included": False,
            "raw_final_response_text_included": False,
            "item_level_structured_decisions_included": True,
            "all_scheduled_terminal_failures_included": True,
        },
    }
    manifest["manifest_sha256"] = sha256_text(canonical_json(manifest))
    write_json(destination / "MANIFEST.json", manifest)


def _project_synthetic_policy_runs(
    source_results: Path,
    destination: Path,
    *,
    expected_lane_ids: set[str],
) -> Json:
    lane_files: Json = {}
    run_root = destination / "runs"
    for source_run in sorted(source_results.glob("*.jsonl")):
        rows = [
            json.loads(line)
            for line in source_run.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        lane_ids = {str(row.get("lane_id")) for row in rows}
        if len(rows) != 120 or len(lane_ids) != 1:
            fail(f"synthetic-policy run has invalid coverage: {source_run.name}")
        lane_id = next(iter(lane_ids))
        if lane_id not in expected_lane_ids or lane_id in lane_files:
            fail(f"synthetic-policy run has an unknown or duplicate lane: {lane_id}")
        projected_rows: list[Json] = []
        for row in rows:
            _reject_hidden_reasoning(row, f"synthetic-policy row {row.get('item_id')}")
            if row.get("provider_response_id") not in (None, ""):
                fail(f"synthetic-policy run retained a provider response ID: {row.get('item_id')}")
            projected: Json = {key: deepcopy(row.get(key)) for key in SYNTHETIC_POLICY_ROW_FIELDS}
            projected["raw_response_text"] = None
            projected["raw_response_sha256"] = None
            projected["parse_error_detail"] = None
            projected["transport_error"] = None
            projected["provider_response_id"] = None
            projected["frozen_plan_commit"] = "0000000000000000000000000000000000000010"
            projected_rows.append(anonymize_provenance(projected))
        target = run_root / source_run.name
        write_jsonl(target, projected_rows)
        lane_files[lane_id] = f"runs/{source_run.name}"
    if set(lane_files) != expected_lane_ids:
        fail("synthetic-policy result lane set differs from the frozen plan")
    return lane_files


def _project_synthetic_policy_aggregate(
    source: Json,
    destination: Path,
    lane_files: Json,
    *,
    execution_receipt_sha256: str | None = None,
) -> Json:
    aggregate = anonymize_provenance(source)
    freeze = aggregate.get("freeze")
    if isinstance(freeze, dict):
        freeze["frozen_plan_commit"] = "0000000000000000000000000000000000000010"
        if execution_receipt_sha256 is not None:
            freeze["execution_receipt_sha256"] = execution_receipt_sha256
    lanes = aggregate.get("lanes")
    if not isinstance(lanes, list):
        fail("synthetic-policy aggregate lacks lanes")
    for lane in lanes:
        if not isinstance(lane, dict):
            fail("synthetic-policy aggregate lane is malformed")
        lane_id = str(lane.get("lane_id"))
        relative = lane_files.get(lane_id)
        if not isinstance(relative, str):
            fail(f"synthetic-policy aggregate has an unknown lane: {lane_id}")
        lane["run_sha256"] = sha256_file(destination / relative)
    return aggregate


def _project_synthetic_policy_execution_receipt(
    source: Json, destination: Path, lane_files: Json
) -> Json:
    receipt = anonymize_provenance(source)
    receipt["frozen_plan_commit"] = "0000000000000000000000000000000000000010"
    receipt["request_intent_journal_sha256"] = None
    receipt["terminal_journal_sha256"] = None
    receipt["source_journal_digests_included"] = False
    receipt["lane_output_sha256"] = {
        Path(str(relative)).name: sha256_file(destination / str(relative))
        for relative in lane_files.values()
    }
    return receipt


def build_slsa_portability_anonymous_evidence(destination: Path) -> None:
    source = ROOT / "v2" / "slsa-portability-v1"
    replacement = source / "replacement-v2"
    plan = load_object(replacement / "study-plan.json")
    aggregate = load_object(replacement / "results" / "aggregate.json")
    expected_lanes = {str(row["lane_id"]) for row in plan["formal_lanes"]}
    if aggregate.get("status") != "COMPLETE":
        fail("SLSA portability aggregate is not complete")

    copy_tree(replacement / "dataset", destination / "dataset")
    copy_tree(replacement / "baseline", destination / "baseline")
    copy_file(source / "policy-contract.json", destination / "policy-contract.json")
    copy_file(source / "source-registry.json", destination / "source-registry.json")
    copy_file(
        replacement / "source-validation-receipt.json",
        destination / "source-validation-receipt.json",
    )
    void_receipt = anonymize_provenance(
        load_object(source / "void-attempt-v1" / "void-receipt.json")
    )
    void_receipt["frozen_plan_commit"] = "0000000000000000000000000000000000000011"
    void_receipt["journal_sha256"] = None
    void_receipt["source_journal_digest_included"] = False
    write_json(destination / "void-exclusion-receipt.json", void_receipt)
    for name in ("study-plan.json", "request-schedule.json"):
        write_json(destination / name, anonymize_provenance(load_object(replacement / name)))
    lane_files = _project_synthetic_policy_runs(
        replacement / "results", destination, expected_lane_ids=expected_lanes
    )
    execution_receipt = _project_synthetic_policy_execution_receipt(
        load_object(replacement / "results" / "execution-receipt.json"),
        destination,
        lane_files,
    )
    write_json(destination / "execution-receipt.json", execution_receipt)
    write_json(
        destination / "reported-aggregate.json",
        _project_synthetic_policy_aggregate(aggregate, destination, lane_files),
    )
    (destination / "README.md").write_text(
        """# SLSA-derived portability reviewer evidence

This directory contains the complete 120-item, 60-pair second-policy study. SLSA and in-toto
ground the evidence fields; the transition policy and labels are author-defined. Every scheduled
service or output failure remains in the end-to-end denominator. The incomplete predecessor is
excluded by `void-exclusion-receipt.json`; its raw records are omitted.

Raw response text, free-form provider errors, credentials, provider response IDs, hidden reasoning,
and source repository or commit identity are excluded. Structured decisions, parser classes,
usage, timings, hashes, gold labels, pair membership, and complete failure cells remain.
""",
        encoding="utf-8",
    )
    _synthetic_policy_manifest(
        destination, study_kind="SLSA_DERIVED_POLICY_PORTABILITY", lane_files=lane_files
    )


def build_policy_switch_anonymous_evidence(destination: Path) -> None:
    source = ROOT / "v2" / "policy-switch-v1"
    frozen = source / "frozen"
    plan = load_object(frozen / "study-plan.json")
    aggregate = load_object(frozen / "results" / "aggregate.json")
    expected_lanes = {str(row["lane_id"]) for row in plan["formal_lanes"]}
    if aggregate.get("status") != "COMPLETE":
        fail("policy-switch aggregate is not complete")

    copy_tree(frozen / "dataset", destination / "dataset")
    copy_tree(frozen / "baseline", destination / "baseline")
    copy_file(source / "policy-contract.json", destination / "policy-contract.json")
    for name in ("study-plan.json", "request-schedule.json"):
        write_json(destination / name, anonymize_provenance(load_object(frozen / name)))
    lane_files = _project_synthetic_policy_runs(
        frozen / "results", destination, expected_lane_ids=expected_lanes
    )
    execution_receipt = _project_synthetic_policy_execution_receipt(
        load_object(frozen / "results" / "execution-receipt.json"), destination, lane_files
    )
    write_json(destination / "execution-receipt.json", execution_receipt)
    write_json(
        destination / "reported-aggregate.json",
        _project_synthetic_policy_aggregate(
            aggregate,
            destination,
            lane_files,
            execution_receipt_sha256=sha256_file(destination / "execution-receipt.json"),
        ),
    )
    (destination / "README.md").write_text(
        """# Counterfactual policy-switch reviewer evidence

Each of the 60 pairs holds the artifact, evidence, current state, and requested state fixed while
changing only the published active policy profile. Both profiles and all labels are author-defined
test instruments. The policy-aware and profile-blind Random Forest comparators were trained on the
development split before scored inference.

Every scheduled service or output failure remains in the end-to-end denominator. Raw response
text, free-form provider errors, credentials, provider response IDs, hidden reasoning, and source
repository or commit identity are excluded; structured decisions and all metric-bearing fields
remain.
""",
        encoding="utf-8",
    )
    _synthetic_policy_manifest(
        destination, study_kind="COUNTERFACTUAL_POLICY_PROFILE_SWITCH", lane_files=lane_files
    )


def build_public_model_breadth_anonymous_evidence(destination: Path) -> None:
    """Create a replayable anonymous projection of the seven-lane breadth supplement."""

    source = ROOT / "v2" / "public-model-breadth-v1"
    results = source / "results"
    source_receipt = load_object(results / "privacy-receipt.json")
    source_files = {
        path.relative_to(results).as_posix(): sha256_file(path)
        for path in sorted(results.rglob("*"))
        if path.is_file()
        and path.name not in {"failure-cause-addendum.json", "privacy-receipt.json"}
    }
    if (
        source_receipt.get("status") != "POST_EXECUTION_PUBLIC_SAFE_DERIVATIVE"
        or source_receipt.get("derived_files_sha256") != source_files
        or source_receipt.get("terminal_records_validated") != 1260
        or source_receipt.get("raw_final_response_text_included") is not False
        or source_receipt.get("free_form_error_detail_included") is not False
        or source_receipt.get("provider_response_identifiers_included") is not False
        or source_receipt.get("hidden_reasoning_fields_included") is not False
        or source_receipt.get("credentials_included") is not False
    ):
        fail("public model-breadth source is not a sealed public-safe derivative")

    destination.mkdir(parents=True, exist_ok=True)
    for name in ("study-plan.json", "request-schedule.json", "catalog-snapshot.json"):
        value = anonymize_provenance(load_object(source / name))
        write_json(destination / name, value)
    failure_addendum = load_object(results / "failure-cause-addendum.json")
    if (
        failure_addendum.get("status") != "POST_RUN_FROZEN_LOG_AUDIT_COMPLETE"
        or failure_addendum.get("transport_failures") != 630
        or failure_addendum.get("transport_failure_categories")
        != {
            "AUTHORIZATION": 76,
            "CONNECTION": 1,
            "QUOTA_RATE_LIMIT": 547,
            "SERVER": 5,
            "TIMEOUT": 1,
        }
        or failure_addendum.get("quota_cutoff", {}).get("cells") != 547
        or failure_addendum.get("quota_cutoff", {}).get("contiguous_schedule_tail") is not True
        or failure_addendum.get("privacy", {}).get("raw_error_text_included") is not False
    ):
        fail("public model-breadth failure addendum changed")
    write_json(destination / "failure-cause-addendum.json", failure_addendum)

    plan = load_object(destination / "study-plan.json")
    lane_order = plan.get("execution", {}).get("base_lane_order")
    source_lane_files = source_receipt.get("public_lane_files")
    if (
        not isinstance(lane_order, list)
        or len(lane_order) != 7
        or not isinstance(source_lane_files, dict)
        or set(source_lane_files) != {str(value) for value in lane_order}
    ):
        fail("public model-breadth lane map differs from the frozen seven-lane plan")

    run_destination = destination / "runs"
    run_destination.mkdir()
    review_lane_files: dict[str, str] = {}
    review_lane_hashes: dict[str, str] = {}
    review_row_hashes: list[Json] = []
    for lane_value in lane_order:
        lane_id = str(lane_value)
        source_run = results / str(source_lane_files[lane_id])
        rows = [
            json.loads(line)
            for line in source_run.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if (
            len(rows) != 180
            or {str(row.get("lane_id")) for row in rows} != {lane_id}
            or len({str(row.get("item_id")) for row in rows}) != 180
        ):
            fail(f"public model-breadth run coverage changed: {lane_id}")
        review_rows: list[Json] = []
        for row in rows:
            label = f"public model-breadth row {lane_id}:{row.get('item_id')}"
            if any(
                row.get(field) is not None
                for field in ("raw_response_text", "transport_error", "parse_error_detail")
            ):
                fail(f"{label} retains private response or error text")
            if (
                row.get("provider_response_id") is not None
                or row.get("system_fingerprint") is not None
            ):
                fail(f"{label} retains a provider identifier")
            _reject_hidden_reasoning(row, label)
            projected = anonymize_provenance(row)
            review_rows.append(projected)
            review_row_hashes.append(
                {
                    "item_id": projected.get("item_id"),
                    "lane_id": projected.get("lane_id"),
                    "review_row_sha256": sha256_text(canonical_json(projected)),
                    "scientific_fields_unchanged": True,
                }
            )
        target = run_destination / source_run.name
        write_jsonl(target, review_rows)
        review_lane_files[lane_id] = target.relative_to(destination).as_posix()
        review_lane_hashes[lane_id] = sha256_file(target)

    write_jsonl(destination / "review-row-hashes.jsonl", review_row_hashes)

    aggregate = anonymize_provenance(load_object(results / "reported-aggregate.json"))
    aggregate_lanes = aggregate.get("lanes")
    if not isinstance(aggregate_lanes, list):
        fail("public model-breadth aggregate lanes are malformed")
    seen_lanes: set[str] = set()
    for lane in aggregate_lanes:
        if not isinstance(lane, dict):
            fail("public model-breadth aggregate contains a malformed lane")
        lane_id = str(lane.get("lane_id"))
        if lane_id not in review_lane_hashes or lane_id in seen_lanes:
            fail(f"public model-breadth aggregate lane changed: {lane_id}")
        seen_lanes.add(lane_id)
        lane["run_sha256"] = review_lane_hashes[lane_id]
    if seen_lanes != set(review_lane_hashes):
        fail("public model-breadth aggregate omits a frozen lane")
    external = aggregate.get("external_commitment")
    if not isinstance(external, dict):
        fail("public model-breadth aggregate commitment is malformed")
    external["plan_sha256"] = sha256_file(destination / "study-plan.json")
    external["workflow_run_url"] = None
    external["workflow_run_attempt"] = None
    aggregate["source_identity"] = "WITHHELD_DURING_DOUBLE_BLIND_REVIEW"
    scope_limits = aggregate.get("scope_limits")
    service_comparison = aggregate.get("service_comparison")
    if not isinstance(scope_limits, dict) or not isinstance(service_comparison, dict):
        fail("public model-breadth aggregate interpretation fields are malformed")
    scope_limits["breadth_dimension_added"] = "SERVICE_ROUTE_FAILURE_ONLY"
    scope_limits["shared_quota_confound_present"] = True
    service_comparison.update(
        {
            "model_family_comparison_supported": False,
            "route_reliability_comparison_supported": False,
            "scope": "QUOTA_CONFOUNDED_OPERATIONAL_RECORD",
        }
    )
    aggregate["post_run_interpretation"] = deepcopy(failure_addendum["interpretation_boundary"])
    write_json(destination / "reported-aggregate.json", aggregate)

    execution = anonymize_provenance(load_object(results / "execution-receipt.json"))
    if execution.get("status") != "COMPLETE_ALL_FROZEN_CELLS_TERMINAL":
        fail("public model-breadth execution receipt is not complete")
    execution["schema_version"] = "1.0.0-review"
    execution["schedule_sha256"] = load_object(destination / "request-schedule.json")[
        "schedule_sha256"
    ]
    execution["lane_output_sha256"] = {
        Path(review_lane_files[lane_id]).name: review_lane_hashes[lane_id]
        for lane_id in sorted(review_lane_files)
    }
    execution.pop("request_intent_journal_sha256", None)
    execution.pop("terminal_journal_sha256", None)
    execution["source_journal_digests_included"] = False
    execution["source_identity"] = "WITHHELD_DURING_DOUBLE_BLIND_REVIEW"
    write_json(destination / "execution-receipt-review.json", execution)

    readme = """# Frozen service-route reviewer evidence

This directory contains seven frozen service configurations on the known 180-item pair-balanced
public challenge. Each scheduled cell has one terminal outcome and zero client retries. Every
unusable outcome remains incorrect in end-to-end metrics.

The runs retain scoring fields and final-response digests but exclude final-response text,
free-form error detail, provider response identifiers, account identifiers, credentials, and
hidden reasoning. `failure-cause-addendum.json` records a post-run audit of the sealed private
errors: a shared quota/rate-limit condition occupies the final 547 schedule cells. The supplement
therefore supports neither route-reliability comparison nor model-family ranking. The shared
dataset and prompt packet are in the sibling `balanced-public-challenge` evidence directory.
"""
    (destination / "README.md").write_text(readme, encoding="utf-8", newline="\n")

    review_files = {
        path.relative_to(destination).as_posix(): sha256_file(path)
        for path in sorted(destination.rglob("*"))
        if path.is_file() and path.name not in {"MANIFEST.json", "privacy-receipt-review.json"}
    }
    privacy_receipt: Json = {
        "schema_version": "1.0.0-review",
        "status": "ANONYMOUS_PUBLIC_MODEL_BREADTH_DERIVATIVE",
        "source_identity": "WITHHELD_DURING_DOUBLE_BLIND_REVIEW",
        "terminal_records_validated": len(review_row_hashes),
        "raw_final_response_text_included": False,
        "free_form_error_detail_included": False,
        "provider_response_identifiers_included": False,
        "system_fingerprints_included": False,
        "hidden_reasoning_fields_included": False,
        "credentials_included": False,
        "source_row_hashes_included": False,
        "scientific_fields_unchanged": True,
        "model_calls_performed": 0,
        "review_lane_files": review_lane_files,
        "review_lane_files_sha256": review_lane_hashes,
        "review_row_hashes": {
            "path": "review-row-hashes.jsonl",
            "rows": len(review_row_hashes),
            "sha256": sha256_file(destination / "review-row-hashes.jsonl"),
        },
        "review_files_sha256": review_files,
    }
    privacy_receipt["privacy_receipt_sha256"] = sha256_text(canonical_json(privacy_receipt))
    write_json(destination / "privacy-receipt-review.json", privacy_receipt)

    files = {
        path.relative_to(destination).as_posix(): sha256_file(path)
        for path in sorted(destination.rglob("*"))
        if path.is_file() and path.name != "MANIFEST.json"
    }
    manifest: Json = {
        "schema_version": "1.0.0-review",
        "status": "ANONYMOUS_PUBLIC_MODEL_BREADTH_EVIDENCE",
        "file_count": len(files),
        "files": files,
        "lane_files": review_lane_files,
        "scope": {
            "breadth_dimension_added": "SERVICE_ROUTE_FAILURE_ONLY",
            "hidden_generalization_claimed": False,
            "hidden_reasoning_included": False,
            "naturalistic_cases": 0,
            "provider_response_identifiers_included": False,
            "public_known_challenge": True,
            "shared_quota_confound_present": True,
            "source_row_hashes_included": False,
        },
    }
    manifest["manifest_sha256"] = sha256_text(canonical_json(manifest))
    write_json(destination / "MANIFEST.json", manifest)


def anonymize_stronger_results(source: Json) -> Json:
    pilot = source.get("pilot")
    full = source.get("full")
    if not isinstance(pilot, dict) or not isinstance(full, dict):
        fail("unexpected GPT-5.4 result structure")
    pilot_keys = (
        "records",
        "parseable_decisions",
        "transport_errors",
        "gate",
        "raw_action_accuracy",
        "raw_pair_accuracy",
        "raw_flip_rate",
        "routed_provider_values",
        "model_returned_values",
    )
    full_keys = (
        "records",
        "parseable_decisions",
        "decision_coverage",
        "complete_pairs",
        "pair_coverage",
        "raw_correct_decisions",
        "raw_action_accuracy",
        "raw_correct_pairs",
        "raw_pair_accuracy",
        "raw_flip_rate",
        "false_promotions",
        "invalid_promotion_trials",
        "raw_false_promotion_rate",
        "valid_promotions",
        "valid_promotion_trials",
        "raw_valid_promotion_rate",
        "status_counts",
        "raw_action_distribution",
        "postgate_action_distribution",
        "single_nonparseable_case",
        "routed_provider_values",
        "model_returned_values",
    )
    return {
        "schema_version": "1.0.0-review",
        "study_kind": "POST_PROTOCOL_GPT54_PUBLIC_DEVELOPMENT_FOLLOWUP",
        "source_identity": "WITHHELD_DURING_DOUBLE_BLIND_REVIEW",
        "interpretation_boundary": source.get("interpretation_boundary"),
        "pilot": {key: pilot[key] for key in pilot_keys},
        "full": {key: full[key] for key in full_keys},
        "raw_prompts_or_responses_in_summary": False,
    }


def minimal_pyproject() -> str:
    return """[build-system]
requires = ["setuptools>=75", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "claimpromote-bench-anonymous-review"
version = "0.1.0"
description = "Anonymous public-data validation bundle"
requires-python = ">=3.11"
license = { file = "LICENSE" }
dependencies = ["jsonschema>=4.23,<5"]

[project.optional-dependencies]
test = ["pytest>=8.3,<10", "pytest-cov>=6,<8"]

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra"

[tool.coverage.run]
branch = true
source = ["claimpromotebench"]
"""


def anonymous_license() -> str:
    source = (ROOT / "LICENSE").read_text(encoding="utf-8")
    lines = source.splitlines()
    copyright_indexes = [
        index for index, line in enumerate(lines) if line.startswith("Copyright (c) ")
    ]
    if len(copyright_indexes) != 1:
        fail("source LICENSE must contain exactly one copyright notice")
    lines[copyright_indexes[0]] = "Copyright (c) 2026 Anonymous Authors"
    return "\n".join(lines) + "\n"


def review_readme() -> str:
    return """# ClaimPromoteBench anonymous reviewer bundle

This focused bundle contains the material needed to replay the paper: the public controlled
benchmark, executable and Lean fixtures, the reviewer-release r6 data, the pair-balanced public
challenge, the SLSA-derived portability study, the counterfactual policy-switch study, and
item-level scoring records. It
contains no Git history, author metadata, public repository link, private construction seed,
human-subject record, or public workflow identifier.

## Reproduce the review environment

```bash
python -m pip install --require-hashes -r requirements-review.lock
python -m pip install --no-deps -e .
python scripts/run_review_checks.py
```

The default command uses the staged files to validate the public alpha benchmark, verify all 20
controlled-pair contracts, run shortcut, invariance, executable, empirical-evidence,
naturalistic-freeze, and selected pytest checks, then build and check the Lean fixtures. It fails
if `lake` is missing.
Use `--python-only` for an explicitly partial replay when Lean is unavailable.

The evidence directory retains the r6 300-item hidden realization, frozen baseline, projected
records, and analysis; the 180-item public challenge; and both 120-item software-supply-chain
studies. The balanced-challenge records retain the model's final JSON text and sanitized error text
for parser audit. The newer studies retain structured decisions but omit raw response text and
free-form provider errors. Provider account and response identifiers, credentials, author
provenance, and hidden reasoning are excluded.

## Scope limitation

The private deterministic-construction seed remains excluded because the released dataset bytes,
prompt packet, labels, records, and commitments suffice for result recomputation. The r6
construction manifest remains byte-frozen. Its stale `CFM_R5` namespace label and
three construction-time `PENDING` values are corrected by a bound overlay; all released r6 item
and pair IDs use the `v1-test-cfo-*` namespace. The original manifest is not rewritten because its
digest is bound by C1 and C2. Provider hidden-thinking blocks are excluded from the r6 derivative,
and a redaction receipt records the post-C2 publication boundary and score-equivalence check.

The challenge is pair-balanced and non-ALLOW-balanced, with gold support 90/30/30/30; it is not a
four-class-balanced hidden test. Its service stacks differ, so their outcomes do not form a causal
model ablation. Every unusable r6 or challenge response remains in the registered denominator. The
top-level manifest records the generated tree's actual file count.

The SLSA-derived study tests protocol portability to a second authored policy ontology. The
policy-switch study then holds evidence and states fixed while changing only the applicable
published policy profile. SLSA and in-toto ground the evidence vocabulary; all transition rules,
profiles, and labels remain author-defined. These studies are not standards certification,
naturalistic deployment estimates, or between-route causal comparisons. Every scheduled failure
remains in the end-to-end denominator.

The frozen naturalistic-candidate pool contains 12 source pointers. Source-level review created
zero benchmark cases and made zero model calls because the records lacked the time-stamped
execution, dependency, runtime, provenance, and licensing evidence required for a defensible
author-policy mapping. This is an inclusion decision, not a naturalistic evaluation result; no
human annotators, human gold labels, or agreement statistic are claimed.

Post-gate correctness applies the same fixed policy as the benchmark oracle. It must not be
interpreted as model learning or independent prediction accuracy.
"""


def review_validator() -> str:
    return r'''#!/usr/bin/env python3
"""Validate anonymous compact v1/v2 result summaries."""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
V1 = ROOT / "results" / "v1-paper-results.json"
V2 = ROOT / "results" / "v2-public-pilot-study.json"
V3 = ROOT / "results" / "v2-gpt54-public-dev-followup.json"
MODELS = ("0.6B", "1.7B")
ARMS = ("narrative", "ledger", "ledger_verifier", "ledger_verifier_gate")
SEEDS = (104729, 130363, 169087)
EXPECTED_ERRORS = {
    ("0.6B", "narrative"): 900,
    ("0.6B", "ledger"): 261,
    ("0.6B", "ledger_verifier"): 335,
    ("0.6B", "ledger_verifier_gate"): 585,
    ("1.7B", "narrative"): 900,
    ("1.7B", "ledger"): 900,
    ("1.7B", "ledger_verifier"): 900,
    ("1.7B", "ledger_verifier_gate"): 546,
}


def fail(message: str) -> None:
    raise SystemExit(f"review-results: {message}")


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        fail(f"{path.name} is not a JSON object")
    return value


def close(observed: Any, expected: float, label: str) -> None:
    if not isinstance(observed, (int, float)) or isinstance(observed, bool):
        fail(f"{label} is not numeric")
    if not math.isclose(float(observed), expected, rel_tol=0.0, abs_tol=1e-12):
        fail(f"{label}: expected {expected}, got {observed}")


def validate_v1(value: dict[str, Any]) -> None:
    runs = value.get("runs")
    if not isinstance(runs, list) or len(runs) != 24:
        fail("v1 summary must contain 24 runs")
    seen: set[tuple[str, str, int]] = set()
    errors: Counter[tuple[str, str]] = Counter()
    python_versions: Counter[str] = Counter()
    total_errors = 0
    total_parseable = 0
    gate_cov: dict[str, list[float]] = defaultdict(list)
    gate_pair_cov: dict[str, list[float]] = defaultdict(list)
    for row in runs:
        identity = (str(row["m"]), str(row["a"]), int(row["s"]))
        if identity in seen:
            fail(f"duplicate v1 run: {identity}")
        seen.add(identity)
        format_errors = int(row["fe"])
        parseable = 300 - format_errors
        close(row["cov"], parseable / 300, f"{identity}.coverage")
        total_errors += format_errors
        total_parseable += parseable
        errors[(identity[0], identity[1])] += format_errors
        python_versions[str(row["py"])] += 1
        if parseable:
            close(row["fpr"], 1.0, f"{identity}.raw_fpr")
            close(row["vpr"], 1.0, f"{identity}.raw_vpr")
            close(row["pta"], 0.0, f"{identity}.raw_pta")
            if identity[1] == "ledger_verifier_gate":
                close(row["efpr"], 0.0, f"{identity}.effective_fpr")
                close(row["epta"], 1.0, f"{identity}.effective_pta")
                gate_cov[identity[0]].append(float(row["cov"]))
                gate_pair_cov[identity[0]].append(float(row["pcov"]))
        elif any(row.get(key) is not None for key in ("fpr", "vpr", "pta")):
            fail(f"undefined v1 rates are populated: {identity}")
    expected = {(model, arm, seed) for model in MODELS for arm in ARMS for seed in SEEDS}
    if seen != expected:
        fail("v1 run matrix is incomplete")
    if dict(errors) != EXPECTED_ERRORS:
        fail("v1 model/arm format-error totals changed")
    if (total_errors, total_parseable) != (5327, 1873):
        fail("v1 headline totals changed")
    if python_versions != Counter({"3.11.15": 21, "3.11.16": 3}):
        fail("v1 Python identity distribution changed")
    expected_ranges = {
        "0.6B": ((0.14, 0.49), (0.07333333333333333, 0.35333333333333333)),
        "1.7B": ((0.21666666666666667, 0.48333333333333334), (0.1, 0.38)),
    }
    for model, (coverage, pair_coverage) in expected_ranges.items():
        if (min(gate_cov[model]), max(gate_cov[model])) != coverage:
            fail(f"v1 {model} gate coverage range changed")
        if (min(gate_pair_cov[model]), max(gate_pair_cov[model])) != pair_coverage:
            fail(f"v1 {model} gate pair-coverage range changed")


def validate_v2(value: dict[str, Any]) -> None:
    if value.get("aggregate_status_counts") != {"OK": 108, "SCHEMA_ERROR": 52}:
        fail("v2 aggregate status counts changed")
    protocol = value.get("protocol")
    if not isinstance(protocol, dict) or protocol.get("total_decisions") != 160:
        fail("v2 protocol changed")
    runs = value.get("runs")
    if not isinstance(runs, list) or len(runs) != 4:
        fail("v2 must contain four run summaries")
    expected = {
        ("Qwen/Qwen3-0.6B", "free"): (0.75, 0.70, 30),
        ("Qwen/Qwen3-0.6B", "json_schema"): (1.0, 1.0, 40),
        ("Qwen/Qwen3-1.7B", "free"): (0.0, 0.0, 0),
        ("Qwen/Qwen3-1.7B", "json_schema"): (0.95, 0.90, 38),
    }
    constrained_ok = 0
    constrained_pairs = 0
    for row in runs:
        identity = (str(row["model_id"]), str(row["decoding_mode"]))
        if identity not in expected:
            fail(f"unexpected v2 run: {identity}")
        summary = row["summary"]
        coverage, pair_coverage, ok = expected[identity]
        close(summary["decision_coverage"], coverage, f"{identity}.coverage")
        close(summary["pair_coverage"], pair_coverage, f"{identity}.pair_coverage")
        if int(summary["status_counts"]["OK"]) != ok:
            fail(f"{identity} OK count changed")
        if ok:
            close(summary["raw_action_accuracy"], 0.5, f"{identity}.raw_accuracy")
            close(summary["raw_pair_accuracy"], 0.0, f"{identity}.pair_accuracy")
            close(summary["raw_flip_rate"], 0.0, f"{identity}.flip_rate")
            close(summary["raw_fpr"], 1.0, f"{identity}.raw_fpr")
            close(summary["raw_vpr"], 1.0, f"{identity}.raw_vpr")
        if identity[1] == "json_schema":
            constrained_ok += ok
            constrained_pairs += int(summary["covered_pairs"])
    if (constrained_ok, constrained_pairs) != (78, 38):
        fail("v2 constrained headline counts changed")


def validate_v3(value: dict[str, Any]) -> None:
    pilot = value.get("pilot")
    full = value.get("full")
    if not isinstance(pilot, dict) or not isinstance(full, dict):
        fail("GPT-5.4 follow-up summary is malformed")
    if (pilot.get("records"), pilot.get("parseable_decisions"), pilot.get("gate")) != (
        12,
        12,
        "GO",
    ):
        fail("GPT-5.4 pilot headline counts changed")
    expected_full = {
        "records": 100,
        "parseable_decisions": 99,
        "complete_pairs": 49,
        "raw_correct_decisions": 99,
        "raw_correct_pairs": 49,
        "false_promotions": 0,
        "invalid_promotion_trials": 49,
        "valid_promotions": 50,
        "valid_promotion_trials": 50,
    }
    for key, expected in expected_full.items():
        if full.get(key) != expected:
            fail(f"GPT-5.4 full result changed: {key}")
    close(full.get("decision_coverage"), 0.99, "GPT-5.4 decision coverage")
    close(full.get("pair_coverage"), 0.98, "GPT-5.4 pair coverage")
    for key in ("raw_action_accuracy", "raw_pair_accuracy", "raw_flip_rate"):
        close(full.get(key), 1.0, f"GPT-5.4 {key}")
    if full.get("status_counts") != {"OK": 99, "SCHEMA_ERROR": 1}:
        fail("GPT-5.4 status counts changed")
    if full.get("raw_action_distribution") != {
        "ALLOW": 50,
        "HOLD": 45,
        "DEMOTE": 2,
        "ESCALATE": 2,
    }:
        fail("GPT-5.4 action distribution changed")
    if full.get("routed_provider_values") != ["OpenAI"]:
        fail("GPT-5.4 routed provider changed")


def main() -> int:
    validate_v1(load(V1))
    validate_v2(load(V2))
    validate_v3(load(V3))
    print("review-results: PASS (v1 7,200; v2 160; GPT-5.4 100 decisions)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def review_runner() -> str:
    return r'''#!/usr/bin/env python3
"""Run public anonymous-review checks."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON_COMMANDS = [
    [sys.executable, "-m", "claimpromotebench", "validate", "data/alpha"],
    [
        sys.executable,
        "scripts/audit_public_pair_contracts.py",
        "--dataset",
        "data/alpha",
        "--out",
        "work/public-pair-contract-audit.json",
    ],
    [
        sys.executable,
        "-m",
        "claimpromotebench.shortcuts",
        "--dataset",
        "data/alpha",
        "--out",
        "work/shortcut-audit.json",
    ],
    [
        sys.executable,
        "-m",
        "claimpromotebench.invariance",
        "--dataset",
        "data/alpha",
        "--out",
        "work/invariance-audit.json",
    ],
    [
        sys.executable,
        "-m",
        "claimpromotebench.executable",
        "--fixtures",
        "fixtures/executable",
        "--out",
        "work/executable-fixtures.json",
    ],
    [sys.executable, "scripts/validate_anonymous_empirical_evidence.py"],
    [
        sys.executable,
        "scripts/validate_v2_naturalistic_candidates.py",
        "--registry",
        "v2/naturalistic-sources.json",
        "--pool",
        "v2/naturalistic-candidates.json",
        "--out",
        "work/naturalistic-candidate-validation.json",
    ],
    [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "tests/test_v2.py",
        "tests/test_v2_naturalistic.py",
    ],
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--python-only",
        action="store_true",
        help="run a partial replay without the pinned Lean checks",
    )
    args = parser.parse_args()
    (ROOT / "work").mkdir(exist_ok=True)
    env = os.environ.copy()
    package_root = str(ROOT / "src")
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        package_root + os.pathsep + existing_pythonpath
        if existing_pythonpath
        else package_root
    )
    for command in PYTHON_COMMANDS:
        print("+", " ".join(command), flush=True)
        subprocess.run(command, cwd=ROOT, check=True, env=env)
    if args.python_only:
        print("anonymous-review-checks: PARTIAL_PASS (Python only; Lean explicitly skipped)")
        return 0

    lake = shutil.which("lake")
    if lake is None:
        raise SystemExit(
            "anonymous-review-checks: lake is required for full replay; "
            "install Lean or pass --python-only for a partial replay"
        )
    formal_root = ROOT / "data" / "alpha"
    formal_commands = [
        [lake, "build"],
        [lake, "env", "leanchecker", "ClaimPromoteFormal"],
        [
            sys.executable,
            "-m",
            "claimpromotebench.formal",
            "--dataset",
            "data/alpha",
            "--fixtures",
            "fixtures/formal/cases.json",
            "--out",
            "work/formal-fixtures.json",
        ],
    ]
    for command in formal_commands:
        print("+", " ".join(command), flush=True)
        cwd = formal_root if command[0] == lake else ROOT
        subprocess.run(command, cwd=cwd, check=True, env=env)
    print("anonymous-review-checks: PASS (Python and Lean)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def scan_identity(bundle: Path) -> None:
    findings: list[str] = []
    for path in sorted(bundle.rglob("*")):
        if not path.is_file():
            continue
        relative_text = path.relative_to(bundle).as_posix()
        for token in sorted(FORBIDDEN_TEXT):
            if token.lower() in relative_text.lower():
                findings.append(f"{relative_text}: filename contains {token}")
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in TEXT_NAMES:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for token in sorted(FORBIDDEN_TEXT):
            if token.lower() in text.lower():
                findings.append(f"{path.relative_to(bundle)}: {token}")
        for label, pattern in FORBIDDEN_CREDENTIAL_PATTERNS.items():
            if pattern.search(text):
                findings.append(f"{path.relative_to(bundle)}: possible {label}")
        for label, pattern in FORBIDDEN_PROVIDER_RESPONSE_PATTERNS.items():
            if pattern.search(text):
                findings.append(f"{path.relative_to(bundle)}: possible {label}")
        for label, (pattern, _replacement) in SENSITIVE_PROVENANCE_REPLACEMENTS.items():
            if pattern.search(text):
                findings.append(f"{path.relative_to(bundle)}: possible {label}")
    if findings:
        fail("identity/provenance leak detected:\n" + "\n".join(findings))


def scan_sensitive_payloads(bundle: Path) -> None:
    """Reject retained provider IDs and machine-readable hidden-reasoning content."""

    def inspect(value: Any, label: str) -> None:
        if isinstance(value, dict):
            hidden_keys = {
                "reasoning_content",
                "thinking",
                "thinking_content",
                "thought",
                "thoughts",
            }
            overlap = hidden_keys & set(value)
            if overlap:
                fail(f"{label}: hidden-reasoning fields survived: {sorted(overlap)}")
            if str(value.get("type", "")).lower() in {"reasoning", "thinking"}:
                fail(f"{label}: hidden-reasoning content block survived")
            for key in ("provider_response_id", "provider_request_id"):
                if value.get(key) not in (None, ""):
                    fail(f"{label}: retained {key}")
            for child in value.values():
                inspect(child, label)
        elif isinstance(value, list):
            for child in value:
                inspect(child, label)

    for path in sorted(bundle.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(bundle)
        label = relative.as_posix()
        if "schemas" in relative.parts or path.name.endswith(".schema.json"):
            # Schema property names document the record contract; they are not retained values.
            # Literal identifiers in schema examples remain covered by the text-pattern scan.
            continue
        if path.suffix == ".json":
            inspect(json.loads(path.read_text(encoding="utf-8")), label)
        elif path.suffix == ".jsonl":
            for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if line.strip():
                    inspect(json.loads(line), f"{label}:{index}")


def verify_bundle(bundle: Path) -> None:
    manifest_path = bundle / "MANIFEST.json"
    if not manifest_path.is_file():
        fail("MANIFEST.json is missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or not isinstance(manifest.get("files"), dict):
        fail("MANIFEST.json does not contain a file map")

    declared = manifest["files"]
    if manifest.get("file_count") != len(declared):
        fail("MANIFEST.json file_count differs from its generated file map")
    actual_paths = {
        str(path.relative_to(bundle)).replace("\\", "/"): path
        for path in sorted(bundle.rglob("*"))
        if path.is_file() and path != manifest_path
    }
    if set(declared) != set(actual_paths):
        missing = sorted(set(declared) - set(actual_paths))
        extra = sorted(set(actual_paths) - set(declared))
        fail(f"manifest coverage mismatch; missing={missing}, extra={extra}")

    for relative, path in actual_paths.items():
        if should_skip(Path(relative)):
            fail(f"generated or excluded file survived staging: {relative}")
        if declared[relative] != sha256_file(path):
            fail(f"manifest digest mismatch: {relative}")

    required = {
        "DATA_LICENSE.md",
        "LICENSE",
        "README.md",
        "THIRD_PARTY_NOTICES.md",
        "docs/PUBLIC_RELEASE_BOUNDARY.md",
        "pyproject.toml",
        "requirements-review.lock",
        "evidence/fresh-confirmatory/MANIFEST.json",
        "evidence/fresh-confirmatory/frozen-manifest-metadata-correction.json",
        "evidence/fresh-confirmatory/redaction-receipt-review.json",
        "evidence/fresh-confirmatory/reported-analysis.json",
        "evidence/fresh-confirmatory/runs/opencode-go-deepseek-v4-flash-matched.jsonl",
        "evidence/fresh-confirmatory/runs/opencode-go-qwen3.7-max.jsonl",
        "evidence/balanced-public-challenge/MANIFEST.json",
        "evidence/balanced-public-challenge/privacy-receipt-review.json",
        "evidence/balanced-public-challenge/reported-aggregate.json",
        "evidence/balanced-public-challenge/runs/opencode-go-deepseek-v4-flash-matched-full.jsonl",
        "evidence/balanced-public-challenge/runs/opencode-go-qwen3.7-max-full.jsonl",
        "evidence/slsa-portability/MANIFEST.json",
        "evidence/slsa-portability/execution-receipt.json",
        "evidence/slsa-portability/reported-aggregate.json",
        "evidence/slsa-portability/void-exclusion-receipt.json",
        "evidence/policy-switch/MANIFEST.json",
        "evidence/policy-switch/execution-receipt.json",
        "evidence/policy-switch/reported-aggregate.json",
        "v2/naturalistic-candidates.json",
        "v2/naturalistic-review-decision.json",
        "v2/naturalistic-sources.json",
    }
    if (bundle / "evidence" / "public-model-breadth").exists():
        fail("excluded seven-route evidence survived anonymous staging")
    absent = sorted(required - set(actual_paths))
    if absent:
        fail(f"required reviewer-bundle files are missing: {absent}")

    excluded = {
        "configs/decoding-v1.json",
        "scripts/aggregate_capable_hidden_study.py",
        "scripts/analyze_stronger_model_study.py",
        "scripts/build_v1_dataset.py",
        "src/claimpromotebench/review.py",
        "src/claimpromotebench/review_analysis.py",
        "scripts/validate_v1_plan.py",
        "scripts/validate_v1_public_dev_freeze.py",
    }
    survived = sorted(excluded & set(actual_paths))
    if survived:
        fail(f"unused human-review workflow files survived staging: {survived}")
    scan_identity(bundle)
    scan_sensitive_payloads(bundle)


def write_manifest(bundle: Path) -> None:
    files = {
        str(path.relative_to(bundle)).replace("\\", "/"): sha256_file(path)
        for path in sorted(bundle.rglob("*"))
        if path.is_file() and path != bundle / "MANIFEST.json"
    }
    fresh_confirmatory_included = (bundle / "evidence" / "fresh-confirmatory").is_dir()
    balanced_challenge_included = (bundle / "evidence" / "balanced-public-challenge").is_dir()
    slsa_portability_included = (bundle / "evidence" / "slsa-portability").is_dir()
    policy_switch_included = (bundle / "evidence" / "policy-switch").is_dir()
    manifest = {
        "schema_version": "1.0.0-review",
        "status": "ANONYMOUS_REVIEW_BUNDLE",
        "file_count": len(files),
        "files": files,
        "scope": {
            "public_alpha_included": True,
            "reviewer_release_hidden_data_included": True,
            "human_subject_study_records_included": False,
            "public_repository_identity_included": False,
            "item_level_empirical_records_included": True,
            "legacy_v1_evidence_included": False,
            "public_pilot_evidence_included": False,
            "gpt54_public_development_evidence_included": False,
            "capable_hidden_evidence_included": False,
            "fresh_confirmatory_summary_included": fresh_confirmatory_included,
            "fresh_confirmatory_item_level_records_included": fresh_confirmatory_included,
            "fresh_confirmatory_hidden_reasoning_included": False,
            "balanced_public_challenge_summary_included": balanced_challenge_included,
            "balanced_public_challenge_item_level_records_included": (balanced_challenge_included),
            "balanced_public_challenge_hidden_reasoning_included": False,
            "slsa_portability_summary_included": slsa_portability_included,
            "slsa_portability_item_level_records_included": slsa_portability_included,
            "slsa_portability_raw_response_text_included": False,
            "slsa_portability_void_raw_records_included": False,
            "policy_switch_summary_included": policy_switch_included,
            "policy_switch_item_level_records_included": policy_switch_included,
            "policy_switch_raw_response_text_included": False,
            "ontology_count": 2,
            "policy_instrument_count": 4,
            "public_model_breadth_summary_included": False,
            "public_model_breadth_item_level_records_included": False,
            "public_model_breadth_raw_final_response_text_included": False,
            "public_model_breadth_hidden_reasoning_included": False,
            "provider_response_identifiers_included": False,
            "private_construction_seed_included": False,
        },
    }
    (bundle / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def project_python_module(source_path: Path, roots: set[str], description: str) -> str:
    """Return the transitive function closure needed by ``roots``.

    Reviewer code should not carry archived study implementations merely because the private
    validator imports them. The projection retains only referenced imports, constants, and local
    helpers, and deliberately omits CLI entry points and unrelated module-level side effects.
    """

    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(source_path))
    functions = {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    missing = roots - set(functions)
    if missing:
        fail(f"Python projection roots are missing from {source_path}: {sorted(missing)}")

    selected_functions: set[str] = set()
    pending = list(roots)
    while pending:
        name = pending.pop()
        if name in selected_functions:
            continue
        selected_functions.add(name)
        loaded = {
            node.id
            for node in ast.walk(functions[name])
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
        }
        pending.extend(sorted((loaded & set(functions)) - selected_functions))

    selected_nodes: list[ast.stmt] = [functions[name] for name in selected_functions]
    loaded_names = {
        node.id
        for selected in selected_nodes
        for node in ast.walk(selected)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
    }

    assignments: list[ast.Assign | ast.AnnAssign] = []
    for node in tree.body:
        target: ast.expr | None = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
        elif isinstance(node, ast.AnnAssign):
            target = node.target
        if isinstance(target, ast.Name) and target.id in loaded_names:
            assignments.append(node)
    loaded_names.update(
        node.id
        for assignment in assignments
        for node in ast.walk(assignment)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
    )

    imports: list[ast.stmt] = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            aliases = [
                alias
                for alias in node.names
                if (alias.asname or alias.name.split(".")[0]) in loaded_names
            ]
            if aliases:
                imports.append(ast.Import(names=aliases))
        elif isinstance(node, ast.ImportFrom):
            if node.module == "__future__":
                imports.append(node)
                continue
            aliases = [
                alias for alias in node.names if (alias.asname or alias.name) in loaded_names
            ]
            if aliases:
                imports.append(ast.ImportFrom(module=node.module, names=aliases, level=node.level))

    body: list[ast.stmt] = [
        ast.Expr(value=ast.Constant(value=description)),
        *imports,
        *assignments,
        *sorted(selected_nodes, key=lambda node: node.lineno),
    ]
    projected = ast.unparse(ast.fix_missing_locations(ast.Module(body=body, type_ignores=[])))
    return "#!/usr/bin/env python3\n" + projected.rstrip() + "\n"


def paper_balanced_analyzer() -> str:
    return project_python_module(
        ROOT / "scripts" / "analyze_balanced_public_challenge.py",
        {"derive_reporting_metrics"},
        "Minimal balanced-challenge metrics used by the anonymous reviewer replay.",
    )


def paper_empirical_validator() -> str:
    """Project the shared validator onto the four paper-facing empirical studies."""

    projected = project_python_module(
        ROOT / "scripts" / "validate_anonymous_empirical_evidence.py",
        {
            "validate_fresh_confirmatory",
            "validate_balanced_public_challenge",
            "validate_slsa_portability",
            "validate_policy_switch",
        },
        "Recompute the four paper-facing studies from anonymous item-level records.",
    ).rstrip()
    main = """

def main() -> int:
    result = {
        "status": "PASS",
        "fresh_confirmatory": validate_fresh_confirmatory(),
        "balanced_public_challenge": validate_balanced_public_challenge(),
        "slsa_portability": validate_slsa_portability(),
        "policy_switch": validate_policy_switch(),
    }
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
"""
    projected += main
    forbidden = (
        "aggregate_capable_hidden_study",
        "analyze_stronger_model_study",
        "def validate_capable_hidden",
        "def validate_public_model_breadth",
        "def validate_v1_",
        "public-model-breadth",
        "quota/rate-limit",
        "1,260",
        "78/1,260",
    )
    if any(token in projected for token in forbidden):
        fail("excluded study code leaked into projected empirical validator")
    return projected


def build(destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)

    for directory in ("src/claimpromotebench", "data/alpha", "policies", "schemas", "fixtures"):
        copy_tree(ROOT / directory, destination / directory)

    selected_files = (
        "DATA_LICENSE.md",
        "LICENSE",
        "THIRD_PARTY_NOTICES.md",
        "docs/PUBLIC_RELEASE_BOUNDARY.md",
        "scripts/analyze_confirmatory_hidden_study.py",
        "scripts/audit_public_pair_contracts.py",
        "scripts/build_alpha.py",
        "scripts/build_v2_naturalistic_candidates.py",
        "scripts/validate_v2_naturalistic_candidates.py",
        "tests/test_v2.py",
        "tests/test_v2_naturalistic.py",
        "v2/naturalistic-candidates.json",
        "v2/naturalistic-review-decision.json",
        "v2/naturalistic-sources.json",
        "v2/schemas/slsa-agent-decision.schema.json",
        "v2/schemas/run-record-v2.schema.json",
        "v2/schemas/stronger-model-run-record.schema.json",
    )
    for relative in selected_files:
        copy_file(ROOT / relative, destination / relative)
    validator_path = destination / "scripts" / "validate_anonymous_empirical_evidence.py"
    validator_path.parent.mkdir(parents=True, exist_ok=True)
    validator_path.write_text(paper_empirical_validator(), encoding="utf-8", newline="\n")
    (destination / "scripts" / "analyze_balanced_public_challenge.py").write_text(
        paper_balanced_analyzer(), encoding="utf-8", newline="\n"
    )
    copy_file(
        ROOT / "release" / "requirements-review.lock",
        destination / "requirements-review.lock",
    )

    (destination / "LICENSE").write_text(anonymous_license(), encoding="utf-8", newline="\n")

    rewrite_alpha_manifest(destination)

    empirical_sources = {
        "fresh-confirmatory": (
            ROOT / "release" / "reviewer-evidence-source" / "fresh-confirmatory"
        ),
    }
    for name, source in empirical_sources.items():
        evidence_destination = destination / "evidence" / name
        if name == "fresh-confirmatory":
            build_fresh_confirmatory_anonymous_evidence(source, evidence_destination)
        else:
            copy_anonymized_tree(source, evidence_destination)
    build_balanced_public_anonymous_evidence(destination / "evidence" / "balanced-public-challenge")
    build_slsa_portability_anonymous_evidence(destination / "evidence" / "slsa-portability")
    build_policy_switch_anonymous_evidence(destination / "evidence" / "policy-switch")
    (destination / "pyproject.toml").write_text(minimal_pyproject(), encoding="utf-8")
    (destination / "README.md").write_text(review_readme(), encoding="utf-8")
    (destination / "scripts" / "run_review_checks.py").write_text(review_runner(), encoding="utf-8")

    scan_identity(destination)
    scan_sensitive_payloads(destination)
    write_manifest(destination)
    scan_identity(destination)
    scan_sensitive_payloads(destination)
    verify_bundle(destination)


def main() -> int:
    parser = argparse.ArgumentParser()
    destination_group = parser.add_mutually_exclusive_group(required=True)
    destination_group.add_argument("--out", type=Path)
    destination_group.add_argument("--verify", type=Path)
    args = parser.parse_args()
    if args.verify is not None:
        destination = args.verify.resolve()
        if not destination.is_dir():
            fail(f"bundle directory does not exist: {destination}")
        verify_bundle(destination)
        print(json.dumps({"status": "PASS", "verified": str(destination)}, sort_keys=True))
        return 0

    if args.out is None:
        fail("--out is required when not verifying")
    destination = args.out.resolve()
    build(destination)
    print(
        json.dumps(
            {
                "status": "PASS",
                "output": str(destination),
                "manifest_sha256": sha256_file(destination / "MANIFEST.json"),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
