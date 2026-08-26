# Two-study release-candidate review closure — 2026-08-23

## Scope

At the user's explicit request, two context-isolated AI reviewers performed read-only, adversarial
checks of the two-study manuscript and reviewer artifact. They were not human peer reviewers,
annotators, or a source of inter-annotator agreement. Neither reviewer edited files, called a model
service, or reran a completed singleton experiment.

The review candidate excluded the quota-confounded seven-route study in full. Its 78 valid rows
were not selected as a replacement sample. The immutable records and offline failure-cause audit
remain private repository evidence only.

## Findings and resolutions

The first reviewer found no blocker or high-severity issue and raised two medium-severity points.

1. The action-recall and confusion tables covered the three learned service configurations but did
   not show the output-producing Naive Bayes reference. The manuscript now reports its four action
   recalls, balanced recall, Macro-F1, and all 16 valid-prediction confusion cells. The old r6 Flash
   interface produced no decisions, so it remains a route-level end-to-end failure in the coverage
   table and is explicitly outside the decision confusion matrix.
2. The anonymous bundle contained dead validation code for studies absent from the paper. The
   builder now projects the empirical validator onto fresh r6 and the balanced public challenge,
   emits only the balanced metrics dependency it needs, removes capable/stronger/legacy-v1 scripts,
   and rejects those paths during verification.

An independent closure reviewer then checked the regenerated bundle, PDFs, and added Naive Bayes
rows. It reported `Closure PASS`: zero blocker, high, or medium findings. The reviewer recomputed
the Naive Bayes recall vector `.5000/.8134/.0000/.0000`, balanced recall `.3284`, Macro-F1 `.3124`,
and all four confusion rows from the frozen records.

## Final verification

- Ruff lint and format pass; strict mypy reports no issues in 28 source files.
- Full pytest reports 224 passed with 83.24% branch coverage.
- The focused reviewer replay passes its Python, selected pytest, Lean build, `leanchecker`, and
  formal-fixture checks.
- The anonymous manifest lists 392 payload files; the tree and ZIP each contain 393 files including
  the manifest. Every digest matches.
- Structured privacy scans find zero non-null provider response/request identifiers and zero hidden
  reasoning fields or blocks. Final response JSON and sanitized parser text remain only in the
  confidential reviewer bundle, as its README and data-license boundary state.
- The official-style ICLR PDF has nine physical pages. Its complete main-text probe has seven pages,
  and references begin on physical page eight. The arXiv PDF has eight pages. Every page was checked
  for overlap, clipping, crowding, isolated headings, malformed glyphs, and table readability.
- Release checksums, source-archive structure, font embedding, ICLR anonymity, named arXiv identity,
  and the style-lock receipt pass.

No safely improvable blocker, high, or medium issue remains from this review cycle. Experimental
breadth, naturalistic validity, independently authored policies, stronger learned comparators, and
causal service effects require new studies and remain limitations rather than post hoc claims.
