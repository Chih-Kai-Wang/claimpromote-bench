#!/usr/bin/env python3
"""Fail-closed preflight for the frozen ClaimPromoteBench v1 model study."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_CONFIGS = (
    ROOT / "configs" / "models" / "qwen3-0.6b.json",
    ROOT / "configs" / "models" / "qwen3-1.7b.json",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected object in {path}")
    return value


def command_output(command: list[str], *, cwd: Path | None = None) -> str | None:
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or result.stderr.strip() or None


def hardware_summary() -> dict[str, Any]:
    accelerator: dict[str, str] = {}
    probes = {
        "nvidia_smi": ["nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader"],
        "rocminfo": ["rocminfo"],
        "vulkaninfo": ["vulkaninfo", "--summary"],
    }
    for name, command in probes.items():
        output = command_output(command)
        if output:
            accelerator[name] = output[:4000]
    return {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python": platform.python_version(),
        "logical_cpu_count": os.cpu_count(),
        "accelerator_probe": accelerator,
    }


def check_model(config_path: Path, model_dir: Path) -> tuple[dict[str, Any], list[str]]:
    config = load_json(config_path)
    failures: list[str] = []
    filename = Path(str(config["weights_file"])).name
    path = model_dir / filename
    observed_hash: str | None = None
    if not path.is_file():
        failures.append(f"missing model file: {path}")
    else:
        observed_hash = sha256_file(path)
        expected_hash = str(config["artifact_sha256"])
        if observed_hash != expected_hash:
            failures.append(
                f"model hash mismatch for {filename}: expected {expected_hash}, got {observed_hash}"
            )
    return (
        {
            "config": str(config_path.relative_to(ROOT)).replace("\\", "/"),
            "model_id": config["model_id"],
            "revision": config["revision"],
            "quantization": config["quantization"],
            "weights_file": filename,
            "expected_sha256": config["artifact_sha256"],
            "observed_sha256": observed_hash,
            "present": path.is_file(),
        },
        failures,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--llama-dir", type=Path, required=True)
    parser.add_argument("--model-config", type=Path, action="append")
    parser.add_argument("--out", type=Path, default=ROOT / "work" / "v1-model-preflight.json")
    args = parser.parse_args()

    model_configs = tuple(args.model_config or DEFAULT_MODEL_CONFIGS)
    if not model_configs:
        raise RuntimeError("at least one model config is required")

    failures: list[str] = []
    model_reports: list[dict[str, Any]] = []
    runtime_commits = {str(load_json(path)["backend_commit"]) for path in model_configs}
    if len(runtime_commits) != 1:
        failures.append("selected model configs do not agree on one frozen llama.cpp commit")
    expected_runtime = next(iter(runtime_commits)) if len(runtime_commits) == 1 else None

    observed_runtime = command_output(["git", "rev-parse", "HEAD"], cwd=args.llama_dir)
    if observed_runtime is None:
        failures.append(f"cannot resolve llama.cpp git commit in {args.llama_dir}")
    elif expected_runtime is not None and observed_runtime != expected_runtime:
        failures.append(
            "llama.cpp commit mismatch: "
            f"expected {expected_runtime}, got {observed_runtime}"
        )

    for config_path in model_configs:
        report, model_failures = check_model(config_path, args.model_dir)
        model_reports.append(report)
        failures.extend(model_failures)

    report = {
        "schema_version": "1.0.0",
        "status": "PASS" if not failures else "FAIL",
        "runtime": {
            "backend": "llama.cpp",
            "expected_commit": expected_runtime,
            "observed_commit": observed_runtime,
            "directory": str(args.llama_dir),
        },
        "models": model_reports,
        "hardware": hardware_summary(),
        "failures": failures,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
