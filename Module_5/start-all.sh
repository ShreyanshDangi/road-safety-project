#!/bin/bash
# Module 5 — Master Startup Script
# Runs both backend and frontend in parallel

echo "════════════════════════════════════════════════════════════"
echo "  Module 5 — Road Damage Heatmap Dashboard"
echo "  Starting Full Stack Application"
echo "════════════════════════════════════════════════════════════"
echo ""

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down servers..."
    kill $(jobs -p) 2>/dev/null
    exit
}

trap cleanup SIGINT SIGTERM

# Start backend
echo "1️⃣  Starting Backend (FastAPI)..."
cd "$BACKEND_DIR"

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "   Creating virtual environment..."
    python3 -m venv venv
fi

# Activate and install
source venv/bin/activate
pip install -q -r requirements.txt --break-system-packages 2>&1 | grep -v "ERROR: pip's dependency"

# Start backend in background
echo "   ✅ Backend starting on port 8000..."
python main.py > /tmp/module5-backend.log 2>&1 &
BACKEND_PID=$!

# Wait for backend to be ready
echo "   ⏳ Waiting for backend to start..."
for i in {1..15}; do
    if curl -s http://localhost:8000/ > /dev/null 2>&1; then
        echo "   ✅ Backend is ready!"
        break
    fi
    sleep 1
done

# Start frontend
echo ""
echo "2️⃣  Starting Frontend (React + Vite)..."
cd "$FRONTEND_DIR"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "   Installing npm packages..."
    npm install > /tmp/module5-npm-install.log 2>&1
fi

echo "   ✅ Frontend starting on port 5173..."
npm run dev > /tmp/module5-frontend.log 2>&1 &
FRONTEND_PID=$!

# Wait for frontend to be ready
echo "   ⏳ Waiting for frontend to start..."
for i in {1..20}; do
    if curl -s http://localhost:5173/ > /dev/null 2>&1; then
        echo "   ✅ Frontend is ready!"
        break
    fi
    sleep 1
done

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                    🎉 ALL SYSTEMS GO! 🎉                   ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "📍 Backend API:     http://localhost:8000"
echo "📚 API Docs:        http://localhost:8000/docs"
echo "🌐 Frontend:        http://localhost:5173"
echo ""
echo "🔧 Logs:"
echo "   Backend:  tail -f /tmp/module5-backend.log"
echo "   Frontend: tail -f /tmp/module5-frontend.log"
echo ""
echo "Press Ctrl+C to stop all servers"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
