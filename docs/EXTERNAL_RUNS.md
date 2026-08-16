# External run accumulation

ClaimPromoteBench can accumulate model diversity without requiring the maintainer to execute
or purchase every run. External results enter through a fail-closed contribution package,
not by pasting aggregate scores into documentation.

The package binds four layers:

1. **Dataset identity** — the selected `gold.jsonl`, its manifest SHA-256, policy SHA-256,
   inputs SHA-256, and evaluation time.
2. **Run identity** — model ID, model artifact SHA-256, quantization, runtime commit, arm,
   seed, and hardware.
3. **Execution record** — complete item coverage, frozen prompt hashes, parse status,
   raw/final decisions, latency, tokens, and verifier calls.
4. **Contributor contract** — attribution, MIT redistribution, privacy and secret
   attestations, reproduction command, and stable contribution ID.

The validator first checks the JSON Schema and hashes, then reuses the same run-record loader
and prompt renderer used by `evaluate-runs` and `compare-runs`. A package that passes can be
added to cumulative study comparisons without rewriting earlier results.

Preparation and validation are separate:

```bash
python -m claimpromotebench.contributions \
  --prepare contributions/example/contribution.json \
  --write

python -m claimpromotebench.contributions \
  --manifest contributions/example/contribution.json
```

Preparation derives immutable fields from the actual run; validation proves they still match.
CI additionally validates every `contribution.json` below `contributions/` and rejects duplicate
contribution IDs or duplicate validated run IDs.

A passing package does not prove model-weight provenance, absence of benchmark contamination,
or independent scientific reproduction. Those remain separate review claims.
