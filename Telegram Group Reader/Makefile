# 🚀 Telegram Chat Manager - Makefile
# Simplified commands for development and deployment

.PHONY: help setup-dev build run run-dev test lint clean logs health migrate backup

# Default target
help: ## Show this help message
	@echo "🚀 Telegram Chat Manager - Available Commands"
	@echo "=============================================="
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Development

setup-dev: ## Setup development environment
	@echo "🔧 Setting up development environment..."
	@cp -n .env.example .env || true
	@echo "📝 Please edit .env file with your Telegram API credentials"
	@echo "✅ Development environment ready"

build: ## Build all Docker containers
	@echo "🐳 Building Docker containers..."
	@docker-compose -f docker-compose.dev.yml build
	@echo "✅ Build completed"

run-dev: ## Run development environment
	@echo "🚀 Starting development environment..."
	@docker-compose -f docker-compose.dev.yml up --build

run-dev-d: ## Run development environment in background
	@echo "🚀 Starting development environment (detached)..."
	@docker-compose -f docker-compose.dev.yml up --build -d
	@echo "✅ Development environment running in background"
	@echo "📱 Web interface: http://localhost:8080"

##@ Production

run: ## Run production environment
	@echo "🚀 Starting production environment..."
	@docker-compose up --build -d
	@echo "✅ Production environment running"
	@echo "📱 Web interface: http://localhost:8080"

scale: ## Scale backend services (usage: make scale REPLICAS=3)
	@echo "📈 Scaling backend services to $(REPLICAS) replicas..."
	@docker-compose up --scale backend=$(REPLICAS) -d
	@echo "✅ Scaling completed"

##@ Database

migrate: ## Run database migrations
	@echo "🗄️  Running database migrations..."
	@docker-compose exec backend flask db upgrade
	@echo "✅ Migrations completed"

migrate-create: ## Create new migration (usage: make migrate-create MSG="description")
	@echo "📝 Creating new migration: $(MSG)"
	@docker-compose exec backend flask db migrate -m "$(MSG)"
	@echo "✅ Migration created"

backup: ## Create database backup
	@echo "💾 Creating database backup..."
	@mkdir -p backups
	@docker-compose exec postgres pg_dump -U postgres chatmanager > backups/backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "✅ Backup created in backups/ directory"

##@ Testing

test: ## Run all tests
	@echo "🧪 Running tests..."
	@docker-compose exec backend pytest
	@echo "✅ Tests completed"

test-unit: ## Run unit tests only
	@echo "🧪 Running unit tests..."
	@docker-compose exec backend pytest tests/unit/
	@echo "✅ Unit tests completed"

test-integration: ## Run integration tests only
	@echo "🧪 Running integration tests..."
	@docker-compose exec backend pytest tests/integration/
	@echo "✅ Integration tests completed"

test-coverage: ## Run tests with coverage report
	@echo "📊 Running tests with coverage..."
	@docker-compose exec backend pytest --cov=backend --cov-report=html
	@echo "✅ Coverage report generated in htmlcov/"

##@ Code Quality

lint: ## Run linting and code formatting
	@echo "🔍 Running code linting..."
	@docker-compose exec backend flake8 .
	@docker-compose exec backend black --check .
	@docker-compose exec backend isort --check-only .
	@echo "✅ Linting completed"

format: ## Format code with black and isort
	@echo "✨ Formatting code..."
	@docker-compose exec backend black .
	@docker-compose exec backend isort .
	@echo "✅ Code formatted"

security-scan: ## Run security vulnerability scan
	@echo "🔒 Running security scan..."
	@docker-compose exec backend bandit -r backend/
	@docker-compose exec backend safety check
	@echo "✅ Security scan completed"

##@ Monitoring

logs: ## Show application logs
	@echo "📋 Showing application logs..."
	@docker-compose logs -f --tail=100

logs-backend: ## Show backend logs only
	@echo "📋 Showing backend logs..."
	@docker-compose logs -f backend

logs-frontend: ## Show frontend logs only
	@echo "📋 Showing frontend logs..."
	@docker-compose logs -f frontend

health: ## Check application health
	@echo "🏥 Checking application health..."
	@curl -s http://localhost:8080/health | jq .
	@echo "\n✅ Health check completed"

status: ## Show container status
	@echo "📊 Container status:"
	@docker-compose ps
	@echo "\n💾 Resource usage:"
	@docker stats --no-stream

##@ Utilities

shell-backend: ## Open shell in backend container
	@echo "🐚 Opening backend shell..."
	@docker-compose exec backend /bin/bash

shell-frontend: ## Open shell in frontend container
	@echo "🐚 Opening frontend shell..."
	@docker-compose exec frontend /bin/bash

shell-db: ## Open database shell
	@echo "🗄️  Opening database shell..."
	@docker-compose exec postgres psql -U postgres chatmanager

redis-cli: ## Open Redis CLI
	@echo "💾 Opening Redis CLI..."
	@docker-compose exec redis redis-cli

##@ Cleanup

stop: ## Stop all services
	@echo "🛑 Stopping all services..."
	@docker-compose down
	@echo "✅ Services stopped"

clean: ## Clean containers and volumes
	@echo "🧹 Cleaning containers and volumes..."
	@docker-compose down -v
	@docker system prune -f
	@echo "✅ Cleanup completed"

clean-all: ## Clean everything (containers, volumes, images)
	@echo "🧹 Cleaning everything..."
	@docker-compose down -v --rmi all
	@docker system prune -af
	@echo "✅ Complete cleanup done"

reset: ## Reset development environment
	@echo "🔄 Resetting development environment..."
	@docker-compose down -v
	@docker-compose -f docker-compose.dev.yml up --build -d
	@echo "✅ Environment reset completed"

##@ Quick Actions

dev: setup-dev run-dev-d migrate ## Quick setup: prepare and start development environment

prod: build run migrate ## Quick setup: build and start production environment  

restart: stop run-dev-d ## Quick restart development environment

deploy: ## Deploy to production (with backup)
	@echo "🚀 Deploying to production..."
	@make backup
	@make stop
	@make run
	@make migrate
	@make health
	@echo "✅ Deployment completed"

##@ Information

config: ## Show current configuration
	@echo "⚙️  Current Configuration:"
	@echo "=========================="
	@echo "Environment: $$(docker-compose config | grep -E 'FLASK_ENV|DEBUG' || echo 'Not set')"
	@echo "Services: $$(docker-compose config --services | tr '\n' ' ')"
	@echo "Ports: $$(docker-compose config | grep -E 'ports:' -A1 || echo 'Default ports')"

check-env: ## Check environment variables
	@echo "🔍 Checking environment variables..."
	@echo "=================================="
	@test -f .env && echo "✅ .env file exists" || echo "❌ .env file missing"
	@test -n "$$TELEGRAM_API_ID" && echo "✅ TELEGRAM_API_ID set" || echo "❌ TELEGRAM_API_ID missing"
	@test -n "$$TELEGRAM_API_HASH" && echo "✅ TELEGRAM_API_HASH set" || echo "❌ TELEGRAM_API_HASH missing"
	@test -n "$$SECRET_KEY" && echo "✅ SECRET_KEY set" || echo "❌ SECRET_KEY missing"

version: ## Show version information
	@echo "📦 Version Information:"
	@echo "======================="
	@echo "Docker: $$(docker --version)"
	@echo "Docker Compose: $$(docker-compose --version)"
	@echo "Make: $$(make --version | head -n1)"

##@ Examples

example-user: ## Create example user for testing
	@echo "👤 Creating example user..."
	@docker-compose exec backend python -c "
from backend.models.user import User; 
from backend.auth.security import hash_password;
user = User(phone='+1234567890', password_hash=hash_password('test123'));
print('Example user created: +1234567890 / test123')"

example-load-test: ## Run example load test
	@echo "🔥 Running load test example..."
	@docker run --rm -v $(PWD):/app -w /app locustio/locust \
		-f tests/load/locustfile.py \
		--host=http://localhost:8080 \
		--users=10 --spawn-rate=2 --run-time=60s --headless

# Color output
MAKEFLAGS += --silent
.DEFAULT_GOAL := help 