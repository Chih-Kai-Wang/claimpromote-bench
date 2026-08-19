# Submission gate

This file is deliberately fail-closed. A polished manuscript is not evidence that every archival release gate is complete.

## Current verdict

**PREPRINT READY — ARCHIVAL / ICLR ACCOUNT-AND-ETHICS GATES STILL OPEN**

The private hidden freeze, frozen inference source, 24-run / 7,200-decision artifact-only recovery, aggregate study, primary manuscript Results, authoritative bibliography checks, ICLR 2027 AI-disclosure checks, hosted CI, LaTeX/submission-package builds, quantitative cross-check, and prior PDF visual/anonymity audit are complete. A fresh 2026-08-20 related-work pass has also narrowed the novelty language after finding close policy-action and counterfactual benchmarks. Archival-submission readiness remains separate and still requires the release, ethics, and account-side gates below. The v1 infrastructure-identity limitation remains disclosed and unchanged.

## Gate A — research boundary and novelty

- [x] Narrow target: policy-governed scientific evidence-state transition admissibility, not general truth classification.
- [x] Distinguish claim/evidence verification, abstention, computational reproducibility, hypothesis validation, policy-aware agent actions, counterfactual evaluation, evidence-state maintenance, verifier-governed claim workflows, and formal-specification generation from the transition benchmark.
- [x] Use cautious priority language; do not claim “first” without qualification.
- [x] Fresh related-work search refreshed on 2026-08-20 in `docs/RELATED_WORK.md`.
- [x] Manuscript now directly positions SteerBench-Work, ST-WebAgentBench, CofCA, MEDSYN, RECV, SeekBench, Omni-Decision, EviGraph, and ClaimLedger.
- [x] Do not claim novelty for counterfactual pairs, evidence reversal, generic policy compliance, or the phrase `evidence sensitivity`.
- [x] Bibliography entries rechecked against authoritative records (ACL Anthology, ICLR/OpenReview or proceedings, arXiv for contemporaneous preprints, PMLR, AAAI, and the cited official ClaimLedger report page as applicable).

## Gate B — v1 benchmark freeze

- [x] Machine-readable preregistration fixes 200 pairs / 400 instances, 20 policy factors, family totals, invalid-side balance, and action balance.
- [x] Stable v1 policy identity is frozen separately from alpha.
- [x] Shared dev/test constructor exists and is covered end-to-end.
- [x] Public development split is 50 pairs / 100 instances and passes schema, pair, oracle, artifact, shortcut, metamorphic, and pinned-Lean gates.
- [x] Private hidden test was generated as 150 pairs / 300 instances from a private seed kept outside the public repository.
- [x] Hidden split passed the private freeze validation before scored inference.
- [x] Hidden commitment commit `8d9b3f5c831f432cf6b321e6402724c4f52bb3e1` predates scored trigger commit `aa5268dcde2aa44f8eabf0246631efbca27de7e5`.
- [x] Frozen dataset-manifest SHA-256 is `sha256:fe838548389ee1516d9cf9442201a22c291add0ddb6cabf4f39de99b6489caba`.
- [x] Frozen prompt-manifest SHA-256 is `sha256:b6c1dacdb6db34aef4a9532df8e24a6e6f51724df75b0f2e8a14ffa01dca2957`.
- [x] Raw `CPB_V1_HIDDEN_SEED` remains secret and is not printed, committed, or embedded in artifacts.
- [x] No hidden gold, policy, prompt, or controlled-factor edit was made to improve scored results.

## Gate C — model/runtime freeze

For both preregistered Qwen3 model sizes:

- [x] exact upstream model/revision identity recorded;
- [x] exact GGUF/model artifact SHA-256 recorded;
- [x] Q8_0 quantization recorded;
- [x] llama.cpp commit `de699957b92f490efebad149665b0dccf127eaff` recorded;
- [x] frozen decoding settings and seeds recorded;
- [x] scored-study preflight identities are present in all 24 source artifacts;
- [x] 24 complete source `run.jsonl` files exist with 300 records each;
- [x] recovery validated exact frozen prompt hashes for every normalized run.

### v1 infrastructure identity limitation

Three hosted jobs recorded Python 3.11.16 while most recorded Python 3.11.15. Because the preregistered `compare-runs` grouping includes the exact hardware-summary string, this splits three intended model×seed sets into separate identity groups. The official aggregate therefore has 9 identity groups and only 3 all-four-arm complete groups. This is retained and disclosed; no post-hoc regrouping is used to manufacture a complete significance panel.

## Gate D — frozen quantitative study

- [x] Primary scoring uses only the private hidden test: 300 instances × 2 models × 4 arms × 3 seeds = **7,200 decisions**.
- [x] Source workflow run `32255636879` produced exactly 24 `cpb-v1-scored-*` immutable source artifacts.
- [x] Artifact-only recovery run `32274814703` reconstructed the committed hidden set from the frozen scoring source and verified the same commitment/prompt identity.
- [x] Exactly 24 source `run.jsonl`, 24 normalized `run.jsonl`, and 7,200 records were validated.
- [x] Semantic recovery reclassified only frozen cross-field semantic violations as `FORMAT_ERROR`; 27 records were affected and no legal model decision was rewritten.
- [x] Primary metrics are reported from the recovered aggregate artifact only.
- [x] Raw intent and effective post-gate behavior are reported separately.
- [x] Pair-bootstrap intervals and exact matched McNemar/Holm comparisons were generated by the repository evaluator wherever an exact identity group contained both arms.
- [x] All three seeds are retained; no seed is cherry-picked or removed.
- [x] Negative results and high `FORMAT_ERROR` rates are retained.
- [x] Deterministic gate catches are described as system-level enforcement, not improved model reasoning/calibration.
- [x] Study-file SHA-256 is `sha256:3eb5b534ab486dac774a62de3d623fa33009be3705d9e8d620bb9942e8bfe664`.
- [x] Recovered GitHub artifact `claimpromotebench-v1-scored-study-recovered` is bound to recovery run `32274814703`.
- [x] The one-shot recovery trigger was removed after successful recovery.

## Gate E — benchmark and annotation integrity

### Deterministic engineering evidence

- [x] Alpha/public-dev datasets are deterministically rebuildable.
- [x] Public v1 dev gold labels are generated by the versioned policy/oracle rather than hand-edited after results.
- [x] Applicable numerical artifacts are executable and hash-bound.
- [x] Public v1 dev formal artifacts build under the pinned Lean toolchain and replay with `leanchecker`.
- [x] Registered shortcut and metamorphic infrastructure is executable and fail-closed.
- [x] Hidden-test commitment demonstrably predates scored inference.
- [x] Recovery revalidated hidden construction and prompt freeze before reading source artifacts.

### Supplementary independent human audit

- [x] Two real independent reviewers returned complete submissions for the frozen 20-item procedural-blind alpha audit.
- [x] Both submissions were validated and SHA-256 frozen before unblinding.
- [x] Reviewer-versus-gold action agreement is 0.90 and 0.75; pairwise action agreement is 0.85.
- [x] The conservative multi-reviewer supplementary gate is reported as **mixed / not PASS** because one reviewer is below 0.80.
- [x] Review disagreements are retained and are not used to rewrite frozen gold or policy.
- [ ] Human-audit ethics / IRB applicability and reviewer-consent facts are documented using `docs/HUMAN_AUDIT_ETHICS_CHECKLIST.md`; no approval, exemption, or consent language may be invented.

## Gate F — manuscript integrity

- [x] Anonymous manuscript exists.
- [x] Claims separate transition admissibility from theorem/scientific truth.
- [x] Complete `ALLOW` / `HOLD` / `DEMOTE` / `ESCALATE` action space is documented.
- [x] Primary Results are populated from the validated recovered aggregate rather than partial metrics.
- [x] Manuscript reports 5,327/7,200 `FORMAT_ERROR` outputs and conditional decision coverage instead of hiding them.
- [x] Manuscript states that all 1,873 parseable raw intents were `ALLOW`.
- [x] Manuscript distinguishes raw-intent behavior from deterministic gate enforcement.
- [x] Semantic recovery is disclosed and explicitly states that legal model answers were not changed.
- [x] Exact source/recovery workflow IDs and core commitment/study identities are recorded.
- [x] External audit remains supplementary mixed evidence, not a PASS.
- [x] Limitations disclose high format-error rate, non-retention of free-form text for pre-existing parse failures, exact-identity group drift, gate-prompt disclosure, small-model scope, synthetic control, and author-constructed benchmark risk.
- [x] Related Work explicitly acknowledges the closest current action-boundary, counterfactual, and evidence-sensitivity precedents.
- [x] Submission builder treats unresolved citations/references, horizontal overflow, page-limit violations, and anonymity leaks as failures.
- [x] AI-assistance disclosure includes significant research/writing assistance and a human-responsibility statement rather than implying AI was unused.
- [ ] Final hosted paper/submission-package run on the latest substantive manuscript must finish successfully after the 2026-08-20 novelty/figure revision.
- [ ] Latest compiled ICLR and arXiv PDFs must be rendered and visually inspected again after that revision.

## Gate G — reproducibility release

- [ ] Clean-environment reproduction of final benchmark validation succeeds from the release candidate.
- [ ] Clean-environment reproduction of all paper tables/statistics succeeds from released artifact inputs.
- [ ] Release/tag is immutable and all cited artifact hashes match it.
- [ ] Archive code/data artifacts in a citable long-term repository if required by the target venue.
- [ ] `CITATION.cff`, README, manuscript, and release notes agree on title/version/status.

## Gate H — ICLR account and ethics readiness

- [ ] OpenReview profile exists, is current, and is usable before the abstract deadline.
- [ ] Author information and reciprocal-reviewing status shown by OpenReview are checked by the human author.
- [ ] Human-audit ethics / review-board applicability has an actual documented determination where required.
- [ ] Reviewer consent / privacy / release permissions are documented consistently with the material released in the repository.
- [ ] Any Ethics Statement added to the manuscript contains only documented facts.
- [ ] Final OpenReview title, abstract, author list/order, subject areas, ethics acknowledgement, and uploaded-PDF preview are checked account-side by the human author.

## Post-v1 evidence rule

Draft PR #20 contains a separate low-cost follow-up that retains raw responses, separates syntax/schema/semantic output failures, compares free and schema-constrained decoding under identical prompts, and computes a pure post-processing gate. It is **post-v1** evidence. Until its own run artifacts and aggregate are complete, it must not be quoted as a result. If later used in the ICLR paper, its provenance and limitations must be reported separately rather than changing v1 chronology or tables.

## Readiness rule

The frozen v1 empirical study is complete. **PREPRINT READY** refers to the scientific v1 preprint, not to every conference-side requirement. **ARCHIVAL / ICLR SUBMISSION READY** remains fail-closed until Gates F, G, and H are closed or explicitly determined not applicable.

Do not rerun or rewrite the frozen v1 primary inference to make the negative result cleaner. A future replication that pins the exact Python patch version, retains raw malformed model text, changes the output interface, or adds stronger models must be labeled as a new or supplementary study, not a replacement for v1.
