# ClaimPromoteBench ICLR 2027 v2 low-cost protocol

## Purpose

This document defines a post-v1 study intended to answer the main unresolved scientific question
without silently changing the frozen v1 experiment. The immediate goal is to determine whether
the large v1 `FORMAT_ERROR` rate is mainly an output-interface problem or whether poor
policy-sensitive decisions persist after the output format is constrained.

The v1 hidden study, its labels, prompts, model outputs, normalization, and reported results remain
unchanged. Nothing in this protocol retroactively becomes part of v1.

## Cost boundary

The first pilot uses only the two model artifacts already used in v1 and the public 20-pair alpha
dataset. It runs on standard GitHub-hosted CPU runners in this public repository. No paid model API,
paid GPU runner, or new external reviewer is required by this pilot.

Do not add a paid API model or paid runner to this protocol without a separate explicit decision.
Larger open-weight models may be considered only after the pilot shows that the interface has been
stabilized enough for a broader comparison to answer a scientific question rather than reproduce
format failures.

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

No threshold is allowed to convert an inconvenient pilot result into a hidden rerun. Any change to
the prompt, decision schema, runtime, decoding settings, or pilot dataset after observing outputs is
a new pilot revision and must be labeled as such.

## Promotion to an ICLR-facing v2 study

A full v2 study should be launched only after the pilot supports an evaluable interface. The full
study should then add evidence breadth rather than merely multiplying calls:

### A. New primary split

Construct a new v2 development/hidden split after the pilot interface is frozen. Preserve controlled
pairs and factor identities. Commit the hidden dataset and exact prompts before scored inference.
Raw response text must be retained in the v2 source artifacts.

### B. Naturalistic research records

Add a separate, clearly labeled naturalistic set sourced from public research records. Its purpose
is external validity, not replacement of the controlled benchmark. Every case should include source
provenance, an evidence snapshot, the requested transition, and a policy-grounded label. Sources and
labeling rules must be frozen before model scoring.

### C. Model breadth under a cost cap

The minimum no-new-spend matrix is the two existing Qwen3 models. If the pilot is informative and
standard public GitHub runners can execute them within resource limits, prefer one or two stronger
open-weight models before considering any paid API. Candidate additions must have a pinned public
artifact, a recorded hash, and the same prompt/decoding protocol.

### D. Analysis

The ICLR-facing result should emphasize controlled-pair evidence sensitivity, complete-pair
coverage, failure taxonomy, factor-level failure patterns, and the difference between raw model
behavior and deterministic post-processing. Instance accuracy alone is insufficient.

## Human-review constraint

No new human-review requirement is introduced here. The existing two-reviewer v1 audit remains
reported exactly as observed. If additional reviewers become available later, their work should be
a separately frozen supplementary audit rather than a condition for running the technical v2 pilot.

## Integrity boundary

The following are prohibited:

- overwriting or relabeling v1 hidden data;
- rerunning v1 and presenting the new outputs as the original preregistered study;
- manually fixing raw v2 model responses before scoring;
- selecting only favorable factors or seeds after seeing the pilot;
- treating post-gate correctness as model correctness;
- paying for API/GPU inference without a separate cost decision.
