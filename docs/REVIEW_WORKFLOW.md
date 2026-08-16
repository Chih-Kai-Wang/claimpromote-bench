# Blinded independent review workflow

**Status: INFRASTRUCTURE READY; EXTERNAL REVIEWS PENDING.** No person is represented as an
external reviewer, and no empirical agreement result is claimed.

The workflow checks whether independent humans can apply the versioned transition policy to
benchmark items without seeing gold labels or model outputs. It is a policy and annotation
audit, not an independent reproduction of a model experiment.

## Privacy and blinding boundary

A working review package contains:

```text
work/review-alpha/
  packet.jsonl
  packet-manifest.json
  private-key.json
  submissions/
```

`packet.jsonl` removes item ID, pair ID, split, family, and gold fields. Its item order and
public review IDs are derived with HMAC-SHA256 from a random 32-byte secret. The packet
manifest binds the dataset manifest, policy, evaluation time, item count, packet bytes, and
blinding method.

`private-key.json` contains the secret and the mapping back to dataset item IDs. Keep the
entire working directory private until every reviewer has returned a final submission. Send
reviewers only:

- `packet.jsonl`;
- `packet-manifest.json`;
- the exact manifest-bound policy file;
- their initialized submission draft;
- these instructions.

Do not send `private-key.json`, `gold.jsonl`, pair descriptors, model outputs, aggregate
scores, a disagreement list, or another reviewer's submission.

This is procedural blinding, not contamination-proof blinding. Alpha inputs and gold are
public in the repository, so reviewers must attest that they did not inspect them during the
review. A future hidden review set must be packetized before its gold labels are disclosed.

## Prepare a packet

```bash
cpb-review prepare \
  --dataset data/alpha \
  --out work/review-alpha
```

The command generates a cryptographically random secret. To reproduce the same packet, place
exactly 64 hexadecimal digits in a private file and pass:

```bash
cpb-review prepare \
  --dataset data/alpha \
  --out work/review-alpha \
  --secret-file private/review-secret.txt
```

Preparation fails if the output directory is non-empty. It first validates the complete
source dataset, then checks the generated packet, HMAC mapping, payload equality, policy hash,
and dataset-manifest hash.

## Initialize one reviewer submission

```bash
cpb-review init-submission \
  --package work/review-alpha \
  --reviewer-id reviewer-01 \
  --out reviewer-01.json
```

The generated draft is deliberately invalid until completed. Every action and confidence is
`null`, every reason list is empty, and every attestation is `false`. This avoids pre-filling
a default action that could bias the reviewer.

For every blinded item, the reviewer supplies:

- `action`: `ALLOW`, `HOLD`, `DEMOTE`, or `ESCALATE`;
- one or more reason codes from the bound policy;
- confidence from 1 to 5;
- an optional rationale of at most 2,000 characters.

An `ALLOW` decision must use only `POLICY_SATISFIED`. A non-`ALLOW` decision may not use that
reason. Reviewers also complete a timezone-aware completion timestamp and affirm that the
work was independent, used no gold or model output, involved no collaboration, and may be
released after unblinding.

## Validate returned submissions

```bash
cpb-review validate-submission \
  --dataset data/alpha \
  --package work/review-alpha \
  --submission reviewer-01.json
```

Validation fails closed for:

- stale dataset, policy, packet, or manifest hashes;
- a forged or altered HMAC mapping;
- payload differences from the bound dataset;
- missing, duplicate, or unknown blinded item IDs;
- unknown policy reason codes;
- invalid action/reason combinations;
- missing independence attestations;
- malformed or timezone-free completion timestamps.

Place accepted files under `work/review-alpha/submissions/`, using one file per reviewer. Then
validate the completed package:

```bash
cpb-review validate-package \
  --dataset data/alpha \
  --package work/review-alpha
```

Reviewer IDs must be unique. The validator never infers missing judgments and never treats an
incomplete item as `HOLD`.

## Freeze submissions before unblinding

Do not run the agreement report while reviewers can still change their submissions. First:

1. validate each submission;
2. record its SHA-256;
3. declare the review closed;
4. prohibit further reviewer edits;
5. reveal the private mapping only after closure.

Any correction after closure creates a new submission hash and therefore a new review
package revision. Never silently replace a reviewed decision.

## Compute the agreement report

After unblinding, generate the deterministic report:

```bash
cpb-review-report analyze \
  --dataset data/alpha \
  --package work/review-alpha \
  --out work/review-alpha/review-report.json
```

The report binds the packet, dataset manifest, policy, and every submission hash. It computes:

### Reviewer versus frozen gold

For each reviewer:

- action agreement;
- exact reason-set agreement;
- mean reason-set Jaccard similarity;
- mean confidence;
- a four-by-four action confusion matrix.

### Reviewer versus reviewer

For every reviewer pair:

- raw action agreement;
- Cohen's kappa when defined;
- exact reason-set agreement;
- mean reason-set Jaccard similarity.

Across all reviewers it also reports the unanimous-action rate and Fleiss' kappa when
defined. Kappa is diagnostic rather than the primary gate because class imbalance and
degenerate marginals can make it unstable or undefined.

### Conservative review thresholds

The action gate requires all of the following:

```text
reviewer_count >= 2
EVERY reviewer action agreement with gold >= 0.80
MINIMUM reviewer-pair raw action agreement >= 0.80
```

The gate does not use an average that could hide one poor reviewer or one poorly agreeing
reviewer pair. Reason-code agreement is reported and adjudicated, but is not currently a
separate numeric pass threshold.

## Disagreement export

Every item with any of the following is exported with a stable SHA-256 disagreement ID:

- a reviewer action differs from gold;
- reviewers disagree on action;
- a reviewer reason set differs from gold;
- reviewers disagree on the reason set.

The export contains the unblinded item ID, pair ID, family, gold decision, reviewer decisions,
confidence, and rationale. It is generated only after review closure and must not be sent back
to active reviewers.

## Adjudicate every disagreement

Create a deliberately incomplete draft:

```bash
cpb-review-report init-adjudication \
  --report work/review-alpha/review-report.json \
  --adjudicator-id adjudicator-01 \
  --out work/review-alpha/adjudication.json
```

Every disagreement starts as `UNRESOLVED`, with no recommendation and an empty note. The
adjudicator chooses exactly one disposition:

- `KEEP_GOLD`: the frozen item and policy remain unchanged;
- `REVISE_ITEM`: the item is ambiguous or incorrect and needs a new dataset version;
- `REVISE_POLICY`: the policy is ambiguous or incomplete and needs a new version;
- `UNRESOLVED`: further review is required.

`KEEP_GOLD` must reproduce the exact frozen action and reason list. Revision dispositions
must contain a valid recommended action and policy reason codes. Every disagreement ID must
appear exactly once; unknown, duplicate, or missing entries fail validation.

Validate the report and adjudication together:

```bash
cpb-review-report validate-adjudication \
  --dataset data/alpha \
  --package work/review-alpha \
  --report work/review-alpha/review-report.json \
  --adjudication work/review-alpha/adjudication.json
```

Adjudication cannot repair a failed agreement threshold. When any reviewer or reviewer pair
falls below 0.80, the final status remains `REVISION_REQUIRED` even if every disagreement is
marked `KEEP_GOLD`.

## Final gate meanings

| Status | Meaning |
|---|---|
| `PENDING` | Fewer than two complete independent reviewers |
| `NEEDS_ADJUDICATION` | Numeric thresholds pass, but one or more disagreements remain unresolved |
| `REVISION_REQUIRED` | A numeric threshold failed, or adjudication requires an item or policy revision |
| `PASS` | Numeric thresholds pass and every disagreement is resolved as `KEEP_GOLD`, or no disagreement exists |

A `REVISION_REQUIRED` report is a valid scientific negative result. It must remain publishable
and must not be hidden by making CI fail merely because the review did not support the current
version. CI fails only when files are missing, stale, malformed, tampered with, or not
reproducible from the immutable submissions.

## Publish only after review closure

After review, reporting, and adjudication are complete, publish the immutable directory under:

```text
reviews/<descriptive-packet-name>/
  packet.jsonl
  packet-manifest.json
  private-key.json
  submissions/
    reviewer-01.json
    reviewer-02.json
  review-report.json
  adjudication.json   # required only when disagreements exist
```

At that point the private mapping may be public because the review is closed. Repository CI
runs both integrity and analysis validation:

```bash
cpb-review validate-root \
  --dataset data/alpha \
  --root reviews \
  --allow-empty

cpb-review-report validate-root \
  --dataset data/alpha \
  --root reviews \
  --allow-empty
```

An empty root reports `PENDING`, not a passing external-review result. A published analyzed
package requires at least two reviewers and a deterministic `review-report.json`. When the
report contains disagreements, `adjudication.json` is mandatory.

## Current claim boundary

The repository currently contains no completed review package. The workflow, statistics,
and adjudication gate are executable infrastructure only. Until real independent submissions
are published and recompute successfully, external review remains `PENDING`.
