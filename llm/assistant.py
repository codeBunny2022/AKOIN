"""LLM prompt and structured output for COREP reporting."""
import json
import re
from pathlib import Path

from openai import OpenAI

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import OPENAI_API_KEY, LLM_MODEL
from schemas.corep_ca1 import OwnFundsSchema, CA1_FIELD_LABELS, CA1_REQUIRED_FIELD_IDS


SYSTEM_PROMPT = """You are a PRA COREP regulatory reporting assistant. Your task is to help users complete COREP template extracts (e.g. C 01.00 Own Funds) using only the provided regulatory text.

Rules:
1. Use ONLY the retrieved rule paragraphs below to justify your answers. Do not invent values or sources.
2. For each field you populate, you MUST cite one or more source_chunk_ids from the provided chunks (use the chunk_id exactly as given).
3. If the retrieved text contains illustrative or example amounts (e.g. for C 01.00 rows), use those amounts and cite the chunk that contains them. If the user's scenario specifies amounts or a reference date, use them where applicable.
4. Output valid JSON only, no markdown or explanation outside the JSON.
5. If the retrieved text does not contain enough information to populate a field, leave value as null but still include the field_id and an empty source_chunk_ids list (or omit that field).
6. For monetary amounts use whole numbers (no decimals). For dates use YYYY-MM-DD.
7. Include an answer_summary: a brief direct answer to the user's question based on the rules."""

SCHEMA_DESCRIPTION_CA1 = """
Output JSON schema for template C 01.00 (Own Funds):
{
  "template_id": "C 01.00",
  "template_name": "Own Funds",
  "reference_date": "YYYY-MM-DD or null",
  "answer_summary": "Brief answer to the question",
  "fields": [
    {
      "field_id": "CA1_1_1",
      "value": "numeric string or null",
      "source_chunk_ids": ["PRA-RR-001", "EBA-CA1-001"]
    },
    ...
  ]
}
Valid field_ids for C 01.00: CA1_1_1 (Common Equity Tier 1), CA1_1_2 (Additional Tier 1), CA1_1_3 (Tier 2), CA1_1_4 (Total eligible own funds).
"""


def _format_chunks(chunks: list[dict]) -> str:
    return "\n\n".join(
        f"[{c['chunk_id']}] {c['source_ref']}\n{c['text']}"
        for c in chunks
    )


def build_prompt(
    question: str,
    scenario: str,
    chunks: list[dict],
    template_id: str = "C 01.00",
) -> tuple[str, str]:
    """Build system and user messages for the LLM."""
    system = SYSTEM_PROMPT + SCHEMA_DESCRIPTION_CA1
    context = _format_chunks(chunks)
    user = f"""User question: {question}

Reporting scenario: {scenario}

Retrieved regulatory text (use these chunk_ids in source_chunk_ids):
{context}

Produce the JSON for template {template_id} (Own Funds) with fields populated from the above text. Output only the JSON object, no other text."""
    return system, user


def call_llm(system: str, user: str) -> str:
    """Call OpenAI with JSON mode. Returns raw response content."""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not set")
    client = OpenAI(api_key=OPENAI_API_KEY)
    resp = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
    )
    return resp.choices[0].message.content or "{}"


def _extract_json(raw: str) -> str:
    """Try to extract a JSON object from the response (in case of markdown or extra text)."""
    raw = raw.strip()
    # Strip markdown code block if present
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```\s*$", "", raw)
    return raw


def parse_structured_output(raw: str) -> OwnFundsSchema:
    """
    Parse LLM response into OwnFundsSchema. Missing or invalid fields are left as null/empty;
    unknown fields are dropped by Pydantic.
    """
    raw = _extract_json(raw)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return OwnFundsSchema(template_id="C 01.00", template_name="Own Funds", fields=[])
    # Ensure fields is a list of objects with field_id, value, source_chunk_ids
    if "fields" in data and isinstance(data["fields"], list):
        normalized = []
        for f in data["fields"]:
            if isinstance(f, dict) and "field_id" in f:
                normalized.append({
                    "field_id": str(f["field_id"]),
                    "value": f.get("value") if f.get("value") is not None else None,
                    "source_chunk_ids": list(f.get("source_chunk_ids") or []),
                })
        data["fields"] = normalized
    try:
        return OwnFundsSchema.model_validate(data)
    except Exception:
        return OwnFundsSchema(template_id="C 01.00", template_name="Own Funds", fields=[])
