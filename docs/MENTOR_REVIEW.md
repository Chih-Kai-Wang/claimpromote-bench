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
publish the packet, mapping, submissions, agreement report, disagreement table, and
adjudication record as one immutable package under `reviews/`.

The review report must include:

- per-reviewer action agreement with gold;
- raw inter-reviewer action agreement;
- Cohen pairwise kappa and multi-rater nominal agreement statistics;
- action confusion tables;
- exact reason-set agreement and partial reason overlap;
- every disagreement, its adjudication, and any resulting policy or item revision;
- packet, dataset, policy, submission, and report hashes.

The primary gate is defined conservatively: every reviewer must reach at least 0.80 action
agreement with the frozen gold, and raw inter-reviewer action agreement must be at least 0.80.
Kappa is reported but is not the sole gate because class imbalance can make it unstable. If
either threshold fails, revise the policy or items, create a new version, and conduct a fresh
review rather than opening the hidden test.

External annotation review is not independent model reproduction. Both remain separate
completion requirements. Until real submissions pass the complete gate, the repository must
show external review as `PENDING`.
