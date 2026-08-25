from __future__ import annotations

import importlib.util
import io
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER_PATH = ROOT / "scripts" / "build_local_release_kit.py"
RELEASE = ROOT / "release" / "submission-kit"


def load_builder():
    spec = importlib.util.spec_from_file_location("release_kit_builder", BUILDER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_committed_release_uses_locked_iclr_style() -> None:
    builder = load_builder()
    lock = builder.load_style_lock()
    receipt = json.loads((RELEASE / "iclr-style-receipt.json").read_text(encoding="utf-8"))

    assert receipt["official_source_url"] == lock["official_source_url"]
    assert receipt["style_archive_sha256"] == lock["archive_sha256"]
    assert receipt["files"] == lock["files"]

    source_zip = (RELEASE / "claimpromotebench-iclr2027-source.zip").read_bytes()
    with zipfile.ZipFile(io.BytesIO(source_zip)) as archive:
        observed = {
            name: builder.sha256_bytes(archive.read(name)) for name in sorted(lock["files"])
        }
    assert observed == lock["files"]


def test_release_builder_and_workflow_enforce_style_lock() -> None:
    workflow = (ROOT / ".github" / "workflows" / "submission-package.yml").read_text(
        encoding="utf-8"
    )

    assert "technical-report/iclr2027-style-lock.json" in workflow
    assert "sha256sum -c -" in workflow
    assert "submission style files differ from the committed ICLR style lock" in (
        BUILDER_PATH.read_text(encoding="utf-8")
    )


def test_release_readme_gives_an_exact_checksum_command() -> None:
    readme = (RELEASE / "README.md").read_text(encoding="utf-8")
    assert "cd release/submission-kit && shasum -a 256 -c SHA256SUMS.txt" in readme


def test_release_receipt_records_the_iclr_page_boundary() -> None:
    receipt = json.loads((RELEASE / "validation-receipt.json").read_text(encoding="utf-8"))
    iclr = receipt["submission"]["iclr2027"]

    assert iclr["pages"] >= iclr["references_start_page"]
    assert 1 <= iclr["main_text_pages"] <= 9
    assert iclr["main_text_page_limit"] == 9
    assert iclr["pre_reference_exempt_statement_pages"] in {0, 1}
    assert iclr["references_start_page"] == (
        iclr["main_text_pages"] + iclr["pre_reference_exempt_statement_pages"] + 1
    )
    assert iclr["style_template"] == "ICLR 2027 official style archive"
    assert iclr["style_receipt"] == "iclr-style-receipt.json"


def test_durable_root_readme_omits_private_execution_diary() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "PR #20" not in readme
    assert "account-side preview checks" not in readme
    assert "docs/PUBLIC_RELEASE_BOUNDARY.md" in readme
