"""Streamlit UI: single screen for question, scenario, template -> answer, template extract, validation, audit log."""
import io
import json
import os
import sys
from pathlib import Path

# Reduce TensorFlow/PyTorch console noise (optional; safe to remove if you need debug logs)
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")

sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st

from service.pipeline import run_pipeline

st.set_page_config(page_title="PRA COREP Reporting Assistant", layout="wide")
st.title("PRA COREP Reporting Assistant")
st.caption("Prototype: question + scenario → regulatory retrieval → structured output → template extract with audit log")

question = st.text_area("Question", placeholder="e.g. What amounts should we report in the Own Funds template for Common Equity Tier 1 and Tier 2?")
scenario = st.text_area("Reporting scenario", placeholder="e.g. Quarterly COREP return as at 31 Dec 2024; solo basis.", height=80)
template_id = st.selectbox("Template", ["C 01.00", "CA1"], format_func=lambda x: "C 01.00 – Own Funds" if x in ("C 01.00", "CA1") else x)
if template_id == "CA1":
    template_id = "C 01.00"

if st.button("Run assistant"):
    if not question.strip():
        st.warning("Please enter a question.")
    else:
        with st.spinner("Retrieving rules and generating template..."):
            try:
                result = run_pipeline(question=question.strip(), scenario=scenario.strip(), template_id=template_id)
            except FileNotFoundError as e:
                st.error(f"Service not ready: run ingestion first. {e}")
                st.stop()
            except ValueError as e:
                st.error(str(e))
                st.stop()
            except Exception as e:
                st.error(str(e))
                raise

        st.subheader("Answer summary")
        st.write(result.get("answer_summary") or "—")

        st.subheader("Template extract (C 01.00 Own Funds)")
        if result.get("template_extract_html"):
            st.markdown(
                """
                <style>
                .corep-extract { font-family: sans-serif; margin: 1em 0; }
                .corep-table { border-collapse: collapse; width: 100%; max-width: 600px; }
                .corep-table th, .corep-table td { border: 1px solid #ddd; padding: 8px 12px; text-align: left; }
                .corep-table th { background: #f5f5f5; }
                </style>
                """ + result["template_extract_html"],
                unsafe_allow_html=True,
            )
        else:
            st.info("No template output.")

        val = result.get("validation", {})
        st.subheader("Validation")
        if val.get("valid"):
            st.success("Validation passed.")
        else:
            for e in val.get("errors", []):
                st.error(f"**{e.get('field_id', '')}**: {e.get('message', '')}")
        for w in val.get("warnings", []):
            st.warning(f"**{w.get('field_id', '')}**: {w.get('message', '')}")

        st.subheader("Audit log (rule paragraphs per field)")
        for entry in result.get("audit_log", {}).get("entries", []):
            with st.expander(f"{entry.get('field_label', entry.get('field_id'))} = {entry.get('value') or '—'}"):
                for c in entry.get("citations", []):
                    st.markdown(f"**{c.get('paragraph_id')}** — {c.get('source_ref')}")
                    st.caption(c.get("excerpt", ""))
                    if c.get("source_url"):
                        st.markdown(f"[Source]({c.get('source_url')})")

        st.subheader("Export result")
        schema = result.get("schema")
        if schema:
            json_bytes = json.dumps(schema, indent=2).encode("utf-8")
            st.download_button(
                label="Download result (JSON)",
                data=io.BytesIO(json_bytes),
                file_name="corep_c01_result.json",
                mime="application/json",
            )
            # CSV of template extract for spreadsheets
            rows = [["field_id", "field_label", "value"]]
            for e in result.get("audit_log", {}).get("entries", []):
                rows.append([
                    e.get("field_id", ""),
                    e.get("field_label", ""),
                    e.get("value") or "",
                ])
            csv_lines = ["\t".join(r) for r in rows]
            csv_bytes = "\n".join(csv_lines).encode("utf-8")
            st.download_button(
                label="Download template extract (TSV)",
                data=io.BytesIO(csv_bytes),
                file_name="corep_c01_extract.tsv",
                mime="text/tab-separated-values",
            )

        st.caption("This is a prototype. Always verify against the PRA Rulebook and seek human review before submission.")
