#!/usr/bin/env python3
"""Small fail-closed I/O helpers shared by frozen one-pass study runners."""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, NoReturn

ROOT = Path(__file__).resolve().parents[1]
Json = dict[str, Any]


def fail(message: str) -> NoReturn:
    raise SystemExit(f"frozen-run-io: {message}")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def append_durable(path: Path, payload: Json) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (canonical_json(payload) + "\n").encode("utf-8")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        offset = 0
        while offset < len(encoded):
            offset += os.write(descriptor, encoded[offset:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def write_durable_json(path: Path, payload: Json) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        offset = 0
        while offset < len(encoded):
            offset += os.write(descriptor, encoded[offset:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


@contextmanager
def atomic_output_directory(out_dir: Path) -> Iterator[Path]:
    """Publish a complete result directory with one rename."""

    if out_dir.exists():
        fail(f"output directory already exists: {out_dir}")
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{out_dir.name}.building-", dir=out_dir.parent))
    try:
        yield staging
    except BaseException:
        raise
    else:
        os.replace(staging, out_dir)


def verify_frozen_plan(plan_path: Path, frozen_commit: str) -> None:
    if not re.fullmatch(r"[0-9a-f]{40}", frozen_commit):
        fail("frozen plan commit must be a full lowercase Git SHA")
    try:
        relative = plan_path.relative_to(ROOT).as_posix()
    except ValueError:
        fail("study plan must be inside the repository")
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", frozen_commit, "HEAD"],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    if ancestor.returncode != 0:
        fail("frozen plan commit is not an ancestor of HEAD")
    shown = subprocess.run(
        ["git", "show", f"{frozen_commit}:{relative}"],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    if shown.returncode != 0 or shown.stdout != plan_path.read_bytes():
        fail("current study plan bytes differ from the frozen commit")
