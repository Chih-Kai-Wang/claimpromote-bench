from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import finalize_local_model_results as finalizer  # noqa: E402


def test_local_post_execution_sealer_binds_frozen_generic_code_and_local_schema() -> None:
    plan_path = (
        ROOT
        / "v2"
        / "local-model-replication-v1"
        / "replacement-v2"
        / "frozen"
        / "slsa"
        / "study-plan.json"
    )
    plan = finalizer.load_object(plan_path)
    runtime = plan["freeze"]["runtime_source_sha256"]
    assert runtime["scripts/finalize_synthetic_policy_results.py"] == finalizer.sha256_file(
        finalizer.GENERIC_FINALIZER
    )
    assert runtime["v2/schemas/local-model-run-record.schema.json"] == finalizer.sha256_file(
        finalizer.LOCAL_RUN_SCHEMA
    )
    source = (ROOT / "scripts" / "finalize_local_model_results.py").read_text(encoding="utf-8")
    assert "generic.RUN_SCHEMA = LOCAL_RUN_SCHEMA" in source
    assert '"model_calls_performed": 0' in source
    assert '"metrics_changed": False' in source
