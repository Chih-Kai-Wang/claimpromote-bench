# ClaimPromoteBench publication roadmap

The project is on a fail-closed publication path: calendar dates are secondary to validated, hash-bound evidence. Version 1 primary inference is now complete; the remaining path is manuscript verification and reproducibility release, not rerunning the frozen models.

| Phase | Deliverable | Gate | Current state |
|---|---|---|---|
| Alpha engineering | 20 controlled pairs, schemas, policy, oracle, executable numerical fixtures, pinned Lean fixtures, shortcut/metamorphic audits | Deterministic validation and CI pass | **DONE** |
| v1 design freeze | 200-pair plan, 50-pair public dev / 150-pair private hidden allocation, stable policy, shared constructor | Frozen plan and semantic validation | **DONE** |
| Public dev set | 50 pairs / 100 instances with executable bindings | Schema/pair/oracle/artifact/shortcut/metamorphic + pinned Lean replay | **DONE** |
| Private hidden freeze | 150 pairs / 300 instances from private seed; hidden/prompt commitment before inference | Commitment chronology and hashes validate | **DONE** |
| Model/runtime freeze | Qwen3-0.6B and 1.7B Q8_0, exact GGUF identities, decoding contract, llama.cpp runtime, per-run preflight | Exact identities recorded before scored inference | **DONE** |
| Frozen primary inference | 2 models × 4 arms × 3 seeds × 300 hidden instances = **7,200 decisions** | Exactly 24 immutable source artifacts / 7,200 inference records | **DONE** |
| Artifact-only recovery | Preserve completed inference; reclassify only frozen cross-field semantic output violations as `FORMAT_ERROR` | 24 normalized runs, exact prompt hashes, 10,000 pair-bootstrap aggregate, provenance | **DONE** |
| Primary paper Results | Populate manuscript only from validated recovered artifact; retain negative results and coverage limitations | Every reported primary number artifact-derived | **DONE** |
| Preprint finalization | Citation authority check, current CI/LaTeX compile, PDF visual/reference audit, final quantitative cross-check | No unbound claim or unresolved paper defect | **IN PROGRESS** |
| Reproducibility release | Immutable tag/archive and clean-environment regeneration of validation/tables | Release hashes and paper identities agree | **PENDING** |

## Frozen v1 evidence

- hidden commitment commit: `8d9b3f5c831f432cf6b321e6402724c4f52bb3e1`;
- scored inference head: `aa5268dcde2aa44f8eabf0246631efbca27de7e5`;
- source workflow: `32255636879`;
- recovered workflow: `32274814703`;
- primary matrix: 24 runs / 7,200 hidden decisions;
- recovered study SHA-256: `sha256:3eb5b534ab486dac774a62de3d623fa33009be3705d9e8d620bb9942e8bfe664`;
- semantic recovery: 27/7,200 records reclassified as `FORMAT_ERROR`; no legal model decision rewritten and no inference rerun.

The one-shot recovery trigger has been removed. The frozen primary matrix must not be rerun merely to obtain cleaner output or more convenient matched groups.

## Current critical path

1. Keep PR #19 Draft and preserve every frozen source/recovery artifact.
2. Finish repository-wide removal of stale pre-study wording and keep the 200-pair benchmark distinct from the 300-instance primary hidden study.
3. Run the latest full CI and paper workflow; fix only genuine code/manuscript defects without changing frozen primary semantics.
4. Compile and visually inspect the post-results PDF for unresolved references/citations, table overflow, stale blocker text, anonymity leaks, and metadata problems.
5. Recheck all final manuscript quantitative values against the validated recovered artifact.
6. Verify bibliography entries against authoritative publication/preprint records before archival submission.
7. Produce an immutable release candidate and clean-environment reproduction of benchmark validation and paper tables/statistics.
8. Only after the applicable gates pass, decide whether to release a preprint; archival-submission readiness additionally requires the release/archive gate.

## What v1 actually found

The dominant result is negative at the model-intent layer: 5,327/7,200 outputs are `FORMAT_ERROR`, and all 1,873 parseable raw intents are `ALLOW`. The deterministic gate eliminates measured false promotion among covered decisions without false blocking, but coverage is low. This is a **system-level enforcement result**, not evidence that model reasoning improved.

The exact comparison pipeline also retained a hosted Python patch-version identity drift (3.11.15 vs 3.11.16), which splits three intended model×seed matched groups. This limitation is disclosed rather than repaired post hoc.

## Scope control

Version 1 does not expand into live web research, cross-science datasets, RL, fine-tuning, or large-model training. The contribution remains a preregistered, controlled-pair, artifact-bound evaluation of policy-governed evidence-state transition admissibility.

The supplementary two-reviewer human audit is **mixed / not PASS** and remains supplementary. Reviewer disagreements are not used to change frozen v1 gold or policy.

Success is not measured by stars, model self-ratings, or a deterministic veto presented as model improvement. Success is a defensible research claim whose benchmark, negative results, provenance, limitations, and reproducibility record remain auditable.
