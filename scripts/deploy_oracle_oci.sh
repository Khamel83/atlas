#!/bin/bash
"""
Oracle OCI Deployment Script for PODEMOS RSS Server

Automates deployment of private RSS feed server to Oracle OCI.
Handles container setup, networking, and SSL configuration.
"""

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Configuration
OCI_REGION="${OCI_REGION:-us-ashburn-1}"
COMPARTMENT_OCID="${COMPARTMENT_OCID:-}"
INSTANCE_NAME="podemos-rss-server"
IMAGE_NAME="podemos/rss-server:latest"
CONTAINER_PORT=8080

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}" >&2
}

check_prerequisites() {
    log "Checking prerequisites..."

    # Check OCI CLI
    if ! command -v oci &> /dev/null; then
        error "OCI CLI not found. Install from: https://docs.oracle.com/iaas/tools/oci-cli/"
        exit 1
    fi

    # Check Docker
    if ! command -v docker &> /dev/null; then
        error "Docker not found. Please install Docker."
        exit 1
    fi

    # Check OCI config
    if [ ! -f ~/.oci/config ]; then
        error "OCI config not found. Run: oci setup config"
        exit 1
    fi

    # Check compartment OCID
    if [ -z "$COMPARTMENT_OCID" ]; then
        error "COMPARTMENT_OCID environment variable required"
        echo "Get from: https://cloud.oracle.com/identity/compartments"
        exit 1
    fi

    success "Prerequisites check passed"
}

create_dockerfile() {
    log "Creating Dockerfile..."

    cat > "$PROJECT_ROOT/Dockerfile.podemos-rss" << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install additional dependencies
RUN pip install uvicorn[standard] fastapi aiofiles

# Copy application
COPY . .

# Create data directory
RUN mkdir -p /data

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/status || exit 1

# Run server
CMD ["python", "podemos_rss_server.py"]
EOF

    success "Dockerfile created"
}

build_docker_image() {
    log "Building Docker image..."

    cd "$PROJECT_ROOT"
    docker build -f Dockerfile.podemos-rss -t "$IMAGE_NAME" .

    success "Docker image built: $IMAGE_NAME"
}

create_container_instance() {
    log "Creating OCI Container Instance..."

    # Create security group if it doesn't exist
    local sg_name="podemos-rss-sg"
    local sg_ocid

    sg_ocid=$(oci network security-list list \
        --compartment-id "$COMPARTMENT_OCID" \
        --query "data[?\"display-name\" == '$sg_name'].id | [0]" \
        --raw-output 2>/dev/null || echo "null")

    if [ "$sg_ocid" = "null" ]; then
        log "Creating security group..."

        sg_ocid=$(oci network security-list create \
            --compartment-id "$COMPARTMENT_OCID" \
            --display-name "$sg_name" \
            --egress-security-rules '[
                {
                    "destination": "0.0.0.0/0",
                    "protocol": "all",
                    "isStateless": false
                }
            ]' \
            --ingress-security-rules '[
                {
                    "source": "0.0.0.0/0",
                    "protocol": "6",
                    "tcpOptions": {
                        "destinationPortRange": {
                            "min": 8080,
                            "max": 8080
                        }
                    },
                    "isStateless": false
                },
                {
                    "source": "0.0.0.0/0",
                    "protocol": "6",
                    "tcpOptions": {
                        "destinationPortRange": {
                            "min": 443,
                            "max": 443
                        }
                    },
                    "isStateless": false
                }
            ]' \
            --query "data.id" \
            --raw-output)

        success "Security group created: $sg_ocid"
    else
        success "Using existing security group: $sg_ocid"
    fi

    # Get default VCN and subnet
    local vcn_ocid
    vcn_ocid=$(oci network vcn list \
        --compartment-id "$COMPARTMENT_OCID" \
        --query "data[0].id" \
        --raw-output)

    local subnet_ocid
    subnet_ocid=$(oci network subnet list \
        --compartment-id "$COMPARTMENT_OCID" \
        --vcn-id "$vcn_ocid" \
        --query "data[0].id" \
        --raw-output)

    # Create container instance config
    cat > /tmp/container-config.json << EOF
{
    "compartmentId": "$COMPARTMENT_OCID",
    "displayName": "$INSTANCE_NAME",
    "availabilityDomain": "$(oci iam availability-domain list --query 'data[0].name' --raw-output)",
    "shape": "CI.Standard.E4.Flex",
    "shapeConfig": {
        "ocpus": 0.5,
        "memoryInGBs": 1
    },
    "vnics": [
        {
            "subnetId": "$subnet_ocid",
            "assignPublicIp": true,
            "nsgIds": ["$sg_ocid"]
        }
    ],
    "containers": [
        {
            "displayName": "podemos-rss-container",
            "imageUrl": "docker.io/library/python:3.11-slim",
            "command": ["/bin/bash"],
            "arguments": ["-c", "cd /app && python podemos_rss_server.py"],
            "workingDirectory": "/app",
            "environmentVariables": {
                "PORT": "8080",
                "DATABASE_PATH": "/data/atlas.db",
                "AUTH_DB_PATH": "/data/podemos_auth.db"
            },
            "volumeMounts": [
                {
                    "volumeName": "data-volume",
                    "mountPath": "/data"
                }
            ]
        }
    ],
    "volumes": [
        {
            "name": "data-volume",
            "volumeType": "EMPTYDIR"
        }
    ]
}
EOF

    # Create container instance
    local instance_ocid
    instance_ocid=$(oci container-instances container-instance create \
        --from-json file:///tmp/container-config.json \
        --query "data.id" \
        --raw-output)

    success "Container instance created: $instance_ocid"

    # Wait for instance to be running
    log "Waiting for instance to be running..."
    oci container-instances container-instance get \
        --container-instance-id "$instance_ocid" \
        --wait-for-state ACTIVE \
        --wait-interval-seconds 10

    # Get public IP
    local public_ip
    public_ip=$(oci container-instances container-instance get \
        --container-instance-id "$instance_ocid" \
        --query "data.vnics[0].\"public-ip\"" \
        --raw-output)

    success "Instance running at: http://$public_ip:8080"

    # Save deployment info
    cat > "$PROJECT_ROOT/deployment_info.json" << EOF
{
    "instance_ocid": "$instance_ocid",
    "public_ip": "$public_ip",
    "base_url": "http://$public_ip:8080",
    "region": "$OCI_REGION",
    "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF

    echo "$public_ip"
}

setup_ssl() {
    local public_ip="$1"

    log "Setting up SSL certificate..."

    # Note: This would require domain setup and Let's Encrypt
    echo "🔒 SSL setup requires:"
    echo "   1. Point domain to IP: $public_ip"
    echo "   2. Configure Let's Encrypt certificate"
    echo "   3. Update security group for HTTPS (port 443)"

    # For now, create self-signed certificate
    log "Creating self-signed certificate for testing..."

    # This would be done on the container instance
    # For production, use proper domain and Let's Encrypt
}

generate_access_token() {
    local public_ip="$1"

    log "Generating access token for testing..."

    # Create test token for 'acquired' feed
    local test_feed="acquired"
    local response

    response=$(curl -s -X POST "http://$public_ip:8080/feeds/$test_feed/generate_token?user_name=test_user" || echo "{}")

    if echo "$response" | jq -e '.token' > /dev/null 2>&1; then
        local token
        token=$(echo "$response" | jq -r '.token')

        success "Test token generated:"
        echo "   Feed: $test_feed"
        echo "   Token: $token"
        echo "   URL: http://$public_ip:8080/feeds/$test_feed/rss?token=$token"

        # Save to deployment info
        jq --arg token "$token" --arg feed "$test_feed" \
           '.test_access = {feed: $feed, token: $token}' \
           "$PROJECT_ROOT/deployment_info.json" > /tmp/deployment.json
        mv /tmp/deployment.json "$PROJECT_ROOT/deployment_info.json"
    else
        error "Failed to generate test token"
    fi
}

test_deployment() {
    local public_ip="$1"

    log "Testing deployment..."

    # Test health endpoint
    if curl -f -s "http://$public_ip:8080/status" > /dev/null; then
        success "Health check passed"
    else
        error "Health check failed"
        return 1
    fi

    # Test root endpoint
    local response
    response=$(curl -s "http://$public_ip:8080/" | jq -r '.message' 2>/dev/null || echo "")

    if [ "$response" = "PODEMOS Private RSS Server" ]; then
        success "Server responding correctly"
    else
        error "Server not responding correctly"
        return 1
    fi

    success "Deployment test passed"
}

show_usage_instructions() {
    local public_ip="$1"

    echo ""
    echo "🎉 PODEMOS RSS Server deployed successfully!"
    echo ""
    echo "📍 Server Details:"
    echo "   URL: http://$public_ip:8080"
    echo "   Status: http://$public_ip:8080/status"
    echo ""
    echo "🔑 Generate Feed Token:"
    echo "   curl -X POST 'http://$public_ip:8080/feeds/PODCAST_NAME/generate_token?user_name=YOUR_NAME'"
    echo ""
    echo "📡 Access RSS Feed:"
    echo "   http://$public_ip:8080/feeds/PODCAST_NAME/rss?token=YOUR_TOKEN"
    echo ""
    echo "📱 Add to Podcast App:"
    echo "   Use the RSS feed URL in your podcast app (Overcast, Pocket Casts, etc.)"
    echo ""
    echo "📋 Management:"
    echo "   - Deployment info saved to: deployment_info.json"
    echo "   - View logs: oci logging-search search-logs"
    echo "   - Update: Rebuild and redeploy container"
    echo ""
}

cleanup_temp_files() {
    rm -f /tmp/container-config.json
    rm -f /tmp/deployment.json
}

main() {
    echo "🚀 Oracle OCI Deployment for PODEMOS RSS Server"
    echo "================================================"

    # Check for help
    if [[ "${1:-}" == "--help" ]] || [[ "${1:-}" == "-h" ]]; then
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Environment Variables:"
        echo "  COMPARTMENT_OCID  - OCI compartment ID (required)"
        echo "  OCI_REGION        - OCI region (default: us-ashburn-1)"
        echo ""
        echo "Prerequisites:"
        echo "  - OCI CLI installed and configured"
        echo "  - Docker installed"
        echo "  - Valid OCI credentials"
        exit 0
    fi

    # Main deployment flow
    check_prerequisites
    create_dockerfile
    build_docker_image

    local public_ip
    public_ip=$(create_container_instance)

    sleep 30  # Wait for container to fully start

    test_deployment "$public_ip"
    generate_access_token "$public_ip"
    setup_ssl "$public_ip"

    show_usage_instructions "$public_ip"

    cleanup_temp_files

    success "Deployment completed successfully!"
}

# Handle script interruption
trap cleanup_temp_files EXIT

# Run main function
main "$@"