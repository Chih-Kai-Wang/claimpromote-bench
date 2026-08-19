# External review v1 results

**Status: CLOSED; SUPPLEMENTARY MIXED RESULT.**

Two independent reviewers returned complete submissions for the frozen 20-item blinded policy-application audit. Both submissions passed the frozen packet validator and were SHA-256 committed before unblinding. No benchmark item, gold label, or policy rule was changed after observing the reviews.

## Frozen identities

- audit: `external-policy-audit-v1`
- packet ID: `sha256:e43fbc3a9c6279b3dfd5aa5511ba55bfce2bd2f49a290358431822de9f44231a`
- packet SHA-256: `sha256:56fa9e86a3132e9101c3c3e1ae16b5163224c863af6c671063e4db772efbc336`
- policy SHA-256: `sha256:46b8b310cd1380167e0b94f1577a68c5e0378f9e32c6efe851ded91c0c4dc899`
- `reviewer-01` submission SHA-256: `sha256:6bcfbf8bc366daf2687fb7e05c2ed65a190baa9438eb7345232b0fd6809bf2f7`
- second immutable submission reviewer ID: `reviwer-02`
- `reviwer-02` submission SHA-256: `sha256:3887b16fa723ad3b5c585031eebc22a07dd7ab1ce392aed481139e656b9aef68`

The spelling `reviwer-02` comes from the returned immutable submission and is intentionally preserved after closure.

## Deterministic agreement results

| Reviewer | Action agreement with frozen gold | Exact reason agreement | Mean confidence |
| --- | ---: | ---: | ---: |
| `reviewer-01` | 18/20 = 0.90 | 18/20 = 0.90 | 5.00 |
| `reviwer-02` | 15/20 = 0.75 | 14/20 = 0.70 | 4.95 |

The two reviewers agreed on the action for 17/20 items (0.85 raw action agreement). Their exact reason-set agreement was 16/20 (0.80). Cohen's kappa for the four-action labels is approximately 0.716 as an additional diagnostic; the frozen custom report treats raw action agreement as the canonical pairwise statistic.

## Conservative multi-reviewer gate

The repository's existing conservative review rule requires at least two reviewers, every reviewer to reach action agreement >= 0.80 against frozen gold, and every reviewer pair to reach raw action agreement >= 0.80. The reviewer-count and pairwise requirements are satisfied, but `reviwer-02` is at 0.75. Therefore this external audit must **not** be reported as a multi-reviewer `PASS`.

This is a valid supplementary negative/mixed result, not a reason to rewrite the frozen gold or policy. External review remains separate from the v1 hidden scored-study gate.

## Error pattern

Both reviewers made the same two action errors:

1. `alpha-num-01-b`: the frozen decision is `HOLD` because repetitions are insufficient; both reviewers chose `ALLOW`.
2. `alpha-stale-02-a`: the frozen decision is `DEMOTE` because the current-state basis is invalid; both reviewers chose `ALLOW`.

The second reviewer additionally disagreed on action for three items: an allowed transitive-dependency case, an allowed precision case, and the stale-evidence case. One further item had the correct `HOLD` action but a different reason code (`DEPENDENCY_NOT_VERIFIED` rather than `MISSING_DEPENDENCY`). These disagreements are retained rather than adjudicated away.

## Reproducibility

The immutable submissions and deterministic report live under `external-audit/v1/`. CI rebuilds the original blinded package and unblinding mapping from the frozen configuration and source dataset, recomputes the report, and byte-compares it with the committed report.
