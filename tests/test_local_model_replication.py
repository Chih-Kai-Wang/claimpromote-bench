from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from frozen_run_io import append_durable, atomic_output_directory, write_durable_json  # noqa: E402
from local_model_replication import (  # noqa: E402
    CATALOG_PATH,
    DATASETS,
    format_chat_prompt,
    generation_request,
    lane_id,
    load_catalog,
)
from synthetic_policy_output import extract_single_json_object  # noqa: E402

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
    assert catalog["lanes"][0]["tokenizer_config"] == {
        "fix_mistral_regex": True,
        "trust_remote_code": False,
    }
    assert catalog["lanes"][1]["tokenizer_config"] == {"trust_remote_code": True}
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
    assert request["tokenizer_config"] == lane["tokenizer_config"]
    assert sha256_bytes(canonical_json(request).encode("utf-8")).startswith("sha256:")


def test_local_replication_source_datasets_are_fixed_and_disjoint_studies() -> None:
    assert set(DATASETS) == {"slsa", "policy-switch"}
    assert len({row["study_id"] for row in DATASETS.values()}) == 2
    assert all(str(row["study_id"]).endswith("-v2") for row in DATASETS.values())
    assert len({row["expected_dataset_fingerprint"] for row in DATASETS.values()}) == 2
    catalog = load_catalog(CATALOG_PATH)
    lane_ids = {lane_id(lane, dataset_key) for lane in catalog["lanes"] for dataset_key in DATASETS}
    assert len(lane_ids) == 4


def test_local_runner_forbids_resume_and_records_every_cell() -> None:
    source = (ROOT / "scripts" / "run_local_model_replication.py").read_text(encoding="utf-8")
    assert "from frozen_run_io import" in source
    assert "run_public_model_breadth_study" not in source
    assert "run_slsa_portability_study" not in source
    assert "resume and overwrite are forbidden" in source
    assert '"client_retries_authorized": 0' in source
    assert '"application_posts_authorized_for_cell": 1' in source
    assert "if len(completed) != 240" in source
    assert "--resume" not in source
    assert 'RUN_SCHEMA = ROOT / "v2" / "schemas" / "local-model-run-record.schema.json"' in source


def test_environment_qualification_uses_the_scored_stream_api_without_benchmark_content() -> None:
    source = (ROOT / "scripts" / "qualify_local_model_environment.py").read_text(encoding="utf-8")
    assert "stream_generate(" in source
    assert '"benchmark_inference_calls": 0' in source
    assert '"smoke_prompt_contains_benchmark_content": False' in source
    assert "relative = path.relative_to(snapshot)" in source
    assert '".cache" in relative.parts' in source


def test_frozen_run_io_publishes_only_complete_outputs(tmp_path: Path) -> None:
    journal = tmp_path / "journal.jsonl"
    append_durable(journal, {"sequence": 0})
    append_durable(journal, {"sequence": 1})
    assert journal.read_text(encoding="utf-8").splitlines() == [
        '{"sequence":0}',
        '{"sequence":1}',
    ]

    output = tmp_path / "results"
    with atomic_output_directory(output) as staging:
        write_durable_json(staging / "receipt.json", {"status": "COMPLETE"})
        assert not output.exists()
    assert json.loads((output / "receipt.json").read_text(encoding="utf-8")) == {
        "status": "COMPLETE"
    }


def test_local_output_extraction_requires_exactly_one_balanced_object() -> None:
    assert extract_single_json_object('prefix {"value":"}"} suffix') == '{"value":"}"}'
    assert extract_single_json_object('{"a":1} {"b":2}') is None
    assert extract_single_json_object('prefix {"a":1') is None


def test_replacement_v2_uses_a_local_only_run_record_schema() -> None:
    path = ROOT / "v2" / "schemas" / "local-model-run-record.schema.json"
    schema = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    properties = schema["properties"]
    assert properties["model_family"]["enum"] == ["Mistral", "Phi"]
    assert properties["provider"] == {"const": "Local MLX"}
    assert properties["routed_provider"] == {"const": "LOCAL_MLX"}
    assert properties["phase"] == {"const": "full"}
