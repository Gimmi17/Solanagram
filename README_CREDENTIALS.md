# 🔑 Gestione Credenziali API Telegram

Questo documento spiega come aggiornare le credenziali API di Telegram per gli utenti del sistema.

## 🚨 Problema: API_ID_INVALID

Se ricevi l'errore `API_ID_INVALID`, significa che le credenziali API di Telegram non sono più valide. Questo può succedere per:

- ✅ **Credenziali scadute** o revocate
- ✅ **Limite di utilizzo** raggiunto 
- ✅ **App Telegram disabilitata** su my.telegram.org
- ✅ **Credenziali per test server** invece che produzione

## 🛠️ Come Ottenere Nuove Credenziali

1. **Vai su** https://my.telegram.org/apps
2. **Fai login** con il tuo account Telegram
3. **Crea una nuova app** o verifica quella esistente
4. **Copia** `api_id` e `api_hash`

## 🔧 Metodi per Aggiornare le Credenziali

### 1. 🌐 Via API REST (Utente Autenticato)

```bash
# 1. Fai login per ottenere un token
curl -X POST http://localhost:5001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+393485373976"}'

# 2. Verifica il codice mock (12345 o 94761)
curl -X POST http://localhost:5001/api/auth/verify-code \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+393485373976", "code": "12345"}'

# 3. Aggiorna le credenziali con il token ottenuto
curl -X PUT http://localhost:5001/api/auth/update-credentials \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TUO_SESSION_TOKEN" \
  -d '{"api_id": "12345678", "api_hash": "nuova_api_hash"}'
```

### 2. 🖥️ Via Script CLI (Amministratore)

```bash
# Aggiorna credenziali direttamente nel database
./update_credentials.sh +393485373976 12345678 nuova_api_hash_qui

# Lista tutti gli utenti
./list_users.sh
```

### 3. 🗄️ Via Database Diretto

```sql
-- Connetti al database
docker exec -it solanagram-db psql -U solanagram_user -d solanagram_db

-- Aggiorna manualmente
UPDATE users 
SET api_id = 12345678, 
    api_hash = 'nuova_api_hash_qui', 
    telegram_session = NULL 
WHERE phone_number = 'hash_del_telefono';
```

## 📝 Script Disponibili

| Script | Descrizione | Uso |
|--------|-------------|-----|
| `update_credentials.sh` | Aggiorna credenziali utente | `./update_credentials.sh <phone> <api_id> <api_hash>` |
| `list_users.sh` | Lista tutti gli utenti | `./list_users.sh` |
| `update_credentials.py` | Versione Python (richiede psycopg2) | `python3 update_credentials.py <phone> <api_id> <api_hash>` |

## 🔍 Come Trovare un Utente per Telefono

Se non conosci l'hash del numero di telefono:

```bash
# Calcola l'hash manualmente
echo -n "+393485373976" | shasum -a 256

# O cerca nell'interfaccia admin
./list_users.sh
```

## ✅ Dopo l'Aggiornamento

1. **L'utente deve rifare il login** per usare le nuove credenziali
2. **La sessione Telegram precedente viene invalidata**
3. **Verifica** che `PYROGRAM_AVAILABLE = True` in `backend/app.py`

## 🚀 Riattivazione Pyrogram

Dopo aver aggiornato le credenziali, riattiva Pyrogram:

```python
# In backend/app.py, cambia:
PYROGRAM_AVAILABLE = False  # Da questo
PYROGRAM_AVAILABLE = True   # A questo
```

Poi riavvia il backend:
```bash
docker restart tcm-backend-dev
```

## 🐛 Debug

Per verificare che tutto funzioni:

```bash
# Controlla lo stato di Pyrogram
curl http://localhost:5001/api/telegram/check

# Testa una nuova registrazione/login
curl -X POST http://localhost:5001/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+393485373976",
    "api_id": "12345678", 
    "api_hash": "nuova_api_hash",
    "landing": "test"
  }'
```

## 📚 Risorse Utili

- **Telegram API Docs**: https://core.telegram.org/api
- **My Telegram Apps**: https://my.telegram.org/apps  
- **Pyrogram Docs**: https://docs.pyrogram.org
- **API Errors**: https://docs.pyrogram.org/api/errors 