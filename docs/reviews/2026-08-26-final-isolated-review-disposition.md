# Disposition of the final isolated review

- Review date: 2026-08-26
- Reviewer: context-isolated AI reviewer with independent primary-source checks
- Pre-disposition recommendation: Reject (3/10), confidence 4/5
- Model calls added by the disposition: zero

The review found no arithmetic discrepancy, identity leak, malformed PDF page, missing font, or
fabricated central citation. It identified one blocking validity problem and five major reporting
problems: prose targets lacked policy-owner validation; the non-`ALLOW` result was a completion
gap rather than valid-but-wrong decisions; novelty was overstated relative to evolving-policy work;
the request-cap comparison was described too causally; raw hosted responses could not be
re-adjudicated from the anonymous artifact; and empirical consequentiality remained unmeasured.

## Accepted changes

- Prose-policy results now report agreement with frozen author targets. They do not use those
  mappings as policy-owner ground truth.
- The non-`ALLOW` result is decomposed into target-agreeing, complete-disagreeing, and incomplete
  outcomes. All valid items agree with their author targets; the stable/changed difference is
  attributed to completion on two author-constructed cases.
- “Output-contract intervention” is replaced by “request-cap comparison.” The paper records
  post-screen route selection, one call per cell, joint hidden/visible token budgeting, unbalanced
  non-quota transport failures, and the absence of a policy-reasoning or provider-independent
  effect.
- “Preregistered” is replaced by “prespecified and commit-frozen before inference.” The blind
  artifact's inability to independently timestamp the redacted private commit is explicit.
- The reproducibility statement now says that replay begins with parsed decisions and content-free
  terminal records. Raw response text, response hashes, provider response IDs, private metadata,
  and hidden reasoning are absent, so parsing and provider messages cannot be re-adjudicated.
- PolicyBank and ReguSim are added to the related-work discussion and comparison table. Novelty is
  framed as integration of immutable source pairs, paired cases, full route failures, and relative
  structural certificates, not as a new learning or reduction algorithm.
- The title is shortened to *ClaimPromoteBench: Paired Regression Tests for Versioned Agent
  Policies*. The historical Flash 401 lane is retained only as an exclusion boundary.

## Remaining scientific limit

No evidence-preserving edit can validate the author mappings as policy-owner intent or establish
deployment prevalence and downstream impact. Those questions require external policy-owner labels
or a field study. The revised paper treats the prose cases as a feasibility measurement against
declared targets and keeps deployment claims out of scope.
