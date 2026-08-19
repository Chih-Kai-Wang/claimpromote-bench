# External policy audit v1

This directory publishes the closed evidence for the frozen 20-item ClaimPromoteBench external policy audit.

## Boundary

This audit is supplementary evidence about independent application of the frozen transition policy. It is not a model-study result, does not replace the deterministic oracle, and is not a core submission gate.

The reviewer-facing packet was frozen before review. Both returned submissions were validated against the frozen packet and hashed before unblinding. The immutable second submission contains the reviewer ID `reviwer-02`; that spelling is preserved verbatim rather than edited after closure.

## Reproduction

CI deterministically rebuilds the original blinded package from `configs/external-review-v1.json` and `data/alpha`, then runs:

```bash
python scripts/build_external_review_v1.py analyze \
  --package work/external-review-v1 \
  --submission external-audit/v1/submissions/reviewer-01-submission.json \
  --submission external-audit/v1/submissions/reviwer-02-submission.json \
  --out work/external-audit-report-v1.json

diff -u external-audit/v1/external-audit-report-v1.json \
  work/external-audit-report-v1.json
```

The stored report therefore fails closed if the packet construction, unblinding mapping, frozen gold, policy identity, submission bytes, or analysis logic no longer reproduce the published result.
