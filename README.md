# ClaimPromoteBench: Compiling Policy Differences into Failure-Aware State-Transition Tests

ClaimPromoteBench compiles behavioral differences between executable policy versions into paired
state-transition tests, then evaluates the complete model-service route against the resulting
contract. It is a synthetic conformance-testing protocol, not an evaluation of general
research-agent ability or naturalistic scientific judgment.

## Task

Each item contains a typed subject, evidence ledger, current state, requested target state, and
frozen evaluation time. The policy returns one of four actions:

`ALLOW` · `HOLD` · `DEMOTE` · `ESCALATE`

Research status, computational support, formal certification, and independent review remain
separate state axes. Evidence pairs change one registered prerequisite under a fixed policy;
policy pairs change only the active profile while reusing the evidence and states. A response
counts as valid only if it satisfies the JSON contract and all cross-field semantics.

Service, syntax, schema, and semantic failures remain incorrect in end-to-end metrics. Conditional
accuracy is reported only beside decision or pair coverage. The deterministic policy executor
defines the labels and is therefore a definitional policy ceiling, not a learned baseline.
Primary correctness is action-level after gold-free schema and cross-field validation; it is not
an exact-match score over every field in the decision object.

## Principal evidence

The fresh hidden r6 diagnostic contains 300 items and 150 controlled pairs. Its gold distribution
is imbalanced, with only eight `DEMOTE` and eight `ESCALATE` items.

| Configuration | Valid | E2E item / pair | Conditional item / pair | Pair coverage |
|---|---:|---:|---:|---:|
| Qwen3.7-Max | 272 / 300 | 0.860 / 0.753 | 0.949 / 0.919 | 0.820 |
| Public-development text Naive Bayes | 300 / 300 | 0.613 / 0.227 | 0.613 / 0.227 | 1.000 |
| Old Flash service interface | 0 / 300 | 0.000 / 0.000 | N/E | 0.000 |

The Qwen configuration recovered 143/150 `ALLOW`, 110/134 `HOLD`, 0/8 `DEMOTE`, and 5/8
`ESCALATE` items end to end. The Naive Bayes comparator is a weak learned reference. The old Flash
lane returned 300 HTTP 401 responses before any model output; it measures failure of that frozen
service interface and supplies no model-efficacy estimate.

The separate public robustness challenge contains 180 items and 90 pairs over 15 factors. It
balances 90 `ALLOW` members with 30 members for each other action.

| Configuration | Valid | E2E item / pair | Conditional item / pair | Pair coverage |
|---|---:|---:|---:|---:|
| Qwen route | 148 / 180 | 0.733 / 0.533 | 0.892 / 0.750 | 0.711 |
| Flash route | 146 / 180 | 0.500 / 0.144 | 0.616 / 0.213 | 0.678 |

End-to-end `DEMOTE` recall is 4/30 for Qwen and 0/30 for Flash. Full confusion matrices, all action
recalls, factor-level pair outcomes, and privacy receipts are reported in the manuscript and
committed result artifacts. The challenge was public before inference, and the two routes use
different service stacks. Their difference is descriptive; it is neither hidden-test
generalization nor a causal ablation.

## Policy-migration release gate

For two executable policy profiles, ClaimPromoteBench enumerates contexts on which their prescribed
actions differ. It reports changed-rule coverage separately from reachable directed action-edge
coverage. In the frozen software-policy instrument, a 60-pair rule-stratified suite covers all 12
changed rules but only 6/10 reachable edges and detects 6/10 registered edge-local stale-policy
mutants. The balanced graph suite covers and detects all ten edges; two other directions are
structurally impossible because pair members share their current state.

The reusable compiler in `src/claimpromotebench/policy_difference.py` accepts arbitrary
deterministic policies, a finite context grammar, stable context identifiers, and authored rule
witnesses. It has no dependency on the two study ontologies, prompts, models, or providers. The
exact search returns a smallest jointly rule- and edge-complete suite even when one context per edge
is insufficient; a specialized lower-bound search certifies minimum witnesses that use one context
per edge. A cross-check reconstructs the published witness from the frozen 60-pair candidate graph.
Test-suite reduction is established software-engineering practice; the contribution here is the
paired model-service test object and the joint changed-rule/action-transition adequacy target.

A deterministic selection over the frozen graph yields a provably minimum joint-adequacy smoke
suite: ten pairs, 20 route calls, all 12 rules, and all ten reachable edges. This cuts the structural
gate by 83.3% relative to the 60-pair graph suite. The full suite remains the diagnostic tier for
six-context-per-edge evidence, factor localization, and stochastic-route assessment. Neither the
mutation family nor the minimum suite estimates production fault prevalence.

This division supports two reproducible release operations. A policy change regenerates the
difference set, adequacy certificates, and minimum gate; a model, prompt, decoder, adapter, or
provider change replays the already frozen pairs.

On the 60-pair graph, pinned local Mistral produced 71/120 valid decisions, 40/120 correct items,
and 10/60 correct pairs; Phi-4 produced 43/120, 27/120, and 2/60. Conditional pair accuracy was
10/31 and 2/8, and both routes had 0/24 end-to-end `DEMOTE` recall. On the prospectively selected
minimum gate, Mistral produced 14/20 valid decisions, 9/20 correct items, and 2/10 correct pairs;
Phi-4 produced 6/20, 5/20, and 0/10. Both failed the fixed strict gate. The subset reuses the full
graph records and is not an independent replication.

A separately frozen 40-cell hosted execution of this minimum suite was excluded in full after all
cells returned explicit shared-quota exhaustion. It supplies no model-efficacy row and was not
retried; the public-safe artifact retains only a redacted all-or-nothing exclusion receipt.

## Install and run checks

Python 3.11 or newer is required.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'

python -m pytest --cov --cov-branch --cov-report=term-missing --cov-fail-under=80
ruff check .
ruff format --check .
mypy src
python scripts/lint_paper_submission.py
```

Rebuild and validate the public alpha benchmark:

```bash
python scripts/build_alpha.py
python -m claimpromotebench validate data/alpha
python scripts/audit_public_pair_contracts.py \
  --dataset data/alpha \
  --out work/public-pair-contract-audit.json
python -m claimpromotebench.shortcuts \
  --dataset data/alpha \
  --out work/shortcut-audit.json
python -m claimpromotebench.invariance \
  --dataset data/alpha \
  --out work/invariance-audit.json
```

Build the anonymous reviewer derivative and replay its empirical claims without model credentials:

```bash
python scripts/build_anonymous_review_bundle.py --out work/anonymous-review
cd work/anonymous-review
python scripts/run_review_checks.py
```

Pinned Lean checks and executable fixtures are documented in
[`docs/EXPERIMENTS.md`](docs/EXPERIMENTS.md). Completed singleton model studies must be replayed
from committed records and must not be rerun as part of paper construction.

## Scope and evidence policy

- The policy and labels are authored operational definitions; oracle agreement does not establish
  scientific truth or community consensus.
- Rule-coverage certificates trust authored witness mappings; action edges are recomputed, but an
  incorrect witness inventory would invalidate rule adequacy.
- The hidden r6 study tests a fresh realization of the same ontology and mostly the same template
  family.
- The balanced challenge is a known public robustness construction.
- One call per item and zero client retries define the service-level estimand.
- No naturalistic cases were scored because the frozen candidates lacked sufficient source evidence
  for a defensible policy mapping. No human labels or agreement statistic are claimed.
- Later executability of a different Flash route does not repair the old r6 HTTP 401 lane or identify
  the cause of a cross-stack performance gap.

## Paper, evidence, and release boundary

- Canonical manuscript: [`technical-report/main.tex`](technical-report/main.tex)
- Scientific and packaging gate: [`technical-report/SUBMISSION_GATE_V2.md`](technical-report/SUBMISSION_GATE_V2.md)
- Balanced challenge evidence: [`v2/balanced-public-challenge/results/`](v2/balanced-public-challenge/results/)
- Fresh r6 reviewer evidence: [`release/reviewer-evidence-source/fresh-confirmatory/`](release/reviewer-evidence-source/fresh-confirmatory/)
- Data licensing: [`DATA_LICENSE.md`](DATA_LICENSE.md)
- Third-party notices: [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)
- Future public export policy: [`docs/PUBLIC_RELEASE_BOUNDARY.md`](docs/PUBLIC_RELEASE_BOUNDARY.md)

This development repository remains private. A future public repository must be a new,
history-free export containing the minimum replay core. It must pass dynamic manifest, privacy,
licensing, metric-replay, and standalone-install gates before publication.

The private development history also retains completed studies that are not part of the paper or
anonymous reviewer package. Their presence must not be interpreted as submission evidence.
