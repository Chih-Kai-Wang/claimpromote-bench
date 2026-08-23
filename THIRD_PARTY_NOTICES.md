# Third-party notices

This private repository contains or references material governed separately from the root MIT
license.

## Model-service outputs

Frozen empirical records contain output produced through external model services. OpenCode's
Terms of Use assign Output to the user as between OpenCode and the user, to the extent permitted by
law, but also state that third-party model terms may apply. No provider-by-provider redistribution
review has been completed. A public export must therefore omit raw response text unless a release
receipt records the applicable basis. Structured decisions, parser outcomes, failure classes, and
content hashes should remain available when needed to reproduce reported metrics.

## External dataset pointers

The naturalistic-candidate files contain source pointers and metadata for CORE-Bench. They copy no
source evidence bytes and create no naturalistic benchmark cases. Any later use of upstream content
must follow the upstream license and attribution requirements.

## Software-supply-chain specifications

The SLSA-derived portability study pins public SLSA 1.2 and in-toto Attestation 1.2 specification
files by repository commit, path, and SHA-256. The study's states, four actions, precedence, and
labels are new author policy rather than copied certification decisions. A public export should
retain the source registry and upstream attribution while continuing to describe the policy as an
author operationalization. The counterfactual policy-switch profiles are also author-defined test
instruments; neither profile is a standards interpretation or deployment recommendation.

## Pinned local model snapshots

The local replication downloads, but does not redistribute, two MLX Community snapshots. The
catalog records `mlx-community/Mistral-Small-3.2-24B-Instruct-2506-4bit` as Apache-2.0 and
`mlx-community/phi-4-4bit` as MIT, with exact repository revisions and upstream model-card URLs.
The anonymous evidence contains snapshot file names, sizes, and digests, not weight bytes. Users
who reproduce inference must obtain each model from its upstream repository and comply with the
model, conversion, and dependency terms in effect there.

## Venue and software dependencies

ICLR style files come from the official ICLR 2027 style archive and are not relicensed by this
project. Python and Lean dependencies remain under their own licenses. Generated manifests and
lock files identify versions or digests but do not change those licenses.

See `DATA_LICENSE.md` and `docs/PUBLIC_RELEASE_BOUNDARY.md` before constructing a public repository.
