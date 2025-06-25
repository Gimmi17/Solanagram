#!/bin/bash

# Script per aprire l'interfaccia web di Telegram Chat Manager

# Colori
BLUE='\033[0;34m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo -e "${BLUE}🌐 Telegram Chat Manager - Web Interface${NC}"
echo "=================================================="

# Controlla che i container siano in esecuzione
if ! docker ps | grep -q tcm-frontend-dev; then
    echo "❌ Frontend non in esecuzione"
    echo "💡 Avvia con: docker-compose up -d"
    exit 1
fi

if ! docker ps | grep -q tcm-backend-dev; then
    echo "❌ Backend non in esecuzione"
    echo "💡 Avvia con: docker-compose up -d"
    exit 1
fi

echo -e "${GREEN}✅ Sistema attivo e funzionante${NC}"
echo ""
echo "🔗 URL disponibili:"
echo "   👤 Frontend:  http://localhost:8082"
echo "   🔧 Backend:   http://localhost:5001"
echo "   🗄️  Database: http://localhost:8081 (Adminer)"
echo ""

# Apri automaticamente il browser (macOS)
if command -v open &> /dev/null; then
    echo "🌐 Apertura browser..."
    open http://localhost:8082
elif command -v xdg-open &> /dev/null; then
    echo "🌐 Apertura browser..."
    xdg-open http://localhost:8082
else
    echo "💡 Apri manualmente: http://localhost:8082"
fi 