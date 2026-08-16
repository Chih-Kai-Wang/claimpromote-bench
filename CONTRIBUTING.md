# Contributing

Contributions are welcome through focused issues and pull requests. Before proposing a new
item, state the policy prerequisite, the single counterfactual factor, the deterministic
oracle, and the expected failure reason. Do not add model-judged gold labels.

Run:

```bash
python -m pip install -e ".[dev]"
python scripts/build_alpha.py
python -m pytest
ruff check .
ruff format --check .
python -m claimpromotebench validate data/alpha
python -m claimpromotebench.contributions --root contributions
```

Dataset or policy changes require an entry in `RESEARCH_DECISIONS.md` and a version review.

Externally executed model results use a separate data-only workflow. Read
[`CONTRIBUTING_RUNS.md`](CONTRIBUTING_RUNS.md) before offering compute or opening a model-run
pull request. The contribution validator derives hashes and immutable identity from the
actual run file; do not invent or copy those fields manually.
