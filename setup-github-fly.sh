#!/bin/bash

# 🚀 Setup GitHub Actions + Fly.io per Solanagram
# Configura il repository per deploy automatico

set -e

echo "🚀 Setup GitHub Actions + Fly.io"
echo "================================"

# Colori
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}📋 Step 1: Estrazione configurazioni forwarder...${NC}"

# Estrai configurazioni da container attivi
FORWARDERS=(
    "solanagram-fwd-35-biz_trading_bot_sol-to--1002866779186:sol"
    "solanagram-fwd-35-biz_trading_bot_bsc-to--4801713910:bsc"
    "solanagram-fwd-35-biz_trading_bot_base-to--4954731463:base"
    "solanagram-fwd-34-test1-to-myjarvis17bot:test1"
)

mkdir -p configs

for forwarder in "${FORWARDERS[@]}"; do
    IFS=':' read -r container_name forwarder_id <<< "$forwarder"
    
    echo -e "${YELLOW}📦 Estraendo ${forwarder_id}...${NC}"
    
    # Estrai config.json
    docker cp $container_name:/app/configs/config.json ./configs/forwarder-${forwarder_id}-config.json
    
    # Estrai session file se esiste
    if docker exec $container_name test -f /app/configs/session.session; then
        docker cp $container_name:/app/configs/session.session ./configs/forwarder-${forwarder_id}-session.session
        echo -e "${GREEN}✅ Session file estratto per ${forwarder_id}${NC}"
    else
        echo -e "${YELLOW}⚠️  Nessun session file per ${forwarder_id}${NC}"
    fi
done

echo -e "${GREEN}✅ Configurazioni estratte${NC}"

echo -e "${BLUE}📋 Step 2: Creazione token Fly.io...${NC}"

# Genera token deploy
echo -e "${YELLOW}🔑 Generazione token Fly.io...${NC}"
echo -e "${BLUE}Esegui questo comando e copia il token:${NC}"
echo "fly tokens create deploy -x 999999h"
echo ""
echo -e "${YELLOW}⚠️  IMPORTANTE: Copia tutto il token incluso 'FlyV1'${NC}"
echo ""

echo -e "${BLUE}📋 Step 3: Setup GitHub Secrets...${NC}"
echo -e "${YELLOW}Vai su GitHub > Repository > Settings > Secrets and variables > Actions${NC}"
echo -e "${BLUE}Aggiungi questi secrets:${NC}"
echo ""
echo -e "${GREEN}FLY_API_TOKEN${NC} = [token generato sopra]"
echo -e "${GREEN}TELEGRAM_PHONE${NC} = +393662844242"
echo -e "${GREEN}TELEGRAM_API_ID${NC} = 25128314"
echo -e "${GREEN}TELEGRAM_API_HASH${NC} = 2d44d2d06e412599b94be16f55773241"
echo ""

echo -e "${BLUE}📋 Step 4: Commit e Push...${NC}"
echo -e "${YELLOW}Ora committa e pusha i file:${NC}"
echo ""
echo "git add ."
echo "git commit -m 'Add Fly.io deployment with GitHub Actions'"
echo "git push origin main"
echo ""

echo -e "${GREEN}🎉 Setup completato!${NC}"
echo ""
echo -e "${BLUE}📊 Cosa succederà:${NC}"
echo "  • Ogni push su main triggererà il deploy automatico"
echo "  • 4 forwarder verranno deployati su Fly.io"
echo "  • URL: https://solanagram-fwd-*.fly.dev"
echo ""
echo -e "${BLUE}🔧 Monitoraggio:${NC}"
echo "  • GitHub Actions: https://github.com/[user]/[repo]/actions"
echo "  • Fly.io Dashboard: https://fly.io/apps/"
echo ""
echo -e "${YELLOW}⚠️  Prossimi step:${NC}"
echo "  1. Esegui il comando per generare il token"
echo "  2. Aggiungi i secrets su GitHub"
echo "  3. Fai push del codice"
echo "  4. Monitora il deploy su GitHub Actions" 