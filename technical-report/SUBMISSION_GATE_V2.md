# Revised ICLR/arXiv submission gate

This gate applies to PR #20 and supersedes the v1-only readiness verdict in
`technical-report/SUBMISSION_GATE.md` whenever the post-v1 public controls are included in the
paper. It is deliberately fail-closed.

## Current verdict

**SCIENTIFIC_RC_READY = NO — FRESH CONFIRMATORY SPLIT OR EXPLORATORY REPOSITIONING REQUIRED**

The frozen v1 hidden study, post-v1 public formatting-control pilot, and post-protocol GPT-5.4
public-development follow-up are complete. The capable-model extension is also computationally
complete, but independent review found that it used 14 adaptive pilot executions on the same 12
hidden inputs before selecting seven terminal canonical pilots. Its completed-lane full passes are
therefore exploratory rather than confirmatory. The manuscript and reviewer evidence are being
corrected to disclose every attempt, historical adapter snapshot, pilot-excluded sensitivity, and
per-action confusion. PR #20 stays Draft and unmerged. A main-conference readiness verdict requires
either a new zero-adjustment private split or an explicit workshop/resource-paper repositioning.

The final inspected anonymous ICLR PDF contains 9 physical pages, and the named arXiv PDF contains
9. The ICLR main-text probe is 8 pages; references begin after the counted main text. All fonts are
embedded. The source archives contain only required TeX/BibTeX/style files and no auxiliary build
files.

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
  `sha256:eb2af5fcfce8466306a208a707e0046b389f2fd656d25d549f784acfc04199e5`.
- [x] Across constrained decoding, 78/80 decisions are parseable and 38/40 pairs are complete.
- [x] All constrained parseable actions remain `ALLOW`.
- [x] Raw pair accuracy and raw flip rate remain zero.
- [x] Two duplicate-`reason_codes` responses remain schema errors and were not manually repaired.
- [x] No paid API or paid GPU runner was used.

## Gate C — adaptive capable-model extension and replacement requirement

- [x] The original protocol and every later transport/adapter amendment remain separately recorded.
- [x] All 14 executed pilot attempts (168 records), not only seven terminal canonical pilots, are
  included in reviewer evidence with their analyses and hashes.
- [x] Three historical request/parser source snapshots and a canonical-selection map are included.
- [x] The recorded amendment procedure used transport/parser classes rather than actions or gold
  accuracy, but no independent escrow enforced this boundary.
- [x] Exactly two terminal pilots led to fresh 300-instance full passes; five `STOP` lanes are not
  assigned model-accuracy scores.
- [x] The extension is labeled `EXPLORATORY_ADAPTIVE_INTERFACE_QUALIFICATION`, not confirmatory.
- [x] A post-hoc sensitivity excludes the 12 reused pilot inputs and six pairs.
- [x] On the 288 nonpilot instances, Qwen3.7-Max reaches 270/288 action and 126/144 pair accuracy;
  DeepSeek-V4-Flash reaches 181/288 and 37/144.
- [x] Four-action confusion and recall are reported; both completed lanes score 0/8 on `DEMOTE`.
- [x] The six registered unique-model hypotheses remain the declared family; completed-lane exact
  tests are descriptive and no confirmatory familywise claim is made.
- [x] The same-model alternate service path is treated as descriptive service-path sensitivity, not
  a causal model, tier, or provider ablation.
- [x] The capable-study aggregate SHA-256 is
  `sha256:abfc25e9a01018bdc269b683cbf54ca423264f62cacbbfee0d504ef10beb6f91`.
- [x] The same-oracle post-check is labeled an implementation-conformance check rather than learned
  model evidence.
- [x] Only synthetic, release-intended benchmark material was sent; no secret, personal, or
  unreleased user data was included.
- [ ] A new private split is committed after all adapters, baselines, prompts, and analyses freeze.
- [ ] Every registered model lane runs the new split once with zero pilot-based adjustment,
  selection, or retry.
- [ ] New-split reporting includes always-`ALLOW`, always-`HOLD`, a public-trained shallow baseline,
  per-action confusion/recall, and pair/factor/template-aware sensitivity.

## Gate D — post-protocol GPT-5.4 public-development follow-up

- [x] The extension is labeled post-protocol, public-development, one-model, and one-pass evidence.
- [x] It is not described as preregistered hidden primary evidence.
- [x] The frozen prompt packet contains 50 pairs / 100 instances and balances the 12-instance pilot
  across policy families.
- [x] The first OpenRouter plan and 12-request transport-only `STOP` remain distinct records.
- [x] The revised plan was committed before successful inference and changed only the output-token
  parameter from `max_completion_tokens` to `max_tokens`.
- [x] Direct OpenAI upstream routing, strict JSON Schema, medium reasoning, a 3,072-token ceiling,
  zero retries, and the authorized $8 cap are registered.
- [x] The revised pilot returned 12/12 parseable decisions and passed its prespecified continuation
  gate.
- [x] The fresh full pass returned 99/100 parseable decisions and 49/50 complete pairs.
- [x] All 99 covered decisions and all 49 covered pairs match the policy oracle.
- [x] Raw false promotions are 0/49 and valid promotions are 50/50.
- [x] The sole nonparseable response is retained as a 3,072-token length-limit failure.
- [x] Provider, item, prompt, request, response, run, analysis, metric, and cost bindings validate.
- [x] Computed pilot-plus-full cost is $2.1883195, below the authorized cap.
- [x] Temporary OpenRouter keys were deleted after usage readback; Gemini has no temporary API key.

## Gate E — manuscript claim integrity

- [x] Abstract foregrounds the capable hidden extension and keeps the original v1 failure result as
  an audit finding rather than the paper's sole capability claim.
- [x] Abstract reports the capable-study headline counts and paired sensitivity correctly.
- [x] Main text contains a dedicated capable hidden protocol subsection and a compact result table.
- [x] The post-v1 public formatting pilot is compressed to reader-relevant prose rather than a
  secondary result table.
- [x] Instance accuracy is not used as a substitute for controlled-pair sensitivity.
- [x] Raw model behavior and post-gate behavior remain separate.
- [x] Gate correctness is described as fixed-policy enforcement, not model learning.
- [x] Limitations preserve public-data, one-seed, small-model, synthetic-data, and post-v1 scope.
- [x] Naturalistic candidate preparation is not called a completed real-world evaluation.
- [x] Manuscript truth lint is bound to both the v1 recovered-study SHA and the v2 pilot SHA.
- [x] Manuscript truth lint is bound to the GPT-5.4 plan, pilot, and full-run SHA values and exact
  paper-facing metrics.
- [x] Manuscript truth lint is bound to the capable-study aggregate, item-level results, baseline
  tests, and exact paper-facing metrics.
- [x] No unqualified “first benchmark,” “first system,” or safety-guarantee claim appears.

## Gate F — naturalistic evaluation boundary

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

## Gate G — code and evidence verification on the final scientific head

- [x] Ruff lint passes.
- [x] Ruff formatting passes.
- [x] Mypy passes.
- [x] Full tests and branch coverage pass.
- [x] Python compatibility matrix passes.
- [x] Deterministic alpha rebuild produces no diff.
- [x] Dataset, public pair-contract, shortcut, invariance, executable, and contribution checks pass.
- [x] Pinned Lean alpha replay passes.
- [x] Pinned Lean v1 public-dev replay passes.
- [x] v1 public release-result validator passes.
- [x] v2 public pilot validator passes.
- [x] GPT-5.4 stronger-model protocol, pilot, full-run, provider, metric, and cost validator passes.
- [x] Capable hidden-study prompt, dataset, pilot/full-run, analysis, aggregate, and baseline
  validators pass.
- [x] Anonymous empirical-evidence validation replays v1, v2, GPT-5.4, and capable-study item-level
  records from inside the finalized reviewer bundle.
- [x] Naturalistic case validator and guard tests pass.
- [x] v1 hidden freeze guard passes.
- [x] v1 scored-study guard passes.
- [x] v1 recovery guard passes.
- [x] A fresh Python 3.12 environment reproduces the public build, validators, audits, and full
  branch-coverage test suite.
- [x] README, manuscript, `CITATION.cff`, and submission metadata use the same canonical title.

## Gate H — final ICLR 2027 package

- [x] Official ICLR 2027 style files are fetched and their hashes are recorded.
- [x] ICLR PDF compiles from the final scientific head.
- [x] ICLR PDF contains 9 physical pages including references and required disclosures.
- [x] Main-text page probe reports 8 pages, within the 9-page limit.
- [x] No unresolved citations or references.
- [x] No horizontal overflow.
- [x] ICLR TeX and extracted PDF text contain no author name, institution, username, email, public
  repository URL, workflow/run identifiers, commit identifiers, or released aggregate hashes.
- [x] ICLR PDF metadata contains no author identity.
- [x] AI-use disclosure remains present in the ICLR submission.
- [x] All PDF fonts are embedded.
- [x] Anonymous reviewer ZIP contains no generated cache, unmanifested file, unused human-review
  workflow module, author identity, or public workflow/provenance identifier.
- [x] Anonymous reviewer ZIP contains the released item-level empirical evidence needed to replay
  the paper-facing v1, v2, GPT-5.4, and capable-study aggregates.
- [x] Final ICLR PDF was rendered and inspected page by page for crowding, overlap, clipping,
  broken glyphs, unreadable tables, and figure/caption collisions.

Observed result: no overlap, clipping, broken glyphs, table overflow, figure collision, or
unacceptable crowding. The densest limitations/reproducibility page remains readable at normal
conference-paper scale.

## Gate I — final arXiv package

- [x] Named arXiv PDF compiles from the final scientific head.
- [x] The arXiv PDF contains 9 physical pages.
- [x] The arXiv source ZIP places `arxiv.tex` and `references.bib` at the archive root and contains
  no auxiliary build output.
- [x] arXiv PDF contains Chih-Kai Wang and National Taipei University of Education.
- [x] Exact operational workflow, commit, and aggregate identities remain in repository evidence
  manifests instead of interrupting the manuscript narrative.
- [x] No unresolved citations/references or horizontal overflow.
- [x] All PDF fonts are embedded.
- [x] Source ZIP contains `arxiv.tex` and `references.bib` and no auxiliary build files.
- [x] Final arXiv PDF was rendered and inspected page by page for crowding, overlap, clipping,
  broken glyphs, unreadable tables, and figure/caption collisions.
- [ ] arXiv metadata, category, title, abstract, author, affiliation, and server-compiled preview are
  checked during the account-side submission.

Observed result: the named PDF and repository-bound provenance statement are correct, and no visual
defect was found.
The final metadata/preview item necessarily remains account-side because arXiv must compile and
show its own preview before submission.

## Gate J — account-side submission

- [ ] OpenReview profile exists and is current.
- [ ] All required author/reviewer-account obligations are satisfied.
- [ ] OpenReview title, genuine abstract, and final author list are entered before **2026-09-18
  AOE**.
- [ ] Full paper and supplementary files are submitted before **2026-09-25 AOE**.
- [ ] Final paper metadata, author list, topics, Code of Ethics acknowledgement, AI-use statement, and uploaded PDF preview are checked by the author.
- [ ] The submission form and manuscript consistently state that no human-subject or human-annotation study is included.
- [ ] arXiv account and any endorsement requirement are complete.

## Gate K — archival release

- [ ] One immutable release/tag is created from the final submission head.
- [x] `CITATION.cff`, README, manuscript, and submission metadata agree on the canonical title and
  current pre-submission status.
- [x] Clean-environment public validation succeeds from the release candidate.
- [x] The committed v1, public-pilot, GPT-5.4, and capable-study evidence reproduces every
  paper-facing empirical result without model inference.
- [ ] Release notes and the final package version agree with the future immutable tag.
- [ ] Long-term citable archive is created if required by the venue or desired for the paper.
- [ ] Archive identifiers are added only after they exist.

## Readiness rule

`SCIENTIFIC_RC_READY` remains false while any fresh-confirmatory item in Gate C is unchecked. The
completed packaging, anonymity, and replay checks establish artifact quality but cannot promote an
adaptive exploratory study into confirmatory hidden evidence. Do not mark PR #20 ready, merge it,
claim “submitted,” or create archival identifiers until the scientific blocker is resolved and the
author completes Gate J. Any later Gate K release must use the exact submitted release candidate,
without inventing an arXiv ID, DOI, or archive identifier.
