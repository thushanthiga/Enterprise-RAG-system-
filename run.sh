#!/bin/bash
set -e

echo "============================================="
echo "  Enterprise RAG — Starting all services"
echo "============================================="

# ── 1. Start Ollama ──────────────────────────────────────────────────
echo "[1/4] Starting Ollama..."
ollama serve &
OLLAMA_PID=$!

# Wait for Ollama to be ready
echo "  Waiting for Ollama to start..."
for i in {1..60}; do
    if curl -sf http://localhost:11434 >/dev/null 2>&1; then
        echo "  ✓ Ollama is up (PID: $OLLAMA_PID)"
        break
    fi
    if [ $i -eq 60 ]; then
        echo "  ✗ Ollama failed to start within 60s"
        exit 1
    fi
    sleep 1
done

# ── 2. Pull model (if not already present) ───────────────────────────
MODEL=${OLLAMA_MODEL:-qwen2.5:7b-instruct-q4_K_M}
echo "[2/4] Checking model: $MODEL"
if ! ollama list | grep -q "$MODEL"; then
    echo "  Pulling $MODEL (this may take a while on first run)..."
    ollama pull "$MODEL"
    echo "  ✓ Model pulled"
else
    echo "  ✓ Model already available"
fi

# ── 3. Start FastAPI ─────────────────────────────────────────────────
echo "[3/4] Starting FastAPI on port 8002..."
cd /app
python3 -m uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8002 \
    --workers 1 &
API_PID=$!
echo "  ✓ FastAPI started (PID: $API_PID)"

# Wait for API to be ready
sleep 3
for i in {1..30}; do
    if curl -sf http://localhost:8002/health >/dev/null 2>&1; then
        echo "  ✓ API health check passed"
        break
    fi
    sleep 1
done

# ── 4. Start Streamlit UI ────────────────────────────────────────────
echo "[4/4] Starting Streamlit UI on port 8501..."
python3 -m streamlit run ui/chat.py \
    --server.port 8501 \
    --server.address 0.0.0.0 \
    --server.headless true \
    --browser.gatherUsageStats false &
UI_PID=$!
echo "  ✓ Streamlit started (PID: $UI_PID)"

echo ""
echo "============================================="
echo "  All services running!"
echo "  API:       http://localhost:8002"
echo "  UI:        http://localhost:8501"
echo "  Ollama:    http://localhost:11434"
echo "============================================="


# Keep container alive — wait for any process to exit
wait -n $OLLAMA_PID $API_PID $UI_PID
echo "A service exited. Shutting down..."
kill $OLLAMA_PID $API_PID $UI_PID 2>/dev/null
