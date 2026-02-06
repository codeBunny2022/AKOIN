"""COREP template schemas."""
from .corep_ca1 import (
    OwnFundsField,
    OwnFundsSchema,
    CA1_REQUIRED_FIELD_IDS,
    CA1_FIELD_LABELS,
    CA1_SUM_FIELDS,
    CA1_TOTAL_FIELD,
)

__all__ = [
    "OwnFundsField",
    "OwnFundsSchema",
    "CA1_REQUIRED_FIELD_IDS",
    "CA1_FIELD_LABELS",
    "CA1_SUM_FIELDS",
    "CA1_TOTAL_FIELD",
]
