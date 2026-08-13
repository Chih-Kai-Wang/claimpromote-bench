from __future__ import annotations

from datetime import UTC, datetime

import pytest

from claimpromotebench.errors import DatasetIntegrityError
from claimpromotebench.policy import interval_covers, parse_timestamp


def interval(lower: str, upper: str, lower_closed: bool = True, upper_closed: bool = True):
    return {
        "variables": [
            {
                "name": "x",
                "lower": lower,
                "upper": upper,
                "lower_inclusive": lower_closed,
                "upper_inclusive": upper_closed,
            }
        ]
    }


def test_decimal_interval_coverage() -> None:
    required = interval("0", "1")
    assert interval_covers(interval("0", "1"), required)
    assert interval_covers(interval("-0.1", "1.1"), required)
    assert not interval_covers(interval("0", "0.999999999999999999"), required)
    assert not interval_covers(interval("0", "1", upper_closed=False), required)
    assert interval_covers(interval("0", "1"), interval("0", "1", upper_closed=False))


def test_timestamp_is_utc_and_explicit() -> None:
    assert parse_timestamp("2026-08-13T08:00:00+08:00") == datetime(2026, 8, 13, tzinfo=UTC)
    with pytest.raises(DatasetIntegrityError):
        parse_timestamp("2026-08-13T00:00:00")
