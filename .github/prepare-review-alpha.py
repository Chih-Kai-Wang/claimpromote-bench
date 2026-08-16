from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import shutil
import subprocess
import zipfile
from pathlib import Path

ROOT = Path.cwd()
PACKAGE = ROOT / "work" / "review-alpha"
EXPORT = ROOT / "work" / "review-export"
PRIVATE_MAPPING = PACKAGE / "private-key.json"
EXPECTED_PUBLIC_KEY_SHA256 = "b334345de1584351c2f345eb932a096263f1f337760b4b6eaf735aeb2100218e"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(*args: str) -> None:
    subprocess.run(args, check=True)


def write_instructions(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "# ClaimPromoteBench alpha blinded review",
                "",
                "Work independently. Do not access `gold.jsonl`, model outputs, another",
                "reviewer's decisions, or the organizer's private mapping. Review only",
                "`packet.jsonl`, the bound policy, and your supplied submission draft.",
                "",
                "For every decision, replace the null action and confidence fields, use only",
                "policy reason codes, add a concise rationale, set `completed_at` to an ISO 8601",
                "timestamp with timezone, and set each attestation flag to true only when it is",
                "factually true. Return only your completed `reviewer-XX.json`.",
            ]
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )


def make_reviewer_archives() -> None:
    dataset_manifest = json.loads((ROOT / "data" / "alpha" / "manifest.json").read_text(encoding="utf-8"))
    policy = ROOT / "policies" / dataset_manifest["policy_file"]
    schema = ROOT / "schemas" / "review-submission.schema.json"
    instructions = EXPORT / "REVIEWER_INSTRUCTIONS.md"
    write_instructions(instructions)
    common = [
        (PACKAGE / "packet.jsonl", "packet.jsonl"),
        (PACKAGE / "packet-manifest.json", "packet-manifest.json"),
        (policy, f"policy/{policy.name}"),
        (schema, f"schema/{schema.name}"),
        (instructions, instructions.name),
    ]
    for reviewer in ("reviewer-01", "reviewer-02"):
        archive = EXPORT / f"{reviewer}-package.zip"
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
            for source, target in common:
                bundle.write(source, target)
            bundle.write(EXPORT / f"{reviewer}.json", f"{reviewer}.json")


def encrypt_private_mapping() -> dict[str, str]:
    public_der = base64.b64decode(os.environ["RECIPIENT_PUBLIC_KEY_DER_B64"], validate=True)
    if hashlib.sha256(public_der).hexdigest() != EXPECTED_PUBLIC_KEY_SHA256:
        raise RuntimeError("recipient public key fingerprint mismatch")

    public_der_path = EXPORT / "recipient-public.der"
    public_pem_path = EXPORT / "recipient-public.pem"
    envelope_path = EXPORT / "organizer-envelope.key"
    encrypted_mapping = EXPORT / "organizer-mapping.enc"
    encrypted_envelope = EXPORT / "organizer-envelope-key.enc"

    public_der_path.write_bytes(public_der)
    run(
        "openssl",
        "pkey",
        "-pubin",
        "-inform",
        "DER",
        "-in",
        str(public_der_path),
        "-out",
        str(public_pem_path),
    )

    aes_key = secrets.token_bytes(32)
    iv = secrets.token_bytes(16)
    envelope_path.write_bytes(aes_key + iv)
    plaintext_sha256 = sha256(PRIVATE_MAPPING)
    run(
        "openssl",
        "enc",
        "-aes-256-cbc",
        "-K",
        aes_key.hex(),
        "-iv",
        iv.hex(),
        "-in",
        str(PRIVATE_MAPPING),
        "-out",
        str(encrypted_mapping),
    )
    run(
        "openssl",
        "pkeyutl",
        "-encrypt",
        "-pubin",
        "-inkey",
        str(public_pem_path),
        "-pkeyopt",
        "rsa_padding_mode:oaep",
        "-pkeyopt",
        "rsa_oaep_md:sha256",
        "-in",
        str(envelope_path),
        "-out",
        str(encrypted_envelope),
    )

    PRIVATE_MAPPING.unlink()
    for temporary in (public_der_path, public_pem_path, envelope_path):
        temporary.unlink(missing_ok=True)
    return {
        "algorithm": "AES-256-CBC with RSA-OAEP-SHA256 envelope",
        "recipient_public_key_der_sha256": EXPECTED_PUBLIC_KEY_SHA256,
        "plaintext_sha256": plaintext_sha256,
    }


def write_export_manifest(encryption: dict[str, str]) -> None:
    packet_manifest = json.loads((PACKAGE / "packet-manifest.json").read_text(encoding="utf-8"))
    names = [
        "reviewer-01-package.zip",
        "reviewer-02-package.zip",
        "organizer-mapping.enc",
        "organizer-envelope-key.enc",
        "prepare-report.json",
    ]
    report = {
        "schema_version": "1.0.0",
        "source_commit": os.environ["SOURCE_COMMIT"],
        "packet_id": packet_manifest["packet_id"],
        "packet_sha256": packet_manifest["packet_sha256"],
        "item_count": packet_manifest["item_count"],
        "encryption": encryption,
        "files": {
            name: {"sha256": sha256(EXPORT / name), "bytes": (EXPORT / name).stat().st_size}
            for name in names
        },
    }
    (EXPORT / "export-manifest.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> None:
    if not PRIVATE_MAPPING.is_file():
        raise RuntimeError("review preparation did not produce private-key.json")
    make_reviewer_archives()
    encryption = encrypt_private_mapping()
    write_export_manifest(encryption)
    for path in (
        EXPORT / "reviewer-01.json",
        EXPORT / "reviewer-02.json",
        EXPORT / "REVIEWER_INSTRUCTIONS.md",
    ):
        path.unlink(missing_ok=True)
    shutil.rmtree(PACKAGE / "submissions", ignore_errors=True)


if __name__ == "__main__":
    main()
