#!/bin/bash
# Stop any existing processes on the specific ports
echo "Cleaning up ports 8000, 5173..."
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:5173 | xargs kill -9 2>/dev/null || true
pkill -f uvicorn || true
pkill -f vite || true


# Activate virtual environment if it exists
if [ -d "../.venv" ]; then
    echo "Activating virtual environment from ../.venv..."
    source ../.venv/bin/activate
elif [ -d ".venv" ]; then
    echo "Activating virtual environment from .venv..."
    source .venv/bin/activate
fi

# Start FastAPI Backend
echo "Starting FastAPI Backend..."
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload &
BACKEND_PID=$!

# Start React Frontend
echo "Starting React Frontend..."
cd frontend && npm run dev &
FRONTEND_PID=$!

echo "============================================="
echo "  All services starting!"
echo "  Backend:  http://localhost:8000"
echo "  Frontend: http://localhost:5173"
echo "============================================="

# Keep script running
wait
