# r4 zero-POST orchestration failure

Run `32438952742` is the terminal scored execution for
`claimpromotebench-v1-fresh-confirmatory-2026-08-r4`.

Both registered lanes stopped at the frozen-source byte check before the
gold-free runner could create a durable `POST_INTENT`.  The C2 seal records
all 600 planned cells as `NOT_ATTEMPTED_ORCHESTRATION_FAILURE`, with zero
application POSTs and zero client retries.  No model output was observed and
no r4 cell may be sent later.

The failure was caused by the scored workflow's default shallow checkout:
the committed source object required by the frozen-plan comparison was absent
from the runner clone.  The workflow therefore reported the deliberately
generic fail-closed message `current plan bytes differ from the supplied
frozen commit` for both lanes.

The exact reviewer-evidence artifact emitted by the run is retained below.
The separate `execution-receipt.json` binds the GitHub run, job identifiers,
failure message, artifact digest, and the machine-verifiable zero-POST facts.
r4 is not relaunched or resumed; any orchestration repair belongs to a new
study version with a new C0, salt, beacon, seed, hidden realization, and C1.
