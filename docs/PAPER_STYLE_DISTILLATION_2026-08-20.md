# Paper-writing distillation for ClaimPromoteBench

Date: 2026-08-20

This note records a writing/presentation distillation pass used to revise the ClaimPromoteBench manuscript. It is about **research communication patterns**, not copying wording or stylistic quirks from any individual author.

## Corpus

The broad scan covered **50+ award-recognized or otherwise high-signal computer-science papers** and award selections across recent top venues, with emphasis on papers whose evaluation or systems structure is relevant to ClaimPromoteBench:

- ICLR 2024 Outstanding Papers + Honorable Mentions (16 recognized papers)
- ICLR 2025 Outstanding Papers + Honorable Mentions (6 recognized papers)
- ICLR 2026 Outstanding Papers + Honorable Mention (3 recognized papers)
- NeurIPS 2024 and 2025 Best Paper / runner-up selections
- ICML 2024 and 2025 award selections
- ACL 2024/2025 Outstanding Paper selections, especially evaluation, abstention, language-model, and benchmark work
- OSDI 2025 Jay Lepreau Best Paper work, especially *Basilisk: Using Provenance Invariants to Automate Proofs of Undecidable Protocols*
- SIGCOMM 2025 Best Paper / Best Student Paper selections
- directly relevant benchmark/research-agent work already cited by ClaimPromoteBench, including CLAIM-BENCH, ScienceAgentBench, CORE-Bench, DeepFact, OSVBench, SeekBench, AbstentionBench, Omni-Decision, EviGraph, and ClaimLedger

Primary award/program sources used for the scan:

- https://blog.iclr.cc/2024/05/06/iclr-2024-outstanding-paper-awards/
- https://blog.iclr.cc/2025/04/22/announcing-the-outstanding-paper-awards-at-iclr-2025/
- https://blog.iclr.cc/2026/04/23/announcing-the-iclr-2026-outstanding-papers/
- https://blog.neurips.cc/2024/12/10/announcing-the-neurips-2024-best-paper-awards/
- https://blog.neurips.cc/2025/11/26/announcing-the-neurips-2025-best-paper-awards/
- https://icml.cc/virtual/2024/awards_detail
- https://icml.cc/virtual/2025/awards_detail
- https://aclanthology.org/
- https://www.usenix.org/conference/osdi25/presentation/zhang-tony
- https://conferences.sigcomm.org/sigcomm/2025/program/papers-info/

The ICLR award committees explicitly cite exceptional writing/presentation and experimental rigor among award criteria. The ICLR 2024 committee specifically praised papers that identify a concrete issue, understand why it occurs, and then give a simple solution; it also singled out clarity and systematic insight. ICLR 2026 highlighted scalable diagnosis and exceptional experimental design in a negative/diagnostic evaluation paper. ICML reviewer guidance separately scores presentation quality (writing, clarity, and contextualization), reinforcing that communication is part of technical quality rather than cosmetic polish.

## Distilled patterns

### 1. One paper, one central question

Strong papers can contain many technical components, but the introduction makes one question dominant. Supporting machinery is subordinated to that question instead of becoming a second story.

**Applied rule:** ClaimPromoteBench centers one question: *does the available evidence license the requested claim-state transition under a frozen policy?*

### 2. Open with the failure mode, not the field overview

High-impact papers often begin with the concrete failure or tension that motivates the work. General background follows only as needed.

**Applied rule:** start with the fact that a research agent can possess valid evidence and still overstate what the evidence licenses.

### 3. Problem -> gap -> idea -> evidence -> implication

Across ML, NLP, systems, and networking papers, abstracts repeatedly follow this five-move sequence. The strongest abstracts put the primary quantitative result before secondary details.

**Applied rule:** the ClaimPromoteBench abstract should surface the 73.99% format-error rate and all-ALLOW parseable raw intent before discussing enforcement details.

### 4. Distinguish mechanism from outcome

Systems papers are especially disciplined about separating the mechanism they introduce from the outcome observed in evaluation.

**Applied rule:** raw model intent and deterministic gate behavior must never share a column whose semantics change by row. The main results table reports raw behavior only; a separate table reports post-gate system behavior.

### 5. Make the main result impossible to miss

Award-recognized benchmark papers do not bury the headline phenomenon under a long metric inventory. They state the phenomenon, then use detailed metrics to characterize it.

**Applied rule:** Results begins with three headline findings: structured-output failure, all-ALLOW raw intent, and conditional gate enforcement.

### 6. Negative results are diagnoses, not apologies

Recent award papers include negative or limitation-revealing findings when the experiment cleanly isolates an important failure mode. The paper should explain what the failure teaches, not apologize for failing to obtain a positive ranking result.

**Applied rule:** ClaimPromoteBench presents the frozen small-model result as a diagnosis of the interface between probabilistic generation and deterministic governance.

### 7. Put caveats adjacent to strong numbers

A number such as effective FPR = 0 is easy to overread. Strong evaluation papers report the conditioning set or coverage at the same time as the headline rate.

**Applied rule:** every gate claim is paired with decision coverage, and the text explicitly rejects interpreting conditional FPR = 0 as full-system reliability.

### 8. Contributions should be few and non-overlapping

Long contribution lists often expose that the manuscript is listing implementation details rather than communicating conceptual advances.

**Applied rule:** compress seven contributions into four: task/benchmark, artifact-bound design, raw-vs-enforced evaluation, and the frozen empirical/human findings.

### 9. Use figures/tables to answer one question each

Strong tables have stable semantics across rows and columns. Captions are self-contained enough that a reader can understand what is being compared without reconstructing the method section.

**Applied rule:**

- overview figure: input -> raw intent -> deterministic enforcement -> effective action;
- raw-results table: raw model behavior only;
- gate table: raw-vs-effective behavior only;
- human-audit table: human policy application only.

### 10. Discussion should separate what is established from what is not

This is particularly important for papers about safety, verification, evaluation, and formal methods, where a narrow guarantee can be mistaken for a broader claim.

**Applied rule:** Discussion is structured as (a) what v1 establishes, (b) what it does not establish, and (c) the systems design implication.

### 11. Group limitations by threat class

A long undifferentiated bullet list is hard to reason about and makes some threats look more severe or less severe than they are.

**Applied rule:** group limitations into external validity, measurement, causal interpretation/infrastructure, and benchmark construction.

### 12. Keep provenance exact but move low-level identifiers out of the narrative path

Systems and reproducibility papers preserve exact artifacts while avoiding unreadable hashes in the main argument.

**Applied rule:** keep the authoritative run/commit/study identities, abbreviate display hashes in prose, and retain full identities in the repository and recovery provenance.

### 13. Avoid stacked nominalizations and internal project language

Readable top-conference prose prefers verbs and concrete nouns. Phrases such as “policy-governed evidence-state transition admissibility evaluation” are technically precise but expensive to parse.

**Applied rule:** use the formal term where needed, but alternate with direct language such as “whether the evidence licenses the requested transition.”

### 14. State the evaluation boundary before a reviewer has to ask

The strongest empirical papers make scope conditions explicit: model family, benchmark domain, conditioning set, and whether a result is about a model or a system.

**Applied rule:** small-model scope, conditional gate metrics, gate-prompt disclosure, and infrastructure identity drift remain visible in the main paper.

### 15. Treat reproducibility as part of the argument

Top systems and benchmark papers increasingly make artifacts, replay, and provenance part of the scientific evidence, but the main narrative still explains *why* the controls matter.

**Applied rule:** the hidden commitment, exact prompt freeze, artifact-only recovery, and no-rerun rule remain in the manuscript, but are explained as protections against post-hoc flexibility rather than as repository trivia.

## Revision checklist derived from the corpus

- [ ] Title is direct and avoids unnecessary stacked nouns.
- [ ] Abstract follows problem -> gap -> benchmark -> primary result -> implication.
- [ ] Introduction states one research question and no more than four contributions.
- [ ] Core pipeline is visible in one compact figure.
- [ ] Main result is stated before the detailed tables.
- [ ] Every table uses one semantic layer throughout.
- [ ] Raw model intent and post-gate behavior are never mixed in one metric column.
- [ ] Coverage appears next to conditional safety metrics.
- [ ] Negative results are interpreted without overclaiming.
- [ ] Discussion has explicit “establishes / does not establish / implication” structure.
- [ ] Limitations are grouped by threat class.
- [ ] Exact artifact provenance remains reproducible without dominating prose.
- [ ] No absolute novelty claim (“first benchmark/system”) unless independently justified.
- [ ] No stale pre-result language remains.
- [ ] No TeX macro-spacing, unresolved-reference, overflow, anonymity, or metadata defect survives the submission build.
