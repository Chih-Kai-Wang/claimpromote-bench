# Revised ICLR/arXiv submission gate

This gate applies to PR #20 and supersedes the v1-only readiness verdict in
`technical-report/SUBMISSION_GATE.md` whenever the post-v1 public pilot is included in the paper.
It is deliberately fail-closed.

## Current verdict

**SCIENTIFIC RESULTS COMPLETE — FINAL REVISED BUILD, VISUAL, ETHICS, AND ARCHIVAL GATES OPEN**

The frozen v1 hidden study and the post-v1 public formatting-control pilot are complete. The revised
manuscript contains both result sets and binds their paper-facing values to machine-readable
aggregates. PR #20 must remain Draft and unmerged until every final-build and visual item below is
checked on one unchanged head.

## Gate A — frozen v1 study remains intact

- [x] Hidden v1 data, labels, policy, prompts, outputs, and recovery remain unchanged.
- [x] Primary v1 matrix remains 300 hidden instances × 2 models × 4 arms × 3 seeds = 7,200
  decisions.
- [x] Headline values remain 5,327 format errors and 1,873 parseable raw decisions, all `ALLOW`.
- [x] Exactly 27 cross-field-invalid records were reclassified as format errors; legal model
  decisions were not rewritten.
- [x] Source workflow remains `32255636879`.
- [x] Recovery workflow remains `32274814703`.
- [x] Recovered study SHA-256 remains
  `sha256:3eb5b534ab486dac774a62de3d623fa33009be3705d9e8d620bb9942e8bfe664`.
- [x] Human audit remains mixed/not PASS.
- [x] Python 3.11.15/3.11.16 identity drift remains disclosed; no post-hoc regrouping is used.

## Gate B — post-v1 public formatting control

- [x] Pilot is labeled post-v1, public, one-seed diagnostic evidence.
- [x] Pilot is not described as preregistered hidden primary evidence.
- [x] Dataset is the 20-pair / 40-instance public alpha set.
- [x] Models are the same frozen Qwen3-0.6B and Qwen3-1.7B artifacts used in v1.
- [x] Runtime is the same pinned llama.cpp commit.
- [x] Free and constrained conditions have identical prompt hashes, model artifact, runtime, seed,
  and hardware record.
- [x] The only registered decoding difference is `response_format`.
- [x] Canonical source workflow is `32291482079`.
- [x] Artifact-only recovery is `32297818154`.
- [x] Recovery required four complete 40-record runs and recomputed the aggregate twice with
  identical bytes.
- [x] Public aggregate SHA-256 is
  `sha256:83dbee4923bca6a0d1908083172190d7b81e2a5e9613c22e4929cfa25c0b264e`.
- [x] Across constrained decoding, 78/80 decisions are parseable and 38/40 pairs are complete.
- [x] All constrained parseable actions remain `ALLOW`.
- [x] Raw pair accuracy and raw flip rate remain zero.
- [x] Two duplicate-`reason_codes` responses remain schema errors and were not manually repaired.
- [x] No paid API or paid GPU runner was used.

## Gate C — manuscript claim integrity

- [x] Abstract identifies the hidden v1 study as primary and the public pilot as post-v1.
- [x] Abstract reports the v1 and v2 headline counts correctly.
- [x] Main text contains a dedicated public-pilot protocol subsection.
- [x] Main text contains a separate pilot result table with coverage and pair accuracy.
- [x] Instance accuracy is not used as a substitute for controlled-pair sensitivity.
- [x] Raw model behavior and post-gate behavior remain separate.
- [x] Gate correctness is described as fixed-policy enforcement, not model learning.
- [x] Limitations preserve public-data, one-seed, small-model, synthetic-data, and post-v1 scope.
- [x] Naturalistic candidate preparation is not called a completed real-world evaluation.
- [x] Manuscript truth lint is bound to both the v1 recovered-study SHA and the v2 pilot SHA.
- [x] No unqualified “first benchmark,” “first system,” or safety-guarantee claim appears.

## Gate D — naturalistic evaluation boundary

- [x] Source registry is pinned before any naturalistic scoring.
- [x] Candidate selection is deterministic and independent of ClaimPromoteBench model outputs.
- [x] Twelve CORE-Bench candidates are frozen as unlabeled pointer-only candidates.
- [x] Candidate records contain no source results, model outputs, or ClaimPromoteBench labels.
- [x] Naturalistic-case schema separates model-visible and evaluator-only content.
- [x] Validator checks source binding, commit-pinned URLs, evaluation time, evidence time, licensing,
  copied-byte status, and label leakage.
- [x] Curation worksheet states that exclusion is preferable to inventing weak cases.
- [ ] At least one naturalistic case has passed source-level review and defensible labeling.

The unchecked item is **not required to report the completed public pilot**. It means the paper must
not claim a completed naturalistic replication.

## Gate E — code and evidence verification on the final head

- [ ] Ruff lint passes.
- [ ] Ruff formatting passes.
- [ ] Mypy passes.
- [ ] Full tests and branch coverage pass.
- [ ] Python compatibility matrix passes.
- [ ] Deterministic alpha rebuild produces no diff.
- [ ] Dataset, shortcut, invariance, executable, review, and contribution checks pass.
- [ ] Pinned Lean alpha replay passes.
- [ ] Pinned Lean v1 public-dev replay passes.
- [ ] v1 public release-result validator passes.
- [ ] v2 public pilot validator passes.
- [ ] Naturalistic case validator and guard tests pass.
- [ ] v1 hidden freeze guard passes.
- [ ] v1 scored-study guard passes.
- [ ] v1 recovery guard passes.

## Gate F — final ICLR 2027 package

- [ ] Official ICLR 2027 style files are fetched and recorded.
- [ ] ICLR PDF compiles on the final unchanged head.
- [ ] Main-text page probe is at or below 9 pages.
- [ ] No unresolved citations or references.
- [ ] No horizontal overflow.
- [ ] ICLR TeX and extracted PDF text contain no author name, institution, username, email, public
  repository URL, v1 workflow/hash provenance, or v2 workflow/hash provenance.
- [ ] ICLR PDF metadata contains no author identity.
- [ ] AI-use disclosure remains present in the ICLR submission.
- [ ] Final ICLR PDF is inspected page by page for crowding, overlap, clipping, broken glyphs,
  unreadable tables, and figure/caption collisions.

## Gate G — final arXiv package

- [ ] Named arXiv PDF compiles on the final unchanged head.
- [ ] arXiv PDF contains Chih-Kai Wang and National Taipei University of Education.
- [ ] arXiv PDF preserves v1 and v2 public workflow/hash provenance.
- [ ] No unresolved citations/references or horizontal overflow.
- [ ] Source ZIP contains the required TeX/BibTeX sources and no build junk.
- [ ] Final arXiv PDF is inspected page by page for crowding, overlap, clipping, broken glyphs,
  unreadable tables, and figure/caption collisions.
- [ ] arXiv metadata, category, title, abstract, author, and affiliation are checked during the
  account-side preview.

## Gate H — human audit ethics and account-side submission

- [ ] Actual reviewer recruitment relationship is recorded.
- [ ] Actual consent process is recorded.
- [ ] Actual compensation, if any, is recorded.
- [ ] Actual data-retention/anonymity practice is recorded.
- [ ] Appropriate institutional/ethics determination is obtained or documented; no approval or
  exemption is invented.
- [ ] OpenReview profile exists and is current.
- [ ] All required author/reviewer-account obligations are satisfied.
- [ ] OpenReview abstract metadata is submitted before the official deadline.
- [ ] Final paper metadata, author list, topics, ethics acknowledgement, and uploaded PDF preview are
  checked by the human author.
- [ ] arXiv account and any endorsement requirement are complete.

## Gate I — archival release

- [ ] One immutable release/tag is created from the final submission head.
- [ ] `CITATION.cff`, README, manuscript, release notes, and package version agree.
- [ ] Clean-environment public validation succeeds from the release candidate.
- [ ] Released v1 and v2 aggregates reproduce every paper-facing result without model inference.
- [ ] Long-term citable archive is created if required by the venue or desired for the paper.
- [ ] Archive identifiers are added only after they exist.

## Readiness rule

Do not mark PR #20 ready, merge it, claim “submitted,” or replace the downloadable submission kit
until Gates E–G have all passed on one final unchanged head and the page-by-page visual review is
complete. Gates H–I require human account or institutional actions and must remain explicit rather
than being guessed by automation.
