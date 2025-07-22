#!/bin/bash

# 🚀 Script di Deploy Forwarder su Fly.io
# Migra tutti i container forwarder attivi su Fly.io

set -e

echo "🚀 Migrazione Forwarder su Fly.io"
echo "=================================="

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funzione per estrarre configurazione da container
extract_forwarder_config() {
    local container_name=$1
    local forwarder_id=$2
    
    echo -e "${BLUE}📋 Estrazione configurazione da ${container_name}...${NC}"
    
    # Estrai env vars
    local env_vars=$(docker inspect $container_name --format='{{range .Config.Env}}{{println .}}{{end}}')
    
    # Estrai config.json
    docker cp $container_name:/app/configs/config.json ./configs/forwarder-${forwarder_id}-config.json
    
    # Estrai session file se esiste
    if docker exec $container_name test -f /app/configs/session.session; then
        docker cp $container_name:/app/configs/session.session ./configs/forwarder-${forwarder_id}-session.session
        echo -e "${GREEN}✅ Session file estratto${NC}"
    else
        echo -e "${YELLOW}⚠️  Nessun session file trovato${NC}"
    fi
    
    echo -e "${GREEN}✅ Configurazione estratta per ${forwarder_id}${NC}"
}

# Funzione per creare app Fly.io
create_fly_app() {
    local forwarder_id=$1
    local app_name="solanagram-fwd-${forwarder_id}"
    
    echo -e "${BLUE}🛠️  Creazione app Fly.io: ${app_name}${NC}"
    
    # Crea directory per l'app
    mkdir -p fly-apps/${app_name}
    cd fly-apps/${app_name}
    
    # Copia Dockerfile
    cp ../../Dockerfile.forwarder ./Dockerfile
    cp ../../forwarder.py ./
    cp ../../requirements.txt ./
    
    # Copia config
    cp ../../configs/forwarder-${forwarder_id}-config.json ./configs/config.json
    
    # Copia session se esiste
    if [ -f "../../configs/forwarder-${forwarder_id}-session.session" ]; then
        cp ../../configs/forwarder-${forwarder_id}-session.session ./configs/session.session
    fi
    
    # Crea fly.toml
    cat > fly.toml << EOF
app = "${app_name}"
kill_signal = "SIGINT"
kill_timeout = 5
processes = []

[env]
  CONFIG_FILE = "/app/configs/config.json"
  TELEGRAM_PHONE = "+393662844242"
  TELEGRAM_API_ID = "25128314"
  TELEGRAM_API_HASH = "2d44d2d06e412599b94be16f55773241"
  SESSION_FILE = "/app/configs/session.session"

[experimental]
  auto_rollback = true

[[services]]
  internal_port = 8080
  protocol = "tcp"

  [[services.ports]]
    handlers = ["http"]
    port = 80

  [[services.ports]]
    handlers = ["tls", "http"]
    port = 443

[[vm]]
  cpu_kind = "shared"
  cpus = 1
  memory_mb = 256
EOF

    echo -e "${GREEN}✅ App ${app_name} creata${NC}"
    cd ../..
}

# Funzione per deploy su Fly.io
deploy_fly_app() {
    local forwarder_id=$1
    local app_name="solanagram-fwd-${forwarder_id}"
    
    echo -e "${BLUE}🚀 Deploy ${app_name} su Fly.io...${NC}"
    
    cd fly-apps/${app_name}
    
    # Deploy
    fly deploy --remote-only
    
    echo -e "${GREEN}✅ ${app_name} deployato con successo!${NC}"
    echo -e "${BLUE}🌐 URL: https://${app_name}.fly.dev${NC}"
    
    cd ../..
}

# Lista container forwarder attivi
FORWARDERS=(
    "solanagram-fwd-35-biz_trading_bot_sol-to--1002866779186:sol"
    "solanagram-fwd-35-biz_trading_bot_bsc-to--4801713910:bsc"
    "solanagram-fwd-35-biz_trading_bot_base-to--4954731463:base"
    "solanagram-fwd-34-test1-to-myjarvis17bot:test1"
)

# Crea directory per le app Fly.io
mkdir -p fly-apps
mkdir -p configs

echo -e "${BLUE}📦 Preparazione deploy per ${#FORWARDERS[@]} forwarder...${NC}"

# Processa ogni forwarder
for forwarder in "${FORWARDERS[@]}"; do
    IFS=':' read -r container_name forwarder_id <<< "$forwarder"
    
    echo -e "${YELLOW}🔄 Processando ${forwarder_id}...${NC}"
    
    # Estrai configurazione
    extract_forwarder_config $container_name $forwarder_id
    
    # Crea app Fly.io
    create_fly_app $forwarder_id
    
    # Deploy
    deploy_fly_app $forwarder_id
    
    echo -e "${GREEN}✅ ${forwarder_id} completato!${NC}"
    echo ""
done

echo -e "${GREEN}🎉 Migrazione completata!${NC}"
echo ""
echo -e "${BLUE}📊 Riepilogo:${NC}"
echo "  • ${#FORWARDERS[@]} forwarder migrati"
echo "  • App Fly.io create in directory fly-apps/"
echo "  • Configurazioni salvate in configs/"
echo ""
echo -e "${BLUE}🔧 Prossimi step:${NC}"
echo "  1. Verifica che tutti i forwarder siano attivi su Fly.io"
echo "  2. Controlla i log: fly logs -a solanagram-fwd-*"
echo "  3. Monitora le performance"
echo "  4. Rimuovi i container locali quando tutto funziona"
echo ""
echo -e "${YELLOW}⚠️  Importante:${NC}"
echo "  • I forwarder su Fly.io sono sempre-on (no sleep)"
echo "  • Usano il free tier di Fly.io (256MB RAM, 1 vCPU)"
echo "  • Ogni forwarder ha il suo dominio .fly.dev" 