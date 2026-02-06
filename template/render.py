"""Render COREP template extract as HTML."""
from schemas.corep_ca1 import OwnFundsSchema, CA1_FIELD_LABELS, CA1_REQUIRED_FIELD_IDS


def _field_row(field_id: str, value: str | None, label: str | None = None) -> str:
    lbl = label or CA1_FIELD_LABELS.get(field_id, field_id)
    val = (value or "").strip() or "—"
    return f"""<tr><td>{lbl}</td><td>{val}</td></tr>"""


def render_template_extract_html(schema: OwnFundsSchema) -> str:
    """
    Map OwnFundsSchema to a human-readable HTML table (COREP form excerpt).
    """
    field_by_id = {f.field_id: f for f in schema.fields}
    ref_date = schema.reference_date or "—"
    rows: list[str] = []
    for fid in CA1_REQUIRED_FIELD_IDS:
        f = field_by_id.get(fid)
        value = f.value if f else None
        rows.append(_field_row(fid, value))
    # Any extra fields not in the fixed list
    for f in schema.fields:
        if f.field_id not in CA1_REQUIRED_FIELD_IDS:
            rows.append(_field_row(f.field_id, f.value))

    table_rows = "\n".join(rows)
    return f"""<div class="corep-extract">
  <h3>{schema.template_id} – {schema.template_name}</h3>
  <p><strong>Reference date:</strong> {ref_date}</p>
  <table class="corep-table">
    <thead><tr><th>Row</th><th>Amount</th></tr></thead>
    <tbody>
{table_rows}
    </tbody>
  </table>
</div>"""
