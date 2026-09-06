"""Evaluation-only truth; never include OracleTask in a ModelInput."""

from .semantic import SemanticOracle

__all__ = ["SemanticOracle"]
