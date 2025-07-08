# 📚 Guida Utente - Telegram Chat Manager

> **Guida completa per l'utilizzo della piattaforma di gestione chat Telegram con elaborazione automatica dei segnali crypto**

## 🎯 Panoramica del Sistema

Il **Telegram Chat Manager** è una piattaforma web avanzata che permette di:
- **Gestire sessioni Telegram** in modo sicuro e isolato
- **Inserire e monitorare chat** da canali e gruppi Telegram
- **Elaborare automaticamente segnali crypto** tramite parser intelligenti
- **Estrarre dati specifici** dalle chat tramite regole personalizzate
- **Visualizzare statistiche e performance** dei segnali elaborati

---

## 🚀 Primo Accesso e Configurazione

### 1. Registrazione e Login

1. **Accedi alla piattaforma** tramite browser web
2. **Registrati** con il tuo numero di telefono e password
3. **Effettua il login** con le credenziali create

### 2. Configurazione Sessione Telegram

1. **Clicca su "START SESSION"** (pulsante rosso)
2. **Inserisci il codice SMS** ricevuto su Telegram
3. **Attendi la connessione** - la sessione è attiva per 24 ore
4. **Verifica lo stato** - dovresti vedere "✅ Connesso" in verde

> ⚠️ **Importante**: La sessione scade automaticamente dopo 24 ore per motivi di sicurezza

---

## 📱 Gestione Chat e Canali

### 1. Visualizzazione Chat Disponibili

1. **Accedi alla sezione "Chat"** dal menu principale
2. **Visualizza la lista** di tutte le chat e canali disponibili
3. **Usa i comandi di ricerca**:
   - `@username` - Trova chat specifica
   - `search nome` - Cerca per nome
   - `list` - Lista chat recenti

### 2. Selezione Chat per Elaborazione

1. **Identifica la chat** che contiene i segnali crypto
2. **Prendi nota del Chat ID** (visibile nell'interfaccia)
3. **Verifica i permessi** - assicurati di avere accesso in lettura

---

## 🔧 Configurazione Elaborazione Segnali

### 1. Accesso alla Sezione Crypto Signals

1. **Clicca su "Crypto Signals"** nel menu principale
2. **Visualizza l'interfaccia** di gestione segnali
3. **Esplora le sezioni disponibili**:
   - Test Parser
   - Configurazione Processore
   - Statistiche
   - Segnali Recenti

### 2. Test del Parser (Sezione 1)

**Scopo**: Verificare che il parser riconosca correttamente i segnali crypto

1. **Copia un messaggio** di segnale crypto dalla chat
2. **Incolla nel campo "Test Signal Parser"**
3. **Clicca "Test Parser"**
4. **Verifica i risultati**:
   - ✅ Tipo di segnale (BUY/SELL)
   - ✅ Indirizzo token
   - ✅ Nome token
   - ✅ Market cap
   - ✅ Trade score
   - ✅ Smart holders

**Esempio di messaggio da testare**:
```
❗ 0 close
TokenName
🟢 Holder1 ($1000)
🟢 Holder2 ($500)
TradeScore: 85
$1.2M
https://jup.ag/swap/...
```

### 3. Configurazione Processore (Sezione 2)

**Scopo**: Attivare l'elaborazione automatica per una chat specifica

1. **Seleziona la chat** dal dropdown "Seleziona una chat..."
2. **Clicca "Salva Configurazione"**
3. **Verifica l'attivazione**:
   - Il processore appare nella lista
   - Stato: "Attivo" o "In elaborazione"
   - Pulsante "Visualizza" disponibile

> 🔄 **Processo Automatico**: Una volta configurato, il sistema elabora automaticamente tutti i nuovi messaggi della chat

---

## 📊 Monitoraggio e Visualizzazione

### 1. Statistiche Segnali

**Accesso**: Sezione "Statistiche Segnali" (visibile dopo configurazione)

**Metriche disponibili**:
- 📈 **Segnali Totali**: Numero complessivo di segnali elaborati
- 🟢 **Segnali BUY**: Segnali di acquisto rilevati
- 🔴 **Segnali SELL**: Segnali di vendita rilevati
- ⏰ **Ultimi 24h**: Attività recente

### 2. Segnali Recenti

**Accesso**: Sezione "Segnali Recenti"

**Funzionalità**:
- **Filtri**: Tutti / Buy / Sell
- **Dettagli per segnale**:
  - Token name e address
  - Market cap
  - Trade score
  - Smart holders
  - Timestamp
  - Link Jupiter (se disponibile)

### 3. Top Performers

**Accesso**: Sezione "Top Performers"

**Analisi**:
- 🏆 **Token più attivi**
- 📊 **Performance per periodo**
- 💰 **Market cap trends**

---

## 🔍 Estrazione Dati Personalizzata

### 1. Configurazione Regole di Estrazione

**Scopo**: Estrarre dati specifici dalle chat tramite regole personalizzate

1. **Accedi alla sezione "Extractor Rules"**
2. **Clicca "Aggiungi Regola"**
3. **Configura i parametri**:
   - **Nome Regola**: Identificativo della regola
   - **Testo di Ricerca**: Stringa da cercare nel messaggio
   - **Lunghezza Valore**: Numero di caratteri da estrarre dopo il testo

**Esempio di Regola**:
```
Nome: "Token Address"
Testo di Ricerca: "Contract:"
Lunghezza Valore: 44
```

### 2. Gestione Regole

**Operazioni disponibili**:
- ✅ **Aggiungere** nuove regole
- ✏️ **Modificare** regole esistenti
- 🗑️ **Eliminare** regole non più necessarie
- 🔄 **Testare** regole su messaggi di esempio

### 3. Monitoraggio Estrazioni

**Visualizzazione risultati**:
- **Dati estratti** per ogni regola
- **Timestamp** di estrazione
- **Messaggio originale** per riferimento
- **Statistiche** di successo

---

## ⚙️ Configurazioni Avanzate

### 1. Gestione Processori

**Operazioni disponibili**:
- **Attivare/Disattivare** processori
- **Modificare** configurazioni
- **Visualizzare** log di elaborazione
- **Riavviare** processori in caso di problemi

### 2. Impostazioni Sicurezza

**Funzionalità**:
- **Sessione temporanea** (24h auto-expiry)
- **Isolamento utenti** (nessun accesso incrociato)
- **Log di accesso** per audit
- **Rate limiting** per protezione

### 3. Backup e Ripristino

**Procedure**:
- **Export configurazioni** in formato JSON
- **Import regole** da file di backup
- **Sincronizzazione** tra dispositivi
- **Versioning** delle configurazioni

---

## 🚨 Risoluzione Problemi

### Problemi Comuni

#### 1. Sessione Telegram Scaduta
**Sintomi**: Errore "Session expired" o "Not connected"
**Soluzione**:
1. Clicca "START SESSION"
2. Reinserisci il codice SMS
3. Attendi la riconnessione

#### 2. Parser Non Riconosce Segnali
**Sintomi**: Test parser restituisce "No signal detected"
**Soluzione**:
1. Verifica il formato del messaggio
2. Controlla che contenga indicatori BUY/SELL
3. Assicurati che sia un messaggio di segnale valido

#### 3. Chat Non Appare nella Lista
**Sintomi**: Chat non visibile nel dropdown
**Soluzione**:
1. Verifica i permessi di accesso
2. Controlla che la chat sia attiva
3. Prova a ricaricare la lista chat

#### 4. Estrazione Dati Non Funziona
**Sintomi**: Regole non estraggono valori
**Soluzione**:
1. Verifica il testo di ricerca
2. Controlla la lunghezza del valore
3. Testa la regola su un messaggio di esempio

### Log e Debug

**Accesso ai log**:
- **Log applicazione**: Console del browser (F12)
- **Log server**: Sezione "Logs" nell'interfaccia admin
- **Log Telegram**: Monitoraggio connessioni API

---

## 📈 Best Practices

### 1. Configurazione Ottimale

**Raccomandazioni**:
- **Testa sempre** il parser prima di attivare
- **Usa regole specifiche** per estrazioni precise
- **Monitora regolarmente** le statistiche
- **Backup configurazioni** importanti

### 2. Gestione Performance

**Ottimizzazioni**:
- **Limita il numero** di processori attivi
- **Pulisci regole** non utilizzate
- **Monitora l'uso** delle risorse
- **Riavvia periodicamente** le sessioni

### 3. Sicurezza

**Pratiche consigliate**:
- **Cambia password** regolarmente
- **Non condividere** sessioni
- **Logout** quando non utilizzi
- **Monitora** accessi sospetti

---

## 🔗 Integrazioni e API

### 1. API Endpoints

**Endpoint principali**:
- `GET /api/telegram/get-chats` - Lista chat
- `POST /api/crypto/test-parse` - Test parser
- `GET /api/crypto/signals/{chat_id}` - Segnali per chat
- `POST /api/crypto/extraction-rules` - Gestione regole

### 2. Webhook Support

**Configurazione**:
- **URL webhook** per notifiche real-time
- **Formato JSON** per dati estratti
- **Autenticazione** tramite token

### 3. Export Dati

**Formati supportati**:
- **CSV** per analisi Excel
- **JSON** per integrazioni
- **API REST** per sistemi esterni

---

## 📞 Supporto e Contatti

### Canali di Supporto

- **Documentazione**: Questa guida e file README
- **Issues**: GitHub Issues per bug e feature requests
- **Discussions**: GitHub Discussions per domande generali
- **Email**: Supporto diretto per problemi critici

### Informazioni Utili

- **Versione**: Controlla sempre la versione del software
- **Changelog**: Leggi le note di rilascio
- **Roadmap**: Consulta i piani di sviluppo futuri
- **Community**: Partecipa alle discussioni della community

---

## 🎓 Tutorial Video

### Serie di Video Guide

1. **Setup Iniziale** - Registrazione e configurazione
2. **Gestione Chat** - Selezione e monitoraggio chat
3. **Configurazione Parser** - Test e attivazione elaborazione
4. **Regole di Estrazione** - Creazione e gestione regole
5. **Analisi Dati** - Interpretazione statistiche e performance
6. **Risoluzione Problemi** - Troubleshooting comune

> 📹 **Disponibili su**: Canale YouTube ufficiale del progetto

---

## 📝 Note Legali

### Privacy e Sicurezza

- **Dati personali**: Gestiti secondo GDPR
- **Sessione Telegram**: Non persistente, auto-cancellazione
- **Isolamento utenti**: Nessun accesso incrociato ai dati
- **Log**: Solo per funzionalità tecniche

### Termini di Utilizzo

- **Uso responsabile** della piattaforma
- **Rispetto** delle policy Telegram
- **Non utilizzo** per attività illegali
- **Limitazioni** di responsabilità

---

**🎯 Obiettivo**: Questa guida ti accompagna passo dopo passo nell'utilizzo completo della piattaforma Telegram Chat Manager, dall'inserimento dei log delle chat all'elaborazione automatica dei segnali crypto.

**💡 Suggerimento**: Inizia sempre con il test del parser e procedi gradualmente con le configurazioni più avanzate.