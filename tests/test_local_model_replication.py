from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from local_model_replication import (  # noqa: E402
    CATALOG_PATH,
    DATASETS,
    format_chat_prompt,
    generation_request,
    lane_id,
    load_catalog,
)

from claimpromotebench.hashing import canonical_json, sha256_bytes  # noqa: E402


class FakeTokenizer:
    def apply_chat_template(
        self,
        messages: list[dict[str, str]],
        *,
        add_generation_prompt: bool,
        tokenize: bool,
    ) -> str:
        assert add_generation_prompt is True
        assert tokenize is False
        return f"<user>{messages[0]['content']}</user><assistant>"


def test_local_model_catalog_is_preinference_and_family_distinct() -> None:
    catalog = load_catalog(CATALOG_PATH)
    assert [row["model_family"] for row in catalog["lanes"]] == ["Mistral", "Phi"]
    assert all(len(row["model_revision"]) == 40 for row in catalog["lanes"])
    boundary = catalog["selection_boundary"]
    assert boundary["models_selected_before_any_benchmark_inference"] is True
    assert boundary["benchmark_accuracy_or_labels_consulted"] is False
    assert catalog["shared_generation"] == {
        "client_retries": 0,
        "max_output_tokens": 1536,
        "prompt_mode": "USER_ONLY_CHAT_TEMPLATE",
        "sampler": "GREEDY",
        "temperature": 0.0,
        "top_p": 0.0,
    }


def test_local_model_request_hash_binds_template_model_and_generation() -> None:
    catalog = load_catalog(CATALOG_PATH)
    lane = catalog["lanes"][0]
    formatted = format_chat_prompt(FakeTokenizer(), "policy prompt")
    request = generation_request(lane, formatted, catalog["shared_generation"])
    assert request["formatted_prompt"] == "<user>policy prompt</user><assistant>"
    assert request["model_revision"] == lane["model_revision"]
    assert request["sampler"] == "GREEDY"
    assert sha256_bytes(canonical_json(request).encode("utf-8")).startswith("sha256:")


def test_local_replication_source_datasets_are_fixed_and_disjoint_studies() -> None:
    assert set(DATASETS) == {"slsa", "policy-switch"}
    assert len({row["study_id"] for row in DATASETS.values()}) == 2
    assert len({row["expected_dataset_fingerprint"] for row in DATASETS.values()}) == 2
    catalog = load_catalog(CATALOG_PATH)
    lane_ids = {lane_id(lane, dataset_key) for lane in catalog["lanes"] for dataset_key in DATASETS}
    assert len(lane_ids) == 4


def test_local_runner_forbids_resume_and_records_every_cell() -> None:
    source = (ROOT / "scripts" / "run_local_model_replication.py").read_text(encoding="utf-8")
    assert "resume and overwrite are forbidden" in source
    assert '"client_retries_authorized": 0' in source
    assert '"application_posts_authorized_for_cell": 1' in source
    assert "if len(completed) != 240" in source
    assert "--resume" not in source
