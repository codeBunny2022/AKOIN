"""Validation rules for COREP template output."""
from dataclasses import dataclass, field

from schemas.corep_ca1 import (
    OwnFundsSchema,
    CA1_REQUIRED_FIELD_IDS,
    CA1_SUM_FIELDS,
    CA1_TOTAL_FIELD,
)


@dataclass
class ValidationItem:
    """Single validation finding."""
    field_id: str
    severity: str  # "error" | "warning"
    message: str


@dataclass
class ValidationResult:
    """Aggregate validation result."""
    valid: bool
    items: list[ValidationItem] = field(default_factory=list)

    def errors(self) -> list[ValidationItem]:
        return [i for i in self.items if i.severity == "error"]

    def warnings(self) -> list[ValidationItem]:
        return [i for i in self.items if i.severity == "warning"]


def _field_value_map(schema: OwnFundsSchema) -> dict[str, str | None]:
    return {f.field_id: f.value for f in schema.fields}


def _parse_number(s: str | None) -> int | float | None:
    if s is None or (isinstance(s, str) and s.strip() == ""):
        return None
    s = str(s).strip().replace(",", "")
    try:
        if "." in s:
            return float(s)
        return int(s)
    except ValueError:
        return None


def validate_ca1(schema: OwnFundsSchema) -> ValidationResult:
    """
    Validate CA1 (Own Funds) output: required fields, numeric format, total = sum of components.
    """
    items: list[ValidationItem] = []
    value_by_id = _field_value_map(schema)

    # Required fields
    for fid in CA1_REQUIRED_FIELD_IDS:
        val = value_by_id.get(fid)
        if val is None or (isinstance(val, str) and val.strip() == ""):
            items.append(ValidationItem(
                field_id=fid,
                severity="error",
                message="Missing required field",
            ))

    # Numeric format for amount fields (all CA1 amount fields should be numeric)
    for fid in CA1_REQUIRED_FIELD_IDS:
        val = value_by_id.get(fid)
        if val is not None and str(val).strip() != "":
            if _parse_number(val) is None:
                items.append(ValidationItem(
                    field_id=fid,
                    severity="error",
                    message="Invalid format: expected numeric value",
                ))

    # Consistency: Total (1.4) = 1.1 + 1.2 + 1.3
    sum_vals = [_parse_number(value_by_id.get(fid)) for fid in CA1_SUM_FIELDS]
    total_val = _parse_number(value_by_id.get(CA1_TOTAL_FIELD))
    if all(v is not None for v in sum_vals) and total_val is not None:
        computed = sum(sum_vals)
        if abs(computed - total_val) > 0.01:
            items.append(ValidationItem(
                field_id=CA1_TOTAL_FIELD,
                severity="warning",
                message=f"Inconsistent: total ({total_val}) does not equal sum of components ({computed})",
            ))

    valid = len([i for i in items if i.severity == "error"]) == 0
    return ValidationResult(valid=valid, items=items)
