#!/bin/bash

# CrewAI Chat Passthrough Agent Container Management Script
# Follows rigorous container naming: crewai-chat-passthrough-{model}-{model_version}-{env}-{instance}

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE_NAME="crewai-chat-passthrough"
MODEL="${MODEL:-claude}"
MODEL_VERSION="${MODEL_VERSION:-sonnet4}"
ENVIRONMENT="${ENVIRONMENT:-prod}"
INSTANCE_ID="${INSTANCE_ID:-001}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

# Generate rigorous container name
CONTAINER_NAME="crewai-chat-passthrough-${MODEL}-${MODEL_VERSION}-${ENVIRONMENT}-${INSTANCE_ID}"

# Network configuration
NETWORK_NAME="${NETWORK_NAME:-crewai-network}"
API_PORT="${API_PORT:-8087}"
METRICS_PORT="${METRICS_PORT:-9097}"

# Service configuration
C2_REGISTRY_URL="${C2_REGISTRY_URL:-http://crewai-c2-dc1-prod-001-v1-0-0:8080}"

# Storage configuration
DATA_DIR="${DATA_DIR:-${SCRIPT_DIR}/data}"
KB_DIR="${KB_DIR:-${SCRIPT_DIR}/kb}"
OUTPUT_DIR="${OUTPUT_DIR:-${SCRIPT_DIR}/output}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
}

success() {
    echo -e "${GREEN}[SUCCESS] $1${NC}"
}

validate_naming_schema() {
    local name="$1"
    if [[ ! "$name" =~ ^crewai-chat-passthrough-[a-z0-9]+-[a-z0-9]+-[a-z0-9]+-[0-9]+$ ]]; then
        error "Container name '$name' does not follow rigorous naming schema:"
        error "Expected: crewai-chat-passthrough-{model}-{model_version}-{env}-{instance}"
        error "Example: crewai-chat-passthrough-claude-sonnet4-prod-001"
        return 1
    fi
    return 0
}

create_directories() {
    log "Creating required directories..."
    mkdir -p "$DATA_DIR" "$OUTPUT_DIR" "$KB_DIR"
    mkdir -p "$OUTPUT_DIR/logs"
    mkdir -p "$KB_DIR/short" "$KB_DIR/long"
}

create_network() {
    if ! docker network inspect "$NETWORK_NAME" >/dev/null 2>&1; then
        log "Creating Docker network: $NETWORK_NAME"
        docker network create \
            --driver bridge \
            --subnet=172.20.0.0/16 \
            --ip-range=172.20.240.0/20 \
            "$NETWORK_NAME"
    else
        log "Network $NETWORK_NAME already exists"
    fi
}

build_image() {
    log "Building Docker image: $IMAGE_NAME:$IMAGE_TAG"
    docker build -t "$IMAGE_NAME:$IMAGE_TAG" "$SCRIPT_DIR"
    success "Image built successfully"
}

stop_container() {
    if docker ps -q -f name="$CONTAINER_NAME" | grep -q .; then
        log "Stopping existing container: $CONTAINER_NAME"
        docker stop "$CONTAINER_NAME" >/dev/null
    fi

    if docker ps -aq -f name="$CONTAINER_NAME" | grep -q .; then
        log "Removing existing container: $CONTAINER_NAME"
        docker rm "$CONTAINER_NAME" >/dev/null
    fi
}

start_container() {
    log "Starting Chat Passthrough agent container: $CONTAINER_NAME"

    docker run -d \
        --name "$CONTAINER_NAME" \
        --network "$NETWORK_NAME" \
        --hostname "crewai-chat-passthrough-${INSTANCE_ID}" \
        -p "$API_PORT:8080" \
        -p "$METRICS_PORT:9090" \
        -v "$DATA_DIR:/work/data" \
        -v "$KB_DIR:/work/kb" \
        -v "$OUTPUT_DIR:/work/output" \
        -v "$HOME/.anthropic:/home/crewai/.anthropic:ro" \
        -e MODEL="$MODEL" \
        -e MODEL_VERSION="$MODEL_VERSION" \
        -e ENVIRONMENT="$ENVIRONMENT" \
        -e INSTANCE_ID="$INSTANCE_ID" \
        -e API_PORT=8080 \
        -e METRICS_PORT=9090 \
        -e C2_REGISTRY_URL="$C2_REGISTRY_URL" \
        --restart unless-stopped \
        --security-opt no-new-privileges:true \
        "$IMAGE_NAME:$IMAGE_TAG"

    success "Container started successfully"
}

wait_for_health() {
    log "Waiting for Chat Passthrough agent to become healthy..."
    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if curl -sf "http://localhost:$API_PORT/health" >/dev/null 2>&1; then
            success "Chat Passthrough agent is healthy and responding"
            return 0
        fi

        log "Attempt $attempt/$max_attempts - waiting for health check..."
        sleep 2
        ((attempt++))
    done

    error "Chat Passthrough agent failed to become healthy"
    return 1
}

show_status() {
    log "Container status:"
    docker ps -f name="$CONTAINER_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

    echo ""
    log "Chat interface: http://localhost:$API_PORT/chat"
    log "Health endpoint: http://localhost:$API_PORT/health"
    log "Metrics: http://localhost:$METRICS_PORT/metrics"
}

show_logs() {
    docker logs -f "$CONTAINER_NAME"
}

cleanup() {
    stop_container
    log "Container stopped"
    success "Cleanup complete"
}

# Command handling
case "${1:-}" in
    build)
        validate_naming_schema "$CONTAINER_NAME"
        create_directories
        build_image
        ;;
    start)
        validate_naming_schema "$CONTAINER_NAME"
        create_directories
        create_network
        stop_container
        start_container
        wait_for_health
        show_status
        ;;
    stop)
        stop_container
        ;;
    restart)
        validate_naming_schema "$CONTAINER_NAME"
        stop_container
        start_container
        wait_for_health
        show_status
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    cleanup)
        cleanup
        ;;
    *)
        echo "Usage: $0 {build|start|stop|restart|status|logs|cleanup}"
        echo ""
        echo "Commands:"
        echo "  build     - Build the Docker image"
        echo "  start     - Start the Chat Passthrough agent container"
        echo "  stop      - Stop the Chat Passthrough agent container"
        echo "  restart   - Restart the Chat Passthrough agent container"
        echo "  status    - Show container status"
        echo "  logs      - Show container logs (follow mode)"
        echo "  cleanup   - Stop and remove container"
        echo ""
        echo "Environment variables:"
        echo "  MODEL             - LLM model name (default: claude)"
        echo "  MODEL_VERSION     - Model version (default: sonnet4)"
        echo "  ENVIRONMENT       - Environment (default: prod)"
        echo "  INSTANCE_ID       - Instance ID (default: 001)"
        echo "  API_PORT          - API port (default: 8087)"
        echo "  METRICS_PORT      - Metrics port (default: 9097)"
        echo "  C2_REGISTRY_URL   - C2 registry URL"
        exit 1
        ;;
esac
