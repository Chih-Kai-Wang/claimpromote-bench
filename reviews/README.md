# Published independent review packages

This directory contains only **completed, unblinded, immutable** independent-review packages.
No external review package is published yet.

Prepare active reviews beneath ignored local working storage, for example:

```bash
cpb-review prepare --dataset data/alpha --out work/review-alpha
```

Do not commit an active packet or its `private-key.json`. Keep the working package private
until every reviewer has submitted and judgments are frozen. After closure, publish the full
package as:

```text
reviews/<packet-name>/
  packet.jsonl
  packet-manifest.json
  private-key.json
  submissions/
    <one-completed-submission-per-reviewer>.json
```

CI validates every published package against the current manifest-bound dataset and policy.
An empty directory is reported as `PENDING`; it is not evidence of external review.

See [`docs/REVIEW_WORKFLOW.md`](../docs/REVIEW_WORKFLOW.md) for preparation, reviewer
instructions, validation, privacy boundaries, and release rules.
