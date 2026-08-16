# External run review policy

External run pull requests are reviewed as data imports. Changes to source code, benchmark
policy, gold labels, schemas, or frozen prompts should be split into a separate pull request.
A result package is merged only after the contribution validator and normal repository CI
both pass and a maintainer confirms the licensing, privacy, provenance, and interpretation
statements.

Model-run data may be removed or superseded if its artifact identity, licensing, prompt
binding, or provenance is later shown to be incorrect. Corrections must preserve the original
Git history and explain why the prior result should no longer be used.
