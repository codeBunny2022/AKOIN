"""End-to-end pipeline: question + scenario -> template extract, validation, audit log."""
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag.retriever import load_retriever
from llm.assistant import build_prompt, call_llm, parse_structured_output
from template.render import render_template_extract_html
from template.validation import validate_ca1
from audit.build import build_audit_log
from schemas.corep_ca1 import CA1_FIELD_LABELS


def run_pipeline(question: str, scenario: str = "", template_id: str = "C 01.00") -> dict:
    """
    Run RAG -> LLM -> parse -> template render -> validation -> audit log.
    Returns dict with answer_summary, template_extract_html, validation, audit_log, schema.
    """
    retriever = load_retriever()
    template_filter = "CA1" if "01" in template_id or "CA1" in template_id else None
    chunks = retriever.retrieve(question=question, scenario=scenario, template_filter=template_filter)
    if not chunks:
        return {
            "answer_summary": "No relevant regulatory text was found for your question.",
            "template_extract_html": "",
            "validation": {"valid": False, "errors": [{"field_id": "", "message": "No chunks retrieved"}]},
            "audit_log": {"template_id": template_id, "entries": []},
            "schema": None,
        }
    system, user = build_prompt(question, scenario, chunks, template_id=template_id)
    raw = call_llm(system, user)
    schema = parse_structured_output(raw)
    html = render_template_extract_html(schema)
    validation = validate_ca1(schema)
    chunks_by_id = {c["chunk_id"]: c for c in chunks}
    audit = build_audit_log(schema, chunks_by_id)
    return {
        "answer_summary": schema.answer_summary or "",
        "template_extract_html": html,
        "validation": {
            "valid": validation.valid,
            "errors": [{"field_id": i.field_id, "message": i.message} for i in validation.errors()],
            "warnings": [{"field_id": i.field_id, "message": i.message} for i in validation.warnings()],
        },
        "audit_log": {
            "template_id": audit.template_id,
            "entries": [
                {
                    "field_id": e.field_id,
                    "field_label": CA1_FIELD_LABELS.get(e.field_id, e.field_id),
                    "value": e.value,
                    "citations": [
                        {
                            "paragraph_id": c.paragraph_id,
                            "source_ref": c.source_ref,
                            "source_url": c.source_url,
                            "excerpt": c.excerpt,
                        }
                        for c in e.citations
                    ],
                }
                for e in audit.entries
            ],
        },
        "schema": schema.model_dump(),
    }
