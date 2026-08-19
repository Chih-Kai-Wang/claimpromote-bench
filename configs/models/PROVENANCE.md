# Frozen model/runtime provenance for v1 study

**Freeze date:** 2026-08-19

This document records the external identities selected for the preregistered v1 study. It does not claim that the model files have been downloaded or that any experiment has been executed.

## Runtime

- backend: `llama.cpp`
- release: `b10218`
- commit: `de699957b92f490efebad149665b0dccf127eaff`
- upstream: `ggml-org/llama.cpp`

The full commit is recorded rather than relying on the moving release label.

## Qwen3-0.6B

- base model ID: `Qwen/Qwen3-0.6B`
- GGUF repository: `Qwen/Qwen3-0.6B-GGUF`
- repository revision: `ef4088322893040952513f532f736ddeab518403`
- file: `Qwen3-0.6B-Q8_0.gguf`
- quantization: `Q8_0`
- file SHA-256: `9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031`

## Qwen3-1.7B

- base model ID: `Qwen/Qwen3-1.7B`
- GGUF repository: `Qwen/Qwen3-1.7B-GGUF`
- repository revision: `90862c4b9d2787eaed51d12237eafdfe7c5f6077`
- file: `Qwen3-1.7B-Q8_0.gguf`
- quantization: `Q8_0`
- file SHA-256: `061b54daade076b5d3362dac252678d17da8c68f07560be70818cace6590cb1a`

## Decoding

The study uses [`../decoding-v1.json`](../decoding-v1.json). Qwen3 is explicitly placed in non-thinking mode via `/no_think`; the sampling parameters are frozen before model execution. The three study seeds remain those in `experiment-v1-planned.json`.

The choice of non-thinking mode is part of the benchmark protocol, not a claim that it is optimal. It keeps the target as a bounded evidence-state decision and avoids treating hidden reasoning text as part of the required machine-readable response. Any future thinking-mode experiment must be a separately named secondary study rather than silently changing v1.

## Verification rule

Before the first scored run, the downloaded bytes must be rehashed locally and compared with the recorded SHA-256. The executable runtime must report a source/build identity consistent with the pinned commit. A mismatch fails closed and does not produce a v1 run record.

External source pages used for this freeze must be rechecked before archival submission; the recorded hashes and revisions remain the immutable identities for this study even if upstream `main` moves.
