# Reproduction

## Clean alpha verification

From a fresh clone with Python 3.11–3.13:

```bash
python -m venv .venv
# Activate .venv using the command for your shell.
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python scripts/build_alpha.py
git diff --exit-code
python -m claimpromotebench verify-manifest data/alpha/manifest.json
python -m claimpromotebench check-pairs data/alpha
python -m claimpromotebench check-gold data/alpha
python -m pytest --cov --cov-branch --cov-fail-under=80
```

Expected structural output is 40 instances, 20 pairs, six families with distribution
`4/4/3/3/3/3`, and oracle/gold equality. These checks do not constitute an external
reproduction of a study because no model study has been reported.

The model-facing renderers require the complete policy and frozen evaluation time; the CLI
loads both from the manifest-bound policy. The `evaluate-runs` command accepts the public
run-record schema and fails closed on any `FORMAT_ERROR` instead of treating missing output
as a hold.

## What an eventual clean-room reproduction must record

- repository commit and release/archive digest;
- Python, OS, CPU/GPU, RAM, and driver versions;
- exact model artifact hash, quantization, and source revision;
- exact llama.cpp commit and build flags;
- dataset, policy, prompt, seed, and run-record hashes;
- deviations, failures, retries, and all missing outputs.

The reproducer must be independent of the benchmark author and must not receive hidden test
labels before their run is committed.
