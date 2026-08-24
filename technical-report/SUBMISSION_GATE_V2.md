# ICLR/arXiv submission gate

This receipt describes the current release candidate. Machine-generated manifests and validation
receipts remain authoritative for file totals, hashes, page counts, and replay results.

## Verdict

`SCIENTIFIC_RC_READY = YES`

The final zero-context review and its single revision cycle are complete. The manuscript, anonymous
replay bundle, and local PDF package pass deterministic, privacy, replay, type, lint, formal, and
visual checks. This verdict covers the scoped scientific release candidate. Merge, public release,
OpenReview upload, arXiv upload, and archival publication require separate author authorization.

## Scientific claim boundary

- ClaimPromoteBench is a prospective synthetic test construction over two caller-supplied policy
  evaluators, a finite context set, stable identifiers, registered rule witnesses, and declared
  coverage inventories.
- Its main contribution is the source-traceable integration of finite policy differencing,
  policy-version paired route records, joint rule/action-transition suite reduction, and
  failure-inclusive model-service endpoints. The component algorithms are established machinery.
- The implementation is a finite policy-difference enumerator and suite reducer. Policy parsing,
  context synthesis, changed-rule discovery, and witness inference remain caller responsibilities.
- The deterministic policy executor defines the policy ceiling. It is an executable task
  specification rather than a learned comparator.
- The r6 multinomial Naive Bayes result is a weak shortcut control: 184/300 items and 34/150 pairs.
- The central model IDs use the same provider, base URL, OpenAI-compatible API, prompt-only output
  mode, and adapter settings. Provider-side serving internals are opaque; route differences are
  descriptive.
- The author-created balanced challenge was frozen publicly before calls, measures known-case
  robustness, and yields
  no hidden-distribution generalization estimate.
- The historical r6 Flash lane records an obsolete frozen service-interface failure. A later
  executable Flash route establishes only that the later service path ran successfully.
- Every scheduled transport, syntax, schema, and semantic failure remains in each end-to-end
  denominator. Failed response content is omitted from paper-facing artifacts.
- The naturalistic-candidate audit produced zero eligible cases and zero model calls. The study
  reports author policy mappings and makes no human-annotation or agreement claim.

## Evidence represented in the manuscript

- Two exact Gatekeeper revisions supply 12 action-changing pairs. Three repetitions on each of two
  hosted routes yield 144 frozen cells with one request per cell and zero client retries.
- All 63 strictly parsed Gatekeeper actions match OPA. The end-to-end losses are 12 timeouts and 69
  serialization or envelope violations, so the central hosted result concerns exact-interface
  completion.
- Independent Trivy and Cosign reproductions exercise policy-logic and verifier-interface faults
  against pinned upstream source bytes and tests.
- An authored SLSA migration instrument covers four actions, changed rules, and directed action
  transitions. Its policy-aware/profile-blind controls reach 47/60 and 0/60 pairs. Its labels and
  policies are author-defined evaluation instruments.
- The offline dual-endpoint audit recomputes strict-action and contract-action outcomes for 1,320
  previously scheduled cells without model calls.
- The r6 coverage addendum and 90-pair balanced public challenge provide auxiliary
  evidence-state diagnostics with complete confusion matrices, per-action recall, coverage,
  conditional metrics, and end-to-end metrics.

## Current package checks

- [x] `technical-report/main.tex` is the canonical scientific source.
- [x] The ICLR build uses the hash-locked official ICLR 2027 style files.
- [x] The ICLR main-text probe is within the nine-page limit.
- [x] The final ICLR PDF has 13 physical pages, an eight-page main-text probe, and references
  beginning on physical page 9; the arXiv PDF has 12 pages.
- [x] The release receipt derives physical pages and the reference boundary from the generated
  PDFs.
- [x] The arXiv PDF and source archive are generated from the same canonical manuscript.
- [x] LaTeX logs contain no unresolved citations, unresolved references, or horizontal overflow.
- [x] Every PDF font is embedded.
- [x] Every ICLR and arXiv page was rendered and inspected for overlap, clipping, crowding,
  isolated headings, table readability, and figure-caption collisions.
- [x] The anonymous source and PDF scans contain no author, affiliation, account, repository,
  workflow, or private commit identity.
- [x] The anonymous replay bundle omits provider request/response identifiers, credentials, hidden
  reasoning, raw failed responses, and free-form transport errors.
- [x] The anonymous manifest derives its file map and count from the generated tree.
- [x] A clean bundle verifies against its manifest before packaging.
- [x] A separate generated copy passes the complete reviewer replay, including Python checks,
  source validators, endpoint recomputation, selected tests, Lean builds, and `leanchecker`.
- [x] The local release-kit receipt reports `PASS` for LaTeX logs, ICLR anonymity, arXiv identity,
  embedded fonts, bundle privacy, and visual review.
- [x] The full repository gates pass: 336 pytest tests, Ruff check, Ruff format check, and mypy over
  29 configured source files.

## Final isolated review

The isolated reviewer assessed the pre-revision candidate `ddcc1d0` with zero prior-review context
and returned Weak Reject (4/10, confidence 4/5). The review found no fatal validity issue and
independently reproduced the numerical, source, minimum-suite, Python, and Lean evidence. Its three
major findings were:

1. real policy revisions were established, while the model-mediated boundary was author-created;
2. “compiler” exceeded the finite enumerator and registered-witness implementation; and
3. the hosted Gatekeeper result measured strict interface completion because every parsed action
   was semantically correct.

The revision accepted all three findings. It narrows the deployment claim, states caller
obligations, replaces compiler terminology in scientific prose, expands primary-source related
work, leads with exact-interface reliability, corrects the shared provider/API route description,
and promotes policy-aware/profile-blind controls. Moderate findings on the public freeze, Naive
Bayes, structural-suite semantics, naturalistic screening, evidence hierarchy, replay command, and
table density were also resolved. Deployment prevalence, naturalistic validity, and stochastic
fault-detection power remain open because they require external evidence.

The review and complete disposition are preserved under `docs/reviews/`. The 4/10 score describes
the pre-revision candidate; no second reviewer or post-hoc rerating was requested.

## Remaining external gates

- [ ] Confirm the final private-branch head, clean worktree, repository visibility, and draft PR
  state after all review fixes are pushed.
- [ ] Obtain a successful remote compatibility matrix when GitHub allocates a runner. Current
  private-repository failures terminate before runner allocation with `steps=[]`; they provide no
  code-regression evidence.
- [ ] Complete OpenReview profile, author, policy, and submission checks only after explicit author
  authorization.
- [ ] Complete arXiv metadata and server-preview checks only after explicit author authorization.
- [ ] Create any public release, tag, DOI, or archival identifier only after explicit author
  authorization.

## Readiness semantics

`SCIENTIFIC_RC_READY` certifies the scoped manuscript and local replay artifacts. Its scope excludes
venue acceptance, cross-provider causality, broad model-family ranking, naturalistic validity,
hidden-test generalization, account-side submission, and repository publication.
