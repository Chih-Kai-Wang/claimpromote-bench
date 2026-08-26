# Additional isolated strict-review disposition — 2026-08-22

## Scope and status

At the user's explicit request, one additional context-isolated AI reviewer examined the manuscript,
frozen evidence, anonymous reviewer bundle, and rendered release artifacts at source head
`e52cee47fd3d3cfae073de8338bb1ff1b56c7532`. The reviewer was read-only and was prohibited from
reading the earlier review disposition, migration handoff, submission gate, or commit narrative.
No model experiment, service call, or one-shot workflow was run.

This was an internal adversarial audit, not human peer review, human annotation, or evidence of
reviewer agreement. Hidden chain-of-thought is neither recorded nor claimed. The reviewer assigned a
borderline recommendation and reported zero blocker/high findings, two medium findings, and one low
finding.

## Findings and resolutions

1. **Old r6 Flash end-to-end denominator.** The manuscript defined E2E metrics over all scheduled
   cells but marked the old Flash item and pair values `N/E`. Its 300 HTTP 401 responses and zero
   model outputs now yield explicit service-configuration E2E scores of 0/300 items and 0/150 pairs.
   Conditional correctness and model efficacy remain `N/E`. Paper lint guards this distinction.
2. **Factor heterogeneity hidden by aggregates.** Existing pair-level records show wide variation
   across controlled factors. The r6 descriptive addendum now derives and self-digests all 20
   factor-level pair outcomes; the anonymous evidence validator independently recomputes them. A
   compact manuscript table reports factors, pairs per factor, coverage and E2E pair-accuracy ranges,
   and zero/perfect-factor counts for r6 Qwen and both public-challenge routes. The text names the r6
   zero-accuracy dependency-statement (0/7) and current-binding (0/8) factors and labels every
   factor-level breakdown small-support and descriptive.
3. **ClaimLedger citation type.** The cited PDF identifies its Zenodo DOI as the archived tagged
   software release. The bibliography now cites the technical report through its direct report URL
   and no longer assigns the software-release DOI to the report entry.

## Evidence boundary

The resolutions use only previously frozen and released records. They do not change any terminal
record, action, confusion cell, recall, registered hypothesis, primary item/pair endpoint, model
call, service comparison, or naturalistic-case decision. The public challenge remains public
robustness evidence, cross-service outcomes remain descriptive rather than causal, and no human
reviewer or agreement claim is introduced.

After resolution, the local Python 3.12 gates passed with 198 tests, 83.24% branch coverage, Ruff
lint and format, strict mypy, the recomputed r6 addendum check, and paper truth lint. Final anonymous
bundle replay, release packaging, privacy scans, Lean replay, and page-by-page PDF inspection are
recorded in the release validation receipt generated from resolution commit
`b3dd1d60726bc3c10ac8555d4aab1401ad9d139b`.
