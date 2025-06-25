#!/bin/bash

# Solanagram Bot Setup Script
# Facilitates initial configuration and deployment

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🚀 Solanagram Bot Setup"
echo "======================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Check if required tools are installed
check_requirements() {
    print_info "Checking requirements..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed. Please install Python 3 first."
        exit 1
    fi
    
    print_status "All requirements satisfied"
}

# Setup environment file
setup_env() {
    print_info "Setting up environment configuration..."
    
    cd "$PROJECT_DIR"
    
    if [ ! -f .env ]; then
        if [ -f env.example ]; then
            cp env.example .env
            print_status "Created .env file from template"
        else
            print_error "env.example file not found"
            exit 1
        fi
    else
        print_warning ".env file already exists, skipping..."
    fi
    
    echo ""
    print_info "Please edit the .env file with your configuration:"
    echo "   - TELEGRAM_API_ID: Get from https://my.telegram.org"
    echo "   - TELEGRAM_API_HASH: Get from https://my.telegram.org"
    echo "   - TELEGRAM_PHONE: Your phone number with country code"
    echo "   - TELEGRAM_GROUP_ID: Your trading group ID"
    echo "   - API_TOKEN: Change from default for security"
    echo ""
    
    read -p "Press Enter to open .env file for editing..."
    ${EDITOR:-nano} .env
}

# Setup data directory
setup_data_dir() {
    print_info "Setting up data directory..."
    
    cd "$PROJECT_DIR"
    
    mkdir -p data
    mkdir -p templates
    mkdir -p static
    
    # Set proper permissions
    chmod 755 data
    chmod 755 templates
    chmod 755 static
    
    print_status "Data directories created"
}

# Telegram authentication
telegram_auth() {
    print_info "Setting up Telegram authentication..."
    
    cd "$PROJECT_DIR"
    
    print_warning "You need to authenticate with Telegram interactively."
    print_info "This is required only once. The session will be saved for future use."
    echo ""
    
    read -p "Do you want to authenticate now? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Install Python dependencies for authentication
        print_info "Installing Python dependencies..."
        pip3 install -r requirements.txt
        
        # Run authentication
        print_info "Starting Telegram authentication..."
        python3 -c "
from telegram_listener import TelegramListener
import asyncio
asyncio.run(TelegramListener().interactive_auth())
"
        
        # Move session to data directory
        if [ -f telegram_session.session ]; then
            mv telegram_session.session data/
            print_status "Telegram session saved to data directory"
        fi
    else
        print_warning "Skipping Telegram authentication. You'll need to do this before running the bot."
    fi
}

# Build and start services
build_and_start() {
    print_info "Building and starting services..."
    
    cd "$PROJECT_DIR"
    
    # Build Docker image
    print_info "Building Docker image..."
    docker-compose build
    
    # Start services
    print_info "Starting services..."
    docker-compose up -d
    
    print_status "Services started successfully!"
    echo ""
    print_info "Access the dashboard at: http://localhost:8000"
    print_info "Check logs with: docker-compose logs -f"
}

# Test configuration
test_config() {
    print_info "Testing configuration..."
    
    cd "$PROJECT_DIR"
    
    if [ ! -f .env ]; then
        print_error ".env file not found. Run setup first."
        return 1
    fi
    
    # Source the .env file
    source .env
    
    # Check required variables
    local missing_vars=()
    
    [ -z "$TELEGRAM_API_ID" ] && missing_vars+=("TELEGRAM_API_ID")
    [ -z "$TELEGRAM_API_HASH" ] && missing_vars+=("TELEGRAM_API_HASH")
    [ -z "$TELEGRAM_PHONE" ] && missing_vars+=("TELEGRAM_PHONE")
    
    if [ ${#missing_vars[@]} -ne 0 ]; then
        print_error "Missing required environment variables:"
        for var in "${missing_vars[@]}"; do
            echo "  - $var"
        done
        return 1
    fi
    
    print_status "Configuration looks good!"
}

# Show status
show_status() {
    print_info "Service status:"
    
    cd "$PROJECT_DIR"
    
    if docker-compose ps | grep -q "solanagram"; then
        docker-compose ps
        echo ""
        print_info "Dashboard: http://localhost:8000"
        print_info "Health check: http://localhost:8000/health"
    else
        print_warning "Services are not running. Use 'start' command to launch."
    fi
}

# Show logs
show_logs() {
    print_info "Showing logs (Ctrl+C to exit)..."
    
    cd "$PROJECT_DIR"
    docker-compose logs -f
}

# Stop services
stop_services() {
    print_info "Stopping services..."
    
    cd "$PROJECT_DIR"
    docker-compose down
    
    print_status "Services stopped"
}

# Clean up
cleanup() {
    print_warning "This will remove all containers, images and data!"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cd "$PROJECT_DIR"
        
        docker-compose down -v --rmi all
        sudo rm -rf data
        
        print_status "Cleanup completed"
    else
        print_info "Cleanup cancelled"
    fi
}

# Main menu
show_menu() {
    echo ""
    echo "Available commands:"
    echo "  setup     - Initial setup (env, auth, directories)"
    echo "  auth      - Telegram authentication only"
    echo "  start     - Build and start services"
    echo "  stop      - Stop services"
    echo "  status    - Show service status"
    echo "  logs      - Show logs"
    echo "  test      - Test configuration"
    echo "  cleanup   - Remove everything (DESTRUCTIVE)"
    echo "  help      - Show this menu"
}

# Full setup process
full_setup() {
    print_info "Starting full setup process..."
    
    check_requirements
    setup_data_dir
    setup_env
    telegram_auth
    test_config
    build_and_start
    
    echo ""
    print_status "Setup completed successfully!"
    echo ""
    print_info "Your Solanagram bot is now running!"
    print_info "Dashboard: http://localhost:8000"
    print_info "API Token: Check your .env file"
    echo ""
    print_warning "Remember to:"
    echo "  - Keep your .env file secure"
    echo "  - Backup your data directory"
    echo "  - Start in dry-run mode first"
}

# Main script logic
case "${1:-help}" in
    "setup")
        full_setup
        ;;
    "auth")
        telegram_auth
        ;;
    "start")
        check_requirements
        test_config && build_and_start
        ;;
    "stop")
        stop_services
        ;;
    "status")
        show_status
        ;;
    "logs")
        show_logs
        ;;
    "test")
        test_config
        ;;
    "cleanup")
        cleanup
        ;;
    "help"|*)
        show_menu
        ;;
esac 