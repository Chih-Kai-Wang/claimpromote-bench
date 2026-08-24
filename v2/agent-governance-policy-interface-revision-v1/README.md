# Agent-governance policy-interface revision

This addendum reproduces one historical Rego interface fault from Microsoft Agent Governance
Toolkit commit `e87b74530e1cbae54d5e90bc1b45ecf5c8911b28`. The repository documents a
deterministic policy decision point around agent input, model, tool, and output intervention
points. The selected stock Rego helper is used by callers that turn a pattern match into a deny
verdict.

Before the fix, `matches_any` accepted a zero-length leftmost regex match while `first_match`
dropped it because OPA defines no result for `indexof(text, "")`. The resulting deny verdict was
undefined. The upstream commit records that a caller using the match as a gate and the verdict as
its decision could fall through to its default. The fix adds a deterministic placeholder offset.

The exact post-fix upstream test file contains 15 tests. OPA 1.19.1 passes 11/15 against the exact
parent source and 15/15 against the exact fixed source. The four failures are the four tests added
for the fault; two directly require a deny verdict. The two decision cases are preserved as an
author mapping from an undefined deny verdict to the commit-documented caller fallback
(`ALLOW`) and from `deny` to `HOLD`.

This is external fault evidence at a deterministic agent policy boundary. It is not a model
inference result, a deployment-frequency estimate, or evidence that a model should replace the
policy engine. The reproduction makes zero model or hosted-service calls.

Rebuild and validate from the repository root:

```text
python scripts/build_agent_governance_policy_interface_revision.py --check
python scripts/validate_agent_governance_policy_interface_revision.py
```
