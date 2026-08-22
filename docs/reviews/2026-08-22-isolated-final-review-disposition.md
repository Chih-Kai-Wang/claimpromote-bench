# Isolated final review disposition — 2026-08-22

## Scope and status

One context-isolated AI reviewer examined the completed manuscript, frozen evidence, anonymous
reviewer bundle, validation receipts, and rendered PDFs at source head
`be523205f05e12766983a5a5cf11e8aba120ff36`. This was an internal adversarial review, not human peer
review, human annotation, or evidence of reviewer agreement. Hidden chain-of-thought is neither
recorded nor claimed; this document preserves only the actionable disposition.

The reviewer reported:

- high-severity findings: 0;
- medium-severity findings: 1;
- other high- or medium-severity findings: 0.

## Finding

The balanced public challenge registered fixed-four-class Macro-F1, but the historical analyzer
represented precision and F1 as `null` when a supported class received no predictions and then
averaged only defined class values. Flash made zero `DEMOTE` predictions, so its historical
end-to-end and conditional Macro-F1 values, `.5236761371215153` and `.6243032962151766`, omitted the
`DEMOTE` class instead of assigning it zero.

This affected two aggregate values and three per-class derived fields. It did not affect terminal
records, confusion cells, action recall, decision coverage, item accuracy, pair accuracy, or any
registered model call.

## Resolution

Commit `4ce6680d9ff7826db66fd01dcd87982a28574684`:

- defines zero division as zero for fixed-four-class precision and F1;
- reports Flash end-to-end Macro-F1 as `.39275710284113646` and conditional Macro-F1 as
  `.46822747216138244`;
- preserves `v2/balanced-public-challenge/results/aggregate.json` byte-for-byte as historical
  workflow output;
- adds `v2/balanced-public-challenge/results/reporting-correction-v1.json`, bound to the unchanged
  analyzer inputs and terminal records;
- projects the correction into the anonymous reviewer aggregate and validates it independently;
- rebuilds the manuscript PDFs, source archives, reviewer ZIP, checksums, and validation receipt.

Post-resolution validation passed with 196 tests, 83.24% branch coverage, Ruff lint and format,
strict mypy, paper truth lint, anonymous one-command evidence replay, final ZIP privacy scans, and
all tracked plus staged-anonymous Lean builds and `leanchecker` replays. Both PDFs were inspected
page by page after the correction.

## Boundary

No model experiment or one-shot workflow was rerun. The correction does not strengthen the paper's
scientific claims, turn the public challenge into hidden-test evidence, or make the cross-service
comparison causal. This completes the single final-review protocol; another final reviewer should
not be created unless the user explicitly changes that protocol.
