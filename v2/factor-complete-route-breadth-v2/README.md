# Factor-complete route-breadth study

This directory holds a prospective public robustness study over one deterministic pair for each
of the balanced challenge's 15 registered factors. Seven OpenCode Go configurations execute the
same 30 public items three times, with one application request per model-item-replication cell and
no client retries. The lexicographic factor selection, route list, output ceiling, concurrency,
metrics, and quota bound are frozen before benchmark inference.

The first replication is the matched breadth screen. All three replications support a separate
route-stability analysis. Historical Qwen and DeepSeek rows are recomputed from their existing
balanced-challenge records; those routes are not called again. The completed singleton workflow
and the quota-confounded seven-route breadth schedule must not be rerun.

The study compares route configurations descriptively. It does not isolate model weights from the
provider, API adapter, serving state, time, or output implementation, and it is not hidden-test or
deployment evidence. Raw final responses remain in the private development repository. Only
privacy-scanned terminal records and aggregates may enter an anonymous or future public bundle.
