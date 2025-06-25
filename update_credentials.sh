#!/bin/bash

# Script per aggiornare le credenziali API Telegram di un utente
# Usage: ./update_credentials.sh <phone_number> <new_api_id> <new_api_hash>

set -e

# Colori per l'output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funzione per hash del numero di telefono (simulazione di SHA256)
hash_phone_number() {
    echo -n "$1" | shasum -a 256 | cut -d' ' -f1
}

# Controllo parametri
if [ $# -ne 3 ]; then
    echo -e "${RED}❌ Uso: ./update_credentials.sh <phone_number> <new_api_id> <new_api_hash>${NC}"
    echo -e "${BLUE}📞 Esempio: ./update_credentials.sh +393485373976 12345678 abcd1234...${NC}"
    exit 1
fi

PHONE_NUMBER="$1"
NEW_API_ID="$2"
NEW_API_HASH="$3"

# Validazione API_ID (deve essere numerico)
if ! [[ "$NEW_API_ID" =~ ^[0-9]+$ ]]; then
    echo -e "${RED}❌ API_ID deve essere un numero intero${NC}"
    exit 1
fi

# Validazione API_HASH (non vuoto)
if [ -z "$NEW_API_HASH" ]; then
    echo -e "${RED}❌ API_HASH non può essere vuoto${NC}"
    exit 1
fi

# Hash del numero di telefono
PHONE_HASH=$(hash_phone_number "$PHONE_NUMBER")

echo -e "${BLUE}🔄 Aggiornamento credenziali per $PHONE_NUMBER${NC}"
echo -e "${BLUE}📊 Nuovo API_ID: $NEW_API_ID${NC}"
echo -e "${BLUE}🔑 Nuovo API_HASH: ${NEW_API_HASH:0:10}...${NC}"
echo

# Richiesta conferma
read -p "✋ Continuare? (s/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[SsYy]$ ]]; then
    echo -e "${RED}❌ Operazione annullata${NC}"
    exit 0
fi

# Verifica che il container del database sia in esecuzione
if ! docker ps | grep -q solanagram-db; then
    echo -e "${RED}❌ Il container del database non è in esecuzione${NC}"
    echo -e "${YELLOW}💡 Avvia il sistema con: docker-compose up -d${NC}"
    exit 1
fi

# Cerca l'utente esistente
echo -e "${BLUE}🔍 Ricerca utente...${NC}"
USER_INFO=$(docker exec solanagram-db psql -U solanagram_user -d solanagram_db -t -A -c "
    SELECT id, api_id 
    FROM users 
    WHERE phone_number = '$PHONE_HASH';
")

if [ -z "$USER_INFO" ]; then
    echo -e "${RED}❌ Utente con numero $PHONE_NUMBER non trovato${NC}"
    exit 1
fi

USER_ID=$(echo "$USER_INFO" | cut -d'|' -f1)
CURRENT_API_ID=$(echo "$USER_INFO" | cut -d'|' -f2)

echo -e "${GREEN}📱 Utente trovato (ID: $USER_ID, API_ID attuale: $CURRENT_API_ID)${NC}"

# Aggiorna le credenziali
echo -e "${BLUE}🔄 Aggiornamento in corso...${NC}"
docker exec solanagram-db psql -U solanagram_user -d solanagram_db -c "
    UPDATE users 
    SET api_id = $NEW_API_ID, api_hash = '$NEW_API_HASH', telegram_session = NULL
    WHERE phone_number = '$PHONE_HASH';
"

if [ $? -eq 0 ]; then
    echo
    echo -e "${GREEN}✅ Credenziali aggiornate con successo!${NC}"
    echo -e "${GREEN}   📊 Nuovo API_ID: $NEW_API_ID${NC}"
    echo -e "${GREEN}   🔑 Nuovo API_HASH: ${NEW_API_HASH:0:10}...${NC}"
    echo -e "${GREEN}   🔄 Sessione Telegram resettata${NC}"
    echo
    echo -e "${YELLOW}💡 L'utente dovrà rifare il login per usare le nuove credenziali${NC}"
else
    echo -e "${RED}❌ Errore durante l'aggiornamento${NC}"
    exit 1
fi 