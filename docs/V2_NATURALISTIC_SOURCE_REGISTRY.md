# ClaimPromoteBench v2 naturalistic-source registry

## Purpose

The controlled benchmark is intentionally synthetic. This registry prepares a separate
naturalistic evaluation set using public research records without changing the controlled-pair
gold labels or presenting external benchmark tasks as if they were ClaimPromoteBench items.

This document freezes source-selection rules before any v2 model scoring on naturalistic cases.
Selection is based on provenance and evidence-state usefulness, not on whether a model is expected
to succeed or fail.

## What counts as an eligible record

A candidate must expose enough public information to reconstruct an evidence snapshot and a
specific research-status question. An eligible case needs all of the following:

1. a public source URL and a stable source identifier (commit, release, paper/task ID, or archived
   record where available);
2. a concrete claim or requested conclusion rather than a generic task description;
3. at least one inspectable evidence object such as code output, reproduction result, evaluation
   report, formal artifact, experiment log, or documented contradiction;
4. a timestamp or source version sufficient to define what evidence was available at the chosen
   evaluation time;
5. a transition question that can be mapped to the existing ClaimPromoteBench state axes without
   inventing evidence that is absent from the source;
6. redistribution terms that permit the material actually copied into this repository, or else a
   pointer-only representation that stores no restricted source bytes.

A case is excluded if its label depends on private context, if the source record is ambiguous about
which artifact/result it refers to, or if author judgment would need to reconstruct missing facts.

## Labeling rule

Naturalistic cases are not labeled by looking at model outputs. For every included case, record:

- the public evidence snapshot;
- the requested transition;
- the policy clauses applied;
- the resulting action and reason codes;
- source URLs/identifiers;
- whether source bytes are copied or only referenced;
- a short note describing any unavoidable interpretation choice.

The policy is applied to the evidence actually present at the chosen time. The label does not claim
that the underlying scientific statement is true or false.

## Sampling rule

Do not select cases because they are easy, dramatic, or known model failures. Build a candidate
pool first, freeze that pool and the inclusion/exclusion decisions, then derive the evaluation set.
Where a source contains many eligible records, cap per-source contribution before inspecting model
outputs so one benchmark or research group cannot dominate the set.

The initial target is 50--100 cases if sufficient public records can be curated without uncertain
licensing or invented state. This is a target, not permission to lower inclusion standards to hit a
number.

## Initial public source pools

### CORE-Bench -- candidate pool approved for curation

- Repository: `siegelz/core-bench`
- Use case: computational reproduction records and task/repository provenance.
- Repository code license: MIT.
- Important restriction: the MIT license on the harness does not automatically establish reuse
  rights for every third-party paper repository or data capsule. Every copied artifact must still
  pass a source-level license check. Pointer-only cases may be used when copying is not permitted.
- Selection must not depend on agent leaderboard outcomes.

### ScienceAgentBench -- candidate pool approved with pointer-only default

- Repository: `OSU-NLP-Group/ScienceAgentBench`
- Use case: data-driven scientific tasks tied to peer-reviewed source publications.
- Repository code license: MIT.
- The project explicitly asks users not to redistribute the unzipped full benchmark data. Therefore
  naturalistic curation defaults to public annotation/source pointers and must not commit restricted
  benchmark data or derived copies of those files.
- Selection must not depend on reported model success/failure.

### POPPER -- not cleared for ingestion

- Repository: `snap-stanford/POPPER`
- Potential use case: hypothesis-testing and falsification records.
- Status: source pool only; do not copy or ingest records until redistribution terms for the
  specific material are verified.

## Source diversity targets

If the naturalistic set proceeds to scoring, prefer multiple evidence families rather than a large
number of near-duplicate cases from one benchmark. Desired coverage includes:

- computational reproduction success and failure;
- runtime completion/failure;
- evidence scope mismatch;
- stale or superseded evidence;
- independent vs non-independent reproduction/review;
- formal artifact scope where genuinely public formal evidence exists;
- documented contradictions or conflicting authoritative results.

These are coverage goals. Missing categories must be reported rather than filled with synthetic
records and called naturalistic.

## Leakage and contamination boundary

Naturalistic source curation is separate from model prompting. Source labels, policy decisions,
selection notes, and any evaluator-only metadata must not be rendered to the model. If a source
contains an explicit benchmark answer, the model-facing representation must be reviewed for direct
answer leakage before the case is accepted.

## Cost boundary

Curation, validation, and deterministic labeling require no paid model calls. Do not score the
naturalistic set with paid APIs as part of this branch. A future model-expansion decision may use
this set only after the controlled-pair v2 pilot establishes an evaluable output interface.

## Release boundary

Naturalistic records must carry per-case provenance and redistribution status. A public release
must omit restricted bytes and must not imply that third-party repositories or benchmark authors
endorsed ClaimPromoteBench labels.
