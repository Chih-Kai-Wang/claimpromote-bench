# SLSA-derived policy-portability study

This directory contains a second synthetic policy ontology for ClaimPromoteBench. SLSA 1.2 and
in-toto Attestation 1.2 define the attestation and verification fields. The artifact-admission
states, action precedence, conflict rule, and labels are an author operationalization. An `ALLOW`
label is not a SLSA certification.

## Attempt boundary

The original v1 execution is permanently void. Its prompt-only route received the six output field
names but not the numeric type of `p_admissible`, whereas the strict-schema route received that
constraint through its API adapter. The incomplete records are retained under `void-attempt-v1/`
for protocol audit only. They are ineligible for manuscript metrics, model or item selection,
resumption, and prompt reissue.

`replacement-v2/` is a new prospective study, not a resumed run. It uses a new study ID, new item
IDs, new prompt bytes, and a complete decision schema visible in the identical prompt sent to each
route. The dataset contains 60 evaluation pairs and 120 items over 12 isolated factors. Its frozen
schedule contains 240 model-item cells, one application request per cell, and zero client retries.
Only an execution receipt with all 240 terminal records permits analysis.

## Evidence map

- `source-registry.json` pins the external specification bytes.
- `policy-contract.json` records the author-defined transition policy and its interpretation limit.
- `void-attempt-v1/void-receipt.json` binds the incomplete predecessor and exclusion rule.
- `replacement-v2/dataset/` contains the fresh data, gold, pair map, and credential-free prompts.
- `replacement-v2/baseline/` contains the development-trained structured action baseline.
- `replacement-v2/study-plan.json` and `request-schedule.json` bind the scored execution.

The private repository retains full audit evidence. A later anonymous or public derivative must
exclude credentials, account and provider-response identifiers, hidden reasoning, private Git
identity, and the void attempt's raw records.
