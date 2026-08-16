# Run contribution review checklist

Maintainers review a contributed model run in this order:

1. The pull request changes only the intended contribution directory and documentation needed
   for that contribution.
2. `contribution.json` was produced with `--prepare --write`, not hand-edited after hashing.
3. The validator reports `PASS` for the single manifest and for the complete contribution tree.
4. The model artifact, runtime commit, arm, seed, quantization, hardware, prompt hashes, and
   dataset manifest are immutable and internally consistent.
5. The package contains no credentials, private URLs, personal data, restricted weights, or
   executable contributor code.
6. The reproduction command is descriptive data only and is not executed during review.
7. Any limitations—network access, unavailable logits, nondeterminism, retries, or mutable
   provider behavior—are stated in the manifest notes and pull request.
8. Scores are described as one validated run, not as independent reproduction or universal
   model behavior.

Only after these checks should the run be included in `compare-runs` or a public report.
