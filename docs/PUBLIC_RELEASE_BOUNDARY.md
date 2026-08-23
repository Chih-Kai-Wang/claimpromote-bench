# Future public-release boundary

The current development repository must remain private. A future public repository should be a
new, history-free export produced by a fail-closed builder. Deleting files from this repository and
then changing its visibility would retain unwanted material in Git history.

The manifest-bound anonymous reviewer bundle is the safest starting point for the public evidence
tree. It must still pass the licensing gate in `DATA_LICENSE.md`; anonymity filtering alone does not
establish redistribution rights.

## A. Minimum reproducibility core

- `src/claimpromotebench/`, the applicable policies and schemas, public controlled data, and
  executable or formal fixtures;
- dataset builders and scoring, audit, validation, and replay scripts used by the paper;
- selected tests that exercise the public replay path;
- the clean r6, balanced challenge, hosted SLSA-field study, and all three retained local studies
  needed to recompute every scheduled denominator, confusion cell, action recall, coverage value,
  and conditional or end-to-end metric;
- redacted full-study exclusion receipts, but no item records or model rows, from the hosted policy
  studies that exhausted shared subscription quota;
- the three local plans, model catalog, pinned revisions, snapshot and environment
  receipts, minimal MLX runner, redacted item records, and a redacted receipt for the excluded
  one-intent/zero-terminal v1 attempt; model weights remain upstream;
- the deterministic policy-migration mutation audit that binds the rule-stratified and graph-complete
  suites to their 6/10 and 10/10 registered edge-local fault-detection receipts;
- the minimum joint-adequacy smoke-suite derivation and receipt, including its 10-pair lower-bound
  certificate and the exact 20 selected items;
- the domain-independent policy-difference compiler and its cross-check that reconstructs the
  frozen 10-pair witness from the 60-pair candidate graph;
- naturalistic source pointers, frozen candidates, and the pre-model-call zero-case decision;
- the manuscript source and references when the public repository is also the paper artifact; and
- `LICENSE`, `DATA_LICENSE.md`, `THIRD_PARTY_NOTICES.md`, a concise README, and a dynamic manifest.

If raw response text is not cleared for redistribution, the public records must retain structured
decisions, parser outcomes, service and failure classes, hashes, gold labels, and pair membership.
The full unredacted archive remains private.

## B. Optional archival material

- earlier v1, formatting-pilot, GPT-5.4 public-development, and capable-extension records;
- protocol snapshots and de-anonymized workflow or artifact receipts;
- historical GitHub workflows;
- final PDFs, venue source archives, style receipt, checksums, and submission validation receipt;
- internal roadmaps and superseded protocol documents that help historians but are not needed for
  the paper's metric replay.

Optional material belongs in a separate archival release or tagged asset when it would obscure the
minimum replay path.

## C. Private or omitted material

- `docs/reviews/`, `docs/handoffs/`, account-side execution notes, and local migration records;
- private construction seeds, review-blinding keys, credentials, account identifiers, and local
  environment files;
- provider response or request identifiers, hidden reasoning or thinking blocks, and unredacted
  source envelopes under `release/reviewer-evidence-source/fresh-confirmatory/collected/`;
- the quota-confounded seven-route study, its service-specific execution records, and its private
  failure journal, which are not needed to reproduce the paper;
- the void hosted SLSA v1 attempt's raw records; retain only a public-safe exclusion receipt if
  needed to document why those records never entered model selection or manuscript metrics;
- the local v1 schema-incompatible attempt's request journal and source bindings; retain only its
  redacted receipt showing one invocation, zero terminal records, and zero retained outputs;
- the quota-confounded hosted policy-switch run's raw records, valid-output subset, conditional
  metrics, and provider errors; retain only its public-safe full-study exclusion receipt;
- the quota-confounded hosted transition-graph run's raw records, route labels, model rows,
  conditional metrics, and provider errors; retain only its public-safe full-study exclusion receipt;
- the quota-confounded 40-cell hosted minimum-suite run's raw records, route labels, model rows,
  conditional metrics, and provider errors; retain only its public-safe full-study exclusion receipt;
- local `work/`, caches, downloaded paper corpora, build directories, and machine-specific paths;
- downloaded model weights and Hugging Face caches;
- the private repository's Git history.

## Required publication gates

1. Build into an empty temporary directory from one reviewed source commit.
2. Derive the file count and every digest from the generated tree.
3. Fail on unknown fields, secrets, identities selected for removal, provider IDs, hidden reasoning,
   local paths, and any file without an allowed license status.
4. Install and replay the package outside the private checkout without model credentials.
5. Recompute the paper metrics from the exported records and compare them with the manuscript.
6. Create a new public repository from the verified export with no inherited Git history.
7. Keep the current repository private until the author explicitly approves the generated tree and
   the new repository's visibility.
