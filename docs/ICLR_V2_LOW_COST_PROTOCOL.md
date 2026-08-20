# ClaimPromoteBench ICLR 2027 v2 low-cost protocol

## Purpose

This document defines a post-v1 study intended to answer the main unresolved scientific question
without silently changing the frozen v1 experiment. The immediate goal is to determine whether
the large v1 `FORMAT_ERROR` rate is mainly an output-interface problem or whether poor
policy-sensitive decisions persist after the output format is constrained.

The v1 hidden study, its labels, prompts, model outputs, normalization, and reported results remain
unchanged. Nothing in this protocol retroactively becomes part of v1.

## Initial-pilot cost boundary

The first pilot uses only the two model artifacts already used in v1 and the public 20-pair alpha
dataset. It runs on standard GitHub-hosted CPU runners in this public repository. No paid model API,
paid GPU runner, or new external reviewer is required by this pilot.

The later capable-model study was authorized, frozen, and recorded under its own plan after this
pilot established an evaluable interface. Its calls and limits do not retroactively change the
zero-paid-call public pilot.

## Pilot freeze

The one-shot pilot is fixed as follows before any v2 model output is observed:

- dataset: `data/alpha`, 20 controlled pairs / 40 instances;
- model artifacts: the frozen Qwen3-0.6B Q8_0 and Qwen3-1.7B Q8_0 artifacts already recorded in
  `configs/models/`;
- runtime: llama.cpp commit `de699957b92f490efebad149665b0dccf127eaff`;
- seed: `104729`;
- model-facing arm: `ledger_verifier` only;
- model-facing prompt: identical between decoding conditions;
- decoding conditions: `free` and `json_schema`;
- constrained output: llama.cpp `response_format` generated from
  `schemas/agent-decision.schema.json`;
- full raw response text: retained for every item in both conditions;
- failure taxonomy: `JSON_SYNTAX_ERROR`, `SCHEMA_ERROR`, `SEMANTIC_ERROR`, or `OK`;
- deterministic gate: computed after generation from the same raw response, never disclosed in the
  pilot prompt and never requiring a second model call;
- primary pilot unit: the controlled pair.

The resulting model-call count is 40 instances x 2 decoding modes x 2 models = 160 decisions.
The gate comparison adds zero model calls because it is evaluated from the same response.

## Pilot outcomes

For every model and decoding condition, report:

1. decision coverage;
2. syntax, schema, and semantic failure counts;
3. raw action accuracy among covered decisions;
4. raw false-promotion rate and valid-promotion recall among covered decisions;
5. complete-pair coverage;
6. exact controlled-pair action accuracy;
7. raw decision flip rate across covered controlled pairs;
8. post-gate action and pair accuracy on the same covered responses;
9. the same pair metrics by policy factor.

Raw response text is diagnostic evidence. It must not be manually repaired before scoring.

## Completed pilot result

The canonical source workflow is `32291482079`, triggered by commit
`f998a05fec36b84e59230fe241f1e9961647ad2e`. Artifact-only recovery workflow `32297818154`
downloaded both immutable model artifacts, required the four-run / 160-record matrix, recomputed
the aggregate twice, and required byte-identical output. The public aggregate is
`v2/pilot-results/v2-public-pilot-study.json`, with SHA-256
`sha256:eb2af5fcfce8466306a208a707e0046b389f2fd656d25d549f784acfc04199e5`.

| Model | Decoding | OK | Schema errors | Decision coverage | Pair coverage | Raw action accuracy | Raw pair accuracy | Raw flip rate |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Qwen3-0.6B | Free | 30 | 10 | 0.75 | 0.70 | 0.50 | 0.00 | 0.00 |
| Qwen3-0.6B | JSON schema | 40 | 0 | 1.00 | 1.00 | 0.50 | 0.00 | 0.00 |
| Qwen3-1.7B | Free | 0 | 40 | 0.00 | 0.00 | undefined | undefined | undefined |
| Qwen3-1.7B | JSON schema | 38 | 2 | 0.95 | 0.90 | 0.50 | 0.00 | 0.00 |

Across the constrained runs, 78 of 80 decisions are parseable and 38 of 40 pairs are complete.
Every parseable action remains `ALLOW`; raw pair accuracy and raw flip rate remain zero. Schema
constraints therefore solve most of the output-contract problem without recovering sensitivity to
the policy-relevant evidence change for these two models on the public set.

The two remaining constrained errors duplicate an entry in `reason_codes` and are retained as
schema errors. No response is manually repaired.

A complete scientific interpretation and limitation record is in
`docs/V2_PUBLIC_PILOT_RESULTS.md`.

## Interpretation rules

The pilot is an interface-selection study, not the new ICLR primary result.

- If schema-constrained decoding sharply increases coverage but raw pair accuracy remains poor, v1's
  central evidence-sensitivity concern survives the formatting control and a larger v2 study is
  justified.
- If schema-constrained decoding increases both coverage and pair accuracy substantially, the v1
  all-`ALLOW` result should be interpreted more strongly as an interaction between the small models
  and the original interface. The paper must not hide that correction.
- If constrained decoding itself remains unreliable, do not spend money on a large model matrix.
  Fix or redesign the interface on public pilot data first, then freeze a new protocol.
- Gate performance is never evidence of model learning. In v2 it is a pure post-processing result
  because the model-facing prompt is identical with and without the gate.

The observed result follows the first branch: coverage rises sharply, but raw controlled-pair
accuracy remains zero. This supports reporting the pilot as a post-v1 public formatting control.
It motivated a bounded stronger-model study whose continuation rule remained independent of
accuracy and action distribution.

No threshold is allowed to convert an inconvenient pilot result into a hidden rerun. Any change to
the prompt, decision schema, runtime, decoding settings, or pilot dataset after observing outputs is
a new pilot revision and must be labeled as such.

## Completed exploratory capable-model hidden extension

The separately frozen extension reuses the committed 150-pair / 300-instance hidden split and the
`ledger_verifier` prompt. It registers six model labels plus one same-label service-path
replication. Transport and parser error classes led to registered adapter amendments and
requalification on the same deterministic 12 pilot inputs. The recorded inspection procedure did
not use actions, raw responses, gold comparisons, or accuracy, but the analyses were not
independently escrowed. The extension is therefore adaptive and exploratory, not confirmatory.

Fourteen pilot attempts were executed and are all released. Two lanes reach terminal qualification
and receive one fresh 300-item no-retry pass; the other five stop before full scoring. The table is
a post-hoc sensitivity that excludes the 12 reused pilot instances and their six pairs:

| Full-pass lane | Decision coverage | Pair coverage | E2E action accuracy | E2E pair accuracy | Raw FPR |
|---|---:|---:|---:|---:|---:|
| Qwen3.7-Max | 0.990 | 0.979 | 0.938 | 0.875 | 0.071 |
| DeepSeek-V4-Flash | 0.913 | 0.826 | 0.628 | 0.257 | 0.689 |

The always-`ALLOW` baseline has 0.500 action accuracy and zero pair accuracy. The aggregate is
`v2/capable-hidden-results/capable-hidden-study.json`, SHA-256
`sha256:abfc25e9a01018bdc269b683cbf54ca423264f62cacbbfee0d504ef10beb6f91`.

All 14 pilots, both full passes, three historical request/parser snapshots, prompts, hidden inputs
and labels, raw responses, parser outcomes, canonical-selection map, and recomputation inputs are
included in the anonymous reviewer evidence. The construction seed remains excluded. Lane
differences are descriptive; the study does not identify causal provider, model-tier, or
serving-stack effects.

## Remaining external-validity work

### A. New primary split

A later benchmark version may construct a fresh development/hidden split after its interface is
frozen. It should preserve controlled pairs and factor identities, commit exact prompts before
scored inference, and retain raw response text. The completed public pilot and capable extension
keep their current labels and are never renamed as a new primary split.

### B. Naturalistic research records

Add a separate, clearly labeled naturalistic set sourced from public research records. Its purpose
is external validity, not replacement of the controlled benchmark. Every case should include source
provenance, an evidence snapshot, the requested transition, and a policy-grounded label. Sources and
labeling rules must be frozen before model scoring.

A deterministic, unlabeled, pointer-only pool of 12 CORE-Bench candidates is now frozen in
`v2/naturalistic-candidates.json`. Every record remains pending source-level review; none is yet a
scored ClaimPromoteBench item.

### C. Analysis

The ICLR-facing result should emphasize controlled-pair evidence sensitivity, complete-pair
coverage, failure taxonomy, factor-level failure patterns, and the difference between raw model
behavior and deterministic post-processing. Instance accuracy alone is insufficient.

The completed pilot demonstrates this point directly: always returning `ALLOW` yields 0.50 instance
accuracy on the balanced public set while yielding zero controlled-pair accuracy and zero flips.

## Human-review boundary

No human-subject, human-annotation, or human-policy-agreement study is part of these experiments.
Any future human audit requires a separately frozen protocol and cannot be inferred from automated
manuscript reviews.

## Integrity boundary

The following are prohibited:

- overwriting or relabeling v1 hidden data;
- rerunning v1 and presenting the new outputs as the original preregistered study;
- manually fixing raw v2 model responses before scoring;
- selecting only favorable factors or seeds after seeing the pilot;
- treating post-gate correctness as model correctness;
- spending outside a separately frozen and explicitly authorized cost boundary;
- changing the completed pilot's prompt, schema, seed, or decoding settings and calling it the same
  run.
