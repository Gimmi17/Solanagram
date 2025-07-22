# 🚀 Guida Deploy Forwarder su Fly.io

## **Prerequisiti**
- Account Fly.io attivo
- Fly CLI installato: `curl -L https://fly.io/install.sh | sh`
- Autenticazione: `fly auth login`

## **🎯 Vantaggi Fly.io per Forwarder**

### **✅ Sempre Attivi**
- I forwarder su Fly.io **non vanno mai in sleep**
- Connessioni Telegram stabili 24/7
- Nessun problema di OOM (Out of Memory)

### **✅ Scalabilità**
- Free tier: 256MB RAM, 1 vCPU per forwarder
- Scaling automatico se necessario
- Regioni globali per latenza ottimale

### **✅ Monitoraggio**
- Log in tempo reale
- Metriche di performance
- Health check automatici

## **🚀 Deploy Automatico**

### **Opzione 1: Script Automatico**
```bash
# Esegui lo script di migrazione
./deploy-forwarders-fly.sh
```

### **Opzione 2: Deploy Manuale**

#### **1. Estrai Configurazione**
```bash
# Per ogni forwarder attivo
docker cp solanagram-fwd-35-biz_trading_bot_sol-to--1002866779186:/app/configs/config.json ./configs/
docker cp solanagram-fwd-35-biz_trading_bot_sol-to--1002866779186:/app/configs/session.session ./configs/
```

#### **2. Crea App Fly.io**
```bash
# Per ogni forwarder
fly launch --name solanagram-fwd-sol --no-deploy
```

#### **3. Configura fly.toml**
```toml
app = "solanagram-fwd-sol"
kill_signal = "SIGINT"
kill_timeout = 5

[env]
  CONFIG_FILE = "/app/configs/config.json"
  TELEGRAM_PHONE = "+393662844242"
  TELEGRAM_API_ID = "25128314"
  TELEGRAM_API_HASH = "2d44d2d06e412599b94be16f55773241"
  SESSION_FILE = "/app/configs/session.session"

[[services]]
  internal_port = 8080
  protocol = "tcp"

  [[services.ports]]
    handlers = ["http"]
    port = 80

[[vm]]
  cpu_kind = "shared"
  cpus = 1
  memory_mb = 256
```

#### **4. Deploy**
```bash
fly deploy
```

## **📊 Monitoraggio**

### **Log in Tempo Reale**
```bash
# Log di un forwarder specifico
fly logs -a solanagram-fwd-sol

# Log di tutti i forwarder
fly logs -a solanagram-fwd-*
```

### **Status App**
```bash
# Status di tutte le app
fly apps list

# Status specifico
fly status -a solanagram-fwd-sol
```

### **Metriche**
- Dashboard Fly.io: https://fly.io/apps/
- CPU, RAM, Network usage
- Errori e restart automatici

## **🔧 Gestione**

### **Restart Forwarder**
```bash
fly machine restart -a solanagram-fwd-sol
```

### **Scale Resources**
```bash
# Aumenta RAM
fly scale memory 512 -a solanagram-fwd-sol

# Aumenta CPU
fly scale cpu 2 -a solanagram-fwd-sol
```

### **Update Config**
```bash
# Modifica variabili d'ambiente
fly secrets set TELEGRAM_API_HASH=new_hash -a solanagram-fwd-sol

# Redeploy
fly deploy -a solanagram-fwd-sol
```

## **🌐 URL Forwarder**

Dopo il deploy, ogni forwarder avrà il suo URL:
- `https://solanagram-fwd-sol.fly.dev`
- `https://solanagram-fwd-bsc.fly.dev`
- `https://solanagram-fwd-base.fly.dev`
- `https://solanagram-fwd-test1.fly.dev`

## **⚠️ Note Importanti**

### **Session Files**
- I session file di Telegram sono critici
- Backup automatico su Fly.io
- Se scadono, ricrea il forwarder

### **Rate Limiting**
- Fly.io ha limiti sul free tier
- Monitora l'uso delle risorse
- Upgrade se necessario

### **Networking**
- I forwarder comunicano via HTTP/HTTPS
- Private networking disponibile
- SSL automatico

## **🔄 Migrazione Completa**

### **1. Deploy Forwarder su Fly.io**
```bash
./deploy-forwarders-fly.sh
```

### **2. Verifica Funzionamento**
```bash
# Controlla log
fly logs -a solanagram-fwd-sol

# Test connessione
curl https://solanagram-fwd-sol.fly.dev/health
```

### **3. Stop Container Locali**
```bash
# Solo dopo aver verificato che tutto funziona
docker stop solanagram-fwd-35-biz_trading_bot_sol-to--1002866779186
docker stop solanagram-fwd-35-biz_trading_bot_bsc-to--4801713910
docker stop solanagram-fwd-35-biz_trading_bot_base-to--4954731463
docker stop solanagram-fwd-34-test1-to-myjarvis17bot
```

### **4. Update Backend**
Aggiorna il backend per puntare ai nuovi URL Fly.io invece dei container locali.

## **🎉 Risultato**

- ✅ Forwarder sempre attivi
- ✅ Nessun problema di memoria
- ✅ Scalabilità automatica
- ✅ Monitoraggio completo
- ✅ Backup automatico
- ✅ SSL gratuito
- ✅ Regioni globali

---

**Fonti:**
- [Fly.io Dockerfile Guide](https://fly.io/docs/languages-and-frameworks/dockerfile/)
- [Fly.io Speedrun](https://fly.io/docs/speedrun/)
- [Fly.io Launch Guide](https://fly.io/docs/getting-started/launch/) 