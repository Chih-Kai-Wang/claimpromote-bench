# AI assistance disclosure

Generative AI tools were used as assistants during this project. They helped with literature search and comparison, early code drafting and debugging, checks on analysis outputs, and parts of manuscript drafting and language editing. They were also useful for finding possible inconsistencies in the repository and for suggesting questions that should be checked before submission.

AI assistance is not treated as authorship, independent review, or evidence that a result is correct.

## Author responsibility

Chih-Kai Wang chose the research problem, defined the evidence-state semantics and policy, designed the benchmark and study protocol, decided which experiments and analyses to use, and is responsible for the claims made in the paper. The author also remains responsible for the released repository, reported numbers, references, final wording, and submission decisions.

The two supplementary audit submissions were completed by real independent reviewers. AI was not used as a substitute for either reviewer, and the mixed audit result was kept rather than changed to make the benchmark look stronger.

## Quantitative results

The v1 primary hidden study contains:

- 150 hidden pairs / 300 instances;
- 2 models × 4 arms × 3 seeds × 300 instances = 7,200 scored decisions;
- scored inference workflow `32255636879` at head `aa5268dcde2aa44f8eabf0246631efbca27de7e5`;
- recovery workflow `32274814703`;
- recovered study SHA-256 `sha256:3eb5b534ab486dac774a62de3d623fa33009be3705d9e8d620bb9942e8bfe664`.

The numbers in the manuscript are taken from the validated study artifacts. AI-generated calculations or remembered values are not used as substitutes for those artifacts.

During recovery, AI tools helped diagnose an evaluator problem that occurred after the model calls had already finished. The fix changed the evaluator, not the model outputs: 27 of 7,200 records that violated a fixed cross-field rule were reclassified as `FORMAT_ERROR`. The models were not queried again and otherwise valid model decisions were not rewritten.

## Interpretation

The main v1 result is negative at the model level: output coverage is poor and every parseable raw decision is `ALLOW`. The deterministic gate prevents invalid promotion among parseable cases because it applies the fixed benchmark policy. That gate result must not be presented as evidence that the model learned the policy, became better calibrated, or improved at mathematical reasoning.

The hidden labels, policy, prompts, seeds, and original model outputs are fixed for v1. Suggestions from AI tools do not authorize changing them after the results are known. A study that changes those elements should be reported as a new or supplementary experiment.

## Submission disclosure

The submission version includes a concise AI-use statement describing the kinds of assistance used in the project and the author's responsibility for the research and final paper. The wording may be adjusted to match the target venue's required format, but the factual division of work should not be changed for presentation purposes.
