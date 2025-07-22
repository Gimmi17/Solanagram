# 🚀 Deploy Automatico: GitHub Actions + Fly.io

## **🎯 Vantaggi del Deploy Automatico**

### **✅ Zero Manutenzione**
- Deploy automatico ad ogni push su `main`
- Rollback automatico in caso di errori
- Testing automatico prima del deploy

### **✅ Sicurezza**
- Credenziali gestite tramite GitHub Secrets
- Token temporanei per Fly.io
- Nessuna credenziale nel codice

### **✅ Scalabilità**
- Matrix build per deployare 4 forwarder contemporaneamente
- Parallel deployment per velocità
- Monitoring integrato

## **🚀 Setup Rapido**

### **Step 1: Esegui Setup Script**
```bash
./setup-github-fly.sh
```

### **Step 2: Genera Token Fly.io**
```bash
fly tokens create deploy -x 999999h
```
**⚠️ IMPORTANTE:** Copia tutto il token incluso `FlyV1`

### **Step 3: Configura GitHub Secrets**
Vai su: `GitHub > Repository > Settings > Secrets and variables > Actions`

Aggiungi questi secrets:
- `FLY_API_TOKEN` = [token generato sopra]
- `TELEGRAM_PHONE` = +393662844242
- `TELEGRAM_API_ID` = 25128314
- `TELEGRAM_API_HASH` = 2d44d2d06e412599b94be16f55773241

### **Step 4: Push e Deploy**
```bash
git add .
git commit -m "Add Fly.io deployment with GitHub Actions"
git push origin main
```

## **📁 Struttura Repository**

```
Solanagram/
├── .github/
│   └── workflows/
│       ├── fly-deploy.yml          # Deploy generale
│       └── deploy-forwarders.yml   # Deploy forwarder specifico
├── configs/
│   ├── forwarder-sol-config.json
│   ├── forwarder-bsc-config.json
│   ├── forwarder-base-config.json
│   └── forwarder-test1-config.json
├── Dockerfile.forwarder            # Dockerfile ottimizzato
├── forwarder.py                    # Script forwarder
├── requirements.txt                # Dipendenze Python
└── setup-github-fly.sh            # Script setup
```

## **🔄 Workflow GitHub Actions**

### **Trigger**
- Push su `main` o `master`
- Modifiche a file specifici (forwarder.py, configs/, ecc.)

### **Processo**
1. **Checkout** del codice
2. **Setup** Fly.io CLI
3. **Matrix Build** per 4 forwarder
4. **Deploy** parallelo su Fly.io

### **Matrix Strategy**
```yaml
strategy:
  matrix:
    forwarder: [sol, bsc, base, test1]
```

Ogni forwarder viene deployato in parallelo!

## **🌐 URL Finali**

Dopo il deploy automatico:
- `https://solanagram-fwd-sol.fly.dev`
- `https://solanagram-fwd-bsc.fly.dev`
- `https://solanagram-fwd-base.fly.dev`
- `https://solanagram-fwd-test1.fly.dev`

## **📊 Monitoraggio**

### **GitHub Actions**
- Dashboard: `https://github.com/[user]/[repo]/actions`
- Log in tempo reale
- Status di ogni step

### **Fly.io Dashboard**
- Apps: `https://fly.io/apps/`
- Log: `fly logs -a solanagram-fwd-sol`
- Status: `fly status -a solanagram-fwd-sol`

## **🔧 Gestione Avanzata**

### **Deploy Manuale**
```bash
# Deploy specifico forwarder
fly deploy -a solanagram-fwd-sol

# Deploy tutti
fly deploy -a solanagram-fwd-sol
fly deploy -a solanagram-fwd-bsc
fly deploy -a solanagram-fwd-base
fly deploy -a solanagram-fwd-test1
```

### **Rollback**
```bash
# Rollback automatico se configurato
fly machine restart -a solanagram-fwd-sol

# Rollback manuale
fly machine destroy -a solanagram-fwd-sol
fly deploy -a solanagram-fwd-sol
```

### **Scale Resources**
```bash
# Aumenta RAM
fly scale memory 512 -a solanagram-fwd-sol

# Aumenta CPU
fly scale cpu 2 -a solanagram-fwd-sol
```

## **⚠️ Best Practices**

### **Secrets Management**
- ✅ Usa sempre GitHub Secrets
- ✅ Non committare mai credenziali
- ✅ Rotazione token periodica

### **Deploy Strategy**
- ✅ Matrix build per parallelizzazione
- ✅ Concurrency control per evitare conflitti
- ✅ Auto-rollback per sicurezza

### **Monitoring**
- ✅ Log centralizzati su Fly.io
- ✅ Health check automatici
- ✅ Alerting su errori

## **🔄 Migrazione Completa**

### **1. Setup Automatico**
```bash
./setup-github-fly.sh
```

### **2. Verifica Deploy**
```bash
# Controlla GitHub Actions
# Controlla Fly.io dashboard
# Testa URL forwarder
```

### **3. Stop Container Locali**
```bash
# Solo dopo verifica funzionamento
docker stop solanagram-fwd-35-biz_trading_bot_sol-to--1002866779186
docker stop solanagram-fwd-35-biz_trading_bot_bsc-to--4801713910
docker stop solanagram-fwd-35-biz_trading_bot_base-to--4954731463
docker stop solanagram-fwd-34-test1-to-myjarvis17bot
```

### **4. Update Backend**
Aggiorna il backend per puntare ai nuovi URL Fly.io.

## **🎉 Risultato Finale**

- ✅ **Deploy automatico** ad ogni push
- ✅ **4 forwarder sempre attivi** su Fly.io
- ✅ **Zero manutenzione** manuale
- ✅ **Rollback automatico** in caso di errori
- ✅ **Monitoring completo** integrato
- ✅ **Scalabilità automatica** se necessario

---

**Fonti:**
- [Fly.io GitHub Actions Guide](https://fly.io/docs/app-guides/continuous-deployment-with-github-actions/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Fly.io Deploy Tokens](https://fly.io/docs/reference/deploy-tokens/) 