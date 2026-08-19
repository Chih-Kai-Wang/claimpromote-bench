# AI assistance disclosure

## Scope of AI assistance

AI tools assisted with:

- literature triage and related-work comparison;
- research-gap exploration and adversarial review of the research boundary and novelty wording;
- methodology and experiment-design feedback;
- schema, test, and CI/workflow drafting;
- implementation, code drafting, and debugging;
- diagnosis of the post-inference evaluator/recovery failure;
- programmatic inspection and interpretation of the validated recovered study artifact;
- documentation and manuscript drafting/editing;
- reference formatting and citation cross-check support.

AI assistance is not treated as authorship, independent human review, external reproduction, or evidence that a benchmark/model result is correct.

## Human responsibility

Chih-Kai Wang chose and approved the research question, evidence-state semantics, policy boundary, benchmark design, frozen study protocol, and publication claims; owns the repository; and is responsible for the final manuscript, released artifacts, citation accuracy, quantitative claims, and submission decisions.

The two supplementary external-audit submissions were completed by real independent reviewers. AI was not substituted for a human reviewer, and the mixed audit result is retained exactly rather than tuned into a pass.

## Frozen quantitative study

The v1 primary hidden study has now been executed and recovered from immutable source inference artifacts:

- private hidden primary test: 150 pairs / 300 instances;
- 2 models × 4 arms × 3 seeds × 300 hidden instances = 7,200 scored decisions;
- source workflow run: `32255636879` at scoring head `aa5268dcde2aa44f8eabf0246631efbca27de7e5`;
- artifact-only recovery workflow: `32274814703`;
- recovered study SHA-256: `sha256:3eb5b534ab486dac774a62de3d623fa33009be3705d9e8d620bb9942e8bfe664`.

AI-assisted artifact analysis was used to summarize already validated machine-generated study outputs. Quantitative values in the manuscript are bound to the recovered artifact rather than accepted from an AI model's unsupported calculation or memory.

The recovery debugging was also AI-assisted. The repaired workflow reconstructs hidden/prompt identity from the original frozen scoring source and reclassifies only frozen cross-field semantic output violations as `FORMAT_ERROR`. Exactly 27/7,200 records were reclassified. No legal model decision was rewritten and no model was re-queried.

## Interpretation boundary

The recovered v1 result is negative at the raw-model layer: structured-output coverage is poor and all parseable raw intents request `ALLOW`. The deterministic gate prevents measured policy-invalid promotion among covered decisions. AI-assisted drafting must not restate that enforcement effect as improved model reasoning, calibration, theorem proving, or scientific truth classification.

Likewise, AI-generated suggestions do not authorize changes to the frozen hidden gold, policy, prompts, seeds, or source inference after results are known. Any future study that changes those elements must be labeled as a new or supplementary study.

## Verification and venue disclosure policy

Repository validators, artifact hashes, GitHub workflow provenance, exact prompt/run identities, deterministic policy/oracle code, human review records, and reproducible statistics—not AI self-assessment—determine what claims are admissible in the paper.

The disclosure was checked on 2026-08-20 against the official ICLR 2027 AI Policy for Authors and Author Guidelines. ICLR 2027 requires a mandatory AI-use statement in the paper (outside the main-text page limit) and explicit disclosure of relevant AI-assisted research and writing tasks. The ICLR submission wrapper therefore discloses literature search/triage and gap exploration, methodology and experiment-design feedback, implementation and code drafting, CI debugging, artifact analysis, quantitative-result interpretation, manuscript drafting/editing, and reference formatting, while stating that the human author reviewed the work and takes responsibility for the research question, benchmark and policy semantics, experimental decisions, released artifacts, quantitative claims, citation accuracy, and final manuscript.

This policy check is time-sensitive and should be repeated immediately before actual submission if ICLR updates its author policy or submission form. Reformatting the disclosure for venue requirements must not change the factual division of work described here.
