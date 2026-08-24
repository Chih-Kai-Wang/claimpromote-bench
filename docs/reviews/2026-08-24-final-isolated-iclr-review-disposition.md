# Disposition of the 2026-08-24 final isolated ICLR review

## Review boundary

The final isolated reviewer evaluated the preceding release candidate from scratch and assigned it
4/10 with confidence 4. The numerical reconstruction, artifact replay, and anonymity audit passed;
the recommendation was driven by contribution framing, evidence breadth, and presentation. This
revision was not sent to a second reviewer and was not rerated. The recorded 4/10 therefore remains
the review outcome for the snapshot that was actually assessed. It is neither an acceptance
prediction nor a score claimed for the revised manuscript.

No model call or completed singleton workflow was rerun for this disposition. All empirical changes
are reinterpretation, presentation, or deterministic validation of already frozen records. Every
scheduled invalid or absent decision remains in its end-to-end denominator, while malformed output
contents remain outside the manuscript and anonymous release.

## Finding-by-finding disposition

### 1. Contribution boundary and prior art — addressed

The title, abstract, introduction, related work, discussion, limitations, and conclusion now define
the contribution as paired, failure-aware action-conformance testing at an existing model-service
boundary under executable policy revision. Semantic policy differencing, edge-local mutation,
test-suite reduction, set cover, and exact bit-mask dynamic programming are explicitly identified as
established methods or implementation machinery. The claimed adaptation is their use to generate
paired route calls, preserve output-contract failures end to end, and separate changed-rule coverage
from observable action-transition coverage.

Primary related work now includes behavioral testing, contrast sets, metamorphic testing,
finite-state conformance, semantic policy differencing, mutation testing, test-suite reduction,
structured output, selective prediction, policy reasoning, and research-agent evaluation. The text
states the closest differences rather than asserting priority.

### 2. Central evidence breadth — addressed

The evaluation-design table and all summary prose separate the central migration from auxiliary
diagnostics. The central evidence is one authored `BLUE`-to-`AMBER` migration, two 60-pair suites,
and the same two pinned local routes evaluated once. There is no independent policy-family or route
replication. The ten-pair gate reuses frozen transition-graph records and is a low-cost structural
gate, not a new sample or sensitivity estimate. R6, the balanced public challenge, and fixed-policy
SLSA results are auxiliary route diagnostics and do not enlarge the central migration count.

### 3. Route selection and stack confounding — addressed

The evaluation section discloses that the hosted Qwen and Flash routes were retained after an older
adaptive interface study because they completed that interface. Route labels now encode the output
stack (`host/prompt`, `host/schema`, or `local/4b`) instead of implying model-family sampling.
Between-route comparisons are descriptive because weights, serving implementations, quantization,
prompts, adapters, and output constraints differ. The historical r6 Flash HTTP 401 outcome appears
as a pre-output interface failure in prose, not as a model-result row. A later executable Flash path
establishes only that the different path ran.

### 4. HOLD/DEMOTE unreachability proof — corrected

The proof now uses first-match precedence. `DEMOTE` requires an admitted state with a failed enforced
check. On an admitted state that failure reaches `DEMOTE` before `HOLD`; on a non-admitted state,
`DEMOTE` is unavailable. The old narrower premise that `HOLD` requires a candidate state was false.
A self-digested interpretation addendum binds and supersedes only that explanation; it changes no
policy, dataset, label, edge set, coverage value, selected suite, terminal record, or model metric.
The validator and regression tests recompute the corrected argument.

### 5. Optimization language — addressed

The manuscript calls the exact solver a standard subset dynamic program and states that the generic
and specialized functions reproduce the same frozen witness from the same input. It no longer calls
them independent reconstructions. The ten-pair optimum is tied directly to the one-pair-per-edge
lower bound and is not presented as an algorithmic contribution.

### 6. Endpoint and certificate scope — addressed

The primary endpoint is now named **action conformance after output-contract validation**. It does
not require exact agreement on all six output fields. Proposition 1 is explicitly necessary but not
sufficient: reacting to the controlled coordinate does not prove faithful policy execution.

### 7. Baseline status — addressed

The deterministic executor is a definitional policy ceiling, not a learned baseline. Naive Bayes is
a weak sanity control. The Random Forest and profile-aware/profile-blind rows are construction and
shortcut controls. They are separated from model-route results in the appendix and are not used to
claim competitive learned-policy performance.

### 8. Table readability — addressed

The central and auxiliary datasets are separated in the design table; model-route results and
controls use different tables. Four confusion tables now give explicit predicted-action and
no-valid-decision columns instead of slash-packed cells. The final PDFs are rendered page by page
and checked for overlap, clipping, crowding, orphaned headings, and table readability.

### 9. Reproducibility boundary — addressed

The paper claims metric and contract replay. The artifact binds frozen policies, datasets, prompts,
terminal outcome classes, structured decisions, analyses, and privacy receipts, and recomputes all
reported values. It does not claim unrestricted reproduction of time-dependent hosted inference or
hardware-specific local generation.

## Resulting novelty and impact statement

The revision makes one narrow operational claim. When an existing model route sits behind a finite
executable decision contract, a policy edit can generate its own paired regression tests. A
rule-complete suite can still miss observable action transitions; a graph-complete suite closes that
gap, and a minimum jointly adequate subset supplies a low-cost continuous-integration rejection
gate. The same frozen pairs can then audit prompt, decoder, adapter, provider, or model changes while
separating missing coverage, invalid output, and wrong actions. This scope includes structured
admission, escalation, and routing boundaries that expose deterministic policies and a finite
grammar. It does not extend to natural policy distributions, policy extraction from prose, or
general agent competence.

## Final verification

Final page counts, manifest-derived file counts, checksums, clean-environment replay, visual review,
and local test results are recorded in `release/submission-kit/validation-receipt.json` and
`technical-report/SUBMISSION_GATE_V2.md`. PR #20 remains draft; no merge, public release,
OpenReview upload, arXiv upload, or formal submission was performed.
