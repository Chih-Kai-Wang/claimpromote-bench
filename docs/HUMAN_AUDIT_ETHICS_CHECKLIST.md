# Human-audit ethics checklist

This checklist exists because ClaimPromoteBench v1 reports decisions made by two real independent reviewers. It does **not** assert that the audit is or is not human-subjects research, and it does not assert an IRB/ethics exemption that has not been documented.

ICLR's Code of Ethics states that when human subjects are involved, including annotators, authors should assess the need for approval from an appropriate ethical review board and report the result. The ICLR author guide also recommends an Ethics Statement when a submission raises human-subject, dataset-release, privacy, legal-compliance, or research-integrity questions.

## Facts already safe to state from repository evidence

- The manuscript reports a small supplementary audit by two real independent reviewers.
- The audit used a fixed 20-item public-alpha packet.
- Reviewer submissions were validated before the answers were revealed.
- The observed agreement values are retained even though one reviewer did not meet the preregistered 0.80 action-agreement threshold.
- Reviewer disagreement did not cause the frozen policy or gold labels to be changed.

## Facts that must be established by the human author before archival submission

Do not infer any of these from the repository. Record the actual answer and supporting documentation.

- [ ] Were both reviewers adults at the time of participation?
- [ ] Did both reviewers know that their responses could be used in a research paper and public research artifacts?
- [ ] Was explicit consent obtained, and is there a durable record of that consent?
- [ ] Were reviewers compensated or otherwise induced to participate? If yes, record the arrangement.
- [ ] Does any released file contain a real name, email address, account identifier, handwriting, voice, IP address, or other personally identifying information?
- [ ] If pseudonymous identifiers are released, can they reasonably be linked back to the reviewers from public information?
- [ ] Has the author's institution or an appropriate ethics/IRB authority been asked whether this activity requires review, exemption, or no formal review?
- [ ] If an exemption / not-human-subjects / no-review-required determination exists, record the exact authority, date, and reference number if one was issued.
- [ ] If formal review is required, do not submit a paper that represents the audit as approved until the required process is complete.
- [ ] Confirm that any reviewer-facing materials and released submissions are consistent with the permission actually granted by the reviewers.

## Manuscript rule

Until the items above are resolved, the manuscript may accurately describe the audit's procedure and aggregate results, but it must not say `IRB approved`, `IRB exempt`, `ethics approved`, `informed consent was obtained`, or equivalent language.

Once the institutional determination and consent facts are known, add a short Ethics Statement before the references if appropriate. The statement should report only documented facts, for example the applicable review/exemption determination, the role of the two reviewers, what data were collected/released, and how privacy/consent were handled.

## Why this is separate from the scientific result

Resolving this checklist must not change reviewer answers, gold labels, policy rules, model outputs, or v1 statistics. Ethics documentation is a submission-integrity requirement, not permission to clean up an inconvenient empirical result.
