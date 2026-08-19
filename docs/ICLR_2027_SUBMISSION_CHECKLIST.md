# ICLR 2027 submission checklist

This checklist covers the account-side steps that cannot be proven by repository CI. The authoritative source is the current ICLR 2027 Author Guidelines; re-check the official page before the final submission in case the conference updates a form or policy.

## Hard dates

All conference deadlines are Anywhere on Earth (AOE).

- **Abstract deadline:** 2026-09-11.
- **Full-paper deadline:** 2026-09-16 at 23:59 AOE.
- No new authors may be added after the abstract deadline.
- Author order may be edited between the abstract and full-paper deadlines.
- After the full-paper deadline, title and author changes are restricted by the conference rules.

Do not plan against an older or secondary deadline list.

## Before the abstract deadline

- [ ] Create or verify the OpenReview profile for every author.
- [ ] Make sure names, affiliation, email domains, publication history, and conflicts are accurate in OpenReview.
- [ ] Resolve any OpenReview profile moderation early; profiles without institutional-email verification may take additional time.
- [ ] Check the ICLR 2027 author quota and reciprocal-reviewing rules against the actual OpenReview profile.
- [ ] Prepare a genuine title and informative abstract. The abstract is used for reviewer bidding and must not be a placeholder.
- [ ] Confirm the final author set before submitting the abstract; no author can be added after this deadline.
- [ ] Submit the abstract through the official ICLR 2027 OpenReview venue.
- [ ] Save a local record of the submitted title, abstract, author order, submission number, and timestamp.

## Before the full-paper deadline

- [ ] Use the official ICLR 2027 style files.
- [ ] Main text is at most 9 pages; references do not count toward that limit.
- [ ] The submitted PDF is anonymous in text, metadata, acknowledgements, repository links, provenance strings, file names, and supplementary material.
- [ ] If the public arXiv version exists, cite any self-related public work in third person where necessary; an arXiv preprint itself does not violate ICLR double-blind policy.
- [ ] Include the required detailed AI-use statement.
- [ ] Review whether an Ethics Statement is appropriate, especially for the two-person human audit and any later naturalistic dataset material.
- [ ] If human-review ethics/IRB applicability has been determined, report only the documented determination; never infer or invent approval/exemption language.
- [ ] Re-run the repository submission-package workflow and use the PDF produced from the final submission head.
- [ ] Preview the exact uploaded PDF in OpenReview. Check every page, not only the first page.
- [ ] Upload anonymized supplementary code/material only after checking it for author identity and private data.
- [ ] Confirm subject areas / keywords accurately match the work; do not select broad categories only to increase reviewer exposure.
- [ ] Complete the conference ethics acknowledgement and all required author-policy fields.
- [ ] Confirm reviewer-registration instructions shown to the actual author account and satisfy any requirement or documented exemption.
- [ ] Submit before the deadline and save the final submission timestamp and PDF hash.

## Final PDF visual pass

Check the exact uploaded file for:

- [ ] title and abstract unchanged from intended final version;
- [ ] no author names or affiliation in the anonymous version;
- [ ] no public GitHub username, email, workflow run ID, commit hash, or searchable provenance that reveals identity;
- [ ] all figures legible at normal zoom;
- [ ] table headers and numbers not clipped;
- [ ] no text overlap or overfull boxes;
- [ ] references resolve and no `??` or undefined citation markers appear;
- [ ] AI-use statement present;
- [ ] any Ethics Statement present if applicable and factually documented;
- [ ] appendix/supplement clearly separated from the main paper.

## After submission

- [ ] Do not submit the same or substantially similar paper concurrently to another archival conference or journal while ICLR review is active.
- [ ] arXiv posting is allowed under ICLR's dual-submission policy; keep the ICLR PDF anonymous even if the arXiv version is named.
- [ ] Preserve the exact submitted PDF/source bundle and its SHA-256.
- [ ] Preserve the code/data commit used for the submission.
- [ ] When reviews arrive, answer only decision-relevant reviewer concerns first; do not turn rebuttal into an unrelated new paper.
- [ ] Any new experiment during discussion should validate the submitted claims rather than materially change the paper's research question.

## Repository-to-OpenReview handoff

Repository CI can prove compilation, page count, reference integrity, selected anonymity checks, and artifact identities. It cannot prove what was actually typed into OpenReview or which PDF was finally uploaded. The human author must therefore compare the OpenReview submission against the repository-generated submission kit before pressing the final submit button.
