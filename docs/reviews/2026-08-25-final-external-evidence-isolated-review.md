# Final external-evidence isolated review

- Date: 2026-08-25
- Candidate commit: `6f13f72ce88bbc67880e92a69902a1e4b0cb1748`
- Reviewer: context-isolated AI reviewer
- Access: read-only checkout, no prior review narratives, no author defense, no model calls
- Recommendation: Weak Reject (4/10)
- Confidence: 4/5

## Summary

The submission presents a source-traceable protocol for turning finite executable-policy
differences into paired model-service regression tests. Its strongest features are complete
end-to-end denominators, exact finite-suite certificates, primary-source bindings, released
confusion matrices, and a substantial deterministic replay artifact. Six revisions across five
projects support the policy, verifier, and adapter fault model. The central hosted study is more
limited: every available Gatekeeper action is semantically correct, and its losses arise from
timeouts or response envelopes. The work therefore supports a prospective testing protocol, not a
claim about deployment prevalence or general research-agent ability.

The review found no fabricated source, arithmetic error in the reported frozen studies, privacy
leak, or ICLR page-limit violation. It did find one material reporting defect: the manuscript used
one “strict” label for two incompatible historical parser behaviors. That defect is safely fixable
from retained records without another model call. The largest remaining weakness—absence of an
independently authored deployed route in which a model interprets a changed executable policy—needs
new external evidence and cannot be repaired through prose.

## Strengths

- Every scheduled transport, syntax, schema, and semantic failure remains in the end-to-end item
  and pair denominator.
- The Gatekeeper, Trivy, Cosign, AGT, and agentgateway evidence is bound to exact upstream commits,
  tests, licenses, and local receipts.
- The set-cover dynamic program and edge lower bound are correct for the declared finite candidate,
  witness, and rule/edge inventories.
- The 465-seed fixed-query audit records all 11 source-reviewed candidates and the two qualifying
  boundary-fault cases. It makes zero model calls and does not claim prevalence.
- The deterministic policy executor is presented as the label definition, while Naive Bayes is
  correctly described as a weak sanity control.
- The anonymous artifact supports deterministic source and score replay while withholding failed
  response text, provider identifiers, hidden reasoning, account identity, and private provenance.

## Ranked findings

### Major 1 — “Strict” endpoint semantics mix raw JSON parsing with registered route parsing

The manuscript states that its strict endpoint accepts a parser-owned object or one strict
top-level JSON object while also saying that fence extraction is rejected. Those claims cannot both
define one parser. The frozen balanced-challenge Qwen route contains six fenced responses accepted
by its registered deterministic single-object extractor. Four actions and two complete pairs among
those six are correct.

Reparsing retained raw text as exactly one duplicate-free top-level JSON object gives:

- 143/180 extractable Qwen actions;
- 128/180 correct items;
- 61/90 covered pairs; and
- 46/90 correct pairs.

The frozen registered parser and full contract retain 148/180 actions, 132/180 correct items,
64/90 complete pairs, and 48/90 correct pairs. All end-to-end denominators remain 180 items and 90
pairs. No audited response contains a duplicate key.

Across all 1,320 audited records, raw-strict parsing finds 69 extractable actions outside the full
contract, including 49 correct actions and 40 correct pairs. The reverse relation also occurs: 452
full-contract actions are unavailable to raw-strict parsing, including 329 correct actions and 78
correct pairs. Historical local routes account for most of the latter through registered
single-object extraction. The endpoints are nonnested.

Required fix: define raw-strict parsing, registered-parser action, contract action, and exact full
decision separately; release parser provenance and parser source; update the Qwen table, recall row,
and raw-strict confusion matrix.

### Major 2 — Problem significance remains prospective

The upstream histories establish real executable-policy, verifier, and guardrail-adapter faults.
They do not establish how often deployed systems ask a model to interpret an executable policy
revision. AGT and agentgateway validate faults at agent or model-adjacent boundaries, but neither is
a frozen model-service policy-interpretation route of the form evaluated by the benchmark.

Required fix: frame the contribution as a source-traceable prospective testing protocol. A stronger
impact claim requires an independently authored deployed route, operational incidence, or a public
failure report.

### Major 3 — Novelty is an integration claim

Finite semantic differencing, behavioral contrasts, metamorphic and conformance testing, policy
test generation, set-cover reduction, structured-output evaluation, and selective prediction are
established. The supported novelty is their joint use in one test object: an action-changing
executable-policy revision, paired model-service records, rule/action-transition certificates,
parser provenance, and failure-inclusive endpoints.

Required fix: use bounded enumerator/protocol language and provide a direct prior-work comparison
organized by controlled coordinate. Do not imply a new general-purpose policy compiler.

### Moderate 1 — Public-freeze evidence is retained but not independently reachable

The receipts support the ordering “commit before model calls,” but an unauthenticated reader cannot
currently recover the original private workflow URLs. “Publicly frozen” is therefore stronger than
the reviewer can verify. Use “author-created and commit-frozen before calls according to retained
workflow receipts.”

### Moderate 2 — agentgateway is not a parent-to-fix replay

The exact fixed commit builds and passes all 33 selected offline tests. The parent behavior is
source-audited; the post-fix test module was not retrofitted onto and rerun against the parent. The
abstract and evidence table must preserve that distinction.

### Moderate 3 — Artifact replay scope needs a precise name

The anonymous bundle deterministically replays released source checks, score aggregation, Python
tests, and Lean checks. It cannot reproduce time-dependent hosted inference because it intentionally
does not reissue calls. Describe it as source and score replay.

### Moderate 4 — Historical parser and SLSA provenance need explanation

The endpoint derivative should include the parser implementation and direct-versus-extraction
provenance. Frozen SLSA plans also contain inert hashes for excluded exploratory runners. State that
those scripts and their results are absent from the release and contribute no manuscript metric.

## Source and literature validity

All six cited public revisions were found at their recorded upstream locations and match the
manuscript's bounded descriptions:

1. Gatekeeper FlexVolume empty-list behavior;
2. Gatekeeper selector-kind behavior;
3. Trivy KCV0030 predicate inversion;
4. Cosign Rego verifier handling;
5. AGT deny-verdict generation, with 11/15 parent and 15/15 fixed tests; and
6. agentgateway Bedrock guardrail adaptation, with the fixed commit passing 33/33 selected tests.

The behavioral-testing, contrast-set, metamorphic-testing, conformance, policy-differencing,
structured-output, selective-prediction, and research-agent citations are valid primary sources for
their stated roles. The manuscript does not support a prevalence estimate, causal model/provider
comparison, or naturalistic model-policy interpretation result.

## Numerical and artifact audit

- The 144-call Gatekeeper totals, terminal taxonomy, three repetitions, and all 63 OPA-correct
  available actions recompute.
- The r6 and challenge coverage, end-to-end and conditional metrics, all 13 action-recall rows, and
  all 232 released confusion-matrix cells recompute.
- The historical r6 Flash lane contains 300 HTTP 401 outcomes before model output and remains
  non-evaluable for model efficacy.
- The quota-confounded seven-route supplement is absent from the manuscript; no successful-cell
  subset is promoted as a model result.
- The reviewed anonymous ZIP contains 626 files at the reviewed commit, passes its manifest and
  privacy scans, and contains no searchable author, account, provider-ID, hidden-reasoning, or
  private-commit marker.
- The reviewed ICLR candidate has eight main-text pages under the probe and begins references after
  the main text. No clipping, overlap, or unreadable main-text table was found.

## Bottom line

The paper is a careful and useful software-testing artifact with a defensible integration novelty.
Its evidence does not yet establish a large deployed problem or broad model capability result. The
endpoint-label defect, novelty comparison, freeze wording, agentgateway wording, and replay boundary
are safely repairable. Deployment prevalence, independently authored model-mediated policy
revision, cross-stack causality, and stochastic fault-detection power require new evidence.

The 4/10 recommendation applies to the reviewed commit. The protocol requests no second reviewer
and no post-revision score.
