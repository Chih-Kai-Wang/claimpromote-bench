from __future__ import annotations

from pathlib import Path

import pytest

from claimpromotebench.dataset import load_json, load_jsonl
from claimpromotebench.policy import load_policy


@pytest.fixture(scope="session")
def root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def dataset_dir(root: Path) -> Path:
    return root / "data" / "alpha"


@pytest.fixture(scope="session")
def inputs(dataset_dir: Path) -> list[dict[str, object]]:
    return load_jsonl(dataset_dir / "inputs.jsonl")


@pytest.fixture(scope="session")
def gold(dataset_dir: Path) -> list[dict[str, object]]:
    return load_jsonl(dataset_dir / "gold.jsonl")


@pytest.fixture(scope="session")
def manifest(dataset_dir: Path) -> dict[str, object]:
    value = load_json(dataset_dir / "manifest.json")
    assert isinstance(value, dict)
    return value


@pytest.fixture(scope="session")
def policy(root: Path, manifest: dict[str, object]) -> dict[str, object]:
    return load_policy(root / "policies" / str(manifest["policy_file"]))
