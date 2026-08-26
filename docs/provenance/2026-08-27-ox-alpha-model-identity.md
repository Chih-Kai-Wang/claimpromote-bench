# Ox Alpha post-hoc model identity

## Evidence

- Z.ai's official 2026-08-26 release announcement states that GLM-5.3-Flash was tested anonymously
  as `ox-alpha` on OpenCode and OpenRouter before release:
  <https://z.ai/blog/glm-5.3-flash>
- Z.ai's official model documentation lists the released API model code as `glm-5.3-flash`:
  <https://docs.z.ai/guides/vlm/glm-5.3-flash>
- The official Hugging Face model card identifies the released open-weight model as
  `zai-org/GLM-5.3-Flash` under the MIT license:
  <https://huggingface.co/zai-org/GLM-5.3-Flash>

## Effect on ClaimPromoteBench

The disclosure resolves the public product identity of the route previously reported as Ox Alpha.
It does not establish that a post-release API call would reproduce the exact checkpoint, adapter,
provider serving state, or data-handling conditions used by the frozen OpenCode Go
`ox-alpha-free` route on 2026-08-24.

Accordingly:

- existing raw records, requested and returned route IDs, historical identity-status fields,
  hashes, and metrics remain immutable;
- reader-facing tables label the route `GLM 5.3 Flash (OX)` and explain that the annotation is
  post-hoc;
- the route remains separate from the distinct `glm-5.3` condition;
- no model call is rerun or substituted;
- the evidentiary ceiling remains a time-stamped route-level observation, not a model-family or
  provider-independent effect.
