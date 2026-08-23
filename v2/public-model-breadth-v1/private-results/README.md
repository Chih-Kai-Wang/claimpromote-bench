# Private model-breadth execution evidence

This directory preserves the source records and durable execution journal for the single frozen
model-breadth run. It belongs only in the private development repository. Do not copy it into an
anonymous review bundle or a future public repository.

The completed archive contains seven 180-record lane files under `runs/`, the failure-aware
`aggregate.json`, the runner's `execution-receipt.json`, and the three files under `journal/`.
The execution receipt binds every lane file and both append-only journals. The public-safe
derivative in `../results/` binds each transformed row to its private source, removes final response
text and free-form error details, and records the exact-byte credential and privacy scan.
`privacy-scan-receipt.json` records a separate scan of this private archive; its dynamic counts
exclude the receipt itself.

No credential is stored here. Completed singleton evidence must be replayed from these records and
must not be resumed, retried, or rerun.
