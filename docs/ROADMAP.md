# ClaimPromoteBench publication roadmap

The project is now on an accelerated paper path. Calendar dates are secondary to fail-closed gates: a milestone advances only when its artifacts are validated and hash-bound.

| Phase | Deliverable | Gate | Current state |
|---|---|---|---|
| Alpha engineering | 20 controlled pairs, schemas, policy, oracle, executable numerical fixtures, pinned Lean fixtures, shortcut/metamorphic audits | Deterministic validation and CI pass | **DONE** |
| Paper scaffold | Anonymous manuscript, related-work positioning, fail-closed submission gate, paper CI | Compiles with explicit blockers and no fabricated results | **DONE** |
| Model/runtime freeze | Qwen3-0.6B and 1.7B GGUF identities, llama.cpp commit, decoding contract, preflight | Exact bytes/runtime verified before inference | **DONE FOR ALPHA PILOT; final scored study still requires its own recorded preflight** |
| Zero-cost alpha pilot | 2 models × 4 arms × 3 seeds × 40 alpha items = 960 decisions | Complete run records and study artifacts, not hand-copied scores | **RUNNING on GitHub-hosted CPU; workflow is manual-only to prevent accidental restarts** |
| v1 design freeze | 200-pair plan, dev/test allocation, stable policy identity, v1 schema, prompt/hidden commitment tooling | `configs/v1-benchmark-plan.json` arithmetic and semantic-no-op policy tests pass | **IN PROGRESS** |
| Public dev set | 50 pairs / 100 instances with diverse surfaces and executable bindings | Full schema/pair/oracle/artifact/shortcut/metamorphic validation | **NEXT CONSTRUCTION TARGET** |
| Private hidden test | 150 pairs / 300 instances generated with a private 32-byte surface seed | Private validation passes; public manifest/prompt/seed-hash commitment is committed before scored inference | **PENDING** |
| Frozen study | 2 models × 4 arms × 3 seeds × 400 instances = 9,600 decisions | Every shard complete or explicitly failed; validated cumulative study report | **PENDING** |
| Paper completion | Results generated from frozen study artifacts, limitations and AI disclosure updated | No submission blockers; every number reproducible from released artifacts | **PENDING** |
| Reproducibility release | Tagged code/data/run artifact release and archival copy as required | Clean-environment reproduction of validation and paper tables | **PENDING** |

## Current critical path

1. Let the already-running zero-cost alpha pilot finish and preserve its artifacts.
2. Finish the v1-compatible constructor and formal/numerical surface library; do not bulk-copy alpha rows.
3. Build and validate the public 50-pair dev split.
4. Freeze exact model-facing prompt hashes with `scripts/freeze_prompt_manifest.py`.
5. Generate the private hidden split with a fresh 32-byte seed kept outside public Git history.
6. Validate the hidden set, create the public-safe commitment with `scripts/make_hidden_test_commitment.py`, and commit that record before any scored hidden inference.
7. Run all 9,600 decisions, preferably with free GitHub-hosted CPU first and only consider paid compute if the measured runtime makes that impractical.
8. Populate the manuscript programmatically from validated study artifacts; never type results from memory or screenshots.

## Scope control

Version 1 does not expand into live web research, cross-science datasets, RL, fine-tuning, or large-model training. The benchmark remains a narrow test of policy-governed evidence-state transition admissibility.

External human audit is optional supplementary validation and is currently outside the critical path. Existing reviewer tooling and frozen materials remain preserved, but ordinary benchmark/paper commits do not rebuild them automatically. When reviewer submissions arrive, ingest them without changing the frozen v1 policy, benchmark factors, or scored-study plan.

Success is not measured by stars, downloads, model self-ratings, or a deterministic gate catch presented as model improvement. Success is a defensible benchmark claim backed by frozen artifacts, complete runs, and reproducible statistics.
