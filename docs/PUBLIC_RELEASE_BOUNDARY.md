# Future public-release boundary

The development repository remains private. Public release should use a new, history-free export
produced by the fail-closed anonymous-bundle builder. Changing this repository's visibility would
expose material retained in Git history.

## Reproducibility core

The public tree should contain only material required to rebuild a reported result:

- benchmark code, policies, schemas, controlled datasets, executable fixtures, and selected tests;
- exact Gatekeeper, Trivy, Cosign, and Agent Governance Toolkit source revisions, upstream test
  bindings, licenses, finite case grammars, minimum-suite certificates, and offline validators;
- the frozen external discovery registry and agentgateway fixed-commit source-test receipt;
- all 144 sanitized Gatekeeper repetition records, the frozen schedule and plan, content-free
  failure classes, aggregate, and privacy receipt;
- the r6 coverage addendum, balanced public challenge, authored SLSA migration instrument, and
  retained pinned local replications used in the manuscript;
- the 1,320 content-free dual-endpoint records and validator that reconstruct strict-action and
  contract-action metrics;
- the policy-difference compiler, mutation audit, transition-coverage certificates, and minimum
  suite derivations used by the paper;
- manuscript source and references when the repository serves as the paper artifact; and
- licensing notices, a concise README, and manifests whose counts and digests are generated from
  the exported tree.

Model weights stay in their upstream repositories. Released model-service records retain the
fields needed for metric replay: item and pair identities, gold and extracted actions, endpoint
validity, terminal classes, and correctness fields. Every scheduled failure remains represented in
the end-to-end denominator.

## Material outside the public tree

The export omits:

- Git history, handoffs, internal reviews, migration notes, local paths, caches, and build trees;
- credentials, account identifiers, provider request or response identifiers, hidden reasoning,
  raw service envelopes, raw response text, and free-form transport errors;
- private construction seeds and review-blinding material;
- model weights and local model caches;
- superseded pilots, the quota-confounded route studies, Ox smoke runs, and other experiments that
  provide no manuscript result; and
- submission actions, venue credentials, and de-anonymized workflow receipts.

An archival release may preserve superseded protocols or de-anonymized provenance after review,
provided it is separate from the minimal replay tree and has an explicit license boundary.

## Publication gates

1. Build the export in an empty temporary directory from one reviewed private commit.
2. Derive every file count and digest from the generated tree.
3. Fail on unknown fields, credentials, selected identity markers, provider identifiers, hidden
   reasoning, machine-specific paths, and files lacking an allowed redistribution status.
4. Install and replay the package outside the private checkout without model credentials.
5. Recompute every manuscript result from exported records and compare it with the paper.
6. Create a new public repository without inherited history.
7. Regenerate public citation metadata and links for the new repository.
8. Keep the development repository private until the author explicitly approves the export and its
   visibility.
