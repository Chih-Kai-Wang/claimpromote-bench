#!/usr/bin/env python3
"""Run the frozen hosted policy-transition graph study once without retries."""

from __future__ import annotations

import run_policy_switch_study as frozen_runner
from validate_policy_transition_graph_hosted_study import validate_freeze


def main() -> int:
    """Use the established hosted runtime with the graph-specific freeze validator."""

    original_validator = frozen_runner.validate_freeze
    frozen_runner.validate_freeze = validate_freeze
    try:
        return frozen_runner.main()
    finally:
        frozen_runner.validate_freeze = original_validator


if __name__ == "__main__":
    raise SystemExit(main())
