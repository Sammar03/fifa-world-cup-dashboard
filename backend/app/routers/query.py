"""POST /query — 501 stub (owner decision 2026-06-12; BACKLOG-001, CLAUDE.md §15).

The constrained tool-select design is fixed in ADR-004 and will be implemented
in backend/app/ai/nl_query.py when the feature is picked up. Input validation
runs even on the stub so the contract (max 500 chars, stripped) is enforced
from day one (CLAUDE.md §11).
"""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)
router = APIRouter()


class QueryRequest(BaseModel):
    question: str = Field(max_length=500)

    @field_validator("question")
    @classmethod
    def strip_and_reject_html(cls, value: str) -> str:
        value = value.strip()
        if "<" in value or ">" in value:
            raise ValueError("question must not contain HTML")
        return value


@router.post("/query", status_code=501)
async def query(request: QueryRequest) -> dict:
    raise HTTPException(
        status_code=501,
        detail="Natural-language query is coming soon (BACKLOG-001).",
    )
