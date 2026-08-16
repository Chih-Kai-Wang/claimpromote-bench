# External contribution security boundary

The contribution validator treats submitted JSON and JSONL as untrusted data. It parses and
validates those files but never executes the reproduction command, imports contributor code,
loads submitted model weights, follows submitted URLs, or invokes an external service.

Run paths are constrained below the manifest directory. Dataset paths are constrained below
the repository root. Every selected file is hashed before evaluation, and every run record is
validated against the frozen schema, prompt renderer, item set, and single-run identity.

Reviewers must still inspect pull-request contents for secrets, personal data, restricted
artifacts, symlinks, oversized files, or unrelated code changes. Passing machine validation is
necessary but not sufficient for merge.
