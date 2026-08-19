#!/usr/bin/env python3
# ruff: noqa: E501
"""Integrate the frozen post-v1 public pilot into the canonical manuscript.

This is intentionally a one-way, idempotent source edit. It labels the pilot as post-v1 and public,
keeps the hidden v1 study unchanged, and refuses to run if the expected manuscript markers drift.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEX = ROOT / "technical-report" / "main.tex"

ABSTRACT = r"""\begin{abstract}
AI research agents may have valid evidence and still make a claim that is too strong. We study a narrower decision problem: given a claim, its evidence, its current status, and a requested status change, should that change be allowed under a fixed policy? We introduce \cpb, a controlled benchmark with 200 pairs over 20 policy factors, including a preregistered 150-pair hidden test. Numerical and formal cases are tied to executable artifacts, and the hidden set and exact prompts were committed before scored inference. The primary study contains 7,200 hidden decisions from two Qwen3 models, four intervention arms, and three seeds. Of these outputs, 5,327 (73.99\%) are \texttt{FORMAT\_ERROR}, and all 1,873 parseable raw decisions are \allow{}. To separate interface failure from decision failure, we also run a post-v1 public pilot with identical prompts under free and JSON-schema-constrained decoding. Constraints raise coverage from 75\% to 100\% for Qwen3-0.6B and from 0\% to 95\% for Qwen3-1.7B, but all 78 constrained parseable decisions remain \allow{}; raw pair accuracy and flip rate remain zero over 38 complete pairs. A deterministic gate blocks false promotion on covered cases, but it applies the same fixed policy as the benchmark oracle. The evidence therefore supports rule enforcement, not improved model reasoning.
\end{abstract}"""

INTRO_OLD = r"""The hidden study produced a clear negative result. Of 7,200 decisions, 73.99\% fail the required output format. Every one of the 1,873 parseable raw decisions is \allow{}, so the tested models do not distinguish allowed from disallowed transitions when they do return a valid structured answer. The gate changes the final system action on the cases it can process, but it does not fix the low coverage or the nonselective model behavior. This distinction is central to the paper."""

INTRO_NEW = r"""The hidden study produced a clear negative result. Of 7,200 decisions, 73.99\% fail the required output format. Every one of the 1,873 parseable raw decisions is \allow{}, so the tested models do not distinguish allowed from disallowed transitions when they do return a valid structured answer. A separate post-v1 public pilot then constrains the output schema while keeping the model-facing prompt fixed. Coverage rises sharply, but every constrained parseable decision is still \allow{} and no covered pair produces the required decision change. The gate changes the final system action on cases it can process, but it does not make the raw decisions selective. This separation between usable output, evidence-sensitive decisions, and rule enforcement is central to the paper."""

CONTRIBUTION_OLD = r"""  \item We report the complete hidden study, including the high format-error rate, the all-\allow{} raw behavior, the low coverage of the gate arm, and a small human audit that did not meet the preregistered pass criterion."""

CONTRIBUTION_NEW = r"""  \item We report the complete hidden study and a separately labeled post-v1 public formatting-control pilot: schema constraints recover output coverage but leave raw controlled-pair accuracy and decision flips at zero."""

PILOT_PROTOCOL = r"""
\subsection{Post-v1 public interface pilot}

After the hidden v1 results were known, we ran a separately labeled public diagnostic to distinguish output-contract failure from the transition decision itself. This pilot is not part of the preregistered primary study. It uses the 20 public alpha pairs (40 instances), the same two frozen model artifacts and llama.cpp runtime, the ledger-plus-verifier prompt, and seed 104729. For each model, the free and constrained runs have identical prompt hashes, model artifact, runtime, seed, and hardware record; the only registered difference is the llama.cpp JSON-schema response constraint. Full raw response text is retained.

The gate is applied only after generation and is not disclosed in the pilot prompt, so it adds no model calls and cannot change the model-facing condition. The matrix contains
\[
40\times 2\ \text{models}\times 2\ \text{decoding modes}=160
\]
decisions. Because the interface was selected after observing v1 and the data are public, this pilot is a formatting control and diagnostic replication, not a new hidden primary test.

"""

PILOT_RESULTS = r"""
\subsection{Public formatting-control pilot}

Table~\ref{tab:v2-pilot} reports the post-v1 public diagnostic. Schema constraints remove 10 schema errors for Qwen3-0.6B and 38 for Qwen3-1.7B. Decision coverage rises from 0.75 to 1.00 for Qwen3-0.6B and from 0 to 0.95 for Qwen3-1.7B; complete-pair coverage rises from 0.70 to 1.00 and from 0 to 0.90, respectively.

\begin{table}[t]
\centering
\small
\caption{Post-v1 public pilot. ``Schema'' uses JSON-schema-constrained decoding with the same prompt as the free condition. Accuracy is conditional on parseable output.}
\label{tab:v2-pilot}
\begin{tabular}{llcccc}
\toprule
Model & Decoding & Decision cov. & Pair cov. & Raw acc. & Raw pair acc. \\
\midrule
Qwen3-0.6B & Free & .75 & .70 & .50 & .00 \\
Qwen3-0.6B & Schema & 1.00 & 1.00 & .50 & .00 \\
Qwen3-1.7B & Free & .00 & .00 & undef. & undef. \\
Qwen3-1.7B & Schema & .95 & .90 & .50 & .00 \\
\bottomrule
\end{tabular}
\end{table}

Across all four runs, 108 of 160 decisions are parseable and every one is \allow{}. More importantly, 78 of 80 constrained decisions are parseable, covering 38 of 40 controlled pairs, yet raw pair accuracy and raw flip rate are both zero. The two remaining constrained errors are duplicate entries in the structured reason-code list and remain schema errors; they are not manually repaired. Thus, for these same small models on the public pairs, making the output contract usable does not recover sensitivity to the policy-relevant evidence change.

Post-gate action and pair accuracy are 1.0 wherever the response is parseable. As in v1, this follows from applying the benchmark policy after generation and is not evidence that the model learned the policy.

"""

DISCUSSION_MARKER = r"""The deterministic gate is still useful as an engineering safeguard. On parseable cases it changes invalid promotions to the action required by the fixed policy. But because the gate uses the same policy that defines the benchmark labels, its perfect conditional scores should be interpreted as correct rule enforcement, not as a learned capability. The practical lesson is that model quality and rule enforcement need to be measured separately."""

DISCUSSION_REPLACEMENT = DISCUSSION_MARKER + r"""

The public formatting-control pilot sharpens this diagnosis. Once the output schema is constrained, nearly all responses are usable, but the raw action remains \allow{} and the controlled-pair decision never changes. This rules out the simplest format-only explanation for these two models on the public pairs. It does not establish the same failure for larger models, private cases, or natural research records."""

LIMITATION_OLD = r"""The source records keep parse status and structured decisions but not the original free-form text for earlier parse failures. We therefore cannot separate syntax errors, schema failures, interface incompatibilities, and failures of the underlying reasoning task after the fact. The reported \texttt{FORMAT\_ERROR} rate covers all of these possibilities. Gate FPR, VPR, PTA, catch rate, and false-block rate are also conditional on covered decisions or complete covered pairs, so effective FPR=0 is not a measure of end-to-end reliability."""

LIMITATION_NEW = r"""The v1 source records keep parse status and structured decisions but not the original free-form text for earlier parse failures. We therefore cannot retrospectively separate syntax errors, schema failures, interface incompatibilities, and failures of the underlying decision task in the hidden study. The post-v1 public pilot retains raw text and shows that schema constraints recover coverage without recovering selective decisions for the same two models, but it uses public data and one seed after the v1 limitation was known. It does not reconstruct the linguistic causes of the hidden v1 failures. Gate FPR, VPR, PTA, catch rate, and false-block rate are also conditional on covered decisions or complete covered pairs, so effective FPR=0 is not a measure of end-to-end reliability."""

REPRO_MARKER = r"""The primary hidden inference comes from workflow run \texttt{32255636879}; the hidden set was committed before that run. Recovery run \texttt{32274814703} reconstructed the fixed dataset and prompt identity, validated 24 original and 24 normalized runs, and produced the 7,200-record aggregate without querying the models again. The recovered study file has SHA-256 \texttt{3eb5b534...e8bfe664}. Full commit and manifest hashes are kept in the repository and recovery record."""

REPRO_REPLACEMENT = REPRO_MARKER + r"""

The post-v1 public interface pilot comes from workflow run \texttt{32291482079}. An artifact-only recovery downloaded both model artifacts, required the complete 160-decision matrix, recomputed the aggregate twice, and obtained identical bytes. Its public aggregate has SHA-256 \texttt{83dbee49...25c0b264e}; it contains metrics and run hashes but not raw response text."""

CONCLUSION_OLD = r"""\cpb studies a simple failure that answer accuracy alone does not capture: valid evidence can still be used to justify a claim-state change that is too strong. In the hidden v1 study, the tested Qwen3 models often fail to return a valid structured decision, and every parseable raw decision is \allow{}. A deterministic gate prevents invalid promotion on the parseable cases by applying the fixed policy, but it does not improve the model's own decisions and it cannot act when the output is unusable. For research-agent evaluation, model behavior and deterministic safeguards should therefore be reported separately, with coverage shown alongside any conditional gate result."""

CONCLUSION_NEW = r"""\cpb studies a failure that answer accuracy alone does not capture: valid evidence can still be used to justify a claim-state change that is too strong. In the hidden v1 study, the tested Qwen3 models often fail to return a valid structured decision, and every parseable raw decision is \allow{}. In the post-v1 public pilot, constraining the output schema recovers nearly complete coverage but leaves all constrained parseable decisions at \allow{}, with zero raw pair accuracy and zero decision flips. A deterministic gate prevents invalid promotion on covered cases by applying the fixed policy, but it does not improve the model's own decisions. Research-agent evaluations should therefore report structured-output coverage, evidence-sensitive model behavior, and deterministic safeguards as separate quantities."""


def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"expected exactly one {label} marker, found {count}")
    return source.replace(old, new, 1)


def main() -> int:
    source = TEX.read_text(encoding="utf-8")
    if r"\label{tab:v2-pilot}" in source:
        print("v2-paper-integration: already integrated")
        return 0

    updated, count = re.subn(
        r"\\begin\{abstract\}.*?\\end\{abstract\}",
        lambda _: ABSTRACT,
        source,
        count=1,
        flags=re.DOTALL,
    )
    if count != 1:
        raise RuntimeError("abstract marker drift")
    updated = replace_once(updated, INTRO_OLD, INTRO_NEW, "introduction result paragraph")
    updated = replace_once(updated, CONTRIBUTION_OLD, CONTRIBUTION_NEW, "fourth contribution")
    updated = replace_once(
        updated,
        r"\section{Results}",
        PILOT_PROTOCOL + r"\section{Results}",
        "Results section",
    )
    updated = replace_once(
        updated,
        r"\subsection{What the gate changes}",
        PILOT_RESULTS + r"\subsection{What the gate changes}",
        "gate-results subsection",
    )
    updated = replace_once(
        updated,
        DISCUSSION_MARKER,
        DISCUSSION_REPLACEMENT,
        "discussion gate paragraph",
    )
    updated = replace_once(updated, LIMITATION_OLD, LIMITATION_NEW, "output limitation")
    updated = replace_once(updated, REPRO_MARKER, REPRO_REPLACEMENT, "reproducibility paragraph")
    updated = replace_once(updated, CONCLUSION_OLD, CONCLUSION_NEW, "conclusion")

    TEX.write_text(updated, encoding="utf-8", newline="\n")
    print("v2-paper-integration: integrated frozen public pilot")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
