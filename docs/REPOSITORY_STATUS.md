# Repository and submission status

Checked on 2026-09-30 UTC. This document separates the checked-out alpha source, later unmerged
research, recorded submission events, and executable validation. It does not change any dataset,
policy, model output, artifact hash, or pinned toolchain.

## Source snapshots

- The inspected `main` commit was
  [`32fbc204d2df27279c8a40dee0b180802d94b47d`](https://github.com/Chih-Kai-Wang/claimpromote-bench/commit/32fbc204d2df27279c8a40dee0b180802d94b47d).
  It preserves the alpha scaffold described by the main README. Its model-experiment and
  technical-report `PENDING` labels apply to that source snapshot.
- [PR #20](https://github.com/Chih-Kai-Wang/claimpromote-bench/pull/20) remained open and draft, with
  inspected head
  [`31613c24d9a6f038b12dfc1fbf81138e51ec12d0`](https://github.com/Chih-Kai-Wang/claimpromote-bench/commit/31613c24d9a6f038b12dfc1fbf81138e51ec12d0).
  Its [README](https://github.com/Chih-Kai-Wang/claimpromote-bench/blob/31613c24d9a6f038b12dfc1fbf81138e51ec12d0/README.md)
  describes the later versioned-agent-policy regression study. Reading this branch does not make
  its implementation or results part of `main`.
- The PR description's previous "final head" and passing-check summary refer to an older commit.
  They should not be used as the validation status of the inspected head above.

## Recorded submission events

The following are repository receipts, not a fresh authenticated inspection of OpenReview:

- [2026-08-25 submission receipt](https://github.com/Chih-Kai-Wang/claimpromote-bench/blob/31613c24d9a6f038b12dfc1fbf81138e51ec12d0/docs/submissions/2026-08-25-iclr2027-openreview.md):
  records completion of ICLR 2027 submission 4338 and its uploaded PDF and supplementary material.
- [2026-08-26 revision receipt](https://github.com/Chih-Kai-Wang/claimpromote-bench/blob/31613c24d9a6f038b12dfc1fbf81138e51ec12d0/docs/submissions/2026-08-26-iclr2027-openreview-revision.md):
  records the revised title, "ClaimPromoteBench: Paired Regression Tests for Versioned Agent
  Policies", the modified date, server attachment identifiers, and a visible 20-page revised PDF.
  It binds local artifact hashes but does not claim independently calculated server hashes for the
  revised attachments.
- [2026-08-27 Ox Alpha update preview](https://github.com/Chih-Kai-Wang/claimpromote-bench/blob/31613c24d9a6f038b12dfc1fbf81138e51ec12d0/docs/submissions/2026-08-27-iclr2027-ox-alpha-update-preview.md):
  records a validated local identity-annotation candidate. It explicitly says no attachments were
  uploaded while preparing that preview. No later upload receipt was identified in this review.

These records do not establish review acceptance, an arXiv submission, a public archival release,
or permission to perform another upload. The repository remained private and PR #20 remained draft
when checked.

## Validation status

The inspected PR #20 head has 11 completed GitHub Actions workflow runs reporting `failure`.
For example:

- [CI run 32989252681](https://github.com/Chih-Kai-Wang/claimpromote-bench/actions/runs/32989252681)
  lists six failed jobs with zero recorded steps and one skipped Lean job.
- [Submission-package run 32989252708](https://github.com/Chih-Kai-Wang/claimpromote-bench/actions/runs/32989252708)
  lists one failed job with zero recorded steps.

Those sampled runs provide no executed test result. The available job-log request returned
`BlobNotFound`; the immediate failure reason was not established. Do not infer a code regression,
billing problem, or passing current-head validation from these observations.

The separate [main CI run 34799672898](https://github.com/Chih-Kai-Wang/claimpromote-bench/actions/runs/34799672898)
passed at `32fbc204d2df27279c8a40dee0b180802d94b47d`. That result validates the main alpha tree,
not the much larger PR #20 branch.

Before presenting PR #20 as ready for review or merge, establish why jobs did not execute and
obtain the applicable checks for the exact candidate commit. Keep completed one-shot studies and
their evidence frozen; an infrastructure retry must not silently rerun a scored study.

## Related drafts and release boundary

- [PR #19](https://github.com/Chih-Kai-Wang/claimpromote-bench/pull/19) is the earlier v1 paper line;
  its head is an ancestor of the inspected PR #20 head. Its study records remain historical evidence.
- [PR #18](https://github.com/Chih-Kai-Wang/claimpromote-bench/pull/18) explicitly describes itself as a
  temporary SAIR data-export helper that should not be merged.
- [PR #17](https://github.com/Chih-Kai-Wang/claimpromote-bench/pull/17) is a separate model-pilot draft.
  Its divergent history alone does not prove every change is included in PR #20.

Merging a branch, changing repository visibility, publishing artifacts, and editing a conference
submission are separate actions. This status correction performs none of them.
