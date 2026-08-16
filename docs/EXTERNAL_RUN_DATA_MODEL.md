# External run data model

A contributed result remains three separate objects:

- the immutable `run.jsonl` execution records;
- the contributor-owned `contribution.json` provenance and consent manifest;
- the derived evaluation or study report, which can always be regenerated.

Derived reports are not required inside a contribution directory. Keeping source records
separate from regenerated analysis prevents stale metrics from surviving evaluator changes and
lets future versions recompute AUPRC, gate effects, or family diagnostics from the same bound
run bytes.
