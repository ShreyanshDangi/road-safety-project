#!/bin/bash
# Quick verification that all files are in place

echo "Module 5 Setup Verification"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

ERRORS=0

# Check backend files
echo "📦 Backend files:"
[ -f "backend/main.py" ] && echo "  ✅ main.py" || { echo "  ❌ main.py MISSING"; ERRORS=$((ERRORS+1)); }
[ -f "backend/requirements.txt" ] && echo "  ✅ requirements.txt" || { echo "  ❌ requirements.txt MISSING"; ERRORS=$((ERRORS+1)); }
[ -f "backend/start.sh" ] && echo "  ✅ start.sh" || { echo "  ❌ start.sh MISSING"; ERRORS=$((ERRORS+1)); }

echo ""
echo "📦 Frontend files:"
[ -f "frontend/index.html" ] && echo "  ✅ index.html" || { echo "  ❌ index.html MISSING"; ERRORS=$((ERRORS+1)); }
[ -f "frontend/vite.config.js" ] && echo "  ✅ vite.config.js" || { echo "  ❌ vite.config.js MISSING"; ERRORS=$((ERRORS+1)); }
[ -f "frontend/tailwind.config.js" ] && echo "  ✅ tailwind.config.js" || { echo "  ❌ tailwind.config.js MISSING"; ERRORS=$((ERRORS+1)); }
[ -f "frontend/postcss.config.js" ] && echo "  ✅ postcss.config.js" || { echo "  ❌ postcss.config.js MISSING"; ERRORS=$((ERRORS+1)); }
[ -f "frontend/package.json" ] && echo "  ✅ package.json" || { echo "  ❌ package.json MISSING"; ERRORS=$((ERRORS+1)); }
[ -f "frontend/src/App.jsx" ] && echo "  ✅ src/App.jsx" || { echo "  ❌ src/App.jsx MISSING"; ERRORS=$((ERRORS+1)); }
[ -f "frontend/src/main.jsx" ] && echo "  ✅ src/main.jsx" || { echo "  ❌ src/main.jsx MISSING"; ERRORS=$((ERRORS+1)); }
[ -f "frontend/src/index.css" ] && echo "  ✅ src/index.css" || { echo "  ❌ src/index.css MISSING"; ERRORS=$((ERRORS+1)); }
[ -f "frontend/start.sh" ] && echo "  ✅ start.sh" || { echo "  ❌ start.sh MISSING"; ERRORS=$((ERRORS+1)); }

echo ""
echo "📚 Documentation:"
[ -f "README.md" ] && echo "  ✅ README.md" || { echo "  ❌ README.md MISSING"; ERRORS=$((ERRORS+1)); }
[ -f "COMPLETE_SETUP_GUIDE.md" ] && echo "  ✅ COMPLETE_SETUP_GUIDE.md" || { echo "  ❌ COMPLETE_SETUP_GUIDE.md MISSING"; ERRORS=$((ERRORS+1)); }

echo ""
echo "🚀 Startup scripts:"
[ -f "start-all.sh" ] && echo "  ✅ start-all.sh" || { echo "  ❌ start-all.sh MISSING"; ERRORS=$((ERRORS+1)); }
[ -x "start-all.sh" ] && echo "  ✅ start-all.sh is executable" || { echo "  ⚠️  start-all.sh not executable (run: chmod +x start-all.sh)"; }
[ -x "backend/start.sh" ] && echo "  ✅ backend/start.sh is executable" || { echo "  ⚠️  backend/start.sh not executable"; }
[ -x "frontend/start.sh" ] && echo "  ✅ frontend/start.sh is executable" || { echo "  ⚠️  frontend/start.sh not executable"; }

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ $ERRORS -eq 0 ]; then
    echo "✅ All files present! You're ready to run."
    echo ""
    echo "Next steps:"
    echo "  1. Run: ./start-all.sh"
    echo "  2. Open: http://localhost:5173"
    echo "  3. Or run backend and frontend separately (see COMPLETE_SETUP_GUIDE.md)"
else
    echo "❌ $ERRORS file(s) missing. Check the errors above."
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
