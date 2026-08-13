"""Typed failures used by dataset and prediction validation."""

from __future__ import annotations


class ClaimPromoteBenchError(Exception):
    """Base error for expected benchmark failures."""


class DatasetIntegrityError(ClaimPromoteBenchError):
    """The benchmark artifact is malformed or fails an integrity check."""


class PredictionFormatError(ClaimPromoteBenchError):
    """A model output is missing or violates the public decision contract."""
