# ClaimPromoteBench post-v1 public formatting-control pilot

## Status

**Complete, artifact-recovered, and separately labeled from the frozen v1 hidden study.**

This document reports a public diagnostic designed after the v1 hidden results were known. It must
not be described as preregistered hidden evidence, a replacement for v1, or a broad evaluation of
frontier research agents.

## Question

The v1 study found a high `FORMAT_ERROR` rate, but its earlier parse-failure records did not retain
the original free-form response text. The pilot asks a narrower question:

> If the same prompt is decoded under a JSON-schema constraint, does output coverage recover, and
> do the tested models then change their action when the policy-relevant evidence changes?

The first part tests the interface. The second tests controlled-pair evidence sensitivity after the
interface is made usable.

## Frozen protocol

| Field | Value |
|---|---|
| Dataset | public `data/alpha` |
| Controlled pairs / instances | 20 / 40 |
| Models | Qwen3-0.6B Q8_0; Qwen3-1.7B Q8_0 |
| Runtime | llama.cpp `de699957b92f490efebad149665b0dccf127eaff` |
| Prompt arm | `ledger_verifier` |
| Seed | `104729` |
| Decoding modes | free; JSON-schema constrained |
| Model calls | 40 × 2 models × 2 modes = 160 |
| Paid API / paid GPU calls | 0 |
| Gate | post-processing only; not disclosed in the prompt; no extra model call |

For each model, the free and constrained records have identical prompt SHA-256 values, model
artifact, runtime commit, seed, and hardware record. The only registered difference is
`response_format`.

## Source and recovery

- Canonical source workflow: `32291482079`
- Trigger commit: `f998a05fec36b84e59230fe241f1e9961647ad2e`
- Qwen3-0.6B source artifact: `claimpromotebench-v2-pilot-qwen3-0.6b`
- Qwen3-1.7B source artifact: `claimpromotebench-v2-pilot-qwen3-1.7b`
- Artifact-only recovery workflow: `32297818154`
- Public aggregate: `v2/pilot-results/v2-public-pilot-study.json`
- Aggregate SHA-256:
  `sha256:eb2af5fcfce8466306a208a707e0046b389f2fd656d25d549f784acfc04199e5`

The recovery downloaded the two immutable source artifacts, required four complete 40-record runs,
validated every run record, recomputed the aggregate twice, and required byte-identical results. It
did not call either model and did not edit raw responses.

## Results

| Model | Decoding | OK | Schema errors | Decision coverage | Pair coverage | E2E action accuracy | E2E pair accuracy | Raw flip rate |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Qwen3-0.6B | Free | 30 | 10 | 0.75 | 0.70 | 0.375 | 0.00 | 0.00 |
| Qwen3-0.6B | JSON schema | 40 | 0 | 1.00 | 1.00 | 0.500 | 0.00 | 0.00 |
| Qwen3-1.7B | Free | 0 | 40 | 0.00 | 0.00 | 0.000 | 0.00 | undefined |
| Qwen3-1.7B | JSON schema | 38 | 2 | 0.95 | 0.90 | 0.475 | 0.00 | 0.00 |

Across all four runs:

- 108 of 160 decisions are parseable;
- all 108 parseable raw actions are `ALLOW`;
- there are 52 schema errors and no JSON-syntax or cross-field-semantic errors.

Across the two constrained runs:

- 78 of 80 decisions are parseable;
- 38 of 40 controlled pairs have both members parseable;
- all 78 parseable raw actions are `ALLOW`;
- raw pair accuracy is 0 on all 38 complete pairs;
- raw flip rate is 0 on all 38 complete pairs.

Schema constraints therefore raise decision coverage by 0.25 for Qwen3-0.6B and 0.95 for
Qwen3-1.7B. Complete-pair coverage rises by 0.30 and 0.90, respectively. The constraint removes 10
and 38 schema errors. Conditional raw action accuracy remains 0.50 wherever output is parseable,
and end-to-end controlled-pair accuracy remains zero.

## Failure taxonomy

The retained raw responses make the remaining interface failures inspectable:

- Qwen3-0.6B free errors chiefly represent `reason_codes` as an object rather than the required
  array.
- Qwen3-1.7B free responses represent `proposed_state` as a string such as `TARGET` or
  `FORMALLY_CERTIFIED` rather than the required state object.
- The two constrained Qwen3-1.7B errors duplicate one entry in `reason_codes`, violating the
  schema's `uniqueItems` requirement.

These responses remain errors. They are not manually repaired or rescored.

## What this result supports

For these two frozen small models on the public controlled pairs, the simplest format-only account
is insufficient. Once schema-constrained decoding makes nearly every response usable, the raw
model action still collapses to `ALLOW`, and the action never changes when the decisive evidence
prerequisite changes.

This strengthens the evidence for an **evidence-insensitive decision failure under the tested
protocol**. It also shows why instance accuracy alone is misleading: always choosing `ALLOW`
produces 0.50 instance accuracy on a balanced public set while producing 0 controlled-pair accuracy
and 0 decision flips.

## What this result does not support

The pilot does not establish that:

- larger open-weight or API-hosted models fail in the same way;
- private hidden cases would yield the same constrained-decoding result;
- natural research records are represented by the synthetic public pairs;
- schema-constrained decoding improves reasoning;
- the deterministic gate is a learned capability;
- the pilot was preregistered before the v1 limitation was known.

It uses one public dataset, one seed, and two small models. The paper must retain these limits.

## Gate interpretation

The one-way gate replaces a parseable invalid `ALLOW` with the action from the same policy oracle
used for evaluation. This is a mechanical implementation check, not an independent model result.

## Decision for the paper

The pilot is suitable for the main paper as a **post-v1 public formatting-control result** because it
directly addresses the principal v1 measurement threat and its protocol difference is verified.
It should remain secondary to the preregistered hidden study and must be described with its public,
post-v1, one-seed scope.

No further run with modified prompts, schema, seed, or decoding parameters may be presented as the
same pilot. Any such run is a new revision and requires a separately frozen protocol.
