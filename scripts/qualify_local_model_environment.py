#!/usr/bin/env python3
"""Download, pin, and smoke-test the preselected local MLX model snapshots."""

from __future__ import annotations

import argparse
import gc
import importlib.metadata
import json
import platform
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import mlx.core as mx  # noqa: E402
from huggingface_hub import snapshot_download  # noqa: E402
from local_model_replication import CATALOG_PATH, load_catalog  # noqa: E402
from mlx_lm import generate, load  # noqa: E402
from mlx_lm.sample_utils import make_sampler  # noqa: E402

from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]


def fail(message: str) -> None:
    raise SystemExit(f"local-model-qualification: {message}")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def self_digest(value: Json) -> str:
    payload = {key: child for key, child in value.items() if key != "self_digest"}
    return sha256_bytes(canonical_json(payload).encode("utf-8"))


def sysctl_value(name: str) -> str | None:
    process = subprocess.run(
        ["sysctl", "-n", name],
        check=False,
        capture_output=True,
        text=True,
    )
    value = process.stdout.strip()
    return value if process.returncode == 0 and value else None


def package_versions() -> Json:
    names = (
        "mlx-lm",
        "mlx",
        "mlx-metal",
        "transformers",
        "tokenizers",
        "huggingface-hub",
        "hf-xet",
        "safetensors",
        "numpy",
    )
    versions: Json = {}
    for name in names:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    return versions


def snapshot_files(snapshot: Path) -> tuple[list[Json], int]:
    records: list[Json] = []
    total_bytes = 0
    for path in sorted(snapshot.rglob("*")):
        if not path.is_file() or ".cache" in path.parts:
            continue
        size = path.stat().st_size
        total_bytes += size
        records.append(
            {
                "path": path.relative_to(snapshot).as_posix(),
                "sha256": sha256_file(path),
                "size_bytes": size,
            }
        )
    if not records:
        fail(f"model snapshot is empty: {snapshot.name}")
    return records, total_bytes


def qualify(catalog_path: Path) -> tuple[Json, Json]:
    catalog = load_catalog(catalog_path)
    snapshots: list[Json] = []
    qualifications: list[Json] = []
    sampler = make_sampler(temp=0.0, top_p=0.0)
    smoke_prompt = "Return exactly the token OK and no other text."
    for lane in catalog["lanes"]:
        repo = str(lane["model_repo"])
        revision = str(lane["model_revision"])
        snapshot = Path(snapshot_download(repo_id=repo, revision=revision)).resolve()
        files, total_bytes = snapshot_files(snapshot)
        snapshot_record: Json = {
            "model_repo": repo,
            "model_revision": revision,
            "file_count": len(files),
            "total_bytes": total_bytes,
            "files": files,
        }
        snapshot_record["snapshot_digest"] = sha256_bytes(
            canonical_json(snapshot_record).encode("utf-8")
        )
        snapshots.append(snapshot_record)

        started = time.perf_counter()
        try:
            model, tokenizer = load(str(snapshot), lazy=False)
            formatted = tokenizer.apply_chat_template(
                [{"role": "user", "content": smoke_prompt}],
                add_generation_prompt=True,
                tokenize=False,
            )
            response = generate(
                model,
                tokenizer,
                prompt=formatted,
                max_tokens=16,
                sampler=sampler,
                verbose=False,
            )
        except Exception as exc:  # pragma: no cover - hardware/runtime boundary
            fail(f"model failed the non-benchmark smoke test ({repo}): {type(exc).__name__}")
        elapsed = time.perf_counter() - started
        if not isinstance(response, str) or not response.strip():
            fail(f"model returned no smoke-test text: {repo}")
        qualifications.append(
            {
                "model_repo": repo,
                "model_revision": revision,
                "load_and_generation_succeeded": True,
                "benchmark_prompt_or_label_used": False,
                "smoke_response_retained": False,
                "smoke_response_sha256": sha256_bytes(response.encode("utf-8")),
                "elapsed_seconds": round(elapsed, 6),
            }
        )
        del model, tokenizer
        gc.collect()
        mx.clear_cache()

    snapshot_receipt: Json = {
        "schema_version": "1.0.0",
        "status": "PINNED_LOCAL_MODEL_SNAPSHOTS_VALIDATED",
        "catalog_sha256": sha256_file(catalog_path),
        "snapshots": snapshots,
    }
    snapshot_receipt["self_digest"] = self_digest(snapshot_receipt)
    qualification: Json = {
        "schema_version": "1.0.0",
        "status": "LOCAL_MODEL_ENVIRONMENT_QUALIFIED_BEFORE_BENCHMARK_INFERENCE",
        "qualified_at_utc": utc_now(),
        "catalog_sha256": sha256_file(catalog_path),
        "snapshot_receipt_self_digest": snapshot_receipt["self_digest"],
        "benchmark_inference_calls": 0,
        "smoke_calls": len(qualifications),
        "smoke_prompt_contains_benchmark_content": False,
        "models": qualifications,
        "environment": {
            "python": platform.python_version(),
            "platform_machine": platform.machine(),
            "macos_version": platform.mac_ver()[0],
            "hardware_model": sysctl_value("hw.model"),
            "memory_bytes": int(sysctl_value("hw.memsize") or 0),
            "packages": package_versions(),
        },
        "credentials_used_or_retained": False,
    }
    qualification["self_digest"] = self_digest(qualification)
    return snapshot_receipt, qualification


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=CATALOG_PATH)
    parser.add_argument("--snapshot-out", type=Path, required=True)
    parser.add_argument("--qualification-out", type=Path, required=True)
    args = parser.parse_args()
    snapshot, qualification = qualify(args.catalog.resolve())
    write_json(args.snapshot_out.resolve(), snapshot)
    write_json(args.qualification_out.resolve(), qualification)
    print(
        canonical_json(
            {
                "status": qualification["status"],
                "models": len(qualification["models"]),
                "benchmark_inference_calls": 0,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
