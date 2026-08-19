# External review v1 freeze

**Status: FROZEN BEFORE REVIEW**

This record freezes the reviewer-facing external policy audit before any external reviewer submission is received. It is supplementary validation and is not a substitute for the benchmark's deterministic oracle, executable artifact checks, or the frozen model study.

## Immutable identities

- audit ID: `external-policy-audit-v1`
- source dataset: `data/alpha`
- source dataset manifest SHA-256: `sha256:9ae9898ecd2c27e3dfddd0ae2e2b9965c56bd535a338ecc349d32b1b93eb72e5`
- policy SHA-256: `sha256:46b8b310cd1380167e0b94f1577a68c5e0378f9e32c6efe851ded91c0c4dc899`
- selection config SHA-256: `sha256:6565a102ef6bd6906881748ef35a63b721651bac7bbc5a072bc9a0847397f2ec`
- frozen item count: **20**
- packet ID: `sha256:e43fbc3a9c6279b3dfd5aa5511ba55bfce2bd2f49a290358431822de9f44231a`
- packet SHA-256: `sha256:56fa9e86a3132e9101c3c3e1ae16b5163224c863af6c671063e4db772efbc336`
- confirmed completed reviewers at freeze: **0**

The selection contains exactly one member of each of the 20 controlled alpha pairs. Selection balance and action coverage are validated by `scripts/build_external_review_v1.py` before a packet is produced; source item IDs and gold actions are deliberately omitted from this public freeze note to avoid making the reviewer-facing task easier.

## Reviewer-facing artifact

The GitHub Actions workflow `external review kit` deterministically builds a reviewer-safe archive named `SEND_THIS_TO_REVIEWER.zip`. It contains the blinded packet, bound policy, Chinese instructions and policy cheat sheet, a local browser form (`review.html`), and a submission template. The reviewer-facing archive contains no private unblinding mapping and no gold labels.

A separate artifact named `DO_NOT_SEND_PRIVATE.zip` contains the mapping needed for later unblinding and analysis. It must never be sent to an active reviewer.

## Review boundary

The source alpha benchmark is already public, so this is **procedural blinding**, not contamination-proof hidden evaluation. Every reviewer must attest that they did not inspect benchmark gold labels, model outputs, or another reviewer's submission while completing the audit.

Once a reviewer begins this packet, the packet, policy, and selection are not edited. A semantic change requires a new audit version and invalidates any affected partial or completed review rather than silently updating the material.
