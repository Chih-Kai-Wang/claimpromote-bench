# ClaimPromoteBench v2 naturalistic-case worksheet

Use this worksheet for each candidate in `v2/naturalistic-candidates.json`. It is a curation aid,
not a label form to complete from memory. Every statement must be supported by the pinned public
source at the selected evaluation time.

Do not use model outputs when deciding whether a candidate is included, excluded, or labelable.
Do not copy third-party source bytes unless the specific copied material has a verified license.
Pointer-only curation is the default.

## 1. Candidate identity

- Candidate ID:
- Sampling-rank SHA-256:
- Source repository:
- Pinned source commit:
- Source path:
- Stable commit-pinned URL:
- Source-file SHA-256:
- Candidate title / task identifier:

Confirm that these values match `v2/naturalistic-candidates.json`. A case with changed source
identity is a new candidate, not an edit to the frozen one.

## 2. Licensing and release boundary

- Source-level license reviewed: `VERIFIED` / `POINTER_ONLY` / `UNCLEAR`
- Intended redistribution mode: `POINTER_ONLY` / `COPY_VERIFIED_FIELDS` /
  `COPY_VERIFIED_ARTIFACT`
- Are any third-party source bytes copied into this repository? `yes` / `no`
- Exact file/field copied, if any:
- Evidence supporting permission to copy:
- Does the source impose a no-redistribution instruction beyond its code license?

If permission is unclear, keep only stable pointers and independently written descriptions. A
repository-level MIT license does not automatically license every paper, dataset, capsule, or
third-party artifact referenced by that repository.

## 3. Evaluation time

- Chosen evaluation timestamp in UTC:
- Why this time is meaningful:
- Source version available at that time:
- Later information intentionally excluded:

Every evidence record must have been public by the chosen evaluation time. Evidence that appeared
later cannot be used to label the earlier case.

## 4. Concrete claim and requested transition

- Claim text, written narrowly enough to match the source:
- Current research status:
- Current computation status:
- Current formal status:
- Current review status:
- Requested target research status:
- Requested target computation status:
- Requested target formal status:
- Requested target review status:

Reject the candidate if the source supports only a task instruction but no defensible claim-state
question. Do not invent a broader scientific conclusion from a benchmark task.

## 5. Evidence snapshot

For each evidence object, record:

- Evidence ID:
- Evidence type:
- Independently written description:
- Stable source pointer:
- Observed-at timestamp:
- Artifact SHA-256, if an inspectable artifact is legitimately available:
- Whether any source bytes are copied:
- What the evidence does support:
- What the evidence does **not** support:

The model-visible snapshot must not contain the oracle action, reason codes, source answers,
leaderboard outcomes, evaluator rationale, or model outputs.

## 6. Inclusion decision

- Inclusion status: `PENDING` / `INCLUDED` / `EXCLUDED`
- Was this decision made without inspecting ClaimPromoteBench model outputs? Must be `yes`.
- Inclusion/exclusion reason:
- Ambiguities that prevent inclusion:

Acceptable exclusion reasons include unclear source identity, insufficient evidence, no meaningful
transition question, unavailable evaluation time, answer leakage that cannot be removed, and
uncertain redistribution rights. Exclusion is preferable to filling a target count with weak cases.

## 7. Evaluator-only policy application

Complete this section only after the case is included and the model-visible snapshot is frozen.

- Policy version:
- Oracle action: `ALLOW` / `HOLD` / `DEMOTE` / `ESCALATE`
- Reason codes:
- Label rationale tied to specific policy clauses:
- Source checks performed:
- Unavoidable interpretation choices:
- Could a reasonable alternative interpretation change the action? Explain.

A label applies the frozen transition policy to the evidence present at the evaluation time. It does
not claim that the underlying scientific statement is ultimately true or false.

## 8. Leakage review

Verify the model-visible record contains none of the following:

- oracle action or reason codes;
- evaluator rationale;
- benchmark answer or expected numerical result;
- agent success/failure field;
- leaderboard result;
- later evidence;
- filename, ID, or wording that directly reveals the label;
- copied source text without verified permission.

Reviewer initials / identifier:

Leakage review date:

## 9. Machine validation

Save accepted case files under `v2/naturalistic-cases/*.json` using
`v2/schemas/naturalistic-case.schema.json`, then run:

```bash
python scripts/validate_v2_naturalistic_cases.py \
  --root v2/naturalistic-cases \
  --out work/v2-naturalistic-case-validation.json
```

Until at least one source-level case is defensibly included and labeled, use `--allow-empty` in CI.
The existence of the 12-candidate pool does not imply that 12 scored naturalistic cases exist.
