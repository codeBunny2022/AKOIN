"""FastAPI app: single endpoint for question + scenario -> template extract, validation, audit log."""
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from service.pipeline import run_pipeline

app = FastAPI(title="PRA COREP Reporting Assistant", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class RequestBody(BaseModel):
    question: str = Field(..., description="Natural language question")
    scenario: str = Field(default="", description="Reporting scenario description")
    template_id: str = Field(default="C 01.00", description="Template to populate (e.g. C 01.00)")


@app.post("/api/assist")
def assist(body: RequestBody) -> dict:
    """Run RAG + LLM + validation + audit and return template extract, validation, and audit log."""
    try:
        return run_pipeline(body.question, body.scenario, body.template_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=f"Service not ready: run ingestion first. {e}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
