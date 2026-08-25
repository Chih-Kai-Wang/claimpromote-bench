# ClaimPromoteBench: Source-Traceable Regression Tests for Model Services under Policy Revision

ClaimPromoteBench turns versioned policy changes into paired tests for a model-service boundary.
For executable policies, it enumerates the behavioral difference between two caller-supplied
evaluators. For versioned prose, it binds immutable source versions to a declared action mapping.
Changed pairs hold the request fixed and require the prescribed action to change; stable controls
test whether the route reacts indiscriminately to a source update.

The benchmark is a synthetic, policy-constrained evaluation. Its claims concern finite authored
context grammars and time-stamped route stacks. A direct deterministic executor remains the
preferred enforcement path when an application can call the policy itself.

Eight public histories ground the tested fault classes. Two independently authored `AGENTS.md`
revisions provide model-facing policy sources. The study authors map ten frozen scenarios to finite
actions under the pinned source versions; no human annotation enters the evaluation.

## What the enumerator and reducer produce

Given `P_old`, `P_new`, a finite context set with stable identifiers, registered changed-rule
witnesses, and declared coverage inventories, the implementation:

1. executes both policies over every context;
2. retains contexts whose prescribed actions differ;
3. creates paired items that vary only the policy source;
4. reports changed-rule and directed action-transition coverage relative to those inputs; and
5. selects a cardinality-minimum structural-coverage suite.

Policy parsing, context synthesis, rule-change discovery, and witness inference remain caller
responsibilities.

The reusable implementation is in `src/claimpromotebench/policy_difference.py`.

## Scoring endpoints

Every scheduled call remains in end-to-end denominators. The evaluator separates four reporting
layers:

- **raw-strict action**: the retained response is exactly one duplicate-free top-level JSON object
  containing a registered action;
- **registered-parser action**: the frozen route parser records a valid action, with provenance for
  direct parsing or deterministic single-object extraction;
- **contract action**: the registered action is correct after the complete task contract passes;
  and
- **full decision**: the complete structured decision matches the deterministic oracle.

The raw-strict parser performs no repair, code-fence extraction, coercion, or duplicate-key
recovery. Registered-parser semantics remain route-specific because the historical records are
frozen; the audit reports that provenance instead of relabeling it as raw-strict parsing. No
audited response contains a duplicate key. Transport, syntax, schema, and semantic failures remain
terminal errors. Conditional metrics are reported beside the corresponding coverage denominator.

## Evidence layers

| Instrument | Evidence role | Size | Main certificate or result |
|---|---|---:|---|
| OPA and Woo `AGENTS.md` revisions | external model-facing policy study | 10 pairs; 8 routes | changed and stable source-version tests |
| Matched factor-complete routes | route-interface diagnostic | 15 pairs; 7 routes | full factor support and three repetitions |
| Gatekeeper revisions | executable policy study | 12 pairs | 2/2 rules, 2/2 edges, two-pair minimum |
| Gatekeeper repeated routes | executable-policy route study | 144 calls | three repetitions on each of two routes |
| Trivy KCV0030 | independent policy-fault reproduction | 4 cases | inverted predicate, two transition directions |
| Cosign Rego verifier | independent interface-fault reproduction | 6 cases | four documented verifier fault modes |
| Agent Governance Toolkit | agent-policy interface reproduction | 2 cases | 11/15 parent versus 15/15 fixed upstream tests |
| agentgateway Bedrock adapter | versioned guardrail-interface audit | 33 tests | exact fixed commit passes 33/33 offline tests |
| Authored SLSA migration | four-action structural stress test | 60 graph pairs | 12/12 rules, 10/10 reachable edges, ten-pair minimum |
| Research r6 | evidence-state coverage addendum | 150 pairs | rare-action support and complete denominators |
| Public balanced challenge | commit-frozen authored diagnostic | 90 pairs | 15 factors and balanced non-`ALLOW` actions |

Exact old and new upstream source bytes, commit bindings, licenses, source-validation receipts, and
minimum-suite certificates are stored under:

- `v2/upstream-policy-revisions-v1/`
- `v2/trivy-policy-revision-v1/`
- `v2/sigstore-policy-verifier-revision-v1/`
- `v2/agent-governance-policy-interface-revision-v1/`
- `v2/external-evidence-audit-v1/`
- `v2/external-agent-policy-revision-v2/`

## Model-facing policy result

Two public `AGENTS.md` histories contribute six changed pairs and four stable controls. Eight hosted
routes receive the same 20 items for three repetitions: 480 calls, one request per cell, and zero
client retries.

| Scope | Valid | E2E item | E2E pair | Conditional item/pair |
|---|---:|---:|---:|---:|
| Designated first replication | 132/160 | 128/160 | 52/80 | 128/132; 52/55 |
| All three repetitions | 399/480 | 387/480 | 158/240 | 387/399; 158/169 |

In the designated first replication, changed pairs score 23/48 end to end and 23/26 conditionally;
stable controls score 29/32 and 29/29. The pooled 81 terminal failures comprise 26 server-side
transport failures, nine length-terminated JSON failures, and 46 action/reason-code conflicts.
Failed outputs never enter decision counts and remain errors in end-to-end denominators.

The matched factor diagnostic sends one balanced-challenge pair for each of 15 registered factors
to seven routes. First-replication coverage spans 3/30 to 29/30 valid decisions and 0/15 to 11/15
correct pairs. Across all 630 calls, a length or token limit accompanies 280/281 syntax and schema
failures. These measurements describe complete route stacks; provider-side serving internals remain
opaque.

## Auxiliary evidence-state results

The executable-policy repetition sends 24 Gatekeeper items to two routes three times. Flash reaches
53/72 raw-strict actions and 21/36 pairs; Qwen reaches 10/72 and 0/36. All 63 extracted actions match
the executable oracle. The other cells comprise 12 read timeouts and 69 serialization or
output-envelope failures.

R6 Qwen returns 272/300 contract-valid decisions. Its end-to-end item/pair scores are 258/300 and
113/150, compared with 258/272 and 113/123 conditional. The historical r6 Flash path returned HTTP
401 before model output on all 300 calls; this records an obsolete service-interface failure.

The public balanced challenge contains 90 `ALLOW` items and 30 items for each of `HOLD`, `DEMOTE`,
and `ESCALATE`.

| Route | Valid | E2E item/pair | Conditional item/pair | `DEMOTE` recall |
|---|---:|---:|---:|---:|
| Qwen | 148/180 | 132/180; 48/90 | 132/148; 48/64 | 4/30 |
| Flash | 146/180 | 90/180; 13/90 | 90/146; 13/61 | 0/30 |

An offline audit of 1,320 prior route items separates raw-strict actions, actions retained by each
frozen registered parser, and the full contract. Raw-strict parsing recovers 69 actions outside the
full contract, including 49 correct actions and 40 correct pairs. Conversely, registered parsers
retain actions from responses that raw-strict parsing rejects; six balanced-challenge Qwen records
use deterministic single-object extraction from a fenced response. The audit reports parser
provenance, changes no frozen record, and makes zero model calls.

## Install and verify

Python 3.11 or newer is required.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
.venv/bin/python -m mypy
```

Run the paper and source bindings:

```bash
.venv/bin/python scripts/validate_upstream_policy_revision_study.py
.venv/bin/python scripts/validate_agent_governance_policy_interface_revision.py
.venv/bin/python scripts/validate_external_evidence_audit.py
.venv/bin/python scripts/validate_upstream_policy_route_repetition_results.py
.venv/bin/python scripts/lint_paper_submission.py
```

Build venue-specific TeX sources:

```bash
.venv/bin/python scripts/build_submission_tex.py --out work/submission
```

The official ICLR style files are hash-pinned by
`technical-report/iclr2027-style-lock.json`. `technical-report/main.tex` is the canonical
scientific source.

## Interpretation and release boundary

The deterministic executor defines every gold label and is the **definitional policy ceiling**.
The r6 multinomial Naive Bayes control reaches 184/300 items and 34/150 pairs and serves as a weak
shortcut check. The balanced challenge was author-created and commit-frozen before calls according
to retained workflow receipts. Route differences support descriptive interpretation only.

Reviewer-facing derivatives exclude raw failed responses, free-form errors, provider response
identifiers, hidden reasoning, account identity, and private commit identity. Their manifests
derive file counts from the generated trees. Completed one-shot studies remain frozen.

The durable export rules are recorded in `docs/PUBLIC_RELEASE_BOUNDARY.md`.

The repository, PR, and submission state are operational controls. A passing local build does not
authorize a merge, public release, OpenReview submission, or arXiv upload.
