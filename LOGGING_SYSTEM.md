# 📝 Sistema di Logging Messaggi Telegram

## Panoramica

Il sistema di logging sostituisce il precedente sistema di inoltri con una funzionalità di logging completo dei messaggi Telegram. Invece di inoltrare i messaggi, il sistema ora li salva nel database con un progressivo univoco e timestamp.

## 🎯 Funzionalità Principali

### ✅ Caratteristiche Implementate

- **Sostituzione del menu "Le mie Chat"** con **"Logging Messaggi"**
- **Sostituzione del bottone "Vedi inoltri"** con **"Metti sotto log"**
- **Container Docker dedicati** per ogni sessione di logging
- **Salvataggio completo** di tutti i messaggi nel database
- **Progressivo univoco** per ogni messaggio nell'intero database
- **Timestamp** di quando il messaggio è arrivato
- **Un solo log attivo** per chat (gruppi, persone, bot)
- **Interfaccia web** per gestire le sessioni di logging
- **Visualizzazione dei log** con paginazione
- **Pagina di backup** per le vecchie funzionalità chat

### 🔧 Componenti del Sistema

1. **Database Schema** (`database/add_logging_table.sql`)
   - `message_logs`: Tabella principale per i messaggi loggati
   - `logging_sessions`: Gestione delle sessioni di logging attive

2. **Backend API** (`backend/app.py`)
   - Endpoints per gestire le sessioni di logging
   - Gestione dei container Docker
   - API per visualizzare i messaggi loggati

3. **Frontend** (`frontend/app.py`)
   - Interfaccia per attivare/disattivare il logging
   - Pagina di visualizzazione dei log
   - Gestione dello stato dei bottoni

4. **Container Logger** (`logger.py`)
   - Container Docker dedicato per ogni chat
   - Connessione Telegram e ascolto messaggi
   - Salvataggio automatico nel database

5. **Manager** (`backend/logging_manager.py`)
   - Gestione dei container Docker
   - Controllo delle risorse
   - Lifecycle dei container

## 🚀 Installazione e Setup

### 1. Applicare la Migrazione Database

```bash
# Avvia i servizi base
docker-compose up -d solanagram-db

# Applica la migrazione
./scripts/apply_logging_migration.sh
```

### 2. Build dell'Immagine Logger

```bash
# Build dell'immagine logger
docker-compose --profile build-only up solanagram-logger-builder
```

### 3. Avvio Completo

```bash
# Avvia tutti i servizi
docker-compose up -d
```

## 📊 Struttura Database

### Tabella `message_logs`

```sql
CREATE TABLE message_logs (
    id SERIAL PRIMARY KEY,                    -- Progressivo univoco
    user_id INTEGER NOT NULL,                 -- ID utente proprietario
    chat_id BIGINT NOT NULL,                  -- ID chat Telegram
    chat_title VARCHAR(255),                  -- Nome della chat
    chat_username VARCHAR(255),               -- Username della chat
    chat_type VARCHAR(50),                    -- Tipo: private/group/supergroup/channel
    message_id BIGINT NOT NULL,               -- ID messaggio Telegram
    sender_id BIGINT,                         -- ID mittente
    sender_name VARCHAR(255),                 -- Nome mittente
    sender_username VARCHAR(255),             -- Username mittente
    message_text TEXT,                        -- Testo del messaggio
    message_type VARCHAR(50),                 -- Tipo: text/photo/video/document/sticker/voice/audio
    media_file_id VARCHAR(255),               -- ID file media (se presente)
    message_date TIMESTAMP WITH TIME ZONE,    -- Data messaggio Telegram
    logged_at TIMESTAMP WITH TIME ZONE,       -- Data salvataggio nel database
    logging_session_id INTEGER NOT NULL       -- ID sessione di logging
);
```

### Tabella `logging_sessions`

```sql
CREATE TABLE logging_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,                 -- ID utente proprietario
    chat_id BIGINT NOT NULL,                  -- ID chat Telegram
    chat_title VARCHAR(255),                  -- Nome della chat
    chat_username VARCHAR(255),               -- Username della chat
    chat_type VARCHAR(50),                    -- Tipo chat
    is_active BOOLEAN DEFAULT TRUE,           -- Stato sessione
    container_name VARCHAR(255),              -- Nome container Docker
    container_id VARCHAR(64),                 -- ID container Docker
    container_status VARCHAR(50),             -- Stato container
    messages_logged INTEGER DEFAULT 0,        -- Contatore messaggi
    errors_count INTEGER DEFAULT 0,           -- Contatore errori
    last_error TEXT,                          -- Ultimo errore
    last_error_at TIMESTAMP WITH TIME ZONE,   -- Data ultimo errore
    created_at TIMESTAMP WITH TIME ZONE,      -- Data creazione
    updated_at TIMESTAMP WITH TIME ZONE,      -- Data ultimo aggiornamento
    last_message_at TIMESTAMP WITH TIME ZONE  -- Data ultimo messaggio
);
```

## 🔌 API Endpoints

### Gestione Sessioni

- `GET /api/logging/sessions` - Lista sessioni di logging
- `POST /api/logging/sessions` - Crea nuova sessione
- `POST /api/logging/sessions/{id}/stop` - Ferma sessione
- `DELETE /api/logging/sessions/{id}` - Elimina sessione

### Visualizzazione Log

- `GET /api/logging/messages/{session_id}` - Messaggi di una sessione
- `GET /api/logging/chat/{chat_id}/status` - Stato logging per chat

## 🎮 Utilizzo

### 1. Attivare il Logging

1. Vai alla pagina **"Le mie Chat"**
2. Trova la chat desiderata
3. Clicca **"📝 Metti sotto log"**
4. Conferma l'operazione

### 2. Visualizzare i Log

1. Nella pagina chat, clicca **"📋 Vedi Log"**
2. Oppure vai direttamente a `/message-logs/{session_id}`

### 3. Fermare il Logging

1. Nella pagina chat, clicca **"⏹️ Ferma Logging"**
2. Conferma l'operazione

### 4. Accesso alle Vecchie Funzionalità

1. Nella pagina principale "Logging Messaggi", clicca il link **"Accedi alle vecchie funzionalità chat"**
2. Oppure vai direttamente a `/chats-backup`
3. Questa pagina contiene le vecchie funzionalità per copiare ID e gestire inoltri

## 🔍 Monitoraggio

### Container Status

```bash
# Lista container di logging attivi
docker ps --filter "label=solanagram.type=logger"

# Logs di un container specifico
docker logs <container_name>

# Statistiche risorse
docker stats <container_name>
```

### Database Queries Utili

```sql
-- Sessioni attive
SELECT * FROM active_logging_sessions;

-- Statistiche per chat
SELECT * FROM chat_logging_stats;

-- Ultimi messaggi loggati
SELECT * FROM message_logs 
ORDER BY logged_at DESC 
LIMIT 10;

-- Messaggi per sessione
SELECT COUNT(*) as total_messages 
FROM message_logs 
WHERE logging_session_id = <session_id>;
```

## 🛠️ Manutenzione

### Cleanup Automatico

Il sistema include funzioni di cleanup automatico:

```sql
-- Cleanup sessioni orfane
SELECT cleanup_orphaned_logging_sessions();
```

### Backup Logs

```bash
# Export messaggi loggati
docker exec solanagram-db pg_dump -U solanagram_user -t message_logs solanagram_db > logs_backup.sql
```

## 🔒 Sicurezza

- **Un solo log attivo** per chat per utente
- **Isolamento container** per ogni sessione
- **Controllo accessi** basato su user_id
- **Limiti risorse** per container (128MB RAM, 0.25 CPU)

## 🐛 Troubleshooting

### Problemi Comuni

1. **Container non si avvia**
   - Controlla i log: `docker logs <container_name>`
   - Verifica le credenziali Telegram
   - Controlla la connessione database

2. **Messaggi non vengono loggati**
   - Verifica che il container sia in esecuzione
   - Controlla i permessi Telegram
   - Verifica la connessione al database

3. **Errore "Già esiste una sessione attiva"**
   - Ferma la sessione esistente prima di crearne una nuova
   - Oppure elimina la sessione orfana dal database

### Log Files

```bash
# Log del container logger
docker logs <container_name>

# Log del backend
docker logs solanagram-backend

# Log del database
docker logs solanagram-db
```

## 📈 Metriche e Performance

### Limiti di Sistema

- **Memoria per container**: 128MB (max 256MB)
- **CPU per container**: 0.25 core (max 0.5)
- **Processi per container**: 50 max
- **Sessioni per utente**: Illimitate (con limiti risorse)

### Monitoraggio Performance

```sql
-- Utilizzo risorse per sessione
SELECT 
    ls.chat_title,
    ls.messages_logged,
    ls.errors_count,
    ls.created_at,
    ls.last_message_at
FROM logging_sessions ls
WHERE ls.is_active = true
ORDER BY ls.messages_logged DESC;
```

## 🔄 Migrazione da Sistema Precedente

### Menu e Navigazione

- **Menu principale**: "Le mie Chat" → **"Logging Messaggi"**
- **Icona menu**: Cambiata da chat bubble a documento con righe
- **Funzionalità**: Focus sul logging invece che sulla visualizzazione chat

### Pagina di Backup

- **URL**: `/chats-backup` (accessibile dalla pagina principale)
- **Funzionalità**: Mantiene tutte le vecchie funzionalità per sviluppi futuri
- **Scopo**: Permette di copiare ID chat e gestire inoltri se necessario

### Dati e Sistema

Il nuovo sistema è completamente indipendente dal sistema di inoltri precedente. Non è necessaria alcuna migrazione dei dati esistenti.

## 📝 Note di Sviluppo

- Il sistema utilizza **Telethon** per la connessione Telegram
- I container sono **isolati** e **leggeri**
- Il database supporta **concorrenza** per più utenti
- L'interfaccia è **responsive** e **user-friendly**

## 🎯 Roadmap Futura

- [ ] **Filtri avanzati** per i messaggi loggati
- [ ] **Export** dei log in vari formati
- [ ] **Analytics** sui messaggi loggati
- [ ] **Notifiche** per nuovi messaggi
- [ ] **Backup automatico** dei log
- [ ] **Ricerca full-text** nei messaggi