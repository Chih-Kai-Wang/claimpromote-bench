# Trivy policy-revision validation

This study reproduces Aqua Trivy Checks commit
`e4defae1e4c6e346104f41e70489503069ad1b90`, which corrected an inverted policy predicate for
Kubernetes API-server encryption configuration. The parent commit is
`f37551204c6c6e731ccdc0b5ade0a74cf3f556b1`.

The `sources/` directory preserves the exact old and new policy, the post-fix upstream regression
tests, the exact upstream Kubernetes helper library, and the upstream MIT license. Trivy supplies
`result.new` as a host function. The deterministic build injects a six-line Rego compatibility
implementation solely to construct the deny payload; the policy predicate, input, and deny
cardinality remain upstream code. The receipt records this boundary and every source digest.

All four cases come from upstream regression tests. Configured and unconfigured API servers cover
both `HOLD->ALLOW` and `ALLOW->HOLD`. A two-case exact minimum covers the single documented fault
mode and both action directions. The study makes zero model calls.

Rebuild and validate from the repository root:

```text
python scripts/build_trivy_policy_revision.py --opa /path/to/opa.v1.19.1 --check
python scripts/validate_trivy_policy_revision.py
```
