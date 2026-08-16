# Blinded independent review workflow

**Status: INFRASTRUCTURE READY; EXTERNAL REVIEWS PENDING.** No person is represented as an
external reviewer, and no agreement result is claimed.

The review workflow checks whether independent humans can apply the versioned transition
policy to benchmark items without seeing gold labels or model outputs. It is a policy and
annotation audit, not an independent reproduction of a model experiment.

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
scores, or another reviewer's submission.

This is procedural blinding, not contamination-proof blinding. Alpha inputs and gold are
public in the repository, so reviewers must attest that they did not inspect them during the
review. A future hidden review set must be prepared before its gold labels are disclosed.

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

## Publish only after review closure

After every reviewer has submitted and no further judgment changes are allowed, unblind the
package and publish the complete immutable directory under:

```text
reviews/<descriptive-packet-name>/
```

At that point the private mapping may be public because the review is closed. Repository CI
runs:

```bash
cpb-review validate-root \
  --dataset data/alpha \
  --root reviews \
  --allow-empty
```

An empty root reports `PENDING`, not `PASSING_EXTERNAL_REVIEW`. A published package must
contain the packet, manifest, private key, and at least one complete submission.

## What this stage does not yet claim

This first stage establishes blinded packet preparation and submission integrity. Agreement,
confusion tables, adjudication coverage, and the 0.80 review gate are computed by the next
review-analysis stage. Until real independent submissions exist, the repository must continue
to display external review as `PENDING`.
