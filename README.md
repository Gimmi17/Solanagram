# 🚀 Solanagram Trading Bot

Un bot Telegram modulare per il trading automatico di token Solana con dashboard web locale.

## 📋 Caratteristiche

- **Ascolta messaggi Telegram** da gruppi privati per segnali di trading
- **Parser intelligente** per estrarre segnali BUY/SELL da messaggi strutturati
- **Modalità dual-mode**: dry-run (simulazione) e live (trading reale)
- **Dashboard web locale** per monitoraggio e controllo
- **Persistenza dati** con SQLite per segnali, trade e configurazioni
- **Wallet Solana sicuro** con crittografia delle chiavi private
- **Filtri avanzati** per market cap, trade score, smart holders
- **Architettura modulare** per facile estensione

## 🏗️ Architettura

```
Solanagram/
├── config.py           # Gestione configurazione
├── parser.py            # Parser messaggi Telegram
├── state.py            # Persistenza dati (SQLite)
├── telegram_listener.py # Client Telegram (Telethon)
├── engine.py           # Logica decisionale e filtri
├── wallet.py           # Gestione wallet Solana
├── api.py              # API web (FastAPI)
├── main.py             # Entry point principale
├── requirements.txt     # Dipendenze Python
├── Dockerfile          # Container Docker
├── docker-compose.yml  # Orchestrazione
└── env.example         # Template variabili ambiente
```

## 🚀 Quick Start

### 1. Prerequisiti

- Docker e Docker Compose
- Account Telegram con API credentials
- Accesso a un gruppo Telegram privato (come admin)

### 2. Setup Telegram API

1. Vai su [my.telegram.org](https://my.telegram.org)
2. Accedi con il tuo numero di telefono
3. Crea una nuova applicazione
4. Annota `api_id` e `api_hash`

### 3. Configurazione

```bash
# Clona il repository
git clone <repository-url>
cd Solanagram

# Copia il template di configurazione
cp env.example .env

# Modifica .env con i tuoi dati
nano .env
```

**Configura `.env`:**
```env
# Telegram configuration
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_PHONE=your_phone_number
TELEGRAM_GROUP_ID=your_group_id

# Solana configuration
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
JUPITER_API_URL=https://quote-api.jup.ag/v6

# Bot configuration
MODE=dry-run
WEB_PORT=1717
API_TOKEN=your_secure_api_token

# Data persistence
DATA_DIR=/data
```

### 4. Prima autenticazione Telegram

**IMPORTANTE**: Devi autenticare Telegram interattivamente la prima volta.

```bash
# Autenticazione interattiva (fuori da Docker)
python -c "
from telegram_listener import TelegramListener
import asyncio
asyncio.run(TelegramListener().interactive_auth())
"
```

Inserisci il codice di verifica quando richiesto. Una volta autenticato, la sessione sarà salvata.

### 5. Deploy con Docker

```bash
# Crea la directory per i dati persistenti
mkdir -p ./data

# Copia la sessione Telegram autenticata
cp telegram_session.session ./data/

# Avvia il bot
docker-compose up -d

# Controlla i log
docker-compose logs -f
```

### 6. Accesso Dashboard

Apri [http://localhost:1717](http://localhost:1717) nel browser.

**Default API Token**: `default-token` (cambialo in produzione!)

## 🐳 Guida Docker Dettagliata

### Setup Completo con Docker

#### Passo 1: Preparazione Ambiente
```bash
# Clona il repository
git clone <repository-url>
cd Solanagram

# Verifica che Docker sia installato
docker --version
docker-compose --version
```

#### Passo 2: Configurazione
```bash
# Copia il template delle variabili d'ambiente
cp env.example .env

# Modifica il file .env con i tuoi dati
nano .env
```

**⚠️ IMPORTANTE**: Configura almeno queste variabili:
- `TELEGRAM_API_ID` - Ottenuto da my.telegram.org
- `TELEGRAM_API_HASH` - Ottenuto da my.telegram.org  
- `TELEGRAM_PHONE` - Il tuo numero con prefisso (+39...)
- `TELEGRAM_GROUP_ID` - ID del gruppo Telegram
- `API_TOKEN` - Cambia da "default-token" per sicurezza

#### Passo 3: Autenticazione Telegram (CRUCIALE)
```bash
# Installa le dipendenze Python localmente (solo per auth)
pip3 install telethon python-dotenv

# Esegui l'autenticazione interattiva
python3 -c "
from telegram_listener import TelegramListener
import asyncio
asyncio.run(TelegramListener().interactive_auth())
"

# Inserisci il codice che ricevi via SMS/Telegram
# Se hai 2FA attivato, inserisci anche la password
```

#### Passo 4: Preparazione Directory Dati
```bash
# Crea la directory per i dati persistenti
mkdir -p ./data

# Sposta la sessione Telegram nella directory dati
mv telegram_session.session ./data/ 2>/dev/null || echo "Session file not found - make sure auth completed successfully"

# Verifica che la sessione sia stata salvata
ls -la ./data/
```

#### Passo 5: Build e Avvio Container
```bash
# Build dell'immagine Docker
docker-compose build

# Avvio in background
docker-compose up -d

# Verifica che i servizi siano attivi
docker-compose ps
```

#### Passo 6: Verifica e Monitoraggio
```bash
# Controlla i log in tempo reale
docker-compose logs -f

# Verifica la salute del servizio
curl http://localhost:1717/health

# Accedi alla dashboard
open http://localhost:1717
```

### Comandi Docker Utili

```bash
# Riavvia i servizi
docker-compose restart

# Aggiorna dopo modifiche al codice
docker-compose down
docker-compose build
docker-compose up -d

# Backup dei dati
tar -czf backup-$(date +%Y%m%d).tar.gz ./data

# Ripristino backup
tar -xzf backup-YYYYMMDD.tar.gz

# Pulizia completa (ATTENZIONE: elimina tutto!)
docker-compose down -v --rmi all
rm -rf ./data
```

### Troubleshooting Docker

#### Problema: "Telegram authentication required"
```bash
# Soluzione: Ri-esegui l'autenticazione
python3 -c "
from telegram_listener import TelegramListener
import asyncio
asyncio.run(TelegramListener().interactive_auth())
"
mv telegram_session.session ./data/
docker-compose restart
```

#### Problema: "Port 1717 already in use"
```bash
# Cambia porta nel docker-compose.yml
nano docker-compose.yml
# Modifica "1717:1717" in "8080:1717"
docker-compose up -d
```

#### Problema: Container non si avvia
```bash
# Controlla i log per errori
docker-compose logs

# Verifica la configurazione
docker-compose config

# Ricostruisci l'immagine
docker-compose build --no-cache
```

### Setup Automatico (Alternativa)

Se preferisci un setup automatico, usa lo script incluso:

```bash
# Setup completo guidato
chmod +x scripts/setup.sh
./scripts/setup.sh setup

# Solo build e start
./scripts/setup.sh start

# Controlla status
./scripts/setup.sh status
```

### 🏷️ Organizzazione Container

I container Docker sono configurati con nomi e labels personalizzati per una migliore organizzazione in Docker Desktop:

#### **Container Name**
- **`solanagram-bot`** - Container principale del bot

#### **Labels Organizzative**
- **Project**: `solanagram-trading-bot`
- **Service**: `main-bot` 
- **Version**: `1.0.0`
- **Description**: `Telegram Solana Trading Bot`

#### **Network & Volume**
- **Network**: `solanagram-network`
- **Volume**: `solanagram-data`

#### **Vantaggi in Docker Desktop**
✅ **Raggruppamento automatico** - Tutti i container del progetto appaiono insieme  
✅ **Filtri per labels** - Puoi filtrare per `com.solanagram.project`  
✅ **Nomi descrittivi** - Facile identificazione  
✅ **Organizzazione gerarchica** - Network e volume correlati  

#### **Comandi per Gestione**
```bash
# Lista container con labels
docker ps --filter "label=com.solanagram.project"

# Rimuovi tutto il progetto
docker-compose down -v

# Rimuovi solo container (mantieni volumi)
docker-compose down

# Ricostruisci con nuovo nome
docker-compose build --no-cache
docker-compose up -d
```

## 📱 Formato Messaggi Telegram

Il bot riconosce messaggi con questa struttura:

### Messaggio BUY (❗ 0 close)
```
TokenName
❗ 0 close
Market Cap: $1.2M
TradeScore: 85
🟢 Assassin.eth ($50K)
🟢 SmartTrader.sol ($30K)
🟢 WhaleAlert ($100K)
https://jup.ag/swap/SOL-TokenAddress
```

### Messaggio SELL (❗ 1 close)
```
TokenName
❗ 1 close
🔴 Assassin.eth
🔴 SmartTrader.sol
```

## 🎛️ Dashboard Web

La dashboard offre:

- **Status Bot**: modalità corrente, statistiche, stato wallet
- **Segnali Recenti**: storico segnali ricevuti e processati
- **Trade Eseguiti**: cronologia delle operazioni
- **Configurazione Filtri**: modifica parametri di trading
- **Controllo Modalità**: switch tra dry-run e live
- **Wallet Info**: bilancio SOL e cronologia transazioni

## ⚙️ Configurazione Avanzata

### Filtri di Trading

```python
# In config.json o via dashboard
{
  "bot": {
    "min_market_cap": 100000,     # Market cap minimo ($)
    "min_trade_score": 70,        # Score minimo
    "max_slippage": 5.0,          # Slippage massimo (%)
    "trade_amount_sol": 0.1       # Importo per trade (SOL)
  },
  "filters": {
    "min_holder_count": 3,        # Smart holders minimi
    "trusted_holders": [          # Holders fidati
      "Assassin.eth",
      "SmartTrader.sol"
    ],
    "blacklisted_tokens": []      # Token blacklist
  }
}
```

### Modalità Operative

- **`dry-run`**: Simula tutti i trade, nessuna transazione reale
- **`live`**: Esegue transazioni reali sulla blockchain

**⚠️ ATTENZIONE**: La modalità live usa fondi reali!

## 🔒 Sicurezza

### Wallet
- Chiavi private crittografate con Fernet
- File wallet protetti con permessi 600
- Backup automatico raccomandato

### API
- Autenticazione con token Bearer
- Rate limiting raccomandato in produzione
- HTTPS obbligatorio in produzione

### Telegram
- Sessione salvata localmente
- Solo messaggi dal gruppo configurato

## 🔧 Sviluppo e Debug

### Sviluppo Locale

```bash
# Installa dipendenze
pip install -r requirements.txt

# Avvia in modalità sviluppo
python main.py

# Debug con log dettagliati
export LOG_LEVEL=DEBUG
python main.py
```

### Test Parser

```python
from parser import parser

test_message = """
TestToken
❗ 0 close
Market Cap: $500K
TradeScore: 75
🟢 TestTrader ($10K)
https://jup.ag/swap/SOL-ABC123
"""

signal = parser.parse_message(test_message)
print(f"Parsed: {signal}")
```

### Struttura Database

```sql
-- Segnali ricevuti
CREATE TABLE signals (
    id INTEGER PRIMARY KEY,
    signal_type TEXT,           -- BUY/SELL
    token_address TEXT,
    token_name TEXT,
    market_cap REAL,
    trade_score INTEGER,
    smart_holders TEXT,         -- JSON
    processed BOOLEAN,
    created_at TIMESTAMP
);

-- Trade eseguiti
CREATE TABLE trades (
    id INTEGER PRIMARY KEY,
    signal_id INTEGER,
    trade_type TEXT,
    amount_sol REAL,
    status TEXT,               -- pending/success/failed
    transaction_hash TEXT,
    timestamp TIMESTAMP
);
```

## 🚧 Estensioni Future

### Trading Live
- [ ] Integrazione Jupiter API completa
- [ ] Gestione slippage dinamico
- [ ] Stop-loss automatico
- [ ] Take-profit automatico

### Analytics
- [ ] Grafici performance
- [ ] ROI tracking
- [ ] Statistiche smart holders
- [ ] Alert personalizzati

### Notification
- [ ] Notification Telegram per trade
- [ ] Email alerts
- [ ] Discord webhook
- [ ] Slack integration

## ❗ Limitazioni Attuali

1. **Trading Live**: Jupiter integration non implementata (solo simulazione)
2. **Multi-token**: Un trade alla volta
3. **Telegram Auth**: Richiede setup interattivo iniziale
4. **Scalability**: SQLite per piccoli volumi

## 📞 Troubleshooting

### Problema: "Telegram authentication required"
**Soluzione**: Esegui autenticazione interattiva prima del deploy Docker

### Problema: "Failed to get balance"
**Soluzione**: Verifica RPC Solana e connessione internet

### Problema: "No valid signal type detected"
**Soluzione**: Controlla formato messaggi e pattern regex

### Problema: "Permission denied" su file wallet
**Soluzione**: Verifica permessi directory data

## 📄 Licenza

MIT License - vedi file LICENSE per dettagli.

## ⚠️ Disclaimer

Questo software è fornito "as-is" per scopi educativi. Il trading di criptovalute comporta rischi significativi. Usa a tuo rischio e responsabilità. Gli autori non sono responsabili per perdite finanziarie.

## 🤝 Contributi

Contributi benvenuti! Apri issue o pull request per:

- Bug fixes
- Nuove funzionalità
- Miglioramenti documentazione
- Test aggiuntivi

---

**Happy Trading! 🚀**
