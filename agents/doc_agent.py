"""
DocumentAgent — holds BM25 index in RAM, searches at query time.
Role-based filtering removes documents the user cannot access.
"""
from __future__ import annotations

import json
import os
import pickle
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np
from rank_bm25 import BM25Okapi
from config import INDEX_PATH
from agents.base_agent import BaseAgent


# ── Role → allowed document categories ───────────────────────────────
DOC_ACCESS = {
    "admin":       None,   # None = all documents
    "hr_manager":  {"hr", "general", "policy", "contract"},
    "dept_head":   {"general", "policy", "department"},
    "pm":          {"general", "project"},
    "employee":    {"general", "public"},
}


class DocumentAgent(BaseAgent):
    """Vector search over document chunks via ChromaDB."""

    def __init__(self, **kwargs):
        super().__init__(temperature=0.0, **kwargs)
        self.client = None
        self.collection = None
        self.model = None
        self.bm25 = None
        self.chunks = []
        self._init_vector_db()
        self._init_bm25()

    def _init_bm25(self):
        """Load BM25 index and chunks from disk."""
        try:
            bm25_path = Path(INDEX_PATH) / "bm25_index.pkl"
            chunks_path = Path(INDEX_PATH) / "chunks.json"
            
            if bm25_path.exists():
                with open(bm25_path, "rb") as f:
                    self.bm25 = pickle.load(f)
            
            if chunks_path.exists():
                with open(chunks_path, "r") as f:
                    self.chunks = json.load(f)
            
            print(f"✓ DocumentAgent loaded BM25 index and {len(self.chunks)} chunks")
        except Exception as e:
            print(f"  WARNING: Could not load BM25 index: {e}")

    # ── Vector DB initialization ─────────────────────────────────────
    def _init_vector_db(self):
        try:
            import chromadb
            from sentence_transformers import SentenceTransformer
            from pathlib import Path
            import json

            # Load settings for model name
            settings_path = Path(__file__).parent.parent / "data" / "settings.json"
            settings = {}
            if settings_path.exists():
                with open(settings_path) as f:
                    settings = json.load(f)
            
            embed_model_name = settings.get("embedding_model", "sentence-transformers/all-MiniLM-L6-v2")
            self.model = SentenceTransformer(embed_model_name)

            persist_dir = os.path.join(INDEX_PATH, "chroma")
            self.client = chromadb.PersistentClient(path=persist_dir)
            
            self.collection = self.client.get_collection(name="enterprise_rag")
            print(f"✓ DocumentAgent connected to vector index at {persist_dir}")
        except Exception as e:
            print(f"  WARNING: Could not connect to vector index: {e}")

    def reload_index(self):
        """Re-initialise the vector database connection."""
        self._init_vector_db()

    # ── Search ───────────────────────────────────────────────────────
    async def search(
        self,
        question: str,
        user_role: str = "admin",
        project_id: Optional[int] = None,
        top_k: int = 5,
        score_threshold: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """Search both vector and BM25 indices and return matching chunks."""
        final_results = []
        allowed_cats = DOC_ACCESS.get(user_role)
        
        # Build filter for Vector search
        where = {}
        if project_id is not None:
            where["project_id"] = project_id

        # --- Vector Search ---
        if self.collection is not None and self.model is not None:
            try:
                query_emb = self.model.encode(question).tolist()
                results = self.collection.query(
                    query_embeddings=[query_emb],
                    n_results=top_k * 2,
                    where=where if where else None
                )

                if results and results["documents"] and results["documents"][0]:
                    docs = results["documents"][0]
                    metas = results["metadatas"][0]
                    distances = results["distances"][0] if "distances" in results else [0.5] * len(docs)

                    for i in range(len(docs)):
                        meta = metas[i]
                        category = meta.get("category", "general")

                        # Role-based filtering
                        if allowed_cats is not None and category not in allowed_cats:
                            continue

                        # Convert distance to a similarity-like score (0-1)
                        # Chroma L2: 0 is exact match, 2 is diametrically opposite
                        score = max(0.0, 1.0 - (distances[i] / 2.0))

                        final_results.append({
                            "text": docs[i],
                            "source": meta.get("source", "unknown"),
                            "doc_type": meta.get("doc_type", "unknown"),
                            "page": meta.get("page"),
                            "heading": meta.get("heading", ""),
                            "category": category,
                            "score": score,
                            "method": "vector"
                        })
            except Exception as e:
                print(f"  WARNING: Vector search failed: {e}")

        # --- BM25 Search ---
        if self.bm25 and self.chunks:
            try:
                tokenized_query = question.lower().split()
                bm25_scores = self.bm25.get_scores(tokenized_query)
                
                # Get top scores
                top_bm25_indices = np.argsort(bm25_scores)[-top_k:][::-1]
                
                # Rough normalization: BM25 scores can be high, let's max at 10 for "1.0"
                for idx in top_bm25_indices:
                    raw_score = bm25_scores[idx]
                    if raw_score <= 0: continue
                    
                    chunk = self.chunks[idx]
                    
                    # Role-based filtering
                    if allowed_cats is not None and chunk.get("category", "general") not in allowed_cats:
                        continue
                    
                    # Project filtering
                    if project_id is not None and chunk.get("project_id") != project_id:
                        continue

                    # Check for duplicates or merging
                    exists = False
                    for res in final_results:
                        if res["text"] == chunk["text"]:
                            res["score"] = max(res["score"], min(1.0, raw_score / 10.0))
                            res["method"] = "hybrid"
                            exists = True
                            break
                    
                    if not exists:
                        final_results.append({
                            "text": chunk["text"],
                            "source": chunk.get("source", "unknown"),
                            "doc_type": chunk.get("doc_type", "unknown"),
                            "page": chunk.get("page"),
                            "heading": chunk.get("heading", ""),
                            "category": chunk.get("category", "general"),
                            "score": min(0.9, raw_score / 10.0), # Cap solo BM25 slightly below 1.0
                            "method": "bm25"
                        })
            except Exception as e:
                print(f"  WARNING: BM25 search failed: {e}")

        # Final sort and limit
        final_results.sort(key=lambda x: x["score"], reverse=True)
        return final_results[:top_k]
