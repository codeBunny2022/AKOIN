"""Pydantic schema for COREP C 01.00 (CA1) Own Funds template."""
from typing import Optional
from pydantic import BaseModel, Field


class OwnFundsField(BaseModel):
    """Single field in the Own Funds template with optional citation."""
    field_id: str = Field(..., description="Unique identifier for the template field")
    value: Optional[str] = Field(None, description="Populated value (amount or code)")
    source_chunk_ids: list[str] = Field(default_factory=list, description="Chunk/paragraph IDs justifying this value")


class OwnFundsSchema(BaseModel):
    """Structured output for C 01.00 (CA1) Own Funds template extract."""
    template_id: str = Field(default="C 01.00", description="COREP template identifier")
    template_name: str = Field(default="Own Funds", description="Template name")
    reference_date: Optional[str] = Field(None, description="Reporting reference date (YYYY-MM-DD)")
    answer_summary: Optional[str] = Field(None, description="Brief answer to the user's question")
    fields: list[OwnFundsField] = Field(
        default_factory=list,
        description="List of populated fields with citations"
    )


# CA1 row identifiers aligned to COREP C 01.00 structure (simplified subset)
CA1_REQUIRED_FIELD_IDS = [
    "CA1_1_1",   # 1.1 Common Equity Tier 1 capital
    "CA1_1_2",   # 1.2 Additional Tier 1 capital
    "CA1_1_3",   # 1.3 Tier 2 capital
    "CA1_1_4",   # 1.4 Total eligible own funds
]

CA1_FIELD_LABELS = {
    "CA1_1_1": "1.1 Common Equity Tier 1 capital",
    "CA1_1_2": "1.2 Additional Tier 1 capital",
    "CA1_1_3": "1.3 Tier 2 capital",
    "CA1_1_4": "1.4 Total eligible own funds",
    "CA1_1_0": "1.0 Total equity",
}

# Consistency: Total (1.4) should equal 1.1 + 1.2 + 1.3 (for validation)
CA1_SUM_FIELDS = ["CA1_1_1", "CA1_1_2", "CA1_1_3"]
CA1_TOTAL_FIELD = "CA1_1_4"
