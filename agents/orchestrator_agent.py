"""
OrchestratorAgent — single entry point for all requests.
Delegates to Router → SQL/Doc → Synthesiser and returns the final answer.
Instantiated once at API startup, reused for all requests.
"""
from __future__ import annotations
from typing import Any, AsyncGenerator, Optional

from agents.router_agent import RouterAgent
from agents.sql_agent import SQLAgent
from agents.doc_agent import DocumentAgent
from agents.synthesiser_agent import SynthesiserAgent


class OrchestratorAgent:
    """Coordinates the full request lifecycle across all sub-agents."""

    def __init__(self, settings: Optional[dict] = None):
        self.router = RouterAgent(settings=settings)
        self.sql_agent = SQLAgent(settings=settings)
        self.doc_agent = DocumentAgent(settings=settings)
        self.synthesiser = SynthesiserAgent(settings=settings)

    # ── Single-shot ask ──────────────────────────────────────────────
    async def ask(
        self, question: str, user_id: str = "anon", user_role: str = "admin", 
        db_url: Optional[str] = None, project_context: Optional[str] = None,
        project_id: Optional[int] = None, search_mode: str = "auto",
        db_schema_text: Optional[str] = None, project_guidelines_text: Optional[str] = None,
        history: Optional[list[dict]] = None
    ) -> dict[str, Any]:
        """Full pipeline: classify → retrieve → synthesise → return."""

        # 1. Route with context if provided
        if search_mode == "db":
            # Use 'project' source when a custom project DB is configured, else fall back to 'erp'
            db_source = "project" if db_url else "erp"
            route = {"intent": "sql", "source": db_source}
        elif search_mode == "doc":
            route = {"intent": "doc_search"}
        else:
            route = await self.router.classify(
                question, user_role,
                project_context=project_context,
                db_schema_text=db_schema_text
            )

        if project_id is None and route.get("intent") in ["sql", "doc_search"]:
            if search_mode != "auto":
                return {
                    "answer": "Please select a specific project to search its databases or documents.",
                    "intent": "conversational",
                    "source": None
                }
            route["intent"] = "conversational"

        if route["intent"] == "access_denied":
            return {
                "answer": route.get("message", "Access denied."),
                "intent": "access_denied",
                "source": route.get("source"),
            }

        # 2. Retrieve
        context: dict[str, Any] = {"intent": route["intent"], "source": route.get("source")}

        if route["intent"] == "sql":
            sql_result = await self.sql_agent.run(
                question, route["source"], user_role, 
                override_url=db_url, db_schema_text=db_schema_text
            )
            if sql_result.get("error"):
                print(f"SQL Error: {sql_result['error']}")
                return {
                    "answer": "I'm sorry, I encountered an issue while processing your database request. The requested information might not be available or the query was too complex to execute. Please try rephrasing your question.",
                    "intent": "sql",
                    "source": route["source"],
                    "error": "Query execution failed.",
                }
            context["sql"] = sql_result["sql"]
            context["rows"] = sql_result["rows"]
            context["total_rows"] = sql_result.get("total_rows", len(sql_result["rows"]))
            # 3. Synthesise
            answer = await self.synthesiser.synthesise_sql(
                question, context["sql"], context["rows"], context["total_rows"], history=history,
                project_guidelines_text=project_guidelines_text
            )

        elif route["intent"] == "doc_search":
            docs = await self.doc_agent.search(question, user_role, project_id=project_id)
            context["docs"] = docs
            if not docs:
                answer = "I couldn't find any relevant documents for your question."
            else:
                answer = await self.synthesiser.synthesise_docs(
                    question, docs, history=history,
                    project_guidelines_text=project_guidelines_text,
                    db_schema_text=db_schema_text
                )

        else:
            # Conversational
            answer = await self.synthesiser.synthesise_conversational(
                question, context=project_context, history=history
            )

        injected_files = []
        if project_guidelines_text: injected_files.append("project_guidelines.md")
        if db_schema_text: injected_files.append("db_schema.md")

        return {
            "answer": answer,
            **context,
            "router_debug": route.get("router_debug"),
            "injected_files": injected_files
        }

    # ── Streaming ask ────────────────────────────────────────────────
    async def ask_stream(
        self, question: str, user_id: str = "anon", user_role: str = "admin", 
        db_url: Optional[str] = None, project_context: Optional[str] = None,
        project_id: Optional[int] = None, search_mode: str = "auto",
        db_schema_text: Optional[str] = None, project_guidelines_text: Optional[str] = None,
        history: Optional[list[dict]] = None
    ) -> AsyncGenerator[str | dict, None]:
        """Stream the final answer token-by-token."""

        # 1. Route
        if search_mode == "db":
            # Use 'project' source when a custom project DB is configured, else fall back to 'erp'
            db_source = "project" if db_url else "erp"
            route = {"intent": "sql", "source": db_source}
        elif search_mode == "doc":
            route = {"intent": "doc_search"}
        else:
            route = await self.router.classify(
                question, user_role,
                project_context=project_context,
                db_schema_text=db_schema_text
            )

        if project_id is None and route.get("intent") in ["sql", "doc_search"]:
            if search_mode != "auto":
                yield "Please select a specific project to search its databases or documents."
                return
            route["intent"] = "conversational"

        if route["intent"] == "access_denied":
            yield route.get("message", "Access denied.")
            return

        injected_files = []
        if project_guidelines_text: injected_files.append("project_guidelines.md")
        if db_schema_text: injected_files.append("db_schema.md")

        # 2. Retrieve + 3. Stream synthesis
        if route["intent"] == "sql":
            sql_result = await self.sql_agent.run(
                question, route["source"], user_role, 
                override_url=db_url, db_schema_text=db_schema_text
            )
            if sql_result.get("error"):
                print(f"SQL Error: {sql_result['error']}")
                yield "I'm sorry, I encountered an issue while processing your database request. The requested information might not be available or the query was too complex to execute. Please try rephrasing your question."
                return
            async for token in self.synthesiser.stream_sql(
                question,
                sql_result["sql"],
                sql_result["rows"],
                sql_result.get("total_rows", len(sql_result["rows"])),
                history=history,
                project_guidelines_text=project_guidelines_text
            ):
                yield token
            yield {"metadata": {
                "sql": sql_result["sql"], 
                "total_rows": sql_result.get("total_rows", len(sql_result["rows"])),
                "intent": "sql",
                "source": route["source"],
                "router_debug": route.get("router_debug"),
                "injected_files": injected_files
            }}

        elif route["intent"] == "doc_search":
            docs = await self.doc_agent.search(question, user_role, project_id=project_id)
            if not docs:
                yield "I couldn't find any relevant documents for your question."
                return
            async for token in self.synthesiser.stream_docs(
                question, docs, history=history,
                project_guidelines_text=project_guidelines_text,
                db_schema_text=db_schema_text
            ):
                yield token
            yield {"metadata": {
                "docs": docs, 
                "intent": "doc_search", 
                "router_debug": route.get("router_debug"), 
                "injected_files": injected_files
            }}

        else:
            async for token in self.synthesiser.stream_conversational(
                question, context=project_context, history=history
            ):
                yield token
            yield {"metadata": {
                "intent": "conversational", 
                "router_debug": route.get("router_debug"), 
                "injected_files": injected_files
            }}
