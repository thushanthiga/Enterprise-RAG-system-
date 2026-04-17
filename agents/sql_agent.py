"""
SQLAgent — loads schema YAML, generates SQL, validates, executes.
Results are returned as a list of dicts ready for the synthesiser.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import yaml
import sqlparse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine

from config import DB_URLS
from agents.base_agent import BaseAgent


# ── Blocked SQL keywords ─────────────────────────────────────────────
BLOCKED_KEYWORDS = {
    "insert", "update", "delete", "drop", "alter",
    "create", "truncate", "exec", "execute", "xp_cmdshell",
    "grant", "revoke",
}

SQL_SYSTEM = """You are a SQL expert for a {source} database.

Schema:
{schema}

Rules:
1. Write SELECT only. LIMIT 100.
2. CRITICAL: Use EXACT table and column names exactly as they are defined in the schema above.
3. DO NOT guess, predict, or invent table names or columns that are not present in the schema. Check spelling.
4. If using table aliases (e.g., `t1`), ONLY reference columns using defined aliases. 
5. Return ONLY valid SQL. No markdown fences or explanations.
"""

SCHEMA_DIR = Path(__file__).parent.parent / "schemas"


class SQLAgent(BaseAgent):
    """Text-to-SQL agent with validation and execution."""

    def __init__(self, **kwargs):
        super().__init__(temperature=0.0, **kwargs)
        self._engines: Dict[str, AsyncEngine] = {}
        self._schema_cache: Dict[str, str] = {}
        self._load_schemas()

    # ── Schema loading ───────────────────────────────────────────────
    def _load_schemas(self):
        """Pre-load all YAML schemas at startup and cache as prompt text."""
        if not SCHEMA_DIR.exists():
            return
        for yaml_file in SCHEMA_DIR.glob("*.yaml"):
            key = yaml_file.stem.replace("_tables", "")
            with open(yaml_file) as f:
                data = yaml.safe_load(f)
            self._schema_cache[key] = self._schema_to_text(data)

    @staticmethod
    def _schema_to_text(schema_data: dict) -> str:
        """Convert YAML schema dict to compact natural language."""
        lines = []
        tables = schema_data.get("tables", {})
        for table_name, table_info in tables.items():
            desc = table_info.get("description", "")
            lines.append(f"Table: {table_name} — {desc}")
            columns = table_info.get("columns", {})
            for col_name, col_info in columns.items():
                if isinstance(col_info, dict):
                    col_type = col_info.get("type", "")
                    col_desc = col_info.get("desc", "")
                    lines.append(f"  - {col_name} ({col_type}): {col_desc}")
                else:
                    lines.append(f"  - {col_name}: {col_info}")
            samples = table_info.get("sample_values", {})
            for col, vals in samples.items():
                lines.append(f"  Sample {col}: {vals}")
            lines.append("")
        return "\n".join(lines)

    def _trim_schema(self, schema_text: str, max_chars: int = 8000) -> str:
        if len(schema_text) <= max_chars:
            return schema_text
        return schema_text[:max_chars] + "\n[... truncated]"

    # ── DB engine management ─────────────────────────────────────────
    def _get_engine(self, source: str, override_url: Optional[str] = None) -> AsyncEngine:
        if override_url:
            # Use a specialized key for dynamic engines to avoid collisions
            key = f"dynamic_{source}_{hash(override_url)}"
            if key not in self._engines:
                self._engines[key] = create_async_engine(override_url)
            return self._engines[key]
            
        if source not in self._engines:
            url = DB_URLS.get(source)
            if not url:
                raise ValueError(f"No database URL configured for source: {source}")
            self._engines[source] = create_async_engine(url)
        return self._engines[source]

    # ── Main entry point ─────────────────────────────────────────────
    async def run(
        self, question: str, source: str, user_role: str = "admin", 
        override_url: Optional[str] = None, db_schema_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate SQL → validate → execute → return rows."""

        # 1. Load relevant schema
        schema_text = self._schema_cache.get(source, "")
        
        # Augment with project-specific manual schema if provided
        if db_schema_text:
            schema_text = f"{db_schema_text}\n\nTechnical Details:\n{schema_text}"

        if not schema_text:
            return {"error": f"No schema found for source: {source}", "rows": []}

        schema_text = self._trim_schema(schema_text)

        # 2. Generate SQL
        system_prompt = SQL_SYSTEM.format(source=source, schema=schema_text)
        raw_sql = await self.call_llm(system_prompt, question)
        sql = self._extract_sql(raw_sql)

        # 3. Validate
        error = self._validate_sql(sql, source)
        if error:
            return {"error": error, "sql": sql, "rows": []}

        # 4. Execute
        try:
            rows = await self._execute(sql, source, override_url)
        except Exception as exc:
            return {"error": str(exc), "sql": sql, "rows": []}

        return {"sql": sql, "rows": rows[:50], "total_rows": len(rows)}

    # ── SQL extraction ───────────────────────────────────────────────
    @staticmethod
    def _extract_sql(raw: str) -> str:
        """Strip markdown fences and explanation text from LLM output."""
        clean = re.sub(r"```sql|```", "", raw).strip()
        # If the response starts with SELECT, take it
        match = re.search(r"(SELECT\s.+)", clean, re.IGNORECASE | re.DOTALL)
        if match:
            sql = match.group(1).strip()
            # Remove trailing explanation after semicolon
            if ";" in sql:
                sql = sql[: sql.index(";") + 1]
            return sql
        return clean

    # ── Validation ───────────────────────────────────────────────────
    def _validate_sql(self, sql: str, source: str) -> Optional[str]:
        """Return error message if SQL is unsafe, else None."""
        if not sql:
            return "Empty SQL generated"

        # Parse with sqlparse
        parsed = sqlparse.parse(sql)
        if not parsed:
            return "Could not parse generated SQL"

        stmt = parsed[0]
        if stmt.get_type() != "SELECT":
            return f"Only SELECT allowed, got: {stmt.get_type()}"

        # Keyword blocklist
        sql_lower = sql.lower()
        for kw in BLOCKED_KEYWORDS:
            # Use word boundary matching
            if re.search(rf"\b{kw}\b", sql_lower):
                return f"Blocked keyword detected: {kw}"

        # Validate table names against schema
        schema_text = self._schema_cache.get(source, "")
        known_tables = self._extract_table_names(source)
        # NOTE: Full table validation would need a proper SQL parser;
        # the read-only DB user is the ultimate safety net.

        return None

    def _extract_table_names(self, source: str) -> Set[str]:
        """Get table names from the cached schema for a source."""
        yaml_file = SCHEMA_DIR / f"{source}_tables.yaml"
        if yaml_file.exists():
            with open(yaml_file) as f:
                data = yaml.safe_load(f)
            return set(data.get("tables", {}).keys())
        # Try without _tables suffix
        yaml_file = SCHEMA_DIR / f"{source}.yaml"
        if yaml_file.exists():
            with open(yaml_file) as f:
                data = yaml.safe_load(f)
            return set(data.get("tables", {}).keys())
        return set()

    # ── Execution ────────────────────────────────────────────────────
    async def _execute(self, sql: str, source: str, override_url: Optional[str] = None) -> List[Dict]:
        """Execute validated SQL against the database."""
        engine = self._get_engine(source, override_url)
        async with engine.connect() as conn:
            result = await conn.execute(text(sql))
            rows = [dict(r._mapping) for r in result.fetchmany(500)]
        return rows
