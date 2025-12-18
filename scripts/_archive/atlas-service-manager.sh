#!/bin/bash
# Atlas Service Management Script
#
# Unified interface for managing all Atlas services

ATLAS_TARGET="atlas.target"
SERVICES=(
    "atlas-api"
    "atlas-manager"
    "atlas-google-search"
    "atlas-web"
    "atlas-health-monitor"
    "atlas-watchdog"
)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}🚀 Atlas Service Manager${NC}"
    echo "=================================="
}

print_service_status() {
    local service="$1"
    local status=$(systemctl is-active "$service" 2>/dev/null || echo "unknown")

    case $status in
        "active")
            echo -e "  ${GREEN}✅ $service: RUNNING${NC}"
            ;;
        "inactive"|"failed")
            echo -e "  ${RED}❌ $service: STOPPED${NC}"
            ;;
        "activating")
            echo -e "  ${YELLOW}⏳ $service: STARTING${NC}"
            ;;
        *)
            echo -e "  ${YELLOW}⚠️  $service: $status${NC}"
            ;;
    esac
}

check_sudo() {
    if [[ $EUID -ne 0 ]]; then
        echo -e "${RED}❌ This operation requires root privileges${NC}"
        echo "Please run: sudo $0 $*"
        exit 1
    fi
}

show_status() {
    print_header
    echo "Service Status:"
    for service in "${SERVICES[@]}"; do
        print_service_status "${service}.service"
    done

    echo ""
    echo "Overall Atlas Status:"
    print_service_status "$ATLAS_TARGET"

    echo ""
    echo "Resource Usage:"
    echo "$(systemctl show atlas-api.service --property=MainPID --value 2>/dev/null | xargs -I {} ps -p {} -o pid,pcpu,pmem,cmd --no-headers 2>/dev/null || echo 'API: Not running')"
    echo "$(systemctl show atlas-manager.service --property=MainPID --value 2>/dev/null | xargs -I {} ps -p {} -o pid,pcpu,pmem,cmd --no-headers 2>/dev/null || echo 'Manager: Not running')"
}

start_services() {
    check_sudo
    print_header
    echo -e "${GREEN}🚀 Starting all Atlas services...${NC}"
    systemctl start "$ATLAS_TARGET"
    sleep 3
    show_status
}

stop_services() {
    check_sudo
    print_header
    echo -e "${YELLOW}🛑 Stopping all Atlas services...${NC}"
    systemctl stop "$ATLAS_TARGET"
    sleep 2
    show_status
}

restart_services() {
    check_sudo
    print_header
    echo -e "${BLUE}🔄 Restarting all Atlas services...${NC}"
    systemctl restart "$ATLAS_TARGET"
    sleep 3
    show_status
}

show_logs() {
    local service="${1:-atlas-api}"
    print_header
    echo -e "${BLUE}📋 Showing logs for $service.service${NC}"
    echo "Press Ctrl+C to exit..."
    sleep 1
    journalctl -u "${service}.service" -f --no-hostname
}

emergency_restart() {
    check_sudo
    print_header
    echo -e "${RED}🚨 Emergency restart - killing all Atlas processes...${NC}"

    # Kill any hung Atlas processes
    pkill -f "python.*atlas" || true
    pkill -f "python.*api/main.py" || true
    pkill -f "python.*google_search_worker" || true

    sleep 2

    # Restart services
    systemctl daemon-reload
    systemctl restart "$ATLAS_TARGET"

    sleep 5
    show_status
}

usage() {
    print_header
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  status                 Show service status (default)"
    echo "  start                  Start all Atlas services"
    echo "  stop                   Stop all Atlas services"
    echo "  restart                Restart all Atlas services"
    echo "  emergency              Emergency restart (kills processes)"
    echo "  logs [service]         Show logs (default: atlas-api)"
    echo "  install                Install systemd services"
    echo ""
    echo "Available services for logs:"
    echo "  atlas-api, atlas-manager, atlas-google-search,"
    echo "  atlas-web, atlas-health-monitor, atlas-watchdog"
    echo ""
    echo "Examples:"
    echo "  $0 status              # Show current status"
    echo "  sudo $0 start          # Start all services"
    echo "  $0 logs atlas-api      # Show API logs"
    echo "  sudo $0 emergency      # Emergency restart"
}

install_services() {
    if [[ ! -f "/home/ubuntu/dev/atlas/scripts/install-systemd-services.sh" ]]; then
        echo -e "${RED}❌ Installation script not found${NC}"
        exit 1
    fi

    echo -e "${BLUE}🔧 Installing Atlas SystemD services...${NC}"
    bash /home/ubuntu/dev/atlas/scripts/install-systemd-services.sh
}

# Main command processing
case "${1:-status}" in
    "status"|"")
        show_status
        ;;
    "start")
        start_services
        ;;
    "stop")
        stop_services
        ;;
    "restart")
        restart_services
        ;;
    "logs")
        show_logs "$2"
        ;;
    "emergency")
        emergency_restart
        ;;
    "install")
        install_services
        ;;
    "help"|"-h"|"--help")
        usage
        ;;
    *)
        echo -e "${RED}❌ Unknown command: $1${NC}"
        echo ""
        usage
        exit 1
        ;;
esac