# 🐳 Telegram Chat Manager - Frontend Dockerfile
# Multi-stage build per ottimizzazione

# ============================================
# 📦 Base Stage
# ============================================
FROM python:3.11-slim as base

# Metadati dell'immagine
LABEL maintainer="Telegram Chat Manager"
LABEL version="1.0.0"
LABEL description="Frontend Web per Telegram Chat Manager"

# Variabili ambiente
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Installa dipendenze sistema
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Crea utente non-root
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Directory di lavoro
WORKDIR /app

# ============================================
# 🔧 Development Stage
# ============================================
FROM base as development

# Installa dipendenze test
COPY requirements-test.txt ./
RUN pip install -r requirements-test.txt

# Copia codice frontend
COPY frontend/ ./frontend/

# Crea directory logs
RUN mkdir -p /app/logs && chown -R appuser:appuser /app

# Espone porta frontend
EXPOSE 8080

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Comando development - usa Python diretto
CMD ["python", "frontend/app.py"]

# ============================================
# 🚀 Production Stage
# ============================================
FROM base as production

# Copia requirements produzione
COPY requirements.txt ./
RUN pip install -r requirements.txt

# Copia codice frontend
COPY frontend/ ./frontend/

# Crea directory logs
RUN mkdir -p /app/logs && chown -R appuser:appuser /app

# Ottimizzazioni produzione
RUN find /app -type f -name "*.pyc" -delete && \
    find /app -type d -name "__pycache__" -delete

# Switch to non-root user
USER appuser

# Espone porta produzione
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Comando produzione
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--timeout", "60", "frontend.app:app"] 