# Revised ICLR/arXiv submission gate

This gate applies to PR #20 and supersedes the v1-only readiness verdict in
`technical-report/SUBMISSION_GATE.md` whenever the post-v1 public controls are included in the
paper. It is deliberately fail-closed.

## Current verdict

**SCIENTIFIC_RC_READY = YES — LOCAL SCIENTIFIC, REVIEW, AND ARTIFACT GATES PASS;
R6 FLASH LANE NON-EVALUABLE; ACCOUNT-SIDE SUBMISSION NOT AUTHORIZED OR COMPLETED**

The manuscript's central claim is a paired, failure-aware regression protocol for an existing
model boundary under executable policy revision. Its central evidence is one authored migration,
two 60-pair suites, and the same two pinned local routes evaluated once; the 10-pair minimum gate
reuses graph records. R6, the public action-balanced challenge, and fixed-policy SLSA results are
auxiliary route diagnostics rather than independent policy-migration replications.

The final isolated reviewer scored the preceding release candidate 4/10. That review was not
rerated: the score describes the reviewed snapshot, not this revision, and does not predict venue
acceptance. All safely actionable high and medium findings were addressed by narrowing novelty,
disclosing post-exploratory route selection and stack confounds, correcting the HOLD/DEMOTE proof,
demoting standard optimization machinery, separating controls, expanding confusion matrices, and
limiting reproducibility claims to metric and contract replay. The exact disposition is recorded in
`docs/reviews/2026-08-24-final-isolated-iclr-review-disposition.md`.

The reviewer tree excludes hidden reasoning and malformed response contents, verifies retained
structured records and failure classes, and derives its file count from the generated manifest. PR
#20 remains Draft and unmerged until the author explicitly authorizes a merge or account-side
submission.

The later balanced public challenge has an executable Flash service path, but it uses a different
stack and does not retroactively turn the r6 HTTP 401 lane into model evidence or a causal ablation.
A post-analysis reporting correction assigns zero to Flash's zero-prediction `DEMOTE` class in the
fixed-four-class Macro-F1, changing only that derived end-to-end value from .5237 to .3928 and its
conditional counterpart from .6243 to .4682. The historical aggregate remains immutable.

A prospectively frozen seven-route supplement was later found to share a quota-confounded failure
tail. It remains immutable private audit material but is excluded from the manuscript, submission
metadata, anonymous reviewer package, and minimum public-release core. No subset of its valid rows
is reported as a replacement study.

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

## Gate C — adaptive capable-model extension and fresh replacement study

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
- [x] A new 150-pair / 300-item private realization is frozen after adapters, baselines, prompts,
  parser, lane definitions, and analysis freeze under C0, a future randomness beacon, and C1.
- [x] The exact 600-request schedule is fixed before inference; each registered lane receives one
  call per item with zero client retries and no post-C1 adjustment or selection.
- [x] C2 seals all 600 terminal cells before gold loading or analysis.
- [x] The frozen public-development text Naive Bayes baseline is trained only on 100 public items;
  constant baselines, per-action confusion/recall, factor/template summaries, and the registered
  composition-sensitivity envelope are retained.
- [x] Qwen3.7-Max produces 272 valid decisions, 258/300 correct actions, and 113/150 correct pairs,
  for .860 item accuracy and .753 pair accuracy.
- [x] The registered pair-blocked comparison remains machine-readable, but the paper does not use
  it as a model-superiority claim because the frozen text Naive Bayes comparator is weak.
- [x] Qwen action-wise reporting preserves 143/150 `ALLOW`, 110/134 `HOLD`, 5/8 `ESCALATE`, and
  0/8 `DEMOTE`; the paper explicitly limits the breadth of the aggregate result.
- [x] Fourteen HTTP 500 responses, one HTTP 503 response, ten timeouts, and three semantic-invalid
  Qwen outputs remain incorrect with zero retries.
- [x] The registered Flash lane returns 300 HTTP 401 responses and no model output; H2 remains in
  the Holm family with `p=1`, model efficacy is non-evaluable, and dual-model confirmation is
  unsupported.
- [x] Service labels are treated as time-stamped configurations; no fixed-weight, provider, tier,
  serving-stack, or causal ablation claim is made.

### Post-r6 public robustness evidence

- [x] The separately preregistered public challenge freezes 90 pairs, 180 items, 15 factors, action
  balance, prompts, adapters, analysis, and a zero-retry schedule before inference.
- [x] Each of its two service routes makes 180 calls. Qwen returns 148 valid decisions and reaches
  .7333/.5333 end-to-end item/pair accuracy; Flash returns 146 and reaches .5000/.1444.
- [x] Conditional item/pair accuracy is reported only beside coverage: .8919/.7500 for Qwen and
  .6164/.2131 for Flash.
- [x] Complete confusion matrices and action recalls retain every no-valid cell. `DEMOTE` recall is
  4/30 for Qwen and 0/30 for Flash.
- [x] The later Flash path establishes only that its different frozen route executed; it neither
  repairs the old r6 401 lane nor identifies a causal model, provider, schema, or adapter effect.
- [x] The quota-confounded seven-route study is not paper evidence and is not included in the
  anonymous reviewer package. Its frozen private records are retained for audit rather than
  selectively rescored or filtered.

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

- [x] Abstract frames the task as synthetic, policy-constrained evidence-state transition
  evaluation rather than broad research-agent capability.
- [x] Abstract leads with one authored migration and reports the auxiliary r6 and balanced-challenge
  coverage, conditional and end-to-end item/pair scores, and `DEMOTE` recalls.
- [x] Abstract calls the deterministic executor a definitional policy ceiling and Naive Bayes a
  weak baseline while rejecting naturalistic-validity and causal-comparison interpretations.
- [x] Main text defines action conformance after output-contract validation as the primary endpoint;
  exact six-field agreement is not claimed.
- [x] The old r6 Flash 401 route appears as a pre-output interface-failure paragraph rather than a
  model-result row. Its zero scheduled coverage remains explicit and conditional scores remain
  undefined.
- [x] The post-v1 public formatting pilot is compressed to reader-relevant prose rather than a
  secondary result table.
- [x] Instance accuracy is not used as a substitute for controlled-pair sensitivity.
- [x] Raw model behavior and post-gate behavior remain separate.
- [x] Gate correctness is described as fixed-policy enforcement, not model learning.
- [x] Limitations preserve public-data, one-pass, two-local-route, one-migration, synthetic-data,
  route-selection, and service-stack scope.
- [x] Naturalistic candidate preparation is not called a completed real-world evaluation.
- [x] Main and appendix tables separate model routes from weak or construction-dependent sanity
  controls and give explicit prediction columns for every confusion cell.
- [x] Manuscript truth lint is bound to the r6 result and reporting addendum, the balanced-challenge
  plan and item records, both migration suites, confusion matrices, action recalls, and privacy
  receipts.
- [x] The anonymous evidence replay validates only the empirical records needed for the current
  paper: fresh r6 and the balanced public challenge.
- [x] Manuscript truth lint is bound to the r6 study-result self-digest, public analysis, complete
  Holm family, redaction/equivalence receipt, correction overlay, and exact paper-facing metrics.
- [x] Balanced-challenge Macro-F1 is a fixed-four-class mean with zero division set to zero; a
  self-digested correction receipt binds the unchanged historical aggregate, analyzer, dataset, and
  360 terminal records.
- [x] A compact factor-level table reports support, coverage range, E2E pair-accuracy range, and
  zero/perfect-factor counts from frozen records; the anonymous artifact retains every factor row.
- [x] Discussion, limitations, and conclusion preserve all r6 and balanced-challenge service,
  syntax, schema, and semantic failures in end-to-end denominators and reject causal,
  hidden-generalization, and naturalistic-transfer interpretations.
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
- [x] Source-level review is bound to the frozen pool and records zero cases and zero model calls
  because the candidate records lack sufficient transition-policy evidence.

The paper therefore does not claim a completed naturalistic replication, human labels, or agreement.

## Gate G — code and evidence verification on the final scientific head

- [x] Ruff lint passes.
- [x] Ruff formatting passes.
- [x] Mypy passes.
- [x] Full Mac tests and branch coverage pass on the final source tree: 301 tests and 83.21% branch
  coverage under Python 3.12.13.
- [x] Python 3.12 Mac gates pass in a fresh virtual environment.
- [ ] A fresh remote compatibility matrix awaits GitHub runner allocation; current private-repo
  failures have `steps=[]` and are recorded as an account billing/spending-limit condition, not a
  code result.
- [x] Deterministic alpha rebuild produces no diff.
- [x] Dataset, public pair-contract, shortcut, invariance, executable, and contribution checks pass.
- [x] Pinned Lean alpha replay passes.
- [x] Pinned Lean v1 public-dev replay passes.
- [x] v1 public release-result validator passes.
- [x] v2 public pilot validator passes.
- [x] GPT-5.4 stronger-model protocol, pilot, full-run, provider, metric, and cost validator passes.
- [x] Capable hidden-study prompt, dataset, pilot/full-run, analysis, aggregate, and baseline
  validators pass.
- [x] Fresh-study C0, C1, C2, dataset, prompt, baseline, service-runner, statistics, public-release,
  redaction, metadata-correction, and permanent-manifest guards pass.
- [x] Balanced public-challenge dataset, prompt packet, one-pass lane records, immutable historical
  aggregate, reporting-correction receipt, corrected reviewer aggregate, per-action/confusion
  diagnostics, workflow receipt, and privacy receipt guards pass.
- [x] The private seven-route records and audit tooling remain repository-verifiable but are outside
  the paper-facing lint, anonymous replay, and release package.
- [x] Anonymous empirical-evidence validation replays fresh r6 and the balanced public challenge
  from inside the finalized reviewer bundle.
- [x] Naturalistic case validator and guard tests pass.
- [x] v1 hidden freeze guard passes.
- [x] v1 scored-study guard passes.
- [x] v1 recovery guard passes.
- [x] A fresh Python 3.12 environment reproduces the public build, validators, audits, and full
  branch-coverage test suite.
- [x] All six pinned Lean packages and `leanchecker` replay successfully: public alpha, capable
  hidden, fresh r6, GPT-5.4 public development, balanced challenge, and r4 reviewer evidence.
- [x] README, manuscript, `CITATION.cff`, and submission metadata use the same canonical title.

## Gate H — final ICLR 2027 package

- [x] Official ICLR 2027 style archive and file hashes are committed in a fail-closed lock.
- [x] The ICLR source archive includes the official pinned `fancyhdr.sty` and `natbib.sty`
  dependencies, preventing system-package drift from removing the anonymous-review page header.
- [x] ICLR PDF compiles from the final scientific head.
- [x] ICLR PDF contains 15 physical pages: nine pages through the scientific conclusion and
  non-counting reproducibility/AI-use statements, three reference pages, and three appendix pages.
- [x] Main-text page probe reports 9 pages, at the 9-page limit; the scientific conclusion ends on
  page 9.
- [x] References begin on physical page 10 and the appendix on page 13; the release receipt binds
  the page boundary, nine-page limit, and official ICLR 2027 style receipt.
- [x] No unresolved citations or references.
- [x] No horizontal overflow.
- [x] ICLR TeX and extracted PDF text contain no author name, institution, username, email, public
  repository URL, workflow/run identifiers, commit identifiers, or released aggregate hashes.
- [x] ICLR PDF metadata contains no author identity.
- [x] AI-use disclosure remains present in the ICLR submission.
- [x] All PDF fonts are embedded.
- [x] Anonymous reviewer ZIP contains no generated cache, unmanifested file, unused human-review
  workflow module, author identity, or public workflow/provenance identifier.
- [x] Anonymous reviewer ZIP contains the item-level evidence needed to replay the paper-facing
  fresh r6 and balanced-challenge aggregates.
- [x] The anonymous manifest and release receipt derive payload and ZIP-entry counts from the
  generated tree; no long-lived prose supplies a fixed expected count. Two empty-directory builds
  and two release kits are byte-identical.
- [x] Fail-closed scans reject author/repository/workflow identity, account identifiers, provider
  response/request identifiers, hidden reasoning, credential patterns, and unknown protected
  fields. An exact-byte Keychain credential scan traverses the current generated files and
  decompressed ZIP entries with zero findings and does not print or retain the credential.
- [x] Final ICLR PDF was rendered and inspected page by page for crowding, overlap, clipping,
  broken glyphs, unreadable tables, and figure/caption collisions.

Observed result: no overlap, clipping, broken glyphs, table overflow, figure collision, or
unacceptable crowding. The densest limitations/reproducibility page remains readable at normal
conference-paper scale.

## Gate I — final arXiv package

- [x] Named arXiv PDF compiles from the final scientific head.
- [x] The arXiv PDF contains 14 physical pages.
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

## Final isolated review checkpoint

- [x] Exactly one additional reviewer was designated as the final isolated review for this
  revision. It audited the manuscript, frozen records, code, anonymous bundle, and rendered PDF
  without access to prior review narratives.
- [x] The reviewer independently reproduced all dataset supports, route metrics, action recalls,
  confusion cells, failure totals, bundle hashes, and page boundaries; numerical, artifact, and
  anonymity checks passed.
- [x] Its 4/10 recommendation on the reviewed snapshot identified three high-level framing issues
  and six additional presentation or proof issues. No second reviewer was used to rerate the fix.
- [x] The revision narrows the contribution to paired failure-aware action-conformance testing at an
  existing model-service boundary; semantic differencing, mutants, set cover, and dynamic
  programming are identified as established machinery.
- [x] The paper now states one migration, two local routes, one pass, no independent replication,
  and reuse of graph records by the minimum gate; auxiliary evidence suites do not inflate the
  central evidence count.
- [x] Hosted route selection timing, route-stack confounds, the historical 401 interface failure,
  corrected HOLD/DEMOTE precedence proof, primary endpoint, sanity controls, explicit confusion
  columns, and metric/contract replay boundary are all stated directly.
- [x] Review and resolution are preserved in
  `docs/reviews/2026-08-24-final-isolated-iclr-review.md` and
  `docs/reviews/2026-08-24-final-isolated-iclr-review-disposition.md`.

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
- [x] The committed fresh r6 and balanced-challenge evidence reproduces every paper-facing
  empirical result without model inference.
- [ ] Release notes and the final package version agree with the future immutable tag.
- [ ] Long-term citable archive is created if required by the venue or desired for the paper.
- [ ] Archive identifiers are added only after they exist.

## Readiness rule

`SCIENTIFIC_RC_READY` means the scoped Qwen hypothesis, manuscript, permanent reviewer artifact,
anonymous evidence package, and local submission package all pass
their deterministic and visual gates. It does not turn the Flash operational failure into model
evidence, rank model families, establish dual-model confirmation, or complete account-side
submission. Keep PR #20 Draft and unmerged, and do not claim “submitted” or create archival
identifiers, until the author explicitly authorizes the corresponding action and Gate J is
completed. Any later Gate K release must use the exact submitted release candidate and must not
invent an arXiv ID, DOI, or archive identifier.
