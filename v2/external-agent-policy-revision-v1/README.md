# External agent-policy revision study

This frozen study tests whether model-service routes track two public `AGENTS.md` revisions written
by upstream maintainers. It pins the change and parent revisions from Open Policy Agent and
WooCommerce Services, verifies source and license hashes, and supplies the complete active policy
to every request.

The dataset contains ten author-constructed pairs: six prescribed actions change with the policy
version and four are stable controls. The upstream policy text is independently authored; the
scenarios, action vocabulary, precedence rule, and labels are deterministic author mappings fixed
before model calls. The study has no human annotators, agreement statistic, deployment telemetry,
or prevalence estimate.

Eight OpenCode Go routes receive the same 20 items in three repetitions, for 480 planned calls.
Each cell permits one application request and zero client retries. Transport, syntax, schema, and
semantic failures remain incorrect in end-to-end metrics. Route comparisons are descriptive
because the model, provider, adapter, serving state, and execution time are not jointly controlled.
The OX Alpha route is an undisclosed, limited-time free service; its identity and data handling
remain unknown and are recorded as such.

`study-plan.json`, `request-schedule.json`, `prompt-packet.json`, the source receipt, and the dataset
were frozen before any case output. Do not rerun or partially resume the schedule after execution.
The privacy-safe `results/` derivative is the only route-output directory eligible for an anonymous
or future public artifact.

The v1 attempt is void. Its first request group exposed a local schema omission: the deliberately
disclosed `Undisclosed OX Alpha` family was absent from the shared run-record enum. Eight request
intents and three terminal records were durably written before the runner stopped; no execution
receipt or result derivative exists. The attempt was never resumed, its outputs were not inspected
or scored, and it is excluded from every paper endpoint. `void-attempt-receipt.json` binds the
failure evidence. A separately frozen v2 replacement preserves the cases, prompts, routes,
replications, and no-retry rule while correcting the schema and accounting for this attempt in its
quota bound.
