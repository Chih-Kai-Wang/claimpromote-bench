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
```

Dataset or policy changes require an entry in `RESEARCH_DECISIONS.md` and a version review.

