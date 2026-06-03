#!/bin/bash
# Module 5 Backend Startup Script

echo "════════════════════════════════════════════════════════════"
echo "  Module 5 — Road Damage Heatmap Dashboard (Backend)"
echo "════════════════════════════════════════════════════════════"
echo ""

# Navigate to backend directory
cd "$(dirname "$0")"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "⚙️  Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
pip install -q -r requirements.txt --break-system-packages

echo ""
echo "✅ Backend ready!"
echo ""
echo "🚀 Starting FastAPI server..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   📍 API: http://localhost:8000"
echo "   📚 Swagger Docs: http://localhost:8000/docs"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start server
python main.py
