#!/bin/bash

# Activate virtual environment if it exists
if [ -d "../.venv" ]; then
    echo "Activating virtual environment from ../.venv..."
    source ../.venv/bin/activate
elif [ -d ".venv" ]; then
    echo "Activating virtual environment from .venv..."
    source .venv/bin/activate
fi

# Start FastAPI Backend
echo "Starting FastAPI Backend on port 8002..."
python -m uvicorn app.main:app --host 127.0.0.1 --port 8002 --reload &
BACKEND_PID=$!

# Start React Frontend
echo "Starting React Frontend..."
cd frontend && npm run dev &
FRONTEND_PID=$!

echo "============================================="
echo "  All services starting!"
echo "  Backend:  http://localhost:8002"
echo "  Frontend: http://localhost:5173"
echo "============================================="

# Keep script running
wait

