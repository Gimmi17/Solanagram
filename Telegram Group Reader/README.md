# 🚀 Telegram Chat Manager

> **Multi-user web platform for managing Telegram chat interactions with privacy-first design**

[![Docker](https://img.shields.io/badge/Docker-Ready-blue?logo=docker)](https://docker.com)
[![Security](https://img.shields.io/badge/Security-First-green?logo=security)](https://security.md)
[![Privacy](https://img.shields.io/badge/Privacy-First-orange?logo=privacy)](https://privacy.md)
[![Python](https://img.shields.io/badge/Python-3.11+-yellow?logo=python)](https://python.org)

## 📋 Overview

Telegram Chat Manager è una piattaforma web multi-utente che consente di gestire chat e canali Telegram attraverso un'interfaccia web sicura e intuitiva. Progettato con un approccio **privacy-first**, garantisce l'isolamento completo tra utenti e la gestione sicura delle sessioni Telegram.

### 🎯 Key Features

- 🔐 **Secure Authentication**: Login con numero di telefono e password  
- 📱 **Telegram Integration**: Gestione sessioni Telegram isolate per utente
- 🌐 **Web Interface**: Terminal-style interface per comandi chat
- 🔒 **Privacy-First**: Sessioni temporanee senza persistenza dati sensibili
- 🐳 **Docker Ready**: Deploy production-ready con Docker Compose
- 📊 **Real-time**: WebSocket per aggiornamenti istantanei
- 📱 **Mobile Responsive**: Ottimizzato per desktop e mobile

## 🏗️ Architecture

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

## 🚀 Quick Start

### Prerequisites
- **Docker** 20.10+
- **Docker Compose** 2.0+
- **Telegram API credentials** (API ID + API Hash)

### 1. Clone & Setup
```bash
git clone <repository-url>
cd telegram-chat-manager

# Setup environment
cp .env.example .env
# Edit .env with your values
```

### 2. Configure Environment
```bash
# .env file
DATABASE_URL=postgresql://user:pass@postgres:5432/chatmanager
REDIS_URL=redis://redis:6379/0
SECRET_KEY=your-secret-key-here
TELEGRAM_API_ID=your-api-id
TELEGRAM_API_HASH=your-api-hash
```

### 3. Launch Services
```bash
# Development
docker-compose -f docker-compose.dev.yml up --build

# Production  
docker-compose up --build -d
```

### 4. Access Application
- **Web Interface**: http://localhost:8080
- **Admin Panel**: http://localhost:8080/admin
- **Health Check**: http://localhost:8080/health

## 🎮 Usage

### 1. User Registration
1. Navigate to the web interface
2. Click "Register" 
3. Enter phone number and password
4. Complete registration

### 2. Telegram Session Setup
1. Login with your credentials
2. Click the red "START SESSION" button
3. Enter the SMS verification code
4. Session is now active (24h auto-expiry)

### 3. Chat Commands
Use the terminal-style interface to execute commands:

```bash
# Find chat by username
@scontierrati

# List recent chats  
list

# Search chats by name
search offerte

# Get help
help

# Clear output
clear
```

## 🔧 Development

### Project Structure
```
telegram-chat-manager/
├── frontend/              # Web interface (Flask)
│   ├── templates/        # HTML templates
│   ├── static/          # CSS, JS, images
│   └── app.py           # Frontend app
├── backend/              # API backend (Flask)
│   ├── models/          # Database models
│   ├── auth/            # Authentication
│   ├── telegram/        # Telegram integration
│   └── utils/           # Utilities
├── database/            # DB schemas & migrations
├── docker/              # Docker configurations
├── environments/        # Environment configs
└── Old/                # Previous version code
```

### Development Workflow
```bash
# Setup development environment
make setup-dev

# Run tests
make test

# Code linting
make lint

# Database migrations
make migrate

# View logs
make logs
```

### Adding New Features
1. Create feature branch
2. Implement changes following architecture
3. Add tests (unit + integration)
4. Update documentation
5. Submit pull request

## 🔒 Security

### Security Features
- ✅ **Password Hashing**: bcrypt with salt
- ✅ **Session Management**: JWT tokens in Redis
- ✅ **Rate Limiting**: 5 login attempts/minute
- ✅ **CSRF Protection**: Token-based protection
- ✅ **Input Validation**: XSS and injection protection
- ✅ **HTTPS Ready**: SSL/TLS termination
- ✅ **Container Security**: Non-root users, read-only filesystems

### Privacy-First Design
```python
# Telegram sessions are NEVER persisted to disk
# Only stored in Redis with auto-expiry
session_data = {
    "user_id": user.id,
    "telegram_session": encrypted_session,
    "expires_at": time.time() + 86400  # 24h
}
redis.setex(f"tg_session:{user_id}", 86400, session_data)
```

### User Isolation
- Each user has completely isolated Telegram session
- Redis namespacing prevents cross-user data access
- Automatic cleanup on logout/session expiry
- No shared session data between users

## 📊 Monitoring

### Health Checks
```bash
# Application health
curl http://localhost:8080/health

# Service status
docker-compose ps

# Resource usage
docker stats
```

### Logs
```bash
# Application logs
docker-compose logs -f backend

# Real-time monitoring
docker-compose logs -f --tail=100
```

### Metrics
- Response time monitoring
- Active user sessions
- Telegram API usage
- Error rates and types

## 🚀 Deployment

### Development
```bash
docker-compose -f docker-compose.dev.yml up
```

### Production
```bash
# With SSL and production optimizations
docker-compose -f docker-compose.yml up -d

# Scale services
docker-compose up --scale backend=3 -d
```

### Environment Variables
| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | ✅ |
| `REDIS_URL` | Redis connection string | ✅ |
| `SECRET_KEY` | Flask secret key | ✅ |
| `TELEGRAM_API_ID` | Telegram API ID | ✅ |
| `TELEGRAM_API_HASH` | Telegram API Hash | ✅ |
| `FLASK_ENV` | Environment (dev/prod) | ❌ |
| `DEBUG` | Debug mode | ❌ |

## 📚 Documentation

- 📖 [**Architecture Overview**](ARCHITECTURE.md) - System design and components
- 🚀 [**Implementation Plan**](IMPLEMENTATION_PLAN.md) - Development roadmap  
- ✅ [**Progress Checklist**](PROGRESS_CHECKLIST.md) - Development tracking
- 🔧 [**API Documentation**](docs/API.md) - API endpoints and usage
- 🐳 [**Docker Guide**](docs/DOCKER.md) - Container setup and management
- 🔒 [**Security Guide**](docs/SECURITY.md) - Security best practices

## 🎯 Roadmap

### Phase 1 - MVP ✏️ (Current)
- [x] Project architecture
- [ ] Docker infrastructure  
- [ ] User authentication
- [ ] Telegram integration
- [ ] Basic web interface

### Phase 2 - Enhanced
- [ ] WebSocket real-time updates
- [ ] Advanced security features
- [ ] Performance optimizations
- [ ] Mobile app support

### Phase 3 - Scale
- [ ] Microservices architecture
- [ ] Kubernetes deployment
- [ ] Advanced analytics
- [ ] Multi-language support

## 🤝 Contributing

1. **Fork** the repository
2. **Create** feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** changes (`git commit -m 'Add amazing feature'`)
4. **Push** to branch (`git push origin feature/amazing-feature`)
5. **Open** Pull Request

### Development Guidelines
- Follow PEP 8 for Python code
- Add tests for new features
- Update documentation
- Ensure security best practices
- Test with Docker before submitting

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/your-repo/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-repo/discussions)
- **Security**: [Security Policy](SECURITY.md)

## 🙏 Acknowledgments

- **Telethon**: Telegram API library
- **Flask**: Web framework
- **Docker**: Containerization platform
- **Bootstrap**: Frontend framework
- **PostgreSQL**: Database system
- **Redis**: Cache and session store

---

Made with ❤️ for secure and private Telegram chat management 