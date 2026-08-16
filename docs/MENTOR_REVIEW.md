# External review gate

## Reviewer shortlist

**Status: PENDING.** No mentor, reviewer, advisor, or collaborator is claimed yet.

By the 50-pair pilot, prepare a 12-person shortlist:

- four Taiwan-based researchers in AI for mathematics, formal methods, ML evaluation, or
  statistics;
- eight overseas faculty whose 2024–2026 work directly concerns theorem proving, agent
  evaluation, or scientific reliability.

Selection must cite one recent relevant work per person. Contact at most four people per
month using an individualized note, a two-page proposal, the 50-pair pilot, and a ten-minute
reproduction command. Do not mass-email.

## Annotation review

Before the formal experiment, at least two external reviewers independently examine 40 pairs
without item IDs, pair IDs, family labels, gold labels, model outputs, aggregate results, or
another reviewer's decisions. They label action and reason codes using the exact versioned
policy and frozen evaluation time.

Use the blinded workflow in [`REVIEW_WORKFLOW.md`](REVIEW_WORKFLOW.md). Active packet mappings
remain private until every reviewer has submitted and judgments are frozen. After closure,
publish the packet, mapping, submissions, deterministic agreement report, disagreement table,
and adjudication record as one immutable package under `reviews/`.

The executable report includes:

- per-reviewer action agreement with gold;
- per-reviewer action confusion matrices;
- exact reason-set agreement and mean reason-set Jaccard similarity with gold;
- raw action agreement for every reviewer pair;
- pairwise Cohen kappa when defined;
- pairwise exact reason agreement and mean reason-set Jaccard similarity;
- unanimous-action rate and Fleiss kappa when defined;
- every gold or inter-reviewer action/reason disagreement with a stable ID;
- packet, dataset, policy, submission, report, and adjudication hashes.

## Primary thresholds

The gate is deliberately conservative:

```text
reviewer_count >= 2
EVERY reviewer action agreement with frozen gold >= 0.80
MINIMUM reviewer-pair raw action agreement >= 0.80
```

An average is insufficient because it can hide one poor reviewer or one poorly agreeing
reviewer pair. Kappa is reported but is not the sole gate because class imbalance and
single-category marginals can make it unstable or undefined. Reason agreement is disclosed
and adjudicated but is not currently assigned a separate numeric pass threshold.

If either action threshold fails, the result is `REVISION_REQUIRED`. Adjudication cannot turn
a failed threshold into a pass. Revise the policy or items, create a new version, and conduct
a fresh blind review before opening the hidden test.

## Disagreement and adjudication rule

Even when numeric thresholds pass, every action or reason disagreement must be adjudicated.
The allowed dispositions are:

- `KEEP_GOLD`;
- `REVISE_ITEM`;
- `REVISE_POLICY`;
- `UNRESOLVED`.

The final gate is `PASS` only when numeric thresholds pass and every disagreement is resolved
as `KEEP_GOLD`, or no disagreement exists. `REVISE_ITEM` or `REVISE_POLICY` requires a new
version and fresh review; `UNRESOLVED` remains `NEEDS_ADJUDICATION`.

A negative external-review result is still valid evidence and must remain publishable. CI
checks reproducibility and completeness, not whether reviewers happened to support the
current version.

External annotation review is not independent model reproduction. Both remain separate
completion requirements. Until real submissions pass the complete gate, the repository must
show external review as `PENDING`.
