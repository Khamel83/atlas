#!/bin/bash
"""
Meilisearch Setup Script

This script sets up Meilisearch for Atlas full-text search functionality.
"""

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
MEILISEARCH_PORT=7700
MEILISEARCH_HOST="http://localhost:${MEILISEARCH_PORT}"
CONTAINER_NAME="atlas-meilisearch"

print_step() {
    echo -e "${BLUE}==> $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed or not in PATH"
        echo "Please install Docker first: https://docs.docker.com/get-docker/"
        exit 1
    fi

    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running"
        echo "Please start Docker and try again"
        exit 1
    fi

    print_success "Docker is available"
}

check_port() {
    if lsof -Pi :${MEILISEARCH_PORT} -sTCP:LISTEN -t >/dev/null ; then
        print_warning "Port ${MEILISEARCH_PORT} is already in use"
        echo "If Meilisearch is already running, you can skip this setup"
        echo "Otherwise, please stop the service using port ${MEILISEARCH_PORT}"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

stop_existing_container() {
    if docker ps -a --format 'table {{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        print_step "Stopping existing Meilisearch container"
        docker stop ${CONTAINER_NAME} 2>/dev/null || true
        docker rm ${CONTAINER_NAME} 2>/dev/null || true
        print_success "Existing container removed"
    fi
}

start_meilisearch() {
    print_step "Starting Meilisearch container"

    docker run -d \
        --name ${CONTAINER_NAME} \
        -p ${MEILISEARCH_PORT}:7700 \
        -e MEILI_ENV=development \
        -e MEILI_NO_ANALYTICS=true \
        -v meilisearch_data:/meili_data \
        getmeili/meilisearch:v1.10.1

    print_success "Meilisearch container started"
}

wait_for_meilisearch() {
    print_step "Waiting for Meilisearch to be ready"

    for i in {1..30}; do
        if curl -s ${MEILISEARCH_HOST}/health &>/dev/null; then
            print_success "Meilisearch is ready"
            return 0
        fi
        echo -n "."
        sleep 1
    done

    print_error "Meilisearch failed to start within 30 seconds"
    exit 1
}

update_env_config() {
    local env_file=".env"

    if [ -f "$env_file" ]; then
        print_step "Updating .env configuration"

        # Backup existing .env
        cp "$env_file" "${env_file}.backup.$(date +%Y%m%d_%H%M%S)"

        # Remove existing Meilisearch config
        sed -i.tmp '/^MEILISEARCH_/d' "$env_file"

        # Add new Meilisearch config
        echo "" >> "$env_file"
        echo "# Meilisearch Configuration" >> "$env_file"
        echo "MEILISEARCH_HOST=${MEILISEARCH_HOST}" >> "$env_file"
        echo "MEILISEARCH_INDEX=atlas_content" >> "$env_file"
        echo "# MEILISEARCH_API_KEY=  # Optional: add API key for production" >> "$env_file"

        print_success "Updated .env configuration"
    else
        print_warning ".env file not found"
        echo "Create one from env.template if needed"
    fi
}

show_next_steps() {
    echo ""
    echo -e "${GREEN}🎉 Meilisearch setup completed successfully!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Set up the search index:"
    echo -e "   ${BLUE}python scripts/search_manager.py setup${NC}"
    echo ""
    echo "2. Index your content:"
    echo -e "   ${BLUE}python scripts/search_manager.py index${NC}"
    echo ""
    echo "3. Test search functionality:"
    echo -e "   ${BLUE}python scripts/search_manager.py search${NC}"
    echo ""
    echo "Service information:"
    echo -e "   ${YELLOW}URL:${NC} ${MEILISEARCH_HOST}"
    echo -e "   ${YELLOW}Container:${NC} ${CONTAINER_NAME}"
    echo -e "   ${YELLOW}Dashboard:${NC} ${MEILISEARCH_HOST} (when available)"
    echo ""
    echo "To stop Meilisearch:"
    echo -e "   ${BLUE}docker stop ${CONTAINER_NAME}${NC}"
    echo ""
    echo "To start Meilisearch again:"
    echo -e "   ${BLUE}docker start ${CONTAINER_NAME}${NC}"
}

show_status() {
    print_step "Checking Meilisearch status"

    if docker ps --format 'table {{.Names}}\t{{.Status}}' | grep -q "^${CONTAINER_NAME}"; then
        print_success "Meilisearch container is running"

        if curl -s ${MEILISEARCH_HOST}/health &>/dev/null; then
            print_success "Meilisearch service is healthy"

            # Show basic stats if available
            if command -v python3 &> /dev/null; then
                echo ""
                echo "Running health check..."
                python3 scripts/search_manager.py health 2>/dev/null || echo "Run 'python scripts/search_manager.py health' for detailed status"
            fi
        else
            print_warning "Meilisearch container is running but service is not responding"
        fi
    else
        print_warning "Meilisearch container is not running"
        echo "Run '$0 start' to start Meilisearch"
    fi
}

show_help() {
    echo "Atlas Meilisearch Setup Script"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  setup     Set up and start Meilisearch (default)"
    echo "  start     Start Meilisearch container"
    echo "  stop      Stop Meilisearch container"
    echo "  restart   Restart Meilisearch container"
    echo "  status    Show Meilisearch status"
    echo "  logs      Show Meilisearch logs"
    echo "  clean     Remove Meilisearch container and data"
    echo "  help      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 setup    # Initial setup"
    echo "  $0 status   # Check if running"
    echo "  $0 logs     # View logs"
}

main() {
    local command="${1:-setup}"

    case "$command" in
        "setup")
            print_step "Setting up Meilisearch for Atlas"
            check_docker
            check_port
            stop_existing_container
            start_meilisearch
            wait_for_meilisearch
            update_env_config
            show_next_steps
            ;;
        "start")
            check_docker
            if docker ps -a --format 'table {{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
                docker start ${CONTAINER_NAME}
                print_success "Meilisearch container started"
                wait_for_meilisearch
            else
                print_error "Container ${CONTAINER_NAME} does not exist. Run '$0 setup' first."
                exit 1
            fi
            ;;
        "stop")
            docker stop ${CONTAINER_NAME} 2>/dev/null || print_warning "Container not running"
            print_success "Meilisearch container stopped"
            ;;
        "restart")
            docker restart ${CONTAINER_NAME} 2>/dev/null || print_error "Container not found"
            print_success "Meilisearch container restarted"
            wait_for_meilisearch
            ;;
        "status")
            show_status
            ;;
        "logs")
            docker logs -f ${CONTAINER_NAME} 2>/dev/null || print_error "Container not found"
            ;;
        "clean")
            print_warning "This will remove the Meilisearch container and all search data"
            read -p "Are you sure? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                docker stop ${CONTAINER_NAME} 2>/dev/null || true
                docker rm ${CONTAINER_NAME} 2>/dev/null || true
                docker volume rm meilisearch_data 2>/dev/null || true
                print_success "Meilisearch container and data removed"
            else
                print_success "Clean operation cancelled"
            fi
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            print_error "Unknown command: $command"
            show_help
            exit 1
            ;;
    esac
}

main "$@"