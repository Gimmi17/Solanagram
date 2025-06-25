#!/bin/bash

# Script per elencare tutti gli utenti registrati
# Usage: ./list_users.sh

set -e

# Colori per l'output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}👥 Lista utenti registrati nel sistema${NC}"
echo "=================================================="

# Verifica che il container del database sia in esecuzione
if ! docker ps | grep -q solanagram-db; then
    echo -e "${RED}❌ Il container del database non è in esecuzione${NC}"
    echo -e "${YELLOW}💡 Avvia il sistema con: docker-compose up -d${NC}"
    exit 1
fi

# Recupera la lista degli utenti
docker exec solanagram-db psql -U solanagram_user -d solanagram_db -c "
    SELECT 
        id,
        api_id,
        CASE 
            WHEN api_hash IS NOT NULL THEN CONCAT(LEFT(api_hash, 10), '...')
            ELSE 'NULL'
        END as api_hash_short,
        CASE 
            WHEN telegram_session IS NOT NULL THEN 'SÌ'
            ELSE 'NO'
        END as has_session,
        created_at::date as created,
        CASE 
            WHEN last_login IS NOT NULL THEN last_login::date
            ELSE NULL
        END as last_login,
        landing
    FROM users 
    ORDER BY id;
"

echo
echo -e "${YELLOW}💡 Per aggiornare le credenziali di un utente:${NC}"
echo "   ./update_credentials.sh <phone_number> <new_api_id> <new_api_hash>"
echo
echo -e "${YELLOW}💡 Per aggiornare via API REST:${NC}"
echo "   PUT /api/auth/update-credentials (richiede autenticazione)" 