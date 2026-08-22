#!/usr/bin/env python3
"""Build and verify the local ICLR/arXiv and anonymous-review release kit."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import platform
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from types import ModuleType
from typing import Any

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
ANONYMOUS_BUILDER = ROOT / "scripts" / "build_anonymous_review_bundle.py"
SUBMISSION_BUILDER = ROOT / "scripts" / "build_submission_tex.py"
STYLE_LOCK = ROOT / "technical-report" / "iclr2027-style-lock.json"
BREADTH_RESULTS = ROOT / "v2" / "public-model-breadth-v1" / "results"
OFFICIAL_STYLE_URL = "https://media.iclr.cc/Conferences/ICLR2027/iclr-2027-style-files.zip"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
LOG_FAILURE_RE = re.compile(
    r"Overfull \\hbox|There were undefined references|"
    r"(?:Citation|Reference).*(?:undefined|multiply defined)"
)
EXPECTED_OUTPUT_NAMES = {
    "README.md",
    "SHA256SUMS.txt",
    "arxiv.pdf",
    "claimpromotebench-anonymous-review-bundle.sha256",
    "claimpromotebench-anonymous-review-bundle.zip",
    "claimpromotebench-arxiv-source.zip",
    "claimpromotebench-iclr2027-source.zip",
    "iclr-style-receipt.json",
    "iclr2027.pdf",
    "validation-receipt.json",
}

Json = dict[str, Any]


def fail(message: str) -> None:
    raise SystemExit(f"local-release-kit: {message}")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_style_lock() -> Json:
    try:
        lock = json.loads(STYLE_LOCK.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"cannot load ICLR style lock: {exc}")
    if not isinstance(lock, dict) or lock.get("schema_version") != "1.0.0":
        fail("ICLR style lock has an unsupported schema")
    if lock.get("official_source_url") != OFFICIAL_STYLE_URL:
        fail("ICLR style lock source URL differs from the approved venue archive")
    if not SHA256_RE.fullmatch(str(lock.get("archive_sha256", ""))):
        fail("ICLR style lock has an invalid archive digest")
    expected_names = {"iclr2027_conference.bst", "iclr2027_conference.sty"}
    files = lock.get("files")
    if not isinstance(files, dict) or set(files) != expected_names:
        fail("ICLR style lock has an unexpected file set")
    if any(not SHA256_RE.fullmatch(str(digest)) for digest in files.values()):
        fail("ICLR style lock has an invalid file digest")
    return lock


def load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        fail(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def require_command(name: str) -> str:
    command = shutil.which(name)
    if command is None:
        fail(f"required command is unavailable: {name}")
    return command


def run_text(command: list[str]) -> str:
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    return result.stdout


def pdf_info(path: Path) -> Json:
    output = run_text([require_command("pdfinfo"), str(path)])
    values: dict[str, str] = {}
    for line in output.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            values[key.strip()] = value.strip()
    try:
        pages = int(values["Pages"])
    except (KeyError, ValueError) as exc:
        fail(f"could not read page count from {path}: {exc}")
    return {
        "pages": pages,
        "page_size": values.get("Page size"),
        "creator": values.get("Creator"),
        "producer": values.get("Producer"),
        "author_metadata": values.get("Author", ""),
    }


def extracted_pdf_text(path: Path) -> str:
    return "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)


def embedded_fonts(path: Path) -> Json:
    fonts: dict[str, bool] = {}
    for page in PdfReader(path).pages:
        resources_reference = page.get("/Resources")
        if resources_reference is None:
            continue
        resources = resources_reference.get_object()
        for resource_name, font_reference in resources.get("/Font", {}).items():
            font = font_reference.get_object()
            target = font
            descendants = font.get("/DescendantFonts")
            if descendants:
                target = descendants[0].get_object()
            descriptor_reference = target.get("/FontDescriptor") or font.get("/FontDescriptor")
            descriptor = descriptor_reference.get_object() if descriptor_reference else None
            embedded = bool(
                descriptor
                and any(key in descriptor for key in ("/FontFile", "/FontFile2", "/FontFile3"))
            )
            name = str(font.get("/BaseFont") or target.get("/BaseFont") or resource_name)
            fonts[name] = fonts.get(name, True) and embedded
    if not fonts:
        fail(f"no fonts found in {path}")
    missing = sorted(name for name, embedded in fonts.items() if not embedded)
    if missing:
        fail(f"fonts are not embedded in {path}: {missing}")
    return {"font_count": len(fonts), "all_embedded": True, "fonts": sorted(fonts)}


def check_log(path: Path) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    match = LOG_FAILURE_RE.search(text)
    if match:
        fail(f"{path.name} contains a release-blocking LaTeX warning: {match.group(0)}")


def zip_bytes(entries: dict[str, Path]) -> bytes:
    with tempfile.SpooledTemporaryFile(max_size=64 * 1024 * 1024) as handle:
        with zipfile.ZipFile(
            handle,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        ) as archive:
            for name, source in sorted(entries.items()):
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, source.read_bytes(), compress_type=zipfile.ZIP_DEFLATED)
        handle.seek(0)
        return handle.read()


def write_zip(path: Path, entries: dict[str, Path]) -> list[str]:
    path.write_bytes(zip_bytes(entries))
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
    expected = sorted(entries)
    if names != expected:
        fail(f"archive entry set differs from expectation: {path.name}")
    return names


def validate_bundle(bundle: Path) -> tuple[Json, list[Path]]:
    builder = load_module(ANONYMOUS_BUILDER, "local_release_anonymous_builder")
    builder.verify_bundle(bundle)
    manifest_path = bundle / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    declared = manifest.get("files")
    if not isinstance(declared, dict) or manifest.get("file_count") != len(declared):
        fail("anonymous manifest file_count or files map is malformed")
    actual = sorted(path for path in bundle.rglob("*") if path.is_file())
    expected_relatives = sorted(["MANIFEST.json", *declared])
    actual_relatives = sorted(path.relative_to(bundle).as_posix() for path in actual)
    if actual_relatives != expected_relatives:
        fail("anonymous staging tree contains unmanifested or missing files")
    for relative, expected_digest in declared.items():
        if f"sha256:{sha256_file(bundle / relative)}" != expected_digest:
            fail(f"anonymous manifest digest mismatch: {relative}")
    scope = manifest.get("scope")
    if not isinstance(scope, dict):
        fail("anonymous manifest scope is missing")
    false_guards = (
        "human_subject_study_records_included",
        "private_construction_seed_included",
        "provider_response_identifiers_included",
        "public_repository_identity_included",
        "fresh_confirmatory_hidden_reasoning_included",
        "balanced_public_challenge_hidden_reasoning_included",
        "public_model_breadth_hidden_reasoning_included",
        "public_model_breadth_raw_final_response_text_included",
    )
    if any(scope.get(key) is not False for key in false_guards):
        fail("anonymous manifest privacy scope changed")
    if BREADTH_RESULTS.is_dir() and (
        scope.get("public_model_breadth_summary_included") is not True
        or scope.get("public_model_breadth_item_level_records_included") is not True
    ):
        fail("anonymous manifest omits completed public model-breadth evidence")
    return manifest, actual


def safe_output(path: Path, replace: bool) -> None:
    resolved = path.resolve()
    if ROOT not in resolved.parents or len(resolved.relative_to(ROOT).parts) < 2:
        fail("output must be a scoped directory below the repository root")
    if not resolved.exists():
        return
    if not replace:
        fail(f"output already exists (pass --replace for this generated directory): {resolved}")
    existing = {item.name for item in resolved.iterdir()}
    unexpected = sorted(existing - EXPECTED_OUTPUT_NAMES)
    if unexpected:
        fail(f"refusing to replace output containing unknown entries: {unexpected}")


def write_readme(path: Path, receipt: Json) -> None:
    submission = receipt["submission"]
    bundle = receipt["anonymous_bundle"]
    path.write_text(
        "# Local submission release kit\n\n"
        "This directory is a verified build artifact, not evidence of submission. It contains the "
        "anonymous ICLR PDF and source, the named arXiv PDF and source, and the anonymous reviewer "
        "bundle. No OpenReview or arXiv upload was performed.\n\n"
        f"- ICLR PDF: {submission['iclr2027']['pages']} pages; main-text probe "
        f"{submission['iclr2027']['main_text_pages']} pages.\n"
        f"- arXiv PDF: {submission['arxiv']['pages']} pages.\n"
        f"- Anonymous manifest: {bundle['manifest_file_count']} listed files plus the manifest; "
        f"ZIP entries {bundle['zip_file_entries']}.\n\n"
        "Verify every release artifact from this directory with:\n\n"
        "```bash\n"
        "cd release/submission-kit && shasum -a 256 -c SHA256SUMS.txt\n"
        "```\n\n"
        "Use `validation-receipt.json` for the corresponding structural checks. "
        "The anonymous bundle file total is read from its generated manifest; do not copy it into "
        "long-lived prose.\n",
        encoding="utf-8",
        newline="\n",
    )


def build(args: argparse.Namespace) -> Json:
    submission = args.submission_dir.resolve()
    bundle = args.anonymous_bundle.resolve()
    output = args.out.resolve()
    safe_output(output, args.replace)

    required_submission = {
        "arxiv.log",
        "arxiv.pdf",
        "arxiv.tex",
        "iclr2027-maintext-probe.pdf",
        "iclr2027.log",
        "iclr2027.pdf",
        "iclr2027.tex",
        "iclr2027_conference.bst",
        "iclr2027_conference.sty",
        "references.bib",
    }
    missing = sorted(name for name in required_submission if not (submission / name).is_file())
    if missing:
        fail(f"submission build is missing files: {missing}")
    check_log(submission / "iclr2027.log")
    check_log(submission / "arxiv.log")

    manifest, bundle_files = validate_bundle(bundle)
    iclr_info = pdf_info(submission / "iclr2027.pdf")
    probe_info = pdf_info(submission / "iclr2027-maintext-probe.pdf")
    arxiv_info = pdf_info(submission / "arxiv.pdf")
    if probe_info["pages"] > 9:
        fail(f"ICLR main text exceeds nine pages: {probe_info['pages']}")
    if not args.visual_qa_complete:
        fail("release packaging requires explicit --visual-qa-complete after page-by-page review")

    submission_builder = load_module(SUBMISSION_BUILDER, "local_release_submission_builder")
    forbidden = {
        "Chih-Kai Wang",
        "National Taipei University of Education",
        "f0909172434",
        "github.com/f0909172434",
        *submission_builder.ICLR_PUBLIC_IDENTIFIERS,
    }
    iclr_text = extracted_pdf_text(submission / "iclr2027.pdf")
    arxiv_text = extracted_pdf_text(submission / "arxiv.pdf")
    iclr_tex = (submission / "iclr2027.tex").read_text(encoding="utf-8", errors="replace")
    searchable = f"{iclr_tex}\n{iclr_text}".lower()
    leaked = sorted(token for token in forbidden if token.lower() in searchable)
    if leaked:
        fail(f"ICLR source/PDF contains forbidden identity or provenance tokens: {leaked}")
    for required_identity in ("Chih-Kai Wang", "National Taipei University of Education"):
        if required_identity not in arxiv_text:
            fail(f"arXiv PDF lacks expected author provenance: {required_identity}")

    style_archive_sha256 = args.style_archive_sha256.lower()
    if not SHA256_RE.fullmatch(style_archive_sha256):
        fail("--style-archive-sha256 must be exactly 64 lowercase hexadecimal characters")
    style_lock = load_style_lock()
    if style_archive_sha256 != style_lock["archive_sha256"]:
        fail("style archive digest differs from the committed ICLR style lock")
    observed_style_files = {
        name: sha256_file(submission / name) for name in sorted(style_lock["files"])
    }
    if observed_style_files != style_lock["files"]:
        fail("submission style files differ from the committed ICLR style lock")

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".submission-kit-") as staging_name:
        staging = Path(staging_name)
        shutil.copyfile(submission / "iclr2027.pdf", staging / "iclr2027.pdf")
        shutil.copyfile(submission / "arxiv.pdf", staging / "arxiv.pdf")

        arxiv_entries = {name: submission / name for name in ("arxiv.tex", "references.bib")}
        iclr_entries = {
            name: submission / name
            for name in (
                "iclr2027.tex",
                "references.bib",
                "iclr2027_conference.sty",
                "iclr2027_conference.bst",
            )
        }
        arxiv_names = write_zip(staging / "claimpromotebench-arxiv-source.zip", arxiv_entries)
        iclr_names = write_zip(staging / "claimpromotebench-iclr2027-source.zip", iclr_entries)

        bundle_entries = {
            f"anonymous-review/{path.relative_to(bundle).as_posix()}": path for path in bundle_files
        }
        bundle_names = write_zip(
            staging / "claimpromotebench-anonymous-review-bundle.zip", bundle_entries
        )
        bundle_zip = staging / "claimpromotebench-anonymous-review-bundle.zip"
        bundle_digest = sha256_file(bundle_zip)
        (staging / "claimpromotebench-anonymous-review-bundle.sha256").write_text(
            f"{bundle_digest}  {bundle_zip.name}\n", encoding="utf-8", newline="\n"
        )

        style_receipt = {
            "schema_version": "1.0.0",
            "status": "PASS",
            "official_source_url": style_lock["official_source_url"],
            "style_archive_sha256": style_archive_sha256,
            "style_lock_sha256": sha256_file(STYLE_LOCK),
            "files": observed_style_files,
        }
        (staging / "iclr-style-receipt.json").write_text(
            json.dumps(style_receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

        major_artifacts = (
            "arxiv.pdf",
            "claimpromotebench-anonymous-review-bundle.zip",
            "claimpromotebench-arxiv-source.zip",
            "claimpromotebench-iclr2027-source.zip",
            "iclr2027.pdf",
        )
        receipt: Json = {
            "schema_version": "1.0.0",
            "status": "PASS",
            "environment": {
                "platform": platform.platform(),
                "python": platform.python_version(),
            },
            "submission": {
                "iclr2027": {
                    **iclr_info,
                    "main_text_pages": probe_info["pages"],
                    "anonymous_source_and_pdf_scan": "PASS",
                    "fonts": embedded_fonts(submission / "iclr2027.pdf"),
                    "visual_pages_inspected": iclr_info["pages"],
                },
                "arxiv": {
                    **arxiv_info,
                    "named_author_and_affiliation_scan": "PASS",
                    "fonts": embedded_fonts(submission / "arxiv.pdf"),
                    "visual_pages_inspected": arxiv_info["pages"],
                },
            },
            "anonymous_bundle": {
                "manifest_sha256": sha256_file(bundle / "MANIFEST.json"),
                "manifest_file_count": manifest["file_count"],
                "manifest_plus_self_file_count": len(bundle_files),
                "zip_file_entries": len(bundle_names),
                "privacy_scope": manifest["scope"],
                "verification": "PASS",
            },
            "source_archives": {
                "arxiv_entries": arxiv_names,
                "iclr2027_entries": iclr_names,
            },
            "checks": {
                "arxiv_identity": "PASS",
                "bundle_manifest_and_privacy": "PASS",
                "iclr_anonymity": "PASS",
                "latex_logs": "PASS",
                "pdf_fonts_embedded": "PASS",
                "visual_page_review": "PASS",
            },
            "artifacts": {
                name: {
                    "sha256": sha256_file(staging / name),
                    "bytes": (staging / name).stat().st_size,
                }
                for name in major_artifacts
            },
        }
        (staging / "validation-receipt.json").write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        write_readme(staging / "README.md", receipt)

        checksum_names = sorted(EXPECTED_OUTPUT_NAMES - {"SHA256SUMS.txt"})
        checksums = "".join(f"{sha256_file(staging / name)}  {name}\n" for name in checksum_names)
        (staging / "SHA256SUMS.txt").write_text(checksums, encoding="utf-8", newline="\n")
        if {path.name for path in staging.iterdir()} != EXPECTED_OUTPUT_NAMES:
            fail("generated release kit has an unexpected output set")

        if output.exists():
            shutil.rmtree(output)
        shutil.copytree(staging, output)

    print(json.dumps(receipt, sort_keys=True))
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission-dir", type=Path, required=True)
    parser.add_argument("--anonymous-bundle", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--style-archive-sha256", required=True)
    parser.add_argument("--visual-qa-complete", action="store_true")
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()
    build(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
