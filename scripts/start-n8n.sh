#!/bin/bash

# 🤖 Solanagram N8N Integration Starter
# Questo script avvia N8N integrato con Solanagram

set -e

echo "🚀 Starting Solanagram N8N Integration..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

# Check if Solanagram is running
echo -e "${BLUE}🔍 Checking Solanagram status...${NC}"
if ! docker ps | grep -q "solanagram-"; then
    echo -e "${YELLOW}⚠️  Solanagram is not running. Starting Solanagram first...${NC}"
    docker-compose up -d
    echo -e "${GREEN}✅ Solanagram started${NC}"
    
    # Wait for services to be healthy
    echo -e "${BLUE}⏳ Waiting for Solanagram services to be healthy...${NC}"
    sleep 10
else
    echo -e "${GREEN}✅ Solanagram is already running${NC}"
fi

# Create directories if they don't exist
echo -e "${BLUE}📁 Creating N8N directories...${NC}"
mkdir -p n8n-workflows
mkdir -p n8n-nodes

# Apply database migrations if needed
echo -e "${BLUE}🗄️ Applying database migrations...${NC}"
if [ -f "database/migrations/004_add_crypto_alerts_table.sql" ]; then
    docker exec -i solanagram-db psql -U solanagram_user -d solanagram_db < database/migrations/004_add_crypto_alerts_table.sql || echo "Migration already applied or failed"
fi

# Start N8N
echo -e "${BLUE}🤖 Starting N8N...${NC}"
docker-compose -f docker-compose.n8n.yml up -d

# Wait for N8N to be ready
echo -e "${BLUE}⏳ Waiting for N8N to be ready...${NC}"
sleep 15

# Check N8N health
if curl -f http://localhost:5679/healthz > /dev/null 2>&1; then
    echo -e "${GREEN}✅ N8N is running successfully!${NC}"
else
    echo -e "${YELLOW}⚠️  N8N might still be starting up...${NC}"
fi

# Show status
echo ""
echo -e "${GREEN}🎉 Solanagram N8N Integration is ready!${NC}"
echo ""
echo -e "${BLUE}📊 Access Points:${NC}"
echo -e "   • N8N Dashboard:           ${GREEN}http://localhost:5679${NC}"
echo -e "   • Username:                ${GREEN}admin${NC}"
echo -e "   • Password:                ${GREEN}solanagram123${NC}"
echo -e "   • Solanagram Frontend:     ${GREEN}http://localhost:8082${NC}"
echo -e "   • Database Admin:          ${GREEN}http://localhost:8081${NC}"
echo -e "   • N8N Database Admin:      ${GREEN}http://localhost:8083${NC}"
echo ""
echo -e "${BLUE}📊 Database Connection for N8N:${NC}"
echo -e "   • Host:                    ${GREEN}solanagram-db${NC}"
echo -e "   • Port:                    ${GREEN}5432${NC}"
echo -e "   • Database:                ${GREEN}solanagram_db${NC}"
echo -e "   • Username:                ${GREEN}solanagram_user${NC}"
echo -e "   • Password:                ${GREEN}solanagram_password${NC}"
echo ""
echo -e "${BLUE}📝 Available Tables for N8N:${NC}"
echo -e "   • saved_messages           ${YELLOW}(Raw messages from listeners)${NC}"
echo -e "   • message_logs             ${YELLOW}(Complete message logs)${NC}"
echo -e "   • elaboration_extracted_values ${YELLOW}(Extracted crypto addresses)${NC}"
echo -e "   • crypto_alerts            ${YELLOW}(N8N generated alerts)${NC}"
echo -e "   • message_listeners        ${YELLOW}(Active listeners config)${NC}"
echo ""
echo -e "${BLUE}🔧 Example Workflows:${NC}"
echo -e "   • Import crypto-address-monitor.json from n8n-workflows/ directory"
echo -e "   • Check README.md in n8n-workflows/ for more examples"
echo ""
echo -e "${BLUE}⚠️  Remember to:${NC}"
echo -e "   • Configure Telegram Bot credentials in N8N for alerts"
echo -e "   • Set your Telegram Chat ID in workflows"
echo -e "   • Import example workflows from n8n-workflows/ directory"
echo ""
echo -e "${BLUE}📚 View logs:${NC}"
echo -e "   • N8N logs:                ${GREEN}docker logs solanagram-n8n${NC}"
echo -e "   • Solanagram logs:         ${GREEN}docker logs solanagram-backend${NC}"
echo ""

# Show running containers
echo -e "${BLUE}🐳 Running containers:${NC}"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(solanagram|n8n)"

echo ""
echo -e "${GREEN}✨ Setup complete! Happy automating with N8N! ✨${NC}" 