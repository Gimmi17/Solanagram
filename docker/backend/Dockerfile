# 🐳 Telegram Chat Manager - Backend Dockerfile
# Multi-stage build per ottimizzazione produzione

# ============================================
# 📦 Base Stage - Dependencies comuni
# ============================================
FROM python:3.11-slim as base

# Metadati dell'immagine
LABEL maintainer="Telegram Chat Manager"
LABEL version="1.0.0"
LABEL description="Backend API per Telegram Chat Manager"

# Variabili ambiente
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Installa dipendenze sistema incluso Docker CLI
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    libpq-dev \
    ca-certificates \
    gnupg \
    lsb-release \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get update \
    && apt-get install -y docker-ce-cli \
    && rm -rf /var/lib/apt/lists/*

# Crea gruppo docker e utente appuser con accesso a docker
RUN groupadd -r appuser \
    && groupadd -f docker \
    && useradd -r -g appuser -G docker appuser

# Directory di lavoro
WORKDIR /app

# ============================================
# 🔧 Development Stage
# ============================================
FROM base as development

# Installa dipendenze development
RUN apt-get update && apt-get install -y \
    git \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Copia e installa prima i requirements di produzione, poi quelli di test
COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY requirements-test.txt ./
RUN pip install -r requirements-test.txt

# Copia codice applicazione
COPY backend/ ./backend/
COPY database/ ./database/

# Crea directory logs e configs
RUN mkdir -p /app/logs /tmp/solanagram-configs && chown -R appuser:appuser /app && chmod 755 /tmp/solanagram-configs

# Espone porta development
EXPOSE 5000

# Switch to non-root user (mantenere root per accesso Docker socket)
# USER appuser

# Health check with fallback
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5000/health 2>/dev/null || curl -f http://localhost:5000/ 2>/dev/null || exit 1

# Comando di avvio development - usa Python diretto
CMD ["python", "backend/app.py"]

# ============================================
# 🚀 Production Stage
# ============================================
FROM base as production

# Copia solo requirements produzione
COPY requirements.txt ./
RUN pip install -r requirements.txt

# Copia codice applicazione
COPY backend/ ./backend/
COPY database/ ./database/

# Crea directory logs e configs con permessi corretti
RUN mkdir -p /app/logs /tmp/solanagram-configs && chown -R appuser:appuser /app && chmod 755 /tmp/solanagram-configs

# Ottimizzazioni produzione
RUN find /app -type f -name "*.pyc" -delete && \
    find /app -type d -name "__pycache__" -delete

# Security: switch to non-root user
USER appuser

# Espone porta produzione
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Comando di avvio produzione (Gunicorn)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "backend.app:app"] 