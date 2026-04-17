"""
SynthesiserAgent — writes the final plain-language answer.
Receives either SQL rows or document chunks and formats a response.
Supports both single-shot and streaming modes.
"""
from __future__ import annotations

import os
import json
from typing import AsyncGenerator, Any, Optional
from .base_agent import BaseAgent


SQL_ANSWER_SYSTEM = """You are a helpful enterprise assistant. The user asked a question
and a SQL query was executed against the company database. Here are the results.

Project Context/Guidelines:
{project_guidelines_text}

Question: {question}
SQL: {sql}
Results ({total_rows} total rows, showing first {shown_rows}):
{rows_text}

Write a clear, concise answer in plain language. If there are zero rows, say so clearly.
Do not show raw SQL or JSON to the user. Format numbers with commas when appropriate."""

DOC_ANSWER_SYSTEM = """You are a helpful enterprise assistant. The user asked a question
and relevant document sections were found. Answer using ONLY the provided content.

Project Context/Guidelines:
{project_guidelines_text}

Database Schema Context (if relevant):
{db_schema_text}

Question: {question}

Retrieved documents:
{docs_text}

Rules:
- Answer based only on the provided document content and the Project Guidelines
- Cite the source file and page number
- If the documents don't contain the answer, say so clearly
- Keep the answer concise and well-structured"""

CONVERSATIONAL_SYSTEM = """You are a polite and professional enterprise assistant.

CONTEXT:
{context}

GUARDRAILS:
1. If the user asks about available projects, use the CONTEXT overview to guide them to enter a specific project for more details. Only summarize what concepts each project carries.
2. If the user asks specific questions about a project while inside another project's context, politely decline to answer and instruct them to switch to the correct project chat.
3. If there is no context available, be naturally helpful but remind them to select a project on the left.
"""


class SynthesiserAgent(BaseAgent):
    """Generates the final natural-language answer for the user."""

    def __init__(self, **kwargs):
        super().__init__(temperature=0.2, **kwargs)

    # ── SQL result synthesis ─────────────────────────────────────────
    async def synthesise_sql(
        self, question: str, sql: str, rows: list[dict], total_rows: int, history: Optional[list[dict]] = None,
        project_guidelines_text: Optional[str] = None
    ) -> str:
        rows_text = json.dumps(rows[:20], indent=2, default=str)
        system = SQL_ANSWER_SYSTEM.format(
            question=question,
            sql=sql,
            total_rows=total_rows,
            shown_rows=min(len(rows), 20),
            rows_text=rows_text,
            project_guidelines_text=project_guidelines_text or "None provided."
        )
        return await self.call_llm(system, question, temperature=0.2, history=history)

    async def stream_sql(
        self, question: str, sql: str, rows: list[dict], total_rows: int, history: Optional[list[dict]] = None,
        project_guidelines_text: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        rows_text = json.dumps(rows[:20], indent=2, default=str)
        system = SQL_ANSWER_SYSTEM.format(
            question=question,
            sql=sql,
            total_rows=total_rows,
            shown_rows=min(len(rows), 20),
            rows_text=rows_text,
            project_guidelines_text=project_guidelines_text or "None provided."
        )
        async for token in self.stream_llm(system, question, temperature=0.2, history=history):
            yield token

    # ── Document result synthesis ────────────────────────────────────
    async def synthesise_docs(
        self, question: str, docs: list[dict], history: Optional[list[dict]] = None,
        project_guidelines_text: Optional[str] = None, db_schema_text: Optional[str] = None
    ) -> str:
        docs_text = self._format_docs(docs)
        system = DOC_ANSWER_SYSTEM.format(
            question=question, 
            docs_text=docs_text,
            project_guidelines_text=project_guidelines_text or "None provided.",
            db_schema_text=db_schema_text or "None provided."
        )
        return await self.call_llm(system, question, temperature=0.15, history=history)

    async def stream_docs(
        self, question: str, docs: list[dict], history: Optional[list[dict]] = None,
        project_guidelines_text: Optional[str] = None, db_schema_text: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        docs_text = self._format_docs(docs)
        system = DOC_ANSWER_SYSTEM.format(
            question=question, 
            docs_text=docs_text,
            project_guidelines_text=project_guidelines_text or "None provided.",
            db_schema_text=db_schema_text or "None provided."
        )
        async for token in self.stream_llm(system, question, temperature=0.15, history=history):
            yield token

    # ── Conversational (no data) ─────────────────────────────────────
    async def synthesise_conversational(self, question: str, context: Optional[str] = None, history: Optional[list[dict]] = None) -> str:
        system = CONVERSATIONAL_SYSTEM.format(context=context or "No specific context provided.")
        return await self.call_llm(system, question, temperature=0.3, history=history)

    async def stream_conversational(
        self, question: str, context: Optional[str] = None, history: Optional[list[dict]] = None
    ) -> AsyncGenerator[str, None]:
        system = CONVERSATIONAL_SYSTEM.format(context=context or "No specific context provided.")
        async for token in self.stream_llm(
            system, question, temperature=0.3, history=history
        ):
            yield token

    # ── Helpers ──────────────────────────────────────────────────────
    @staticmethod
    def _format_docs(docs: list[dict]) -> str:
        parts = []
        for i, doc in enumerate(docs, 1):
            source = doc.get("source", "unknown")
            doc_type = doc.get("doc_type", os.path.splitext(source)[1].replace(".", "") or "txt")
            page = doc.get("page", "?")
            heading = doc.get("heading", "")
            text = doc.get("text", "")
            parts.append(
                f"[{i}] [{doc_type.upper()}] Source: {source}, Page: {page}"
                + (f", Section: {heading}" if heading else "")
                + f"\n{text}\n"
            )
        return "\n".join(parts)
