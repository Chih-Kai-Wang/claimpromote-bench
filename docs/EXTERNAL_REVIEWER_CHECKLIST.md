# External reviewer checklist

This checklist is for optional blinded external validation of ClaimPromoteBench. It is not a request to peer-review the paper, prove the mathematics, or assess novelty.

## Reviewer eligibility

A reviewer should:

- not have authored or edited the benchmark items, policy, gold labels, model prompts, or model results;
- be willing to follow the blinded procedure and avoid opening gold labels or model outputs before finishing;
- be able to read the public transition policy carefully;
- disclose only broad background information needed for the paper (for example, mathematics undergraduate, computer-science undergraduate, or Lean experience). Public disclosure of the reviewer's name is not required.

A mathematics/computer-science student is an appropriate candidate for this audit. Deep expertise in every benchmark family is not required because the task is policy application, not theorem proving.

## What the reviewer receives

Send only:

1. the blinded `packet.jsonl`;
2. `packet-manifest.json`;
3. the exact manifest-bound policy file;
4. an initialized reviewer submission file;
5. these instructions.

Do not send gold labels, pair descriptors, model outputs, aggregate scores, disagreement lists, another reviewer's answers, or the private packet mapping.

## What the reviewer does

For every blinded item:

1. Read the claim, current evidence state, requested transition, and supplied evidence.
2. Apply the public policy exactly as written.
3. Choose one action: `ALLOW`, `HOLD`, `DEMOTE`, or `ESCALATE`.
4. Select one or more permitted policy reason codes.
5. Give confidence from 1 to 5.
6. Optionally write a short rationale when the case is ambiguous or the policy seems unclear.
7. Do not search the repository for the corresponding item, gold label, or model answer.
8. Do not coordinate answers with the author or another reviewer while the packet is open.

An `ALLOW` decision uses `POLICY_SATISFIED`; a non-`ALLOW` decision must use the applicable non-satisfied reason code(s).

## What the reviewer is NOT asked to do

The reviewer does not need to:

- prove any theorem;
- verify Lean source line-by-line;
- recompute every numerical artifact manually;
- judge whether the scientific claim is ultimately true;
- judge whether the paper is novel enough for a venue;
- inspect source code or CI;
- write a referee report;
- reveal their real name publicly.

The purpose is narrower: check whether an independent reader can apply the declared evidence-transition policy to blinded benchmark items in a way broadly consistent with the frozen benchmark semantics.

## Final attestations

Before returning the submission, the reviewer confirms that:

- the judgments were completed independently;
- gold labels and model outputs were not inspected;
- no collaboration was used to choose answers;
- the submission may be used in aggregate research reporting after the review closes;
- the completion timestamp is accurate.

## What the author does after receiving it

The author:

1. validates the returned submission with the repository tool;
2. records its SHA-256 before unblinding;
3. closes the review so the reviewer cannot revise answers after seeing gold;
4. unblinds only after closure;
5. computes reviewer-versus-gold agreement and exports disagreements;
6. reports the external audit as supplementary evidence, including failures or disagreements rather than hiding them.

One independent reviewer is enough to provide a useful supplementary external audit. Two or more reviewers are required only if the paper wants to report inter-reviewer agreement statistics such as reviewer-pair agreement or Cohen's kappa.

## Suggested public description

If one reviewer completes the audit, the paper can report the reviewer anonymously, for example:

> One independent external reviewer with undergraduate mathematics and computer-science training completed the blinded policy-application audit. The reviewer was not involved in benchmark construction and did not receive gold labels or model outputs before submission closure.

If the reviewer consents, an acknowledgement may name them. Otherwise use a reviewer ID and broad background only.
