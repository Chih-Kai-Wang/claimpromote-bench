"""Typed failures used by dataset and prediction validation."""

from __future__ import annotations


class ClaimPromoteBenchError(Exception):
    """Base error for expected benchmark failures."""


class DatasetIntegrityError(ClaimPromoteBenchError):
    """The benchmark artifact is malformed or fails an integrity check."""


class PredictionFormatError(ClaimPromoteBenchError):
    """A model output is missing or violates the public decision contract."""


class ExecutableFixtureError(ClaimPromoteBenchError):
    """A registered executable fixture failed with a stable error code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
