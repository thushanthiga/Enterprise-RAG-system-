# Enterprise RAG System

This repository contains an Enterprise Retrieval-Augmented Generation (RAG) system built with:
*   **FastAPI**: Backend API for handling requests and LLM orchestration.
*   **Streamlit**: Frontend UI for a conversational interface.
*   **Ollama**: Local inference server running the `qwen2.5:7b-instruct-q4_K_M` model.

## Prerequisites

- Python 3.9+
- [Ollama](https://ollama.com/)
- Docker (optional)

## Quick Start

You can run the entire application stack using the provided execution shell script:

```bash
./run.sh
```

The script will automatically:
1. Start the Ollama serve process.
2. Pull the required language model (`qwen2.5:7b-instruct-q4_K_M`) if not already present.
3. Start the FastAPI backend on port `8000`.
4. Start the Streamlit frontend UI on port `8501`.

## Services

*   **API**: `http://localhost:8000` (FastAPI backend)
*   **UI**: `http://localhost:8501` (Streamlit interface)
*   **Ollama**: `http://localhost:11434` (Local Model inference)
