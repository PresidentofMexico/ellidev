# Azure Deployment Guide

> **Version**: 0.2.0
> **Last Updated**: 2026-01-30

This guide covers deploying Elli to Azure Container Instance (ACI) for production use.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Azure Resource Group                  │
│                       (rg-elli-prod)                     │
│                                                          │
│  ┌──────────────────┐     ┌──────────────────────────┐  │
│  │ Azure Container  │     │     Azure Key Vault      │  │
│  │    Instance      │────▶│      (kv-elli-prod)      │  │
│  │ (aci-elli-prod)  │     │                          │  │
│  │                  │     │  Secrets:                │  │
│  │  Socket Mode     │     │  - SLACK_BOT_TOKEN       │  │
│  │  (WebSocket)     │     │  - SLACK_APP_TOKEN       │  │
│  │                  │     │  - SF_REFRESH_TOKEN      │  │
│  └──────────────────┘     │  - SNOWFLAKE_*           │  │
│           │               └──────────────────────────┘  │
│           │                                              │
│           ▼                                              │
│  ┌──────────────────┐                                   │
│  │ Azure Container  │                                   │
│  │    Registry      │                                   │
│  │   (elliacr)      │                                   │
│  └──────────────────┘                                   │
└─────────────────────────────────────────────────────────┘
         │
         │ WebSocket (outbound only)
         ▼
    ┌─────────┐
    │  Slack  │
    └─────────┘
```

**Why Azure Container Instance?**
- **Simple**: Single container, no Kubernetes overhead
- **Cost-effective**: Pay per second (~$30-50/month for 1 CPU, 1.5GB RAM)
- **Socket Mode**: No public ingress needed (outbound WebSocket only)
- **Quick startup**: Container starts in seconds

## Prerequisites

1. **Azure CLI** installed and logged in
   ```bash
   az login
   az account set --subscription "Your Subscription Name"
   ```

2. **Docker** (optional - ACR can build images)

3. **Existing secrets** from local `.env`:
   - Slack tokens (SLACK_BOT_TOKEN, SLACK_APP_TOKEN)
   - Salesforce OAuth (SF_CONSUMER_KEY, SF_CONSUMER_SECRET, SF_REFRESH_TOKEN)
   - Snowflake credentials (SNOWFLAKE_USER, SNOWFLAKE_ACCOUNT, etc.)

## Step 1: Create Azure Resources

### 1.1 Create Resource Group
```bash
az group create --name rg-elli-prod --location eastus2
```

### 1.2 Create Container Registry
```bash
az acr create \
  --resource-group rg-elli-prod \
  --name elliacr \
  --sku Basic \
  --admin-enabled true
```

### 1.3 Create Key Vault
```bash
az keyvault create \
  --name kv-elli-prod \
  --resource-group rg-elli-prod \
  --location eastus2
```

### 1.4 Add Secrets to Key Vault

```bash
# Slack tokens
az keyvault secret set --vault-name kv-elli-prod --name SLACK-BOT-TOKEN --value "xoxb-your-token"
az keyvault secret set --vault-name kv-elli-prod --name SLACK-APP-TOKEN --value "xapp-your-token"

# Salesforce OAuth
az keyvault secret set --vault-name kv-elli-prod --name SF-CONSUMER-KEY --value "your-key"
az keyvault secret set --vault-name kv-elli-prod --name SF-CONSUMER-SECRET --value "your-secret"
az keyvault secret set --vault-name kv-elli-prod --name SF-REFRESH-TOKEN --value "your-refresh-token"
az keyvault secret set --vault-name kv-elli-prod --name SF-INSTANCE-URL --value "https://eldridge.my.salesforce.com"

# Snowflake
az keyvault secret set --vault-name kv-elli-prod --name SNOWFLAKE-USER --value "JOHN.BODDIFORD@ELDRIDGE.COM"
az keyvault secret set --vault-name kv-elli-prod --name SNOWFLAKE-ACCOUNT --value "ELDRIDGE-ECM.azure_eastus2"
az keyvault secret set --vault-name kv-elli-prod --name SNOWFLAKE-PRIVATE-KEY --value "$(cat /path/to/rsa_key.p8 | base64)"

# Cortex Analyst (optional)
az keyvault secret set --vault-name kv-elli-prod --name CORTEX-ANALYST-PAT --value "your-pat-token"
```

## Step 2: Build and Deploy

### Option A: Using the Deploy Script (Recommended)

```bash
# First time: Build and deploy
./scripts/deploy-azure.sh all

# Just build (no deploy)
./scripts/deploy-azure.sh build

# Just deploy (uses existing image)
./scripts/deploy-azure.sh deploy

# View logs
./scripts/deploy-azure.sh logs

# Restart container
./scripts/deploy-azure.sh restart

# Check status
./scripts/deploy-azure.sh status
```

### Option B: Manual Deployment

```bash
# Build and push image
az acr build --registry elliacr --image elli-slack-bot:latest .

# Deploy container (see deploy-azure.sh for full command)
az container create ...
```

### Option C: GitHub Actions (CI/CD)

Push to `main` branch or create a version tag:
```bash
git tag v0.2.0
git push origin v0.2.0
```

The CD pipeline will automatically:
1. Build Docker image
2. Push to Azure Container Registry
3. Deploy to Azure Container Instance
4. Verify deployment

## Step 3: Verify Deployment

### Check Container Status
```bash
az container show \
  --resource-group rg-elli-prod \
  --name aci-elli-prod \
  --query "{Status:instanceView.state, Restarts:containers[0].instanceView.restartCount}"
```

### View Logs
```bash
az container logs \
  --resource-group rg-elli-prod \
  --name aci-elli-prod \
  --follow
```

### Test in Slack
1. Send a message to Elli: `@Elli hello`
2. Try `/ask-deal-agent What deals are in negotiation?`
3. Create a test deal from a thread

## Configuration

### Environment Variables

The container uses these environment variables (set via Azure CLI or Portal):

| Variable | Source | Description |
|----------|--------|-------------|
| `SLACK_BOT_TOKEN` | Key Vault | Bot token from Slack |
| `SLACK_APP_TOKEN` | Key Vault | App token for Socket Mode |
| `SF_CONSUMER_KEY` | Key Vault | Salesforce OAuth consumer key |
| `SF_CONSUMER_SECRET` | Key Vault | Salesforce OAuth consumer secret |
| `SF_REFRESH_TOKEN` | Key Vault | Salesforce OAuth refresh token |
| `SNOWFLAKE_USER` | Key Vault | Snowflake service account |
| `SNOWFLAKE_ACCOUNT` | Key Vault | Snowflake account identifier |
| `SNOWFLAKE_PRIVATE_KEY` | Key Vault | Base64-encoded RSA private key |
| `ENVIRONMENT` | Container | `production` |
| `LOG_LEVEL` | Container | `INFO` |

### Resource Sizing

Default configuration (suitable for small team):
- **CPU**: 1 core
- **Memory**: 1.5 GB
- **Restart Policy**: Always

For larger deployments, adjust in `deploy-azure.sh`:
```bash
CPU_CORES=2
MEMORY_GB=4
```

## Troubleshooting

### Container Won't Start

1. Check logs:
   ```bash
   az container logs --resource-group rg-elli-prod --name aci-elli-prod
   ```

2. Verify secrets in Key Vault:
   ```bash
   az keyvault secret list --vault-name kv-elli-prod -o table
   ```

3. Check container events:
   ```bash
   az container show \
     --resource-group rg-elli-prod \
     --name aci-elli-prod \
     --query "containers[0].instanceView.events"
   ```

### Slack Not Responding

1. Verify Socket Mode is enabled in Slack App settings
2. Check that `SLACK_APP_TOKEN` starts with `xapp-`
3. Look for WebSocket connection errors in logs

### Salesforce Errors

1. Verify refresh token is still valid
2. Check SF_INSTANCE_URL matches your Salesforce org
3. Re-run OAuth flow locally if needed:
   ```bash
   python -c "from services.sf_oauth import run_oauth_flow; run_oauth_flow()"
   ```
   Then update Key Vault with new refresh token.

### Snowflake Connection Issues

1. Verify account format: `ACCOUNT.region` (e.g., `ELDRIDGE-ECM.azure_eastus2`)
2. Check private key is base64 encoded correctly
3. Verify user has necessary permissions

## Updating the Deployment

### Code Changes
```bash
# Push to main branch triggers automatic deployment
git push origin main

# Or manually:
./scripts/deploy-azure.sh all
```

### Secret Updates
```bash
# Update secret in Key Vault
az keyvault secret set --vault-name kv-elli-prod --name SECRET-NAME --value "new-value"

# Redeploy container to pick up new secret
./scripts/deploy-azure.sh deploy
```

## Cost Estimate

| Resource | Monthly Cost (Est.) |
|----------|---------------------|
| Container Instance (1 CPU, 1.5GB, always-on) | ~$35 |
| Container Registry (Basic) | ~$5 |
| Key Vault (secrets storage) | ~$1 |
| **Total** | **~$41/month** |

## Security Considerations

1. **Secrets**: All sensitive values stored in Azure Key Vault, not in code or environment files
2. **Network**: Socket Mode means no inbound ports exposed
3. **Container**: Runs as non-root user (appuser)
4. **Registry**: Private ACR with admin credentials
5. **Logs**: No secrets logged (secure-environment-variables)

## Rollback

To rollback to a previous version:

1. List available images:
   ```bash
   az acr repository show-tags --name elliacr --repository elli-slack-bot --orderby time_desc
   ```

2. Deploy specific version:
   ```bash
   IMAGE_TAG=v0.1.0 ./scripts/deploy-azure.sh deploy
   ```

Or use GitHub Actions workflow_dispatch with "rollback" action.
