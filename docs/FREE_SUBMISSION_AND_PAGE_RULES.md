# ICLR 2027 and arXiv: page and cost rules

Verified against the live official pages on 2026-08-23. When any cached page or earlier note disagrees, use the live ICLR 2027 Author Guidelines as the source of truth.

## ICLR 2027 deadlines

- Abstract deadline: **2026-09-18 AOE**.
- Full paper and supplementary-material deadline: **2026-09-25 AOE**.
- The abstract must be genuine rather than a placeholder.
- No new author may be added after the abstract deadline; author order may still be changed until the full-paper deadline.
- All authors must have current OpenReview profiles by the full-paper deadline. Profiles created without an institutional email may require moderation, so the account should be created immediately.

Official source: `https://iclr.cc/Conferences/2027/AuthorGuidelines`

## ICLR page limit

- Initial submission main text: **at most 9 pages**.
- Discussion/rebuttal and camera-ready: at most 10 pages under the current guide.
- References do not count and may use unlimited pages.
- Appendices after the bibliography may use unlimited pages, but reviewers are not required to read them.
- The required AI-use statement does not count.
- The recommended reproducibility statement does not count.
- An optional ethics statement does not count and should not exceed one page.

There is **no paid overlength option** in the author rules. The guide states that excess main-text pages are desk-rejected. This is a hard compliance rule, not a page charge that can be paid.

The repository therefore keeps an automated ICLR main-text probe at `<= 9` pages. The 2026-08-24
release candidate has a **9-page main-text probe** and a **15-page physical ICLR PDF**. The
scientific conclusion and the non-counting reproducibility and AI-use statements end on page 9.
References start on page 10 and the appendix starts on page 13. The named arXiv PDF has 14 physical
pages. All 29 rendered pages were inspected for overlap, clipping, crowding,
orphaned headings, and table readability.

## Human-subject scope

The revised submission contains no human-subject experiment, human annotation study, or human-review result. Synthetic fields such as `review_status` and `INDEPENDENT_REVIEWER` are benchmark metadata, not observations collected from people.

All authors must still read and acknowledge the ICLR Code of Ethics in OpenReview. Under the official FAQ, a separate Ethics Statement is not required when the submission has no ethics issue to report. The paper therefore does not claim IRB approval, exemption, institutional review, or informed consent.

## ICLR cost boundary

The current ICLR 2027 author guide lists no submission fee and no page charge. Submitting the abstract and paper for review can therefore be planned with no conference payment.

Acceptance is different: the official guide says at least one author of an accepted paper must purchase a **Conference and Workshops** registration; a student registration is sufficient for a student author. The exact 2027 registration price is not presently stated in the author guide. Do not claim that the entire accepted-paper process will be free.

## arXiv

- arXiv submission is free for authors.
- Upload the prepared source ZIP, not only the locally generated PDF.
- arXiv accepts LaTeX source packages, compiles the PDF, and requires the submitter to inspect the generated preview before the final `Submit Article` action.
- New users or authors entering a new category may need endorsement.
- There is no article-submission or page charge for this preprint.

Official sources:

- `https://info.arxiv.org/help/submit/index.html`
- `https://info.arxiv.org/help/submit_tex.html`
- `https://info.arxiv.org/help/endorsement.html`

## Zero-cost plan

1. Post the prepared source package to arXiv: no author fee.
2. Submit only an anonymous ICLR version whose final main-text probe is at most 9 pages: no current submission or page fee is listed.
3. Do not pay for editing, extra pages, or third-party submission services.
4. If accepted, treat registration and travel as a new funding decision and investigate student support or grants then; acceptance cannot presently be guaranteed to remain cost-free.
