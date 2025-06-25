# 🏗️ Architettura - Telegram Chat Manager

## 📋 Requisiti del Sistema

### Funzionali
- ✅ **Login/Registrazione**: Telefono + Password
- ✅ **Gestione Sessioni Telegram**: Per utente isolate
- ✅ **Interface Web**: CLI-style per comandi chat
- ✅ **Privacy-First**: Sessioni solo live, niente persistenza dati sensibili
- ✅ **Multi-User**: Supporto utenti simultanei
- ✅ **Containerized**: Deploy Docker production-ready

### Non-Funzionali  
- 🔒 **Security**: Password hashing, session isolation
- 📈 **Scalability**: Horizontal scaling ready
- 🚀 **Performance**: < 1s response time
- 🌐 **Availability**: 99.9% uptime target
- 📱 **Responsive**: Mobile & desktop friendly

## 🎯 Stack Tecnologico

```yaml
Frontend:
  - Flask Templates + Bootstrap 5
  - JavaScript vanilla (no frameworks)
  - WebSocket per real-time updates

Backend:
  - Flask + SQLAlchemy
  - Redis per session management
  - Celery per background tasks
  - Gunicorn per production

Database:
  - PostgreSQL (production)
  - SQLite (development)
  - Redis (cache & sessions)

Infrastructure:
  - Docker Compose
  - Nginx reverse proxy
  - SSL/TLS termination
  - Health checks
```

## 🏛️ Architettura del Sistema

### Diagramma di Alto Livello
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Nginx Proxy   │    │   Web Frontend  │    │   Telegram API  │
│    (SSL/TLS)    │◄──►│     (Flask)     │◄──►│   (Sessions)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                        │
         ▼                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Load Balancer │    │   Backend API   │    │   Redis Cache   │
│                 │◄──►│    (Flask)      │◄──►│   (Sessions)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                    ┌─────────────────┐
                    │   PostgreSQL    │
                    │   (User Data)   │
                    └─────────────────┘
```

### Componenti Principali

#### 1. 🌐 Frontend Service
```
frontend/
├── app.py              # Flask app principale
├── templates/          # HTML templates
│   ├── base.html      # Template base
│   ├── login.html     # Login/registrazione
│   ├── dashboard.html # Chat interface
│   └── session.html   # Setup sessione Telegram
├── static/            # CSS, JS, images
│   ├── css/
│   ├── js/
│   └── img/
└── forms.py           # WTForms per validazione
```

#### 2. 🔧 Backend Service  
```
backend/
├── app.py             # Flask API
├── models/            # Database models
│   ├── user.py       # Modello utente
│   └── session.py    # Modello sessione
├── auth/              # Sistema autenticazione
│   ├── login.py      # Login logic
│   └── security.py   # Password hashing
├── telegram/          # Gestione Telegram
│   ├── manager.py    # Session manager
│   └── commands.py   # Chat commands
└── utils/             # Utilities
    ├── redis_client.py
    └── validators.py
```

#### 3. 🗄️ Database Schema
```sql
-- Tabella utenti
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    phone VARCHAR(15) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- Sessioni live (in Redis, non persistenti)
-- Key: "session:{user_id}" 
-- Value: JSON con telegram session data
-- TTL: 24 ore auto-expire
```

## 🔐 Security Model

### Autenticazione
- **Password Hashing**: bcrypt con salt
- **Session Management**: JWT tokens in Redis
- **Rate Limiting**: max 5 login attempts/minute
- **CSRF Protection**: Token-based

### Privacy-First Design
```python
# Sessioni Telegram NON persistenti
redis_session = {
    "user_id": user.id,
    "telegram_session": base64_encoded_session,
    "created_at": timestamp,
    "expires_at": timestamp + 24h
}

# Auto-cleanup alla disconnessione
@app.teardown_appcontext
def cleanup_telegram_session():
    if current_user.is_authenticated:
        redis.delete(f"telegram_session:{current_user.id}")
```

### Isolamento Utenti
- Ogni utente ha sessione Telegram separata
- Redis namespace per user: `tg_session:{user_id}`
- Cleanup automatico alla disconnessione
- Nessuna cross-contamination tra utenti

## 🚀 Deployment Architecture

### Docker Compose Stack
```yaml
services:
  nginx:          # Reverse proxy + SSL
  frontend:       # Flask frontend
  backend:        # Flask API
  postgres:       # Database primario  
  redis:          # Cache + sessions
  worker:         # Celery background tasks
```

### Environment Separation
```
📁 environments/
├── development.yml    # Local dev
├── staging.yml        # Test environment  
└── production.yml     # Production config
```

## 📊 Data Flow

### 1. User Registration/Login
```
1. User → Frontend (phone + password)
2. Frontend → Backend API (validation)
3. Backend → PostgreSQL (store/verify user)
4. Backend → Redis (create session)
5. Backend → Frontend (auth token)
```

### 2. Telegram Session Setup  
```
1. User clicks "Start Session"
2. Frontend → Backend (create telegram session)
3. Backend → Telegram API (request auth code)
4. User receives SMS → inputs code
5. Backend → Redis (store live session)
6. Frontend → Dashboard (ready for commands)
```

### 3. Chat Commands
```
1. User types command in frontend
2. WebSocket → Backend (real-time)
3. Backend → Telegram API (via user session)
4. Telegram API → Backend (response)  
5. Backend → Frontend (display result)
```

## 🔧 Configuration Management

### Environment Variables
```bash
# Database
DATABASE_URL=postgresql://user:pass@postgres:5432/chatmanager
REDIS_URL=redis://redis:6379/0

# Security
SECRET_KEY=your-secret-key-here
JWT_SECRET=jwt-signing-secret

# Telegram API
TELEGRAM_API_ID=your-api-id
TELEGRAM_API_HASH=your-api-hash

# App Settings
FLASK_ENV=production
DEBUG=false
SESSION_TIMEOUT=86400  # 24 hours
```

## 📈 Scalability Features

### Horizontal Scaling
- **Stateless Services**: Frontend & Backend
- **Session Store**: Redis cluster
- **Database**: PostgreSQL with read replicas
- **Load Balancing**: Multiple container instances

### Performance Optimizations
- **Connection Pooling**: Database connections
- **Caching Strategy**: Redis per session data
- **Async Operations**: Celery per background tasks
- **CDN Ready**: Static assets serviti via CDN

## 🛡️ Monitoring & Observability

### Health Checks
```python
@app.route('/health')
def health_check():
    return {
        'status': 'healthy',
        'database': check_db_connection(),
        'redis': check_redis_connection(),
        'telegram_api': check_telegram_status()
    }
```

### Metrics da Monitorare
- **Response Time**: < 1s target
- **Active Sessions**: Concurrent users
- **Error Rate**: < 1% target  
- **Resource Usage**: CPU, RAM, Disk

## 🔄 Development Workflow

### Local Development
```bash
# Setup ambiente locale
make setup-dev

# Avvia tutti i servizi
docker-compose -f docker-compose.dev.yml up

# Run tests
make test

# Deploy production
make deploy-prod
```

### Continuous Integration
- **Tests**: Unit + Integration tests
- **Security Scanning**: Container vulnerabilities
- **Code Quality**: Linting, coverage
- **Auto-Deploy**: Staging su push, production su tag

## 🎯 Roadmap Features

### Phase 1 - MVP (Current)
- [x] User auth (phone + password)
- [x] Telegram session management
- [x] Basic chat interface
- [x] Docker deployment

### Phase 2 - Enhanced
- [ ] WebSocket real-time updates
- [ ] Advanced chat features
- [ ] User dashboard analytics
- [ ] Multi-language support

### Phase 3 - Scale
- [ ] Microservices architecture
- [ ] Kubernetes deployment
- [ ] Advanced monitoring
- [ ] API rate limiting

## 🚦 Implementation Steps

1. **Setup Base Infrastructure** (Docker + DB)
2. **Create Authentication System** (Login/Register)
3. **Build Telegram Session Manager** (Privacy-first)
4. **Develop Chat Interface** (WebSocket)
5. **Add Security Hardening** (HTTPS, CSRF, etc.)
6. **Performance Testing** (Load tests)
7. **Production Deployment** (SSL, monitoring)

---

*Questa architettura garantisce scalabilità, sicurezza e privacy mantenendo la semplicità di sviluppo e deployment.* 