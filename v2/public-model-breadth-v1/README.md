# Public model-breadth supplement

This directory freezes a seven-configuration supplement on the existing 90-pair / 180-item
balanced public challenge. The dataset and prompt packet were already public before inference.
The schedule uses one application POST per model-item cell, zero client retries, and item-major
cyclic lane rotation. The supplement adds model-family/configuration coverage only; it is not a
hidden-generalization estimate or a causal ablation of model, serving stack, or API adapter.

After the single frozen execution completes, `private-results/` retains the source records and
journal evidence inside the private development repository. `results/` contains the fail-closed
public-safe derivative used for metric replay and anonymous-bundle construction. A future public
export must include only the reviewed derivative and must not inherit this repository's history.

Do not resume, retry, or rerun the frozen schedule. Every unusable or unattempted terminal cell
remains incorrect in end-to-end item and pair denominators.
