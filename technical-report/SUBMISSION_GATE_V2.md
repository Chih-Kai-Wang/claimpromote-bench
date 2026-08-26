# ICLR/arXiv submission gate

This receipt describes the final locally verified release candidate. Machine-generated manifests
and release receipts remain authoritative for hashes, file totals, page counts, and replay results.

## Verdict

`SCIENTIFIC_RC_READY = YES`

The scoped manuscript, anonymous source-and-score replay bundle, and local PDF package pass the
required scientific, privacy, replay, type, lint, formal, and visual gates. This verdict is not an
acceptance prediction and does not authorize merge, public release, OpenReview upload, arXiv upload,
or archival publication.

## Scientific claim boundary

- ClaimPromoteBench is a prospective synthetic test protocol over two declared deterministic
  evaluators, a finite context set, stable identifiers, registered rule witnesses, and declared
  coverage inventories.
- Its supported novelty is the integration of finite executable-policy differencing,
  policy-version paired route records, joint rule/action-transition reduction, parser provenance,
  and failure-inclusive item/pair endpoints. The constituent algorithms are established.
- Policy parsing, context synthesis, changed-rule discovery, witness inference, and context
  completeness remain user responsibilities.
- The deterministic policy executor is the definitional policy ceiling, not a learned baseline.
  The imbalanced-suite Naive Bayes result is a weak shortcut control.
- Both central model IDs use the same provider/API and adapter configuration. Provider-side serving
  internals are opaque, so cross-route results are descriptive and not causal.
- The balanced challenge was fixed before inference. It measures robustness on known cases, not
  hidden-test generalization.
- The historical Flash configuration for the imbalanced suite records an obsolete service
  interface: 300 HTTP 401 outcomes before model output. Later routes establish only their own
  executability.
- Every scheduled transport, syntax, schema, and semantic failure remains in each end-to-end
  denominator. Failed response contents are excluded from reviewer-facing artifacts.
- No retained external case validates a model interpreting a changed executable policy. The study
  contains zero human annotations and makes no agreement claim.

## Evidence represented in the manuscript

- Six revisions across Gatekeeper, Trivy, Cosign, Microsoft Agent Governance Toolkit, and
  agentgateway ground policy, verifier, and adapter fault classes.
- The fixed-query screen covered 465 unique public repository seeds, inspected 11 candidates, and
  retained two boundary-fault cases with zero model calls. It is a convenience sample.
- Two Gatekeeper revisions supply 12 action-changing pairs and a two-pair structural minimum. Three
  repetitions on each of two hosted routes yield 144 scheduled cells, one request per cell, and zero
  client retries.
- All 63 Gatekeeper raw-strict actions match OPA. Twelve timeouts and 69 serialization/envelope
  failures make the central hosted result an exact-interface completion result.
- The SLSA-inspired migration covers four actions, 12 changed rules, and ten reachable directed
  transitions. Policy-aware/profile-blind controls reach 47/60 and 0/60 pairs.
- The 1,320-record endpoint reanalysis separates raw-strict, registered-parser, and full-contract action
  endpoints. Raw-strict contributes 49 correct items and 40 correct pairs outside the contract; the
  contract contributes 329 correct items and 78 correct pairs outside raw-strict.
- Six Qwen challenge responses are fenced and accepted by the registered parser. Raw-strict
  scores are 128/180 items and 46/90 pairs; full-contract scores remain 132/180 and 48/90.
- The imbalanced suite and 90-pair challenge report complete confusion matrices, every action
  recall, coverage, conditional metrics, and failure-inclusive end-to-end metrics.

## Final local checks

- [x] Python 3.12.13 virtual environment installed with `.[dev]`.
- [x] 343 full repository tests pass.
- [x] Branch coverage is 83.21%, above the 80% gate.
- [x] Ruff lint and format checks pass.
- [x] Strict mypy passes over 29 configured source files.
- [x] Paper truth lint, endpoint rebuild, source validators, and privacy checks pass.
- [x] The prose audit reports 3,322 words, 227 usable sentences, a 14-word median, a 22-word 90th
  percentile, 189 abstract tokens, and zero configured AI-writing-pattern findings.
- [x] The ICLR source uses hash-locked official 2027 style files.
- [x] The ICLR main-text probe is eight pages. The full PDF is 13 physical pages and references begin
  on physical page 9. The arXiv PDF is 12 pages.
- [x] Final LaTeX logs have no unresolved citation/reference or horizontal-overflow warning.
- [x] PDF fonts are embedded.
- [x] Both release source archives rebuild independently to 13-page ICLR and 12-page arXiv PDFs.
- [x] All 13 ICLR and 12 arXiv pages were rendered and inspected for clipping, overlap, crowding,
  isolated headings, figure-caption collisions, and table readability.
- [x] The anonymous manifest derives all 628 entries from the generated tree; the package contains
  629 files including the manifest itself.
- [x] The anonymous package excludes credentials, account identity, author provenance, provider
  request/response IDs, hidden reasoning, raw failed responses, and free-form transport errors.
- [x] A separate clean Python 3.12 environment installs the hash-locked reviewer dependencies and
  passes 27 selected tests, all source/score validators, Lean build, and `leanchecker`.
- [x] The reviewer command performs deterministic source and score replay; it does not reissue
  hosted calls.

## Final isolated review

The context-isolated AI reviewer assessed commit `6f13f72` without prior-review context and returned
Weak Reject (4/10, confidence 4/5). It found no fabricated source, numerical defect in the frozen
studies, privacy leak, or format blocker. Its material finding was an endpoint-label error: six
fenced Qwen challenge objects had been accepted by the historical registered parser while the paper
called their endpoint strict top-level JSON.

The revision corrects the raw-strict score, recall row, confusion matrix, audit schema, parser
provenance, manuscript definitions, and anonymous replay. It also accepts the review's safe changes
to novelty positioning, public-freeze wording, agentgateway replay scope, and artifact terminology.
The 4/10 score remains the only score; no second reviewer or post-hoc rerating was requested.

The review's largest scientific concern remains open because it requires new evidence: an
independently authored deployed route in which a model interprets a changed executable policy.
Deployment prevalence, cross-stack causality, naturalistic validity, and stochastic fault-detection
power are not established.

## Remaining external gates

- Obtain a successful remote compatibility matrix after GitHub allocates a runner. Current private
  repository runs terminate before runner allocation with `steps=[]`; they are not code-regression
  evidence.
- Complete OpenReview and arXiv account, author, policy, metadata, and server-preview checks only
  after explicit author authorization.
- Create a history-free public export, tag, DOI, or archival identifier only after explicit author
  authorization. Never change the development repository's visibility for publication.

## Readiness semantics

`SCIENTIFIC_RC_READY` certifies the bounded manuscript and local replay artifacts. It excludes venue
acceptance, broad model-family ranking, deployed prevalence, causal provider comparisons,
naturalistic model-policy validity, hidden-test generalization, submission, and repository
publication.
