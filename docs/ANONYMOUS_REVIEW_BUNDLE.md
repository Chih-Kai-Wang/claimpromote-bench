# Anonymous reviewer bundle

## Purpose

The `anonymous review bundle` workflow builds a double-blind supplementary artifact from public
ClaimPromoteBench material. It is meant to let reviewers inspect and rerun the public benchmark,
selected validators, compact paper-result summaries, and public Lean evidence without revealing the
author or the public repository during review.

The bundle is supplementary validation evidence. It is not the private hidden v1 dataset, does not
contain the hidden seed, and cannot by itself reproduce the original model inference.

## Included material

The staged bundle contains:

- the public 20-pair / 40-instance alpha benchmark;
- public policies, schemas, exact-rational fixtures, and the public Lean package;
- the benchmark Python package needed for public validation;
- selected v2 diagnostic and naturalistic-boundary validators and tests;
- an anonymized compact v1 per-run result summary sufficient to validate the 24-run matrix,
  headline counts, conditional rates, coverage ranges, and Python patch-version distribution;
- an anonymized v2 public-pilot aggregate sufficient to validate the four-run / 160-decision
  matrix, coverage changes, constrained parseable count, complete-pair count, and zero raw pair
  sensitivity;
- a generated manifest binding every staged file to a SHA-256 digest;
- a one-command public review check runner.

## Deliberately excluded material

The builder excludes:

- Git history and GitHub workflow files;
- author name, institution, username, email, and public repository URL;
- v1/v2 public workflow IDs, trigger commits, and searchable public aggregate hashes;
- the private hidden v1 dataset, hidden seed, hidden prompts, and hidden raw source artifacts;
- raw human-review submissions and reviewer-identifying material;
- manuscript source and public project-status documents that could reveal identity;
- generated caches and build artifacts.

The compact v1 result summary is therefore a paper-value validation input rather than a full
hidden-study release. This limitation is stated in the bundle README.

## Fail-closed identity scan

Before packaging, the builder recursively scans staged text files for known identity and public
provenance tokens, including:

- the author name and institution;
- GitHub username, email, and direct repository path;
- frozen v1 scoring/recovery workflow IDs;
- the post-v1 pilot/recovery workflow IDs;
- known public source, trigger, and aggregate hashes;
- public branch names.

Any match stops the build. JSON Schema `$id` values are removed from staged schemas because their
public repository URLs would reveal identity. The alpha manifest is then rewritten to bind the
anonymized schema bytes.

## Automated validation

The workflow performs the following steps inside the staged artifact rather than only in the source
repository:

1. installs the staged Python package in editable mode;
2. validates the public alpha dataset and oracle labels;
3. reruns shortcut, metamorphic-invariance, and executable-fixture checks;
4. validates the anonymized v1 and v2 result summaries;
5. validates the naturalistic candidate and case-boundary rules;
6. runs the selected v2 test suite;
7. builds the staged public Lean package;
8. replays its declarations with `leanchecker`;
9. executes the public formal fixtures;
10. removes caches, rebuilds the bundle, and requires the manifest to be deterministic;
11. creates a ZIP and SHA-256 sidecar.

## Reviewer command

After extracting the bundle:

```bash
python -m pip install -e ".[test]"
python scripts/run_review_checks.py
```

The public formal replay is documented separately in the generated bundle README.

## Artifact identity

GitHub Actions artifact name:

```text
claimpromotebench-anonymous-review-bundle
```

The Actions artifact is temporary. The final submission should upload the verified ZIP itself to
the venue's supplementary-material interface or another double-blind-compatible location. Do not
link reviewers directly to the public repository during double-blind review.

## Interpretation boundary

A passing bundle shows that the included public data, validators, compact result summaries, and
public formal artifacts are internally reproducible in the staged anonymous package. It does not
show that:

- the hidden model inference was rerun;
- the private hidden dataset is publicly available;
- deterministic gate correctness is model reasoning;
- the human audit passed;
- naturalistic external validation is complete;
- the author identity may be revealed during double-blind review.

These limitations must remain visible in the paper and review artifact description.
