# Sigstore policy-verifier revision addendum

This addendum reproduces a historical policy execution-interface defect from Sigstore Cosign. It
is external fault validation for the test methodology. The Gatekeeper studies remain the policy-
migration evaluations.

Sigstore commit `3b597b999ad083afd2ce0dba68fa2715ddec0f06` changed the verifier query from
`data.signature.deny` to `data.signature.allow`, required an explicitly true result, and treated an
undefined result as a failed policy check. The parent commit is
`0c26fba3492cd6047fbfecbad622c9c2782fb16a`. The `sources/` directory stores exact historical
copies of the pre-fix and post-fix verifier plus the post-fix upstream regression tests. The source
registry binds their paths, commit hashes, and SHA-256 digests.

The six committed contexts contain two exact upstream regression-test semantics, one failure mode
stated in the upstream commit message, and three separately labeled author extensions. OPA 1.19.1
evaluates both historical query targets. The pre-fix and post-fix verifier semantics produce four
`ALLOW->HOLD` and two `HOLD->ALLOW` transitions. A four-case exact minimum covers the four
registered historical fault modes and both observed action directions.

This study makes zero model calls. It establishes that the compiled action-transition view exposes
one independently documented verifier revision over the committed cases. It does not estimate a
production fault distribution or model-route accuracy.

Rebuild and validate from the repository root:

```text
python scripts/build_sigstore_policy_verifier_revision.py --opa /path/to/opa.v1.19.1 --check
python scripts/validate_sigstore_policy_verifier_revision.py
```
