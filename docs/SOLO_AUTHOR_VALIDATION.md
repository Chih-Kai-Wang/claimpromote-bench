# Solo-author validation protocol

ClaimPromoteBench is designed so that its core benchmark study can be completed by one author without inventing independent review.

Independent external benchmark review is useful supplementary evidence, but it is not a prerequisite for the core preprint or archival-submission readiness labels. If no external audit is obtained, the manuscript must disclose that fact explicitly.

## Why a solo path is defensible

The benchmark gold target is not an unrestricted human judgment about whether a mathematical claim is true. It is a deterministic decision about whether a requested evidence-state transition satisfies a versioned public policy. This allows most label integrity to be checked mechanically.

The solo protocol therefore substitutes precommitment and executable checks for a mandatory second human labeler. It does not claim that these checks create independent judgment.

## Mandatory controls

Before scored hidden-test results are inspected:

1. Freeze the benchmark policy and record its SHA-256.
2. Freeze the public development split.
3. Freeze the hidden-test manifest and publish its commitment before opening hidden labels.
4. Freeze prompt renderings and hashes.
5. Freeze model artifact, quantization, runtime commit, decoding settings, and seeds.
6. Regenerate gold labels from the deterministic policy oracle.
7. Validate that every controlled pair differs only at registered policy-relevant pointers.
8. Replay executable numerical artifacts and pinned Lean artifacts where applicable.
9. Run shortcut diagnostics and registered semantics-preserving metamorphic audits.
10. Record all failures and negative/null results rather than changing primary metrics after seeing outcomes.

After the freeze, a defect that changes policy semantics, a gold action, a prompt, or a controlled factor requires a new benchmark version. Affected scored runs become obsolete and must be rerun.

## What external reviewers would do if volunteers become available

The optional blinded-review workflow asks a reviewer to inspect benchmark packets without the gold label and choose the transition action required by the public policy (for example `ALLOW`, `HOLD`, `DEMOTE`, or `ESCALATE`) together with the relevant reasons. The repository can then compare reviewer decisions with the deterministic gold and report agreement/disagreements.

A reviewer is validating whether the authored policy/items reflect understandable intended semantics; the reviewer is not being asked to prove the underlying mathematical claims. Domain expertise is helpful for some cases but the benchmark is deliberately policy-driven and machine-checkable.

## If no reviewer is available

Do not fabricate reviewer identities, ask an AI model to stand in for an independent human, or call an author-side second pass “independent.” Instead:

- complete all mandatory controls above;
- disclose that the benchmark was constructed and audited by the author;
- state that no independent external benchmark audit was obtained;
- keep the blinded-review tooling available for post-publication volunteers;
- avoid claims that depend on human inter-rater agreement.

This limitation affects confidence in benchmark-design choices, not the reproducibility of the deterministic oracle, executable artifacts, frozen model runs, or reported statistics.
