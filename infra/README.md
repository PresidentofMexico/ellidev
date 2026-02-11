# Elli Infrastructure as Code (Bicep)

This folder contains Azure Bicep templates for deploying Elli Slack Bot infrastructure.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 Azure Resource Group (rg-elli-prod)          │
│                                                              │
│  ┌──────────────────┐                                       │
│  │   Managed        │                                       │
│  │   Identity       │──────────────────────────┐            │
│  │  (id-elli-prod)  │                          │            │
│  └────────┬─────────┘                          │            │
│           │ AcrPull                  Key Vault │            │
│           │ role                     Secrets   │            │
│           ▼                          User role ▼            │
│  ┌──────────────────┐       ┌────────────────────────────┐  │
│  │ Container        │       │      Azure Key Vault       │  │
│  │ Registry         │       │     (kv-elli-prod)         │  │
│  │ (elliacrprod)    │       │  - SLACK-BOT-TOKEN         │  │
│  └────────┬─────────┘       │  - SF-REFRESH-TOKEN        │  │
│           │                 │  - CHANNEL-BU-MAPPING      │  │
│           │ pulls image     │  - etc.                    │  │
│           ▼                 └────────────────────────────┘  │
│  ┌──────────────────┐                    ▲                  │
│  │ Container        │                    │                  │
│  │ Instance         │────────────────────┘                  │
│  │ (aci-elli-prod)  │  reads secrets at runtime             │
│  └──────────────────┘                                       │
└─────────────────────────────────────────────────────────────┘
```

## Files

| File | Purpose |
|------|---------|
| `main.bicep` | Main orchestration template |
| `parameters.json` | Development environment parameters |
| `parameters.prod.json` | Production environment parameters |
| `modules/acr.bicep` | Azure Container Registry |
| `modules/keyvault.bicep` | Azure Key Vault |
| `modules/user-assigned-identity.bicep` | Managed Identity |
| `modules/container-instance.bicep` | Container Instance |

## Deployment Steps

### 1. Create Resource Group

```bash
az group create --name rg-elli-prod --location eastus2
```

### 2. Deploy Infrastructure (without container)

First, deploy just the ACR, Key Vault, and Identity:

```bash
# Login to Azure
az login

# Deploy infrastructure
az deployment group create \
  --resource-group rg-elli-prod \
  --template-file infra/main.bicep \
  --parameters infra/parameters.prod.json
```

### 3. Populate Key Vault Secrets

**IMPORTANT:** Secrets must be populated before the container can start successfully.

```bash
# Slack tokens (REQUIRED)
az keyvault secret set --vault-name kv-elli-prod --name "SLACK-BOT-TOKEN" --value "xoxb-your-token"
az keyvault secret set --vault-name kv-elli-prod --name "SLACK-APP-TOKEN" --value "xapp-your-token"

# Salesforce OAuth (REQUIRED for deal creation)
az keyvault secret set --vault-name kv-elli-prod --name "SF-CONSUMER-KEY" --value "your-consumer-key"
az keyvault secret set --vault-name kv-elli-prod --name "SF-CONSUMER-SECRET" --value "your-consumer-secret"
az keyvault secret set --vault-name kv-elli-prod --name "SF-REFRESH-TOKEN" --value "your-refresh-token"
az keyvault secret set --vault-name kv-elli-prod --name "SF-INSTANCE-URL" --value "https://eldridge.my.salesforce.com"

# Snowflake (OPTIONAL)
az keyvault secret set --vault-name kv-elli-prod --name "SNOWFLAKE-ACCOUNT" --value "ELDRIDGE-ECM.azure_eastus2"
az keyvault secret set --vault-name kv-elli-prod --name "SNOWFLAKE-USER" --value "elli_service_account"
az keyvault secret set --vault-name kv-elli-prod --name "SNOWFLAKE-DATABASE" --value "ELLI_PROD"
az keyvault secret set --vault-name kv-elli-prod --name "SNOWFLAKE-SCHEMA" --value "PUBLIC"
az keyvault secret set --vault-name kv-elli-prod --name "SNOWFLAKE-WAREHOUSE" --value "ELLI_XS"
az keyvault secret set --vault-name kv-elli-prod --name "SNOWFLAKE-ROLE" --value "ELLI_READONLY"

# Cortex Analyst (OPTIONAL)
az keyvault secret set --vault-name kv-elli-prod --name "CORTEX-ANALYST-PAT" --value "your-pat"
az keyvault secret set --vault-name kv-elli-prod --name "CORTEX-ANALYST-ACCOUNT" --value "ara18269"
az keyvault secret set --vault-name kv-elli-prod --name "CORTEX-ANALYST-REGION" --value "east-us-2.azure"

# Channel Configuration (OPTIONAL - for pilot)
az keyvault secret set --vault-name kv-elli-prod --name "CHANNEL-BU-MAPPING" --value '{"C12345ABC":"private_credit"}'
az keyvault secret set --vault-name kv-elli-prod --name "BU-RECORD-TYPES" --value '{"private_credit":"012xxx","default":"012yyy"}'
az keyvault secret set --vault-name kv-elli-prod --name "BU-FIELD-DEFAULTS" --value '{"private_credit":{"Strategy__c":"Corporate Credit"}}'
```

### 4. Build and Push Docker Image

```bash
# Build image directly in ACR
az acr build --registry elliacrprod --image elli-slack-bot:latest .
```

### 5. Redeploy Container (if needed)

If the container failed to start because secrets weren't ready:

```bash
# Restart the container
az container restart --resource-group rg-elli-prod --name aci-elli-prod
```

## Verification

```bash
# Check container status
az container show --resource-group rg-elli-prod --name aci-elli-prod --query "instanceView.state"

# View container logs
az container logs --resource-group rg-elli-prod --name aci-elli-prod --follow

# List Key Vault secrets (names only)
az keyvault secret list --vault-name kv-elli-prod --query "[].name" -o tsv
```

## Troubleshooting

### Container keeps restarting

1. Check if all required secrets are populated
2. View logs: `az container logs --resource-group rg-elli-prod --name aci-elli-prod`
3. Common issues:
   - Missing SLACK_BOT_TOKEN or SLACK_APP_TOKEN
   - Invalid Salesforce credentials (expired refresh token)

### Permission denied accessing Key Vault

1. Verify managed identity has "Key Vault Secrets User" role
2. Check role assignments: `az role assignment list --scope /subscriptions/{sub}/resourceGroups/rg-elli-prod`

### Image pull fails

1. Verify managed identity has "AcrPull" role
2. Check ACR login server in container config matches actual ACR name
3. Verify image exists: `az acr repository show-tags --name elliacrprod --repository elli-slack-bot`

## Resource Naming Convention

| Resource Type | Naming Pattern | Example |
|--------------|----------------|---------|
| Resource Group | `rg-{app}-{env}` | `rg-elli-prod` |
| Container Registry | `{app}acr{env}` | `elliacrprod` |
| Key Vault | `kv-{app}-{env}` | `kv-elli-prod` |
| Managed Identity | `id-{app}-{env}` | `id-elli-prod` |
| Container Instance | `aci-{app}-{env}` | `aci-elli-prod` |

## Cost Estimate

- **Container Instance**: ~$30-40/month (1 CPU, 2GB RAM, always-on)
- **Container Registry (Standard)**: ~$5/month
- **Key Vault**: ~$0.03/10,000 operations (minimal cost)
- **Total**: ~$35-50/month
