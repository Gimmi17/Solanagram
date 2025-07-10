# 🤖 N8N Integration con Solanagram

Questa directory contiene workflow N8N per automatizzare l'elaborazione dei messaggi Telegram del sistema Solanagram.

## 🚀 Avvio Rapido

### 1. Avvia Solanagram
```bash
docker-compose up -d
```

### 2. Avvia N8N
```bash
docker-compose -f docker-compose.n8n.yml up -d
```

### 3. Accedi a N8N
- **URL**: http://localhost:5679
- **Username**: admin
- **Password**: solanagram123

## 📊 Database Accessibile

N8N può accedere direttamente al database Solanagram PostgreSQL:

### Configurazione Database N8N:
- **Host**: solanagram-db
- **Port**: 5432
- **Database**: solanagram_db
- **Username**: solanagram_user
- **Password**: solanagram_password

### Tabelle Principali Disponibili:

#### 📝 `saved_messages` - Messaggi Raw
```sql
SELECT * FROM saved_messages 
WHERE saved_at > NOW() - INTERVAL '1 hour'
ORDER BY saved_at DESC;
```

#### 📊 `message_logs` - Log Completi
```sql
SELECT 
    chat_title,
    sender_name,
    message_text,
    message_date,
    message_type
FROM message_logs 
WHERE message_date > NOW() - INTERVAL '24 hours'
ORDER BY message_date DESC;
```

#### 🔍 `elaboration_extracted_values` - Valori Estratti
```sql
SELECT 
    rule_name,
    extracted_value,
    extracted_at
FROM elaboration_extracted_values 
WHERE extracted_at > NOW() - INTERVAL '1 hour'
ORDER BY extracted_at DESC;
```

## 🔧 Esempi di Workflow

### 1. **Monitor Nuovi Messaggi**
- **Trigger**: Polling ogni 30 secondi
- **Query**: `SELECT * FROM saved_messages WHERE saved_at > NOW() - INTERVAL '1 minute'`
- **Azione**: Invia notifica / Webhook / Email

### 2. **Elaborazione Crypto Addresses**
- **Trigger**: Nuovi valori in `elaboration_extracted_values`
- **Filtro**: `rule_name = 'crypto_address'`
- **Azione**: Verifica validità address / Salva in Sheets / API esterna

### 3. **Alert Sistema**
- **Trigger**: Errori nel sistema
- **Query**: `SELECT * FROM message_elaborations WHERE error_count > 0`
- **Azione**: Notifica Telegram / Email / Slack

### 4. **Statistiche Giornaliere**
- **Trigger**: Cron (ogni mattina)
- **Query**: Genera report giornaliero
- **Azione**: Invia report via email

## 📱 Webhook per Trigger Immediati

Puoi configurare Solanagram per inviare webhook a N8N:

### Endpoint N8N Webhook:
```
http://localhost:5679/webhook/solanagram-trigger
```

### Payload Esempio:
```json
{
  "event": "new_message",
  "data": {
    "message_id": 123,
    "chat_title": "Crypto Signals",
    "sender_name": "John Doe",
    "message_text": "BTC address: 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
    "extracted_values": ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"]
  }
}
```

## 🎯 Casi d'Uso Comuni

### 1. **Crypto Address Monitoring**
- Monitor messaggi per indirizzi crypto
- Verifica validità tramite API blockchain
- Invio alert su nuovi address sospetti

### 2. **Message Analytics**
- Analisi sentiment messaggi
- Statistiche per chat
- Identificazione trend

### 3. **Automated Responses**
- Risposte automatiche a keywords
- Forward condizionali
- Moderazione automatica

### 4. **External Integrations**
- Google Sheets per logging
- Slack/Discord notifications
- Email alerts
- Database esterni

## 🛠️ Nodi Utili per Solanagram

### Database Nodes:
- **Postgres**: Query dirette al database
- **HTTP Request**: API calls al backend Solanagram

### Trigger Nodes:
- **Cron**: Operazioni schedulate
- **Webhook**: Trigger immediati da Solanagram
- **Polling**: Monitor database changes

### Action Nodes:
- **Telegram**: Invio messaggi
- **Email**: Notifiche
- **Sheets**: Logging dati
- **HTTP Request**: API esterne

## 🔐 Sicurezza

### Accesso Database:
- N8N accede con user dedicato
- Permessi read-only raccomandati per sicurezza
- Monitor accessi via Adminer (porta 8083)

### Network:
- N8N condivide la rete Docker di Solanagram
- Comunicazione sicura interna
- Accesso esterno solo su porte necessarie

## 📈 Performance

### Best Practices:
- Usa indici database per query veloci
- Limita polling frequency (max ogni 30s)
- Batch operations per grandi dataset
- Monitor memory usage N8N

### Ottimizzazioni:
- Query con LIMIT per grandi tabelle
- Usa WHERE con timestamp per filter
- Cache risultati quando possibile
- Async operations per API calls

## 🚨 Troubleshooting

### N8N non si connette al database:
```bash
# Verifica network Docker
docker network ls | grep solanagram

# Check logs N8N
docker logs solanagram-n8n

# Test database connection
docker exec -it solanagram-db psql -U solanagram_user -d solanagram_db
```

### Performance lente:
- Controlla indici database
- Limita result set size
- Usa connection pooling
- Monitor Docker resources

## 📚 Risorse

- [N8N Documentation](https://docs.n8n.io/)
- [PostgreSQL N8N Node](https://docs.n8n.io/integrations/builtin/app-nodes/n8n-nodes-base.postgres/)
- [Webhook Triggers](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.webhook/)
- [Cron Triggers](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.cron/) 