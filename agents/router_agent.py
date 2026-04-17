"""
RouterAgent — classifies user intent and identifies the data source.
Strategy (fastest to slowest):
  1. Fast rule-based keywords           < 1 ms   (covers ~70% of generic queries)
  2. Schema-keyword matching            < 2 ms   (covers ~20% of domain queries, no LLM)
  3. LLM fallback for truly ambiguous   ~1-3 s   (only ~10% of queries)
"""
from __future__ import annotations

import re
import re
import logging
from typing import Optional, Set

from agents.base_agent import BaseAgent

try:
    import joblib
    from sentence_transformers import SentenceTransformer
    HAS_ML = True
except ImportError:
    HAS_ML = False


# ── Broad SQL trigger phrases ────────────────────────────────────────
# Extended to catch data-intent questions without an LLM call
SQL_TRIGGERS = [
    # counts / aggregates
    "how many", "count", "total", "sum", "average", "avg", "number of",
    "min ", "max ", "minimum", "maximum", "percentage", "ratio", "breakdown",
    # listing / retrieval
    "list", "show me", "show all", "give me", "get me", "fetch", "find all",
    "find me", "retrieve", "display", "what are all", "which ones",
    # reporting / analysis
    "report", "top ", "bottom ", "rank", "ranking", "summary", "overview",
    "statistics", "stats", "analyse", "analyze", "trend", "compare",
    # time-based
    "last month", "last week", "last year", "this month", "this year",
    "yesterday", "today", "recent", "latest", "oldest", "newest",
    "between", "since", "from", "until", "date range",
    # business terms
    "revenue", "sales", "profit", "cost", "budget", "spend", "invoice",
    "order", "purchase", "stock",
    # status queries
    "pending", "completed", "approved", "rejected", "active", "inactive",
    "status", "progress",
    # data existence
    "exists", "available", "is there", "are there", "do we have", "do i have",
    "can be used", "used so far", "remaining",
]

# ── Document trigger phrases ─────────────────────────────────────────
DOC_TRIGGERS = [
    "policy", "procedure", "manual", "guidelines", "form",
    "template", "contract", "handbook", "regulation", "rule",
    "instruction", "clause", "document says", "pdf says", "according to",
    "what does the", "attachment", "uploaded file",
    "what is the table", "which table", "describe the table", "where is it stored"
]

# ── Generic DB source hints (no project schema available) ────────────
ERP_HINTS = [
    "order", "invoice", "stock", "inventory", "supplier",
    "customer", "account", "purchase", "vendor", "product",
    "shipment", "delivery",
]
HR_HINTS = [
    "employee", "leave", "payroll", "salary", "department",
    "attendance", "appraisal", "staff", "hire", "termination",
    "resignation", "onboarding",
]
PROJECT_HINTS = [
    "project", "task", "milestone", "timesheet", "sprint",
    "deadline", "assignment", "resource allocation",
]

# Questions that look like SQL triggers but are actually conversational
CONVERSATIONAL_OVERRIDES = [
    "how many projects", "how many databases", "how many documents",
    "what databases", "list my projects", "list projects", "list databases",
    "what can you", "what are you", "what is this", "help me",
    "tell me about yourself", "who are you",
]

# ── Role → allowed sources ───────────────────────────────────────────
ROLE_ACCESS = {
    "admin":       {"erp", "hr", "projects", "project", "doc_search"},
    "hr_manager":  {"hr", "project", "doc_search"},
    "dept_head":   {"hr", "projects", "project", "doc_search"},
    "pm":          {"projects", "project", "doc_search"},
    "employee":    {"hr", "project", "doc_search"},
}

CLASSIFY_SYSTEM = (
    "You are a query classifier. Respond ONLY with a JSON object, no markdown:\n"
    "{\"intent\": \"sql\" | \"doc_search\" | \"conversational\", "
    "\"source\": \"erp\" | \"hr\" | \"projects\" | \"project\" | null}\n\n"
    "Rules:\n"
    "- intent=sql: user wants ACTUAL ROWS or DATA FROM a database (counts, lists, records, stats).\n"
    "- intent=doc_search: user wants content from uploaded documents, OR wants explanations about the project guidelines/database schema (e.g. 'what is the table for X').\n"
    "- intent=conversational: greeting, help, meta-questions about the system\n"
    "- Use source=project when intent=sql and the project DB is targeted\n"
    "- If intent is not sql, source must be null"
)


class RouterAgent(BaseAgent):
    """Intent classification: ML model first, then rule-based, then LLM."""

    def __init__(self, **kwargs):
        super().__init__(temperature=0.0, **kwargs)
        self.ml_model = None
        self.embedder = None
        # Attempt to load the fine-tuned pickle model if available
        if HAS_ML:
            import os
            model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "thusha_AI.pkl")
            if os.path.exists(model_path):
                try:
                    self.ml_model = joblib.load(model_path)
                    # Load the transformer body since the pkl only has the Scikit-Learn head
                    self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
                    logging.info(f"Successfully loaded ML model from {model_path} with all-MiniLM-L6-v2 embedder")
                except Exception as e:
                    logging.warning(f"Failed to load ML model {model_path}: {e}")

    async def classify(
        self,
        question: str,
        user_role: str = "admin",
        project_context: Optional[str] = None,
        db_schema_text: Optional[str] = None,
    ) -> dict:
        """Return {intent, source} for the given question.
        
        Performance tiers:
        0. ML Classifier (thusha_AI.pkl) (< 5 ms)
        1. Conversational override check (< 1 ms)
        2. Doc-trigger rule              (< 1 ms)
        3. SQL-trigger rule              (< 1 ms)
        4. Schema keyword match          (< 2 ms, only when project DB active)
        5. LLM fallback                  (~1-3 s, rarely reached)
        """
        q = question.lower().strip()

        # ── Tier 0: Fine-Tuned ML Model Classifier ────────────────────
        if self.ml_model is not None and self.embedder is not None:
            try:
                # Embed text first because the pkl is just the LogisticRegression head
                embeddings = self.embedder.encode([q])
                
                # Get predicted label and probabilities
                label = self.ml_model.predict(embeddings)[0]
                label = str(label)
                
                # Check confidence using predict_proba if available
                confidence = 1.0
                if hasattr(self.ml_model, "predict_proba"):
                    probs = self.ml_model.predict_proba(embeddings)[0]
                    confidence = float(max(probs))

                if confidence > 0.65:
                    print(f"DEBUG ML LABEL: {label}, Conf: {confidence}")
                    debug_info = f"ML_LABEL: {label}, CONF: {confidence:.2f}"
                    if label == "sql_agent" or label == "db_search":
                        # ML mapped it to SQL, but we still need to assign the correct source
                        source = self._detect_source(q, has_project_schema=bool(db_schema_text)) or "erp"
                        res = self._enforce_role({"intent": "sql", "source": source}, user_role)
                        res["router_debug"] = debug_info
                        return res
                    elif label == "doc_agent" or label == "doc_search":
                        res = self._enforce_role({"intent": "doc_search", "source": None}, user_role)
                        res["router_debug"] = debug_info
                        return res
                    elif label == "conversational":
                        res = self._enforce_role({"intent": "conversational", "source": None}, user_role)
                        res["router_debug"] = debug_info
                        return res
                else:
                    self._last_debug_info = f"ML_LABEL: {label}, CONF: {confidence:.2f} (Skipped, < 0.65)"
            except Exception as e:
                logging.error(f"ML Classifier error: {e}")
                # Fallthrough to rule-based on failure


        # ── Tier 1: Conversational overrides (fast exits) ─────────────
        if self._is_conversational_override(q):
            res = self._enforce_role({"intent": "conversational", "source": None}, user_role)
            res["router_debug"] = getattr(self, "_last_debug_info", "") + " | Rule: Conversational Override"
            return res

        # ── Tier 2: Document trigger ──────────────────────────────────
        if any(t in q for t in DOC_TRIGGERS):
            res = self._enforce_role({"intent": "doc_search", "source": None}, user_role)
            res["router_debug"] = getattr(self, "_last_debug_info", "") + " | Rule: Doc Trigger"
            return res

        # ── Tier 3: Generic SQL triggers ──────────────────────────────
        has_sql_trigger = any(t in q for t in SQL_TRIGGERS)
        if has_sql_trigger:
            source = self._detect_source(q, has_project_schema=bool(db_schema_text))
            if source:
                res = self._enforce_role({"intent": "sql", "source": source}, user_role)
                res["router_debug"] = getattr(self, "_last_debug_info", "") + " | Rule: SQL Trigger"
                return res

        # ── Tier 4: Schema keyword matching (zero LLM cost) ───────────
        # if db_schema_text:
        #     schema_keywords = self._extract_schema_keywords(db_schema_text)
        #     if self._matches_schema_keywords(q, schema_keywords):
        #         return self._enforce_role({"intent": "sql", "source": "project"}, user_role)

        # ── Tier 5: LLM fallback (slow — only for truly ambiguous) ────
        # Only call LLM if the question seems to have data intent but we couldn't
        # classify it rule-based. Skip LLM for clearly conversational questions.
        looks_like_data_question = any(w in q for w in [
            "how", "which", "what", "show", "tell", "give", "find", "get",
            "is there", "are there", "do we", "can i", "can be"
        ])
        if looks_like_data_question:
            result = await self._llm_classify(question, project_context, db_schema_text)
            res = self._enforce_role(result, user_role)
            res["router_debug"] = getattr(self, "_last_debug_info", "") + " | Rule: LLM Fallback"
            return res

        res = self._enforce_role({"intent": "conversational", "source": None}, user_role)
        res["router_debug"] = getattr(self, "_last_debug_info", "") + " | Rule: Default Conversational"
        return res

    # ── Tier 1: Conversational override ──────────────────────────────
    @staticmethod
    def _is_conversational_override(q: str) -> bool:
        return any(phrase in q for phrase in CONVERSATIONAL_OVERRIDES)

    # ── Tier 3: Source detection ──────────────────────────────────────
    @staticmethod
    def _detect_source(q: str, has_project_schema: bool) -> Optional[str]:
        """Detect which database source based on domain hints."""
        if has_project_schema:
            return "project"
        if any(h in q for h in HR_HINTS):
            return "hr"
        if any(h in q for h in PROJECT_HINTS):
            return "projects"
        if any(h in q for h in ERP_HINTS):
            return "erp"
        # If project schema is not available and no domain hint, don't guess
        return None

    # ── Tier 4: Schema keyword extraction + matching ──────────────────
    @staticmethod
    def _extract_schema_keywords(schema_text: str) -> Set[str]:
        """Extract table names and column names from the db_schema.md text.
        Returns a set of lowercase keywords that signal this project's domain.
        Only keywords ≥ 4 chars to avoid false positives on common words.
        """
        keywords: Set[str] = set()
        # Match patterns like: Table: xxx, column names, markdown headers, backtick words
        patterns = [
            r"Table[:\s]+(\w+)",          # Table: interviews
            r"`(\w+)`",                    # `candidate_id`
            r"^\s*[-*]\s+(\w+)",           # - column_name
            r"\*\*(\w+)\*\*",              # **TableName**
            r"^#+\s+(\w+)",                # ## TableName
            r"(\w+)\s*[|]",               # column | type tables
        ]
        for pat in patterns:
            for match in re.finditer(pat, schema_text, re.MULTILINE | re.IGNORECASE):
                word = match.group(1).lower()
                if len(word) >= 4 and word not in {
                    "type", "name", "date", "time", "null", "true", "false",
                    "with", "from", "where", "select", "table", "column", "index"
                }:
                    keywords.add(word)
                    # Also add singular/plural variants
                    if word.endswith("s") and len(word) > 5:
                        keywords.add(word[:-1])
                    else:
                        keywords.add(word + "s")
        return keywords

    @staticmethod
    def _matches_schema_keywords(q: str, keywords: Set[str]) -> bool:
        """Return True if any schema keyword appears in the question."""
        q_words = set(re.findall(r"\w+", q))
        return bool(q_words & keywords)

    # ── Tier 5: LLM fallback (minimal prompt for speed) ──────────────
    async def _llm_classify(
        self,
        question: str,
        context: Optional[str] = None,
        db_schema_text: Optional[str] = None,
    ) -> dict:
        system_prompt = CLASSIFY_SYSTEM
        if db_schema_text:
            # Only inject first 800 chars — enough for table names, keeps tokens low
            system_prompt += f"\n\nProject DB Schema (excerpt):\n{db_schema_text[:800]}"
        if context:
            system_prompt += f"\n\nProject context: {context[:300]}"

        raw = await self.call_llm(system_prompt, question)
        try:
            parsed = self.parse_llm_json(raw)
            return {
                "intent": parsed.get("intent", "conversational"),
                "source": parsed.get("source"),
            }
        except (ValueError, KeyError):
            return {"intent": "conversational", "source": None}

    # ── Role enforcement ─────────────────────────────────────────────
    def _enforce_role(self, result: dict, role: str) -> dict:
        allowed = ROLE_ACCESS.get(role, {"doc_search"})
        source = result.get("source")

        if result["intent"] == "sql":
            if source is None:
                return {"intent": "conversational", "source": None}
            if role == "admin":
                return result
            if source not in allowed:
                return {
                    "intent": "access_denied",
                    "source": source,
                    "message": (
                        f"Your current role '{role}' does not grant access "
                        f"to query the '{source}' database."
                    ),
                }

        if result["intent"] == "doc_search" and "doc_search" not in allowed:
            return {
                "intent": "access_denied",
                "source": None,
                "message": (
                    f"Your current role '{role}' does not have permission "
                    "to search project documents."
                ),
            }
        return result
