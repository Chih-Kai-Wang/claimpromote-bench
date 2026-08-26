# ClaimPromoteBench Codex conversation migration — 2026-08-26

This file is the durable, sanitized handoff for the Codex task titled **完成 ICLR 論文與審核**.
It records user-visible decisions and completed repository work, not hidden reasoning, credentials,
raw browser state, or the 693 MB local event log. The private GitHub branch remains the canonical
source. When this file conflicts with `2026-08-22-mac-migration.md`, this newer handoff and the
current branch take precedence.

## Read this first

- Repository: `f0909172434/claimpromote-bench`
- Visibility: **PRIVATE**, confirmed from GitHub on 2026-08-26 (Asia/Taipei)
- Working branch: `agent/iclr2027-v2-low-cost-study`
- Draft PR: `#20`, open, targeting `paper/v1-submission-prep`
- Scientific/release head before this migration note:
  `b1d6337fd6cf1ab25244d80457717aba9da79c7f`
- Local and remote commit and tree hashes matched at the migration audit; the worktree was clean.
- Before adding this note, the branch contained 1,857 tracked files and approximately 116 MB of Git
  blobs, with 179 commits after the original takeover head
  `057e785483eed14742e63817f81bea6add579c53`.
- The original evidence anchors `1901e471bdf94f434f9671708b93599a106b1543` and
  `3746403ea8784a95ae2cb1c66ee1b95e4a67ad42` remain reachable from the current head.
- Actions run `32509532820` remains a successful one-shot validation at `1901e471...`. Later
  private-repository Actions failures with `steps=[]` are account billing or spending-limit
  allocation failures, not demonstrated code regressions.

Do not rerun completed one-shot studies, expose credentials, make the repository public, merge or
undraft PR 20, upload to arXiv, or change external submission state without fresh user authority.

## Critical publication state

An ICLR 2027 OpenReview submission **does exist**. Earlier handoff prose saying that no submission
existed is obsolete.

- OpenReview note: `8JTLEHqGRl`
- Submission number: `4338`
- Submission date: 2026-08-25 (Asia/Taipei)
- Private receipt: `docs/submissions/2026-08-25-iclr2027-openreview.md`
- Title at submission time:
  `ClaimPromoteBench: Source-Traceable Regression Tests for Model Services under Policy Revision`
- Submitted PDF SHA-256:
  `ccb67b171aa808365d02a2cacfb85c418474aacfc232ae65098e079b506bbaa8`
- Submitted supplementary ZIP SHA-256:
  `6c29c80fca2b4e33905304754d529f25a6309cacf4670d0d720fe40b866599eb`

The GitHub candidate advanced by five commits after the submission receipt, changing 104 files.
The current title is:

`ClaimPromoteBench: Paired Regression Tests for Versioned Agent Policies`

Current release hashes are:

- ICLR PDF: `4bd7f70ac7e0e220ffa3fb8db6f16310915491f832faa8775ea3db83418e9b7d`
- arXiv PDF: `745c1b6008c6cdb451832621f6bed55474c06d4bcb8045a4006451b135fbce73`
- anonymous review ZIP:
  `d42657ba3fcddaa45a812cd8b4b4102883785d05c80407b748ce7724db1555ff`

Therefore the OpenReview attachments and metadata recorded at submission time are older than the
current GitHub release candidate. The server-built PDF has not been independently downloaded and
rehashed. The next agent must not infer that OpenReview already contains the current title,
abstract, PDF, or supplement. Updating OpenReview is an external mutation and requires explicit
user authorization.

No arXiv identifier, DOI, public code release, repository visibility change, PR merge, or PR
ready-for-review transition has been recorded.

## What this conversation completed

### 1. Mac and GitHub takeover

- Installed and verified GitHub CLI on Apple Silicon macOS, completed user-driven GitHub OAuth,
  and cloned the private repository without exposing credentials.
- Checked out `agent/iclr2027-v2-low-cost-study`, inspected the migration handoff, PR 20, the
  successful Actions run, and the two original evidence commits.
- Created a Python 3.12 virtual environment, installed `.[dev]`, and used local gates while GitHub
  runners were blocked before allocation.
- Preserved PRIVATE visibility and draft PR state throughout.

### 2. Initial paper and evidence repair

- Reframed the work away from broad research-agent capability claims and toward bounded,
  failure-aware evaluation of policy-governed evidence-state transitions.
- Integrated the public balanced challenge, the r6 coverage addendum, complete confusion matrices,
  per-action recall, and conditional and end-to-end metrics.
- Corrected the balanced-challenge Flash fixed-four-class Macro-F1 reporting definition without
  changing raw outputs or primary endpoints.
- Described the old r6 Flash HTTP 401 lane as a historical service-interface failure. Later Flash
  routes prove only their own executability; differing stacks do not form a causal ablation.
- Named the deterministic policy executor the **definitional policy ceiling** and retained Naive
  Bayes only as a weak shortcut check.

### 3. Writing quality, related work, and review

- Distilled conventions from strong computer-science papers and added automated manuscript-style
  checks. The prose was repeatedly shortened to remove execution diaries, instruction residue,
  formulaic AI language, and reader-irrelevant details.
- Used a de-AI writing skill and preserved a machine-readable style audit.
- Added and source-checked work on behavioral testing, contrast sets, metamorphic testing,
  structured and constrained outputs, selective prediction, research agents, GuideBench, TDAD,
  PolicyBank, and ReguSim.
- Added a compact benchmark/evidence-flow figure and repeatedly repaired page density, float
  placement, appendix table size, isolated headings, and references.
- Ran multiple context-isolated strict reviews. Their reports and dispositions are committed under
  `docs/reviews/`; the final disposition is
  `docs/reviews/2026-08-26-final-isolated-review-disposition.md`.

### 4. Method redesign: paired policy regression

- Implemented a reusable finite policy-difference enumerator and suite reducer in
  `src/claimpromotebench/policy_difference.py`.
- Given two caller-supplied policy evaluators, a finite context grammar, registered change
  witnesses, and declared coverage inventories, it enumerates action-changing contexts, creates
  paired cases, reports relative changed-rule and directed-transition coverage, and finds a
  cardinality-minimum structural suite.
- Added exact finite claims, mutation audits, coverage receipts, generic replay code, and bounded
  optimality statements. Policy parsing, grammar construction, changed-rule discovery, and witness
  validity remain caller responsibilities.
- Repositioned the benchmark as paired regression tests for versioned agent policies rather than a
  new learning algorithm or general test-suite-reduction algorithm.

### 5. Synthetic and local policy studies

- Built SLSA-inspired four-action policy migration suites, policy-switch controls, a reachable
  action-transition graph, local-model replications, and structural minimum release gates.
- The rule suite covers 12/12 changed rules and 6/10 reachable action edges. The graph suite covers
  12/12 rules and 10/10 edges. A ten-pair suite is jointly minimum for the committed candidate pool.
- Added a policy-aware structured random-forest control and a profile-blind control. Their current
  reported results are 107/120 items and 47/60 pairs versus 57/120 and 0/60.
- Preserved and clearly excluded quota-confounded, resource-ineligible, schema-invalid, or void
  hosted attempts rather than recycling them as efficacy evidence.

### 6. Source-traceable external policy evidence

- Added immutable upstream evidence for OPA and WooCommerce `AGENTS.md` revisions.
- Added exact Gatekeeper policy revisions with 12 pairs covering 2/2 changed rules and 2/2 observed
  action edges; a two-pair suite is jointly complete for the committed grammar.
- Reproduced the Trivy KCV0030 inverted predicate on four upstream cases.
- Reproduced four Cosign/Rego verifier-interface fault modes on six cases.
- Reproduced an agent-policy verdict gap in Microsoft Agent Governance Toolkit and verified the
  fixed path against 15 upstream tests.
- Audited the agentgateway Bedrock guardrail adapter; the fixed commit passes 33/33 selected offline
  tests.
- Screened 465 public repository seeds, manually reviewed 11 candidates, and retained two
  qualifying external policy-boundary cases with source and license bindings. This was an author
  inclusion audit, not a human-label study.

### 7. Hosted route and parser diagnostics

- Preserved the original public balanced challenge: 90 pairs, 180 items, 15 factors, 90 `ALLOW`
  members, and 30 members for each restrictive action. Qwen reports 148/180 valid decisions,
  132/180 items, and 48/90 pairs end to end. Flash reports 146/180 valid decisions, 90/180 items,
  and 13/90 pairs end to end. All invalid outcomes remain in fixed end-to-end denominators.
- Audited 1,320 prior route items using raw-strict action, registered-parser action, contract action,
  and full-decision endpoints. This separated interface completion from policy agreement without
  altering frozen records or making new model calls.
- Ran a factor-complete matched-route diagnostic with three repetitions. The low-validity earlier
  breadth study was retained as route/quota evidence and not used for model-family ranking.
- Tested a free Ox Alpha route as a bounded route smoke study; it was not elevated into a broad
  capability claim.

### 8. External model-facing policy study

- Bound two public `AGENTS.md` histories to six changed pairs and four stable controls. The prose
  targets are frozen author mappings, not policy-owner ground truth.
- Eight hosted routes received the same 20 items for three repetitions: 480 scheduled calls, one
  request per cell, zero client retries.
- Designated first replication: 132/160 valid decisions, 128/160 author-target item agreements,
  and 52/80 pair agreements.
- All repetitions: 399/480 valid decisions, 387/480 item agreements, and 158/240 pair agreements.
- The 81 terminal failures comprise 26 server-side transport failures, nine length-terminated JSON
  failures, and 46 action/reason-code conflicts.

### 9. Reviewer-gap follow-up studies

- Froze and ran a non-`ALLOW` extension before inference. It contains restrictive-action stable
  controls and two `HOLD`-to-`ESCALATE` author-mapped changed pairs.
- Every valid item agrees with its author target. Stable pairs decompose into 50 target-agreeing,
  zero complete-disagreeing, and four incomplete outcomes; changed pairs decompose into 6, 0, and
  12. The evidence is a completion difference on two author-constructed cases, not an isolated
  policy-use effect.
- Ran a 360-call same-item request-cap comparison on three selected routes, one call per cell. From
  4096 to 12288 tokens, complete target-agreeing pairs change from 0/15 to 7/15, 0/15 to 9/15, and
  7/15 to 7/15. The comparison is associated with route completion and does not identify a
  provider-independent reasoning effect.
- Added a content-free transport diagnostic: 63 late quota-or-billing rejections, six server
  errors, four timeouts, and three network errors. No cell was retried or replaced.
- Stopped further OpenCode calls after the user's 2026-08-26 04:19 quota warning.

### 10. OpenReview submission and post-submission revision

- With explicit user confirmation, created ICLR 2027 OpenReview submission 4338 and recorded its
  account-side receipt in the private repository.
- Did not upload to arXiv, publish the repository, merge or undraft the PR, or create a public
  release.
- After submission, processed another strict external-evidence review and made the current title,
  abstract, claim-boundary, request-cap, replay-boundary, literature, and appendix revisions.
- The last isolated review gave a pre-disposition score of Reject 3/10 with confidence 4/5. It found
  no arithmetic discrepancy, identity leak, malformed PDF page, missing font, or fabricated central
  citation. All safe reporting corrections were implemented. The remaining scientific limit is
  external policy-owner validity and deployment consequentiality, which cannot be manufactured by
  editing prose.

## Current paper and release candidate

- Canonical source: `technical-report/main.tex`
- Title: `ClaimPromoteBench: Paired Regression Tests for Versioned Agent Policies`
- Abstract length: 186 tokens
- Reader-facing prose: approximately 4,514 words
- Configured AI/slop pattern counts: all zero
- ICLR PDF: 20 physical pages, exactly 9 main-text pages, one permitted pre-reference statement
  page, references beginning on page 11
- arXiv PDF: 18 pages
- Fonts embedded: yes
- Visual inspection: all ICLR and arXiv pages inspected; no unresolved clipping, overlap, crowded
  tables, or isolated headings recorded
- Anonymous manifest payload: 967 files; ZIP entries including manifest: 968
- Anonymous privacy scan: PASS
- Anonymous replay: Python-only replay passes 27 tests and is truthfully labeled
  `PARTIAL_PASS (Python only)` because Lean is skipped in that mode
- Full local Python suite at the final candidate: 366 tests passed
- Ruff lint and formatting: PASS
- mypy: PASS for 29 source files
- Paper truth lint and whitespace checks: PASS

The anonymous bundle starts from released parsed decisions and content-free terminal records. It
does not include raw response text, raw-response hashes, provider response IDs, private account
metadata, or hidden reasoning. A reviewer can replay source and score derivations but cannot
independently re-adjudicate the original raw-output-to-parser transformation or provider messages.

## Claims that must remain bounded

- The work evaluates finite authored grammars, synthetic policy-constrained cases, and frozen
  author mappings. It does not establish general agent intelligence or deployment prevalence.
- Prose-policy scores are agreement with declared author targets, not correctness against
  policy-owner or human-consensus labels.
- Route stacks differ by model, provider, API adapter, prompt, parser, output contract, and time.
  Cross-route differences are descriptive, not strict causal model ablations.
- Transport, syntax, schema, semantic, and completion failures remain in fixed end-to-end
  denominators. Conditional metrics may accompany, but never replace, those denominators.
- The deterministic executor is a definitional ceiling, not a learned baseline. Naive Bayes remains
  a weak sanity control.
- The public balanced challenge is a commit-frozen robustness challenge, not a hidden-test
  generalization estimate.
- Historical HTTP 401, quota, billing, timeout, schema, and resource failures must not be promoted
  into model-efficacy conclusions.
- No policy-owner label study, annotator agreement study, human-subject study, or deployment field
  outcome exists. Do not invent one.
- Completed one-shot experiments are frozen. Diagnose existing records offline before considering
  any authorized new calls.

## Important files for continuation

- `README.md` — current scope, evidence layers, metrics, and release boundary
- `technical-report/main.tex` — canonical manuscript
- `technical-report/references.bib` — committed bibliography
- `docs/SUBMISSION_METADATA.md` — current copy-ready metadata and OpenReview state
- `docs/submissions/2026-08-25-iclr2027-openreview.md` — private submission receipt
- `docs/reviews/2026-08-26-final-isolated-review-disposition.md` — final review disposition
- `release/submission-kit/validation-receipt.json` — current release validation
- `release/submission-kit/SHA256SUMS.txt` — current artifact hashes
- `release/submission-kit/iclr2027.pdf` — current anonymous conference PDF
- `release/submission-kit/arxiv.pdf` — current identified preprint PDF
- `release/submission-kit/claimpromotebench-anonymous-review-bundle.zip` — current reviewer bundle
- `v2/balanced-public-challenge/results/` — original balanced challenge records and receipts
- `v2/external-agent-policy-revision-v2/` — public-source prose-policy study
- `v2/nonallow-policy-controls-v1/` — restrictive-action follow-up
- `v2/output-contract-ablation-v1/` — request-cap comparison and diagnostics; historical directory
  name is retained for artifact stability
- `v2/upstream-policy-revisions-v1/`, `v2/trivy-policy-revision-v1/`,
  `v2/sigstore-policy-verifier-revision-v1/`, and
  `v2/agent-governance-policy-interface-revision-v1/` — external executable evidence

## Next-task startup protocol

1. Authenticate as the repository owner without printing credentials.
2. Fetch `agent/iclr2027-v2-low-cost-study` from the private GitHub repository and read this file.
3. Confirm the remote branch has not advanced. If it has, inspect the diff; never reset or discard
   later work.
4. Confirm PRIVATE visibility, PR 20 open/draft state, the OpenReview receipt, and a clean worktree.
5. Treat GitHub as authoritative. Do not depend on the previous Codex event log, browser state,
   `/tmp`, untracked build directories, or Keychain contents.
6. First unresolved publication task: determine whether the user explicitly wants the current
   title, abstract, PDF, and anonymous supplement uploaded to the existing OpenReview submission.
   Before any update, compare server fields and attachments with the committed receipt and current
   hashes, preview the exact changes, and obtain clear authorization.
7. Do not upload to arXiv or publish code until separately authorized and the venue's anonymity and
   timing requirements have been checked against current official instructions.
8. If manuscript or bundle inputs change, rebuild both PDFs, both source archives, the anonymous
   bundle, dynamic checksums, validation receipts, and visual QA before committing and pushing.

## Conversation provenance

The original Codex task began on 2026-08-22 and accumulated a 693 MB local JSONL event record with
65,611 events at the migration audit. It contained 83 automatic compactions and a long sequence of
user-visible requests, ambient UI wrappers, and subagent notifications. The raw file remains local
and is intentionally not committed because it includes tool traces, platform instructions, and
reader-irrelevant state. This handoff was reconstructed from the substantive user-visible messages
and verified against the 179 committed Git changes, current artifacts, validation receipts, and
live GitHub state.
