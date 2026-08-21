# Anonymous reviewer bundle

## Purpose

The `anonymous review bundle` workflow builds a double-blind supplementary artifact for
ClaimPromoteBench. It combines the public benchmark with privacy-filtered reviewer-release
evidence so reviewers can recompute paper-facing results without receiving repository identity,
provider response identifiers, hidden reasoning, credentials, or private construction seeds.

The bundle replays archived evidence; it does not rerun model inference. Its top-level
`MANIFEST.json` computes `file_count` and every file digest from the generated tree. Documentation
must not replace that dynamic value with a hard-coded file total.

## Included material

The staged bundle contains:

- the public 20-pair / 40-instance alpha benchmark, policy, schemas, exact-rational fixtures,
  executable checks, and pinned Lean package;
- anonymized v1 source and normalized records plus the compact 24-run result summary;
- all four public-interface pilot runs and the GPT-5.4 public-development follow-up records;
- all 14 executed capable-extension pilot attempts, both fresh full passes, protocol snapshots,
  analyses, and aggregate evidence;
- the preregistered r6 reviewer-release dataset, study plan, prompt packet, frozen baseline,
  projected C2 records, item-level final outputs, gold, analysis, redaction/equivalence receipt,
  and frozen-manifest correction overlay;
- the balanced public challenge's 90 pairs / 180 items, two one-pass lane records, analyses,
  aggregate, full confusion matrices, action-level metrics, and privacy receipt;
- the frozen 12-record naturalistic candidate pool and the bound source-level decision recording
  zero created cases, zero model calls, zero human annotators, and no agreement statistic;
- selected validation code and tests, an anonymous MIT license, a one-command review runner, and a
  generated SHA-256 manifest.

## Deliberately excluded material

The builder excludes:

- Git history, GitHub workflow files, public branch names, repository links, author name,
  institution, username, and email;
- source workflow, artifact, commit, and searchable released-digest identifiers;
- credentials, provider account identifiers, provider response/request identifiers, and
  machine-readable hidden-reasoning fields or content blocks;
- private construction seeds or salts, raw human-subject records, unused human-review workflow
  modules, manuscript source, and identity-bearing status documents;
- caches, bytecode, logs, generated work products, and unrelated build artifacts.

The original v1 archive did not retain free-form text for records classified as format failures,
so no reviewer derivative can reconstruct those bytes. The bundle preserves every archived field
used by the released analysis and states this boundary in its generated README.

## Fail-closed privacy and identity scan

Before manifesting or packaging, the builder recursively scans filenames and text for known author
and repository identity, frozen provenance tokens, common credential forms, provider response IDs,
provider account IDs, and hidden-reasoning keys/content blocks. Unknown fields in protected
empirical record types fail validation. JSON Schema `$id` values and named license provenance are
rewritten only in the anonymous derivative. Any finding stops the build.

## Automated validation

Validation runs inside the staged artifact:

1. install the staged Python package;
2. validate the public alpha dataset, oracle labels, pair contracts, shortcut resistance,
   metamorphic invariance, and executable fixtures;
3. recompute the v1, public-pilot, GPT-5.4, capable-extension, r6, and balanced-challenge results
   from included item-level evidence;
4. validate the naturalistic candidate freeze and its pre-model-call zero-case decision;
5. run the selected v2 tests;
6. build and replay the public Lean package and execute formal fixtures;
7. rebuild a fresh clean bundle and require a byte-identical manifest;
8. verify that every manifested path and digest matches disk and that no excluded file survives;
9. package the clean tree as a ZIP and produce a SHA-256 sidecar.

## Reviewer command

After extraction:

```bash
python -m pip install -e ".[test]"
python scripts/run_review_checks.py
```

The generated README documents the separate Lean replay commands.

## Artifact identity

The workflow artifact name is:

```text
claimpromotebench-anonymous-review-bundle
```

The Actions artifact is temporary. A future venue upload must use the verified ZIP itself or a
double-blind-compatible location; reviewers must not be directed to the identity-bearing private
repository during review.

## Interpretation boundary

A passing bundle establishes internal replayability of the included data, validators, archived
service outputs, and paper-facing statistics. It does not establish that model inference was
rerun, that the author-defined policy is external scientific consensus, that the deterministic
executor is a learned baseline, that naturalistic transfer was measured, or that differing service
stacks form a causal ablation.
