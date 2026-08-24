# Local submission release kit

This directory is a verified build artifact, not evidence of submission. It contains the anonymous ICLR PDF and source, the named arXiv PDF and source, and the anonymous reviewer bundle. No OpenReview or arXiv upload was performed.

- ICLR PDF: 14 pages; main-text probe 9 pages; references start on physical page 10.
- arXiv PDF: 13 pages.
- Anonymous manifest: 628 listed files plus the manifest; ZIP entries 629.

Verify every release artifact from this directory with:

```bash
cd release/submission-kit && shasum -a 256 -c SHA256SUMS.txt
```

Use `validation-receipt.json` for the corresponding structural checks. The anonymous bundle file total is read from its generated manifest; do not copy it into long-lived prose.
