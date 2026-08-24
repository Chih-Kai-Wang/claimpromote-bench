# Final isolated ICLR review (2026-08-24)

This is the single final review requested for the release candidate at commit `6a00fec`.
The reviewer worked in an isolated, read-only context and reconstructed the paper, receipts, and
anonymous bundle from scratch. No further reviewer will be commissioned for this revision cycle.

## Verdict

- ICLR score: **4/10**
- Confidence: **4/5**
- Recommendation: **reject in the reviewed form**
- Numerical consistency: **pass**
- Anonymous-artifact integrity: **pass**
- Reproducibility: **pass for metric and contract replay**, not exact hosted or hardware-specific
  inference re-execution

The rejection was not based on arithmetic, denominator manipulation, anonymity, or an invalid
central reduction. It was based on insufficient ICLR-level novelty and impact in the reviewed
framing.

## High-priority findings

1. The title, abstract, and contribution list combined established semantic differencing,
   contrast testing, transition coverage, mutation testing, constrained output, and set-cover
   reduction as if they jointly constituted a new algorithmic advance. The defensible new claim is
   narrower: paired, failure-aware action-conformance testing of model-service routes under an
   executable policy revision. The established components should be called adaptations or
   implementation machinery. The intended use must be an existing model-mediated boundary, not a
   claim that a model should replace a deterministic executor.
2. The aggregate description of five evaluations and 420 pairs overstated evidence for the central
   policy-revision claim. Only the 120 policy-switch and transition-graph pairs exercise policy
   differencing; both use one authored migration, one finite grammar, the same two local model
   snapshots, one stack, one decoding setting, and no independent replication. The minimum gate
   also reuses graph records. Central migration evidence must be separated from auxiliary evidence
   and failure-accounting diagnostics.
3. Hosted-route selection and route-stack confounding were not prominent enough. The hosted
   configurations were retained after an older adaptive interface study because they completed
   that interface. Qwen used prompt-only JSON, Flash used strict schema output, the historical
   Flash run produced only HTTP 401 responses, and later Flash results used another service path.
   Tables should label route stacks, the selection timing belongs in the evaluation section, and
   the historical 401 event should be reported as an interface failure rather than a model row.

## Additional findings

4. The two unreachable HOLD/DEMOTE directions were identified correctly, but the stated premise
   that HOLD requires a CANDIDATE state was false. The correct proof uses first-match precedence:
   DEMOTE requires an ADMITTED state with a failed enforced check; on that state, the same failure
   reaches DEMOTE before HOLD, while DEMOTE is unavailable on non-ADMITTED states.
5. The exact bit-mask dynamic program is correct but should be presented as implementation
   machinery. Two functions in one module over one input do not constitute independent
   reconstruction, and the released optimum meets the direct one-pair-per-edge lower bound.
6. The primary endpoint is action conformance after output-contract validation, not exact
   six-field policy execution. Proposition 1 is a necessary, not sufficient, certificate of using
   the controlled coordinate.
7. Naive Bayes, Random Forest, profile-aware/profile-blind comparisons, and the deterministic
   executor are sanity or shortcut controls, not competitive learned baselines.
8. Result tables were cramped despite unused main-text space. Route results and sanity controls
   should be separated, and slash-packed confusion matrices should be expanded into explicit
   prediction columns.
9. The artifact supports metric and contract replay. It should not be described as unrestricted
   reproduction of hosted or hardware-specific inference.

## Independently reconstructed checks

The reviewer matched all five dataset sizes and supports, all reported route metrics, all action
recalls, and every confusion cell. Across 1,920 model-service records, the reviewer counted 1,208
valid outcomes and 712 retained failures: 315 HTTP, 54 transport, 48 JSON syntax, 11 schema, and
284 semantic failures. The reviewed PDF had nine main-text pages, references beginning on physical
page 10, and appendices on pages 13--14. The anonymous ZIP had 542 entries (541 manifest entries
plus the manifest), all manifest hashes matched, and no identity, hidden-reasoning field, provider
response identifier, raw malformed response, or invalid structured decision was found.
