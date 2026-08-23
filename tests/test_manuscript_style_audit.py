from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_manuscript_style.py"


def module():
    spec = importlib.util.spec_from_file_location("audit_manuscript_style", SCRIPT)
    assert spec is not None and spec.loader is not None
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def test_style_audit_excludes_tables_figures_and_math() -> None:
    audit = module()
    source = r"""
Useful prose remains here.
\begin{table}Secret table words disappear.\end{table}
\begin{figure}Secret figure words disappear.\end{figure}
\[ hidden equation words \]
Another useful sentence remains here.
"""
    prose = audit.prose_from_latex(source)
    assert "Useful prose remains here" in prose
    assert "Another useful sentence remains here" in prose
    assert "Secret table" not in prose
    assert "Secret figure" not in prose
    assert "hidden equation" not in prose


def test_style_audit_records_honest_revision_call_boundary() -> None:
    audit = module()
    value = audit.build_audit(
        ROOT / "technical-report" / "main.tex",
        ROOT / "docs" / "PAPER_STYLE_CORPUS_MANIFEST_2026-08-23.json",
        ROOT / "docs" / "PAPER_STYLE_CORPUS_STATISTICS_2026-08-23.json",
        ROOT / "docs" / "MANUSCRIPT_STYLE_AUDIT_2026-08-23.json",
        720,
        480,
        1,
    )
    assert value["status"] == "PASS"
    assert value["after"]["abstract_submission_lint_tokens"] <= 220
    assert all(value == 0 for value in value["after"]["configured_pattern_findings"].values())
    boundary = value["scientific_content_boundary"]
    assert boundary["retained_scored_model_calls_performed"] == 720
    assert boundary["excluded_resource_failure_model_calls_performed"] == 480
    assert boundary["total_model_calls_performed"] == 1200
    assert boundary["excluded_resource_failure_model_rows_entered_manuscript"] is False
    assert boundary["void_protocol_application_posts"] == 1
    assert boundary["total_application_posts_during_revision"] == 1201
    assert boundary["completed_singleton_workflows_rerun"] is False
