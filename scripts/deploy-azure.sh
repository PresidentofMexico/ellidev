#!/bin/bash
# Elli Slack Bot - Azure Deployment Script
# Version: 0.2.0
#
# Prerequisites:
# 1. Azure CLI installed and logged in (az login)
# 2. Docker installed
# 3. Azure Container Registry created
# 4. Azure Key Vault created with secrets populated
#
# Usage:
#   ./scripts/deploy-azure.sh [build|deploy|logs|restart|all]
#
# Commands:
#   build   - Build and push Docker image to ACR
#   deploy  - Deploy/update container instance
#   logs    - Stream container logs
#   restart - Restart the container instance
#   all     - Build, push, and deploy (default)

set -e

# ==========================================
# CONFIGURATION
# ==========================================
# Override these via environment variables or edit directly

RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-rg-elli-prod}"
REGISTRY="${AZURE_CONTAINER_REGISTRY:-elliacr}"
IMAGE_NAME="elli-slack-bot"
IMAGE_TAG="${IMAGE_TAG:-latest}"
CONTAINER_NAME="${AZURE_CONTAINER_NAME:-aci-elli-prod}"
KEY_VAULT="${AZURE_KEY_VAULT_NAME:-kv-elli-prod}"
LOCATION="${AZURE_LOCATION:-eastus2}"

# Container resources
CPU_CORES="${AZURE_CPU_CORES:-1}"
MEMORY_GB="${AZURE_MEMORY_GB:-1.5}"

# ==========================================
# HELPER FUNCTIONS
# ==========================================

log_info() {
    echo "[INFO] $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo "[ERROR] $(date '+%Y-%m-%d %H:%M:%S') - $1" >&2
}

get_secret() {
    local secret_name=$1
    az keyvault secret show --vault-name "$KEY_VAULT" --name "$secret_name" --query value -o tsv 2>/dev/null
}

check_prerequisites() {
    log_info "Checking prerequisites..."

    if ! command -v az &> /dev/null; then
        log_error "Azure CLI not found. Install: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
        exit 1
    fi

    if ! az account show &> /dev/null; then
        log_error "Not logged into Azure. Run: az login"
        exit 1
    fi

    log_info "Prerequisites OK"
}

# ==========================================
# BUILD COMMAND
# ==========================================

build_and_push() {
    log_info "Building and pushing Docker image to Azure Container Registry..."

    # Build using ACR (no local Docker required)
    az acr build \
        --registry "$REGISTRY" \
        --image "$IMAGE_NAME:$IMAGE_TAG" \
        --image "$IMAGE_NAME:$(date +%Y%m%d-%H%M%S)" \
        .

    log_info "Image pushed: $REGISTRY.azurecr.io/$IMAGE_NAME:$IMAGE_TAG"
}

# ==========================================
# DEPLOY COMMAND
# ==========================================

deploy_container() {
    log_info "Deploying container instance..."

    # Get ACR credentials
    ACR_USERNAME=$(az acr credential show --name "$REGISTRY" --query username -o tsv)
    ACR_PASSWORD=$(az acr credential show --name "$REGISTRY" --query "passwords[0].value" -o tsv)

    # Fetch secrets from Key Vault
    log_info "Fetching secrets from Key Vault..."
    SLACK_BOT_TOKEN=$(get_secret "SLACK-BOT-TOKEN")
    SLACK_APP_TOKEN=$(get_secret "SLACK-APP-TOKEN")
    SF_CONSUMER_KEY=$(get_secret "SF-CONSUMER-KEY")
    SF_CONSUMER_SECRET=$(get_secret "SF-CONSUMER-SECRET")
    SF_REFRESH_TOKEN=$(get_secret "SF-REFRESH-TOKEN")
    SF_INSTANCE_URL=$(get_secret "SF-INSTANCE-URL")
    SNOWFLAKE_USER=$(get_secret "SNOWFLAKE-USER")
    SNOWFLAKE_ACCOUNT=$(get_secret "SNOWFLAKE-ACCOUNT")
    SNOWFLAKE_PRIVATE_KEY=$(get_secret "SNOWFLAKE-PRIVATE-KEY")
    CORTEX_ANALYST_PAT=$(get_secret "CORTEX-ANALYST-PAT")

    # Channel-based business unit configuration (optional)
    CHANNEL_BU_MAPPING=$(get_secret "CHANNEL-BU-MAPPING" || echo "{}")
    BU_RECORD_TYPES=$(get_secret "BU-RECORD-TYPES" || echo "{}")
    BU_FIELD_DEFAULTS=$(get_secret "BU-FIELD-DEFAULTS" || echo "{}")

    # Check if container exists
    EXISTING=$(az container show --resource-group "$RESOURCE_GROUP" --name "$CONTAINER_NAME" --query id -o tsv 2>/dev/null || true)

    if [ -n "$EXISTING" ]; then
        log_info "Deleting existing container instance..."
        az container delete --resource-group "$RESOURCE_GROUP" --name "$CONTAINER_NAME" --yes
        sleep 10
    fi

    log_info "Creating container instance..."
    az container create \
        --resource-group "$RESOURCE_GROUP" \
        --name "$CONTAINER_NAME" \
        --image "$REGISTRY.azurecr.io/$IMAGE_NAME:$IMAGE_TAG" \
        --registry-login-server "$REGISTRY.azurecr.io" \
        --registry-username "$ACR_USERNAME" \
        --registry-password "$ACR_PASSWORD" \
        --cpu "$CPU_CORES" \
        --memory "$MEMORY_GB" \
        --restart-policy Always \
        --location "$LOCATION" \
        --os-type Linux \
        --secure-environment-variables \
            SLACK_BOT_TOKEN="$SLACK_BOT_TOKEN" \
            SLACK_APP_TOKEN="$SLACK_APP_TOKEN" \
            SF_CONSUMER_KEY="$SF_CONSUMER_KEY" \
            SF_CONSUMER_SECRET="$SF_CONSUMER_SECRET" \
            SF_REFRESH_TOKEN="$SF_REFRESH_TOKEN" \
            SF_INSTANCE_URL="$SF_INSTANCE_URL" \
            SNOWFLAKE_USER="$SNOWFLAKE_USER" \
            SNOWFLAKE_ACCOUNT="$SNOWFLAKE_ACCOUNT" \
            SNOWFLAKE_PRIVATE_KEY="$SNOWFLAKE_PRIVATE_KEY" \
            CORTEX_ANALYST_PAT="$CORTEX_ANALYST_PAT" \
        --environment-variables \
            ENVIRONMENT="production" \
            LOG_LEVEL="INFO" \
            LOG_FORMAT="json" \
            RAG_ENABLED="true" \
            SEMANTIC_MEMORY_ENABLED="true" \
            CORTEX_ANALYST_ENABLED="true" \
            CORTEX_ANALYST_ACCOUNT="ara18269" \
            CORTEX_ANALYST_REGION="east-us-2.azure" \
            CORTEX_ANALYST_AGENT="DEAL_AGENT" \
            CORTEX_ANALYST_DATABASE="DEV_CURATE" \
            CORTEX_ANALYST_SCHEMA="CORE" \
            SNOWFLAKE_DATABASE="DEV_CURATE" \
            SNOWFLAKE_SCHEMA="CORE" \
            SNOWFLAKE_WAREHOUSE="COMPUTE_WH" \
            CHANNEL_BU_MAPPING="$CHANNEL_BU_MAPPING" \
            BU_RECORD_TYPES="$BU_RECORD_TYPES" \
            BU_FIELD_DEFAULTS="$BU_FIELD_DEFAULTS"

    log_info "Container deployed successfully!"

    # Show container status
    az container show --resource-group "$RESOURCE_GROUP" --name "$CONTAINER_NAME" --query "{Status:instanceView.state, IP:ipAddress.ip}" -o table
}

# ==========================================
# LOGS COMMAND
# ==========================================

stream_logs() {
    log_info "Streaming container logs (Ctrl+C to stop)..."
    az container logs --resource-group "$RESOURCE_GROUP" --name "$CONTAINER_NAME" --follow
}

# ==========================================
# RESTART COMMAND
# ==========================================

restart_container() {
    log_info "Restarting container instance..."
    az container restart --resource-group "$RESOURCE_GROUP" --name "$CONTAINER_NAME"
    log_info "Container restarted"
}

# ==========================================
# STATUS COMMAND
# ==========================================

show_status() {
    log_info "Container status:"
    az container show \
        --resource-group "$RESOURCE_GROUP" \
        --name "$CONTAINER_NAME" \
        --query "{Name:name, Status:instanceView.state, Restarts:containers[0].instanceView.restartCount, CPU:containers[0].resources.requests.cpu, Memory:containers[0].resources.requests.memoryInGB}" \
        -o table
}

# ==========================================
# MAIN
# ==========================================

check_prerequisites

COMMAND="${1:-all}"

case "$COMMAND" in
    build)
        build_and_push
        ;;
    deploy)
        deploy_container
        ;;
    logs)
        stream_logs
        ;;
    restart)
        restart_container
        ;;
    status)
        show_status
        ;;
    all)
        build_and_push
        deploy_container
        show_status
        ;;
    *)
        echo "Usage: $0 [build|deploy|logs|restart|status|all]"
        exit 1
        ;;
esac

log_info "Done!"
