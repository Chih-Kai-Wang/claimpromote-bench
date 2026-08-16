# Published independent review packages

This directory contains only **completed, unblinded, immutable** independent-review packages.
No external review package is published yet.

Prepare active reviews beneath ignored local working storage, for example:

```bash
cpb-review prepare --dataset data/alpha --out work/review-alpha
```

Do not commit an active packet or its `private-key.json`. Keep the working package private
until every reviewer has submitted and judgments are frozen. After closure, compute the
agreement report and finish adjudication before publication.

A complete package has this shape:

```text
reviews/<packet-name>/
  packet.jsonl
  packet-manifest.json
  private-key.json
  submissions/
    <one-completed-submission-per-reviewer>.json
  review-report.json
  adjudication.json   # required when review-report.json has disagreements
```

Published analyzed packages require at least two unique reviewers. `review-report.json` must
recompute byte-for-byte from the packet, private mapping, frozen gold, policy, and submission
files. When any action or reason disagreement exists, `adjudication.json` must cover every
stable disagreement ID exactly once.

CI validates both layers:

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

The analysis validator preserves `PASS`, `NEEDS_ADJUDICATION`, and `REVISION_REQUIRED` as
scientific outcomes. A negative review result is not a malformed artifact. CI fails only for
missing, stale, tampered, incomplete, or non-reproducible material.

An empty directory is reported as `PENDING`; it is not evidence of external review. No
reviewer, agreement score, or gate result may be claimed until a complete package is present.

See [`docs/REVIEW_WORKFLOW.md`](../docs/REVIEW_WORKFLOW.md) for preparation, reviewer
instructions, metric definitions, adjudication, privacy boundaries, and release rules.
