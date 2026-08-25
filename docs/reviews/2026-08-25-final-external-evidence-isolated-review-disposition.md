# Disposition of the final external-evidence isolated review

- Review date: 2026-08-25
- Reviewed candidate: `6f13f72ce88bbc67880e92a69902a1e4b0cb1748`
- Reviewer: context-isolated AI reviewer
- Pre-revision recommendation: Weak Reject (4/10), confidence 4/5
- Protocol: one context-isolated review and one evidence-preserving revision

The review found one material reporting defect and no fabricated source, arithmetic defect,
privacy leak, or page-limit blocker. The revision changes no frozen response, scheduled denominator,
or model result. It makes zero model calls.

## Accepted scientific and manuscript changes

### Endpoint semantics

- The audit schema now distinguishes raw-strict action, frozen registered-parser action, full
  contract action, and exact full decision.
- Raw-strict parsing accepts exactly one duplicate-free top-level JSON object and performs no fence
  or substring extraction, repair, coercion, or non-standard constant handling.
- Registered-parser provenance records direct parsing, deterministic single-object extraction, or
  absence of an action. The anonymous bundle includes both parser implementations and parser tests.
- The balanced Qwen challenge is corrected to 128/180 raw-strict items and 46/90 raw-strict pairs.
  Its full-contract result remains 132/180 and 48/90 because the registered parser accepted six
  fenced objects, four correct actions, and two correct pairs.
- The Qwen raw-strict recalls are corrected to 77/90 ALLOW, 26/30 HOLD, 3/30 DEMOTE, and 22/30
  ESCALATE. The corresponding confusion matrix is regenerated from the retained records.
- The 1,320-record audit reports both overlap directions: raw-strict contributes 69 extractable,
  49 correct items, and 40 correct pairs outside the contract; the contract contributes 452
  extractable, 329 correct items, and 78 correct pairs outside raw-strict.

### Scope, novelty, and evidence hierarchy

- At that review stage, the paper was titled *ClaimPromoteBench: Source-Traceable Regression Testing
  of Model Services Across Policy Revisions*.
- The abstract and Introduction describe a prospective, synthetic model-service setting. They do
  not infer deployment prevalence from upstream faults.
- The contribution is stated as an integration of finite executable differencing, paired route
  records, joint structural reduction, parser provenance, and failure-inclusive endpoints.
- A compact related-work table compares behavioral/contrast testing, policy differencing and
  conformance, rule following, structured output/abstention, prompt regression, and this work by
  controlled coordinate.
- The external audit remains bounded to 465 repository seeds, 11 source reviews, and two qualifying
  boundary-fault cases. Naturalistic model-policy interpretation remains unvalidated.

### Source, freeze, and replay wording

- AGT remains an exact parent-to-fix replay. agentgateway is described as a source-audited parent
  plus an exact fixed commit that passes 33/33 selected offline tests.
- “Publicly frozen” is replaced in paper-facing claims by “author-created and commit-frozen before
  calls according to retained workflow receipts.”
- The anonymous bundle is described as deterministic source and score replay. It never claims to
  reproduce hosted inference and never reissues model calls.
- Documentation explains the inert historical SLSA runner hashes and excludes those scripts and
  results from manuscript metrics and the public core.

### Prose and reviewer usability

- The title, abstract, Discussion, Limitations, and Conclusion are narrowed to the supported test
  setting.
- Repeated operational chronology is removed or moved to the appendix. The old Flash 401 result is
  retained only as an obsolete-interface limitation and is not treated as a causal comparison.
- The prior-work table and benchmark/evidence-flow figure put caller obligations, novelty, and
  endpoint semantics beside the first relevant claims.
- The style audit measures 4,142 prose words and 276 sentences, with a 13-word median and 213-token
  abstract. All configured AI-pattern and formulaic-prose checks report zero findings.

## Verification after disposition

- 343 full repository tests pass under Python 3.12.13.
- Branch coverage is 83.21%, above the 80% gate.
- Ruff lint and format checks pass.
- Strict mypy passes over 29 configured source files.
- Paper truth lint and deterministic endpoint rebuild checks pass.
- A fresh Python 3.12 environment installs the hash-locked reviewer dependencies and passes 27
  selected tests, all source validators, all score replay, Lean build, and `leanchecker`.
- The final anonymous manifest is generated from the tree; privacy scans and file totals are not
  hard-coded in prose.
- The ICLR main-text probe is nine pages. The full ICLR PDF has 14 physical pages with references
  beginning on page 10; the arXiv PDF has 13 pages. All pages were rendered and inspected.

## Remaining evidence limits

The final review's largest scientific concern remains open: the project has no independently
authored deployed route in which a model interprets a changed executable policy. Deployment
prevalence, cross-stack causality, naturalistic validity, and stochastic fault-detection power
cannot be created through editing. The revision states these limits and makes no acceptance,
general-capability, or causal claim.

This review was later superseded by the stricter 2026-08-26 isolated review and disposition.
