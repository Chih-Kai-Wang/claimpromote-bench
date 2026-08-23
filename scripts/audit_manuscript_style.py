#!/usr/bin/env python3
"""Measure submission prose against the frozen computer-science house style."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEX = ROOT / "technical-report" / "main.tex"
DEFAULT_CORPUS_MANIFEST = ROOT / "docs" / "PAPER_STYLE_CORPUS_MANIFEST_2026-08-23.json"
DEFAULT_CORPUS_STATISTICS = ROOT / "docs" / "PAPER_STYLE_CORPUS_STATISTICS_2026-08-23.json"
DESLOP_COMMIT = "a906154bef375d9d49ed2ad7da13b2db16f0d3d2"

PATTERNS = {
    "throat_clearing": re.compile(
        r"\b(?:it is worth noting|it should be noted|needless to say|it is important to note)\b",
        re.IGNORECASE,
    ),
    "vague_importance": re.compile(
        r"\b(?:plays? (?:a|an) (?:crucial|vital|important) role|"
        r"of (?:critical|paramount) importance)\b",
        re.IGNORECASE,
    ),
    "pompous_copula": re.compile(
        r"\b(?:serves as|stands as|represents a testament to|embodies)\b", re.IGNORECASE
    ),
    "ai_lexicon": re.compile(
        r"\b(?:delve|tapestry|multifaceted|nuanced interplay|seamlessly)\b", re.IGNORECASE
    ),
    "formulaic_pivot": re.compile(r"\bnot (?:only|merely)\b[^.]{0,100}\bbut also\b", re.IGNORECASE),
    "superficial_participle": re.compile(
        r",\s+(?:highlighting|underscoring|showcasing)\s+(?:the|this|its)\b",
        re.IGNORECASE,
    ),
    "signposted_summary": re.compile(
        r"\b(?:in summary|in conclusion|to sum up|all in all)\b", re.IGNORECASE
    ),
    "grandiose": re.compile(
        r"\b(?:transformative|revolutionary|paradigm[- ]shifting|paves? the way|"
        r"far-reaching implications)\b",
        re.IGNORECASE,
    ),
}


def fail(message: str) -> None:
    raise SystemExit(f"manuscript-style-audit: {message}")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def percentile(values: list[int], quantile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def remove_environment(text: str, name: str) -> str:
    return re.sub(
        rf"\\begin\{{{re.escape(name)}\}}.*?\\end\{{{re.escape(name)}\}}",
        "\n",
        text,
        flags=re.DOTALL,
    )


def prose_from_latex(source: str) -> str:
    text = re.sub(r"(?<!\\)%.*", "", source)
    for environment in (
        "table",
        "table*",
        "figure",
        "figure*",
        "equation",
        "equation*",
        "align",
        "align*",
        "gather",
        "gather*",
    ):
        text = remove_environment(text, environment)
    text = re.sub(r"\\\[.*?\\\]", "\n", text, flags=re.DOTALL)
    text = re.sub(r"\$\$.*?\$\$", "\n", text, flags=re.DOTALL)
    text = re.sub(r"\$[^$]*\$", " ", text)
    text = re.sub(r"\\(?:cite|citet|citep)\{[^{}]*\}", " ", text)
    text = re.sub(r"\\(?:label|ref|eqref|bibliography|bibliographystyle)\{[^{}]*\}", " ", text)
    text = re.sub(r"\\(?:begin|end)\{[^{}]*\}(?:\[[^\]]*\])?", "\n", text)
    text = re.sub(
        r"\\(?:section|subsection|subsubsection|paragraph|caption|title|author|date)\*?"
        r"\{([^{}]*)\}",
        r"\1.\n",
        text,
    )
    for _ in range(4):
        text = re.sub(r"\\[A-Za-z]+\*?(?:\[[^\]]*\])?\{([^{}]*)\}", r"\1", text)
    text = re.sub(r"\\[A-Za-z]+\*?", " ", text)
    text = text.replace("{", " ").replace("}", " ")
    text = text.replace("~", " ").replace("\\_", "_").replace("\\%", "%")
    text = re.sub(r"\s*\\\\\s*", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def words(value: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9][A-Za-z0-9'._-]*", value)


def measure(prose: str, abstract: str) -> dict[str, Any]:
    sentences: list[str] = []
    for candidate in re.split(r"(?<=[.!?])\s+", prose):
        count = len(words(candidate))
        if 5 <= count <= 100:
            sentences.append(candidate)
    sentence_lengths = [len(words(sentence)) for sentence in sentences]
    prose_words = words(prose)
    return {
        "manuscript_sha256": sha256_file(DEFAULT_TEX),
        "prose_words": len(prose_words),
        "sentences": len(sentences),
        "sentence_words_mean": round(statistics.mean(sentence_lengths), 2)
        if sentence_lengths
        else 0.0,
        "sentence_words_median": round(statistics.median(sentence_lengths), 2)
        if sentence_lengths
        else 0.0,
        "sentence_words_p90": round(percentile(sentence_lengths, 0.90), 2),
        "sentence_words_p95": round(percentile(sentence_lengths, 0.95), 2),
        "sentence_words_over_40_percent": round(
            100 * sum(length > 40 for length in sentence_lengths) / len(sentence_lengths), 4
        )
        if sentence_lengths
        else 0.0,
        "abstract_submission_lint_tokens": len(words(abstract)),
        "configured_pattern_findings": {
            name: len(pattern.findall(prose)) for name, pattern in PATTERNS.items()
        },
    }


def build_audit(
    tex_path: Path,
    corpus_manifest_path: Path,
    corpus_statistics_path: Path,
    prior_path: Path | None,
    scored_model_calls: int,
    void_protocol_posts: int,
) -> dict[str, Any]:
    source = tex_path.read_text(encoding="utf-8")
    abstract_match = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", source, re.DOTALL)
    if abstract_match is None:
        fail("manuscript abstract is missing")
    prose = prose_from_latex(source)
    abstract = prose_from_latex(abstract_match.group(1))
    after = measure(prose, abstract)
    after["manuscript_sha256"] = sha256_file(tex_path)
    prior: dict[str, Any] = {}
    if prior_path is not None and prior_path.is_file():
        loaded = json.loads(prior_path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict) and isinstance(loaded.get("before"), dict):
            prior = loaded["before"]
    total_posts = scored_model_calls + void_protocol_posts
    audit: dict[str, Any] = {
        "schema_version": "1.1.0",
        "status": "PASS"
        if all(value == 0 for value in after["configured_pattern_findings"].values())
        else "FAIL_NEGATIVE_PATTERN_SCAN",
        "corpus_binding_sha256": "2821dd53d145feefc2473b09433ddd26866371788e9101965b9490213700713f",
        "corpus_manifest_sha256": sha256_file(corpus_manifest_path),
        "corpus_statistics_sha256": sha256_file(corpus_statistics_path),
        "installed_skill": {
            "name": "deslop",
            "repository": "https://github.com/stephenturner/skill-deslop",
            "commit": DESLOP_COMMIT,
            "license": "MIT",
            "use": "negative editorial pattern filter, not detector evasion",
        },
        "method": {
            "measurement_revision": "paper-facing-five-study-transition-graph-v1",
            "latex_tables_figures_and_display_math_excluded": True,
            "sentence_filter_alphanumeric_tokens_min_max": [5, 100],
            "pattern_scan": "case-insensitive regular expressions",
            "limitations": [
                "LaTeX stripping and sentence segmentation are approximate",
                "metrics guide editing ranges and do not determine scientific quality",
            ],
        },
        "before": prior,
        "after": after,
        "scientific_content_boundary": {
            "metrics_changed": True,
            "existing_terminal_records_changed": False,
            "new_scored_terminal_records_added": scored_model_calls,
            "scored_model_calls_performed": scored_model_calls,
            "void_protocol_application_posts": void_protocol_posts,
            "total_application_posts_during_revision": total_posts,
            "completed_singleton_workflows_rerun": False,
            "balanced_public_v1_rerun": False,
            "paper_binding_validator": "scripts/lint_paper_submission.py",
        },
    }
    return audit


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tex", type=Path, default=DEFAULT_TEX)
    parser.add_argument("--corpus-manifest", type=Path, default=DEFAULT_CORPUS_MANIFEST)
    parser.add_argument("--corpus-statistics", type=Path, default=DEFAULT_CORPUS_STATISTICS)
    parser.add_argument("--prior-audit", type=Path)
    parser.add_argument("--scored-model-calls", type=int, required=True)
    parser.add_argument("--void-protocol-posts", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    audit = build_audit(
        args.tex.resolve(),
        args.corpus_manifest.resolve(),
        args.corpus_statistics.resolve(),
        args.prior_audit.resolve() if args.prior_audit is not None else None,
        args.scored_model_calls,
        args.void_protocol_posts,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": audit["status"], "after": audit["after"]}, sort_keys=True))
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
