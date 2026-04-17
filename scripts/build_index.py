#!/usr/bin/env python3
"""
build_index.py — Crawl a document directory, extract text, chunk it,
build a BM25 index, and save to disk.

Usage:
    python scripts/build_index.py [DOC_ROOT] [--index-dir INDEX_PATH]
"""

import argparse
import json
import os
import pickle
import sys
from pathlib import Path

from rank_bm25 import BM25Okapi

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from typing import Any, Dict, List, Optional, Tuple
from config import DOC_ROOT, INDEX_PATH
from app.database import SessionLocalSync
from app.models import AppSetting


# ── Document extraction ──────────────────────────────────────────────
def extract_text_from_pdf(path: str) -> list[dict]:
    """Extract text chunks from a PDF file."""
    chunks = []
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(path)
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text and text.strip():
                chunks.append({
                    "text": text.strip(),
                    "source": os.path.basename(path),
                    "doc_type": "pdf",
                    "page": i + 1,
                    "heading": "",
                    "category": _guess_category(path),
                })
    except Exception as e:
        print(f"  WARNING: Could not read PDF {path}: {e}")
    return chunks


def extract_text_from_docx(path: str) -> list[dict]:
    """Extract text chunks from a DOCX file."""
    chunks = []
    try:
        from docx import Document
        doc = Document(path)
        current_heading = ""
        current_text = []

        for para in doc.paragraphs:
            if para.style and para.style.name and para.style.name.startswith("Heading"):
                # Flush previous section
                if current_text:
                    chunks.append({
                        "text": "\n".join(current_text),
                        "source": os.path.basename(path),
                        "doc_type": "docx",
                        "page": None,
                        "heading": current_heading,
                        "category": _guess_category(path),
                    })
                    current_text = []
                current_heading = para.text
            elif para.text.strip():
                current_text.append(para.text)

        # Flush last section
        if current_text:
            chunks.append({
                "text": "\n".join(current_text),
                "source": os.path.basename(path),
                "doc_type": "docx",
                "page": None,
                "heading": current_heading,
                "category": _guess_category(path),
            })
    except Exception as e:
        print(f"  WARNING: Could not read DOCX {path}: {e}")
    return chunks


def extract_text_from_txt(path: str) -> list[dict]:
    """Extract text chunks from a plain text file."""
    chunks = []
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            text = f.read()
        if text.strip():
            # Chunk by paragraphs (double newline)
            paragraphs = text.split("\n\n")
            for i, para in enumerate(paragraphs):
                if para.strip():
                    chunks.append({
                        "text": para.strip(),
                        "source": os.path.basename(path),
                        "doc_type": os.path.splitext(path)[1].lower().replace(".", ""),
                        "page": i + 1,
                        "heading": "",
                        "category": _guess_category(path),
                    })
    except Exception as e:
        print(f"  WARNING: Could not read TXT {path}: {e}")
    return chunks


EXTRACTORS = {
    ".pdf": extract_text_from_pdf,
    ".docx": extract_text_from_docx,
    ".txt": extract_text_from_txt,
    ".md": extract_text_from_txt,
    ".html": extract_text_from_txt,
}


def _guess_category(path: str) -> str:
    """Guess document category from path or filename."""
    lower = path.lower()
    if "hr" in lower or "human" in lower or "employee" in lower:
        return "hr"
    if "policy" in lower or "procedure" in lower:
        return "policy"
    if "contract" in lower or "agreement" in lower:
        return "contract"
    if "project" in lower:
        return "project"
    return "general"


# ── Chunking ─────────────────────────────────────────────────────────
def chunk_text(text: str, max_tokens: int = 400, overlap: int = 50) -> list[str]:
    """Split text into overlapping token windows."""
    words = text.split()
    if len(words) <= max_tokens:
        return [text]

    chunks = []
    start = 0
    while start < len(words):
        end = start + max_tokens
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start = end - overlap
    return chunks


# ── Scan and index ───────────────────────────────────────────────────
def scan_docs(doc_root: str, uploads_root: Optional[str] = None) -> List[Tuple[str, Optional[int]]]:
    """Recursively find all supported document files with project_id."""
    supported = set(EXTRACTORS.keys())
    files = []
    
    # 1. Scan global DOC_ROOT
    if os.path.exists(doc_root):
        for dirpath, _, filenames in os.walk(doc_root):
            for fn in sorted(filenames):
                ext = os.path.splitext(fn)[1].lower()
                if ext in supported:
                    files.append((os.path.join(dirpath, fn), None))
    
    # 2. Scan project uploads
    if uploads_root and os.path.exists(uploads_root):
        for pid_dir in os.listdir(uploads_root):
            pid_path = os.path.join(uploads_root, pid_dir)
            if os.path.isdir(pid_path) and pid_dir.isdigit():
                project_id = int(pid_dir)
                for dirpath, _, filenames in os.walk(pid_path):
                    for fn in sorted(filenames):
                        ext = os.path.splitext(fn)[1].lower()
                        if ext in supported:
                            files.append((os.path.join(dirpath, fn), project_id))
    
    return files


def build_index(doc_root: str, index_dir: str):
    """Main index build pipeline."""
    uploads_root = str(Path(__file__).parent.parent / "data" / "uploads")
    print(f"Scanning documents in: {doc_root} and {uploads_root}")
    files = scan_docs(doc_root, uploads_root)
    print(f"Found {len(files)} documents")

    all_chunks = []
    for fpath, project_id in files:
        ext = os.path.splitext(fpath)[1].lower()
        extractor = EXTRACTORS.get(ext)
        if not extractor:
            continue

        print(f"  Processing: {os.path.basename(fpath)} (Project: {project_id})")
        raw_chunks = extractor(fpath)

        # Re-chunk large sections
        for rc in raw_chunks:
            sub_chunks = chunk_text(rc["text"])
            for sc in sub_chunks:
                all_chunks.append({
                    "text": sc,
                    "source": rc["source"],
                    "doc_type": rc.get("doc_type", "unknown"),
                    "page": rc["page"],
                    "heading": rc["heading"],
                    "category": rc["category"],
                    "project_id": project_id
                })

    if not all_chunks:
        print("WARNING: No chunks extracted. Check your document directory.")
        return

    # Build BM25 (keeping for hybrid if needed later)
    print(f"Building BM25 index over {len(all_chunks)} chunks...")
    tokenised = [chunk["text"].lower().split() for chunk in all_chunks]
    bm25 = BM25Okapi(tokenised)

    # Build Vector Index (ChromaDB)
    print(f"Building Vector index via ChromaDB and Sentence-Transformers...")
    try:
        import chromadb
        from sentence_transformers import SentenceTransformer
        
        # Load embedding model from Database (MySQL)
        settings = {}
        try:
            with SessionLocalSync() as db:
                db_settings = db.query(AppSetting).all()
                for s in db_settings:
                    settings[s.key] = s.value
        except Exception as db_err:
            print(f"  WARNING: Could not fetch settings from DB, using defaults: {db_err}")
        
        embed_model_name = settings.get("embedding_model", "sentence-transformers/all-MiniLM-L6-v2")
        print(f"  Loading embedding model: {embed_model_name}")
        model = SentenceTransformer(embed_model_name)

        # Initialize Chroma
        persist_dir = os.path.join(index_dir, "chroma")
        client = chromadb.PersistentClient(path=persist_dir)
        
        # Reset or get collection
        collection_name = "enterprise_rag"
        try:
            client.delete_collection(collection_name)
        except:
            pass
        collection = client.create_collection(name=collection_name)

        # Prepare data for Chroma
        documents = [c["text"] for c in all_chunks]
        embeddings = model.encode(documents).tolist()
        metadatas = []
        for c in all_chunks:
            meta = {
                "source": c["source"],
                "doc_type": c.get("doc_type", "unknown"),
                "page": str(c["page"]) if c["page"] else "None",
                "heading": c.get("heading", ""),
                "category": c.get("category", "general"),
            }
            if c.get("project_id") is not None:
                meta["project_id"] = c["project_id"]
            metadatas.append(meta)
        
        ids = [f"id_{i}" for i in range(len(all_chunks))]

        # Add to Chroma
        batch_size = 100
        for i in range(0, len(ids), batch_size):
            collection.add(
                ids=ids[i:i+batch_size],
                embeddings=embeddings[i:i+batch_size],
                metadatas=metadatas[i:i+batch_size],
                documents=documents[i:i+batch_size]
            )
        
        print(f"✓ Saved Vector index to {persist_dir}")

    except Exception as e:
        print(f"  ERROR building vector index: {e}")

    # Save BM25 and chunks
    os.makedirs(index_dir, exist_ok=True)
    bm25_path = os.path.join(index_dir, "bm25_index.pkl")
    chunks_path = os.path.join(index_dir, "chunks.json")

    with open(bm25_path, "wb") as f:
        pickle.dump(bm25, f)

    with open(chunks_path, "w") as f:
        json.dump(all_chunks, f, indent=2)

    print(f"✓ Saved BM25 index to {bm25_path} ({os.path.getsize(bm25_path) / 1024:.0f} KB)")
    print(f"✓ Saved {len(all_chunks)} chunks to {chunks_path}")


# ── CLI ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build BM25 document index")
    parser.add_argument("doc_root", nargs="?", default=DOC_ROOT, help="Document directory")
    parser.add_argument("--index-dir", default=INDEX_PATH, help="Output index directory")
    args = parser.parse_args()

    build_index(args.doc_root, args.index_dir)
