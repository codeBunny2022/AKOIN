"""Build audit log from structured output and retrieved chunks."""
from dataclasses import dataclass, field

from schemas.corep_ca1 import OwnFundsSchema


@dataclass
class AuditCitation:
    """Single citation: paragraph_id, source_ref, short excerpt."""
    paragraph_id: str
    source_ref: str
    source_url: str
    excerpt: str


@dataclass
class AuditEntry:
    """Audit entry for one field: field_id, value, list of citations."""
    field_id: str
    value: str | None
    citations: list[AuditCitation] = field(default_factory=list)


@dataclass
class AuditLog:
    """Full audit log: list of entries, one per populated/cited field."""
    template_id: str
    entries: list[AuditEntry] = field(default_factory=list)


def _short_excerpt(text: str, max_len: int = 200) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rsplit(" ", 1)[0] + "..."


def build_audit_log(
    schema: OwnFundsSchema,
    chunks_by_id: dict[str, dict],
) -> AuditLog:
    """
    Build audit log from schema (fields with source_chunk_ids) and chunk metadata.
    chunks_by_id: chunk_id -> { source_ref, source_url, text }
    """
    entries: list[AuditEntry] = []
    for f in schema.fields:
        citations: list[AuditCitation] = []
        for cid in f.source_chunk_ids:
            c = chunks_by_id.get(cid)
            if c:
                citations.append(AuditCitation(
                    paragraph_id=cid,
                    source_ref=c.get("source_ref", ""),
                    source_url=c.get("source_url", ""),
                    excerpt=_short_excerpt(c.get("text", "")),
                ))
        entries.append(AuditEntry(
            field_id=f.field_id,
            value=f.value,
            citations=citations,
        ))
    return AuditLog(template_id=schema.template_id, entries=entries)
