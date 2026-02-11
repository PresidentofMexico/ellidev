// Azure Container Instance Module
// Runs Elli Slack Bot in a Docker container

@description('Name of the container group')
param containerGroupName string

@description('Location for the container')
param location string = resourceGroup().location

@description('Container image to deploy (e.g., elliacr.azurecr.io/elli-slack-bot:latest)')
param containerImage string

@description('Name of the container registry')
param acrName string

@description('Container registry login server')
param acrLoginServer string

@description('Resource ID of the user-assigned managed identity')
param managedIdentityId string

@description('Key Vault name for secret references')
param keyVaultName string

@description('Number of CPU cores')
param cpuCores int = 1

@description('Memory in GB')
@minValue(1)
@maxValue(16)
param memoryInGb int = 2

@description('Restart policy')
@allowed([
  'Always'
  'OnFailure'
  'Never'
])
param restartPolicy string = 'Always'

@description('Tags to apply to the resource')
param tags object = {}

// Reference existing Key Vault
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
}

// Reference existing ACR
resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = {
  name: acrName
}

resource containerGroup 'Microsoft.ContainerInstance/containerGroups@2023-05-01' = {
  name: containerGroupName
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${managedIdentityId}': {}
    }
  }
  properties: {
    containers: [
      {
        name: 'elli-slack-bot'
        properties: {
          image: containerImage
          resources: {
            requests: {
              cpu: cpuCores
              memoryInGB: memoryInGb
            }
          }
          environmentVariables: [
            // Slack Configuration (secrets from Key Vault)
            {
              name: 'SLACK_BOT_TOKEN'
              secureValue: keyVault.getSecret('SLACK-BOT-TOKEN')
            }
            {
              name: 'SLACK_APP_TOKEN'
              secureValue: keyVault.getSecret('SLACK-APP-TOKEN')
            }
            // Salesforce OAuth Configuration
            {
              name: 'SF_CONSUMER_KEY'
              secureValue: keyVault.getSecret('SF-CONSUMER-KEY')
            }
            {
              name: 'SF_CONSUMER_SECRET'
              secureValue: keyVault.getSecret('SF-CONSUMER-SECRET')
            }
            {
              name: 'SF_REFRESH_TOKEN'
              secureValue: keyVault.getSecret('SF-REFRESH-TOKEN')
            }
            {
              name: 'SF_INSTANCE_URL'
              secureValue: keyVault.getSecret('SF-INSTANCE-URL')
            }
            // Snowflake Configuration
            {
              name: 'SNOWFLAKE_ACCOUNT'
              secureValue: keyVault.getSecret('SNOWFLAKE-ACCOUNT')
            }
            {
              name: 'SNOWFLAKE_USER'
              secureValue: keyVault.getSecret('SNOWFLAKE-USER')
            }
            {
              name: 'SNOWFLAKE_DATABASE'
              secureValue: keyVault.getSecret('SNOWFLAKE-DATABASE')
            }
            {
              name: 'SNOWFLAKE_SCHEMA'
              secureValue: keyVault.getSecret('SNOWFLAKE-SCHEMA')
            }
            {
              name: 'SNOWFLAKE_WAREHOUSE'
              secureValue: keyVault.getSecret('SNOWFLAKE-WAREHOUSE')
            }
            {
              name: 'SNOWFLAKE_ROLE'
              secureValue: keyVault.getSecret('SNOWFLAKE-ROLE')
            }
            // Cortex Analyst Configuration
            {
              name: 'CORTEX_ANALYST_PAT'
              secureValue: keyVault.getSecret('CORTEX-ANALYST-PAT')
            }
            {
              name: 'CORTEX_ANALYST_ACCOUNT'
              secureValue: keyVault.getSecret('CORTEX-ANALYST-ACCOUNT')
            }
            {
              name: 'CORTEX_ANALYST_REGION'
              secureValue: keyVault.getSecret('CORTEX-ANALYST-REGION')
            }
            // Channel-Based Opportunity Configuration
            {
              name: 'CHANNEL_BU_MAPPING'
              secureValue: keyVault.getSecret('CHANNEL-BU-MAPPING')
            }
            {
              name: 'BU_RECORD_TYPES'
              secureValue: keyVault.getSecret('BU-RECORD-TYPES')
            }
            {
              name: 'BU_FIELD_DEFAULTS'
              secureValue: keyVault.getSecret('BU-FIELD-DEFAULTS')
            }
            // Non-secret environment variables
            {
              name: 'CORTEX_ANALYST_ENABLED'
              value: 'true'
            }
            {
              name: 'CORTEX_ANALYST_AGENT'
              value: 'DEAL_AGENT'
            }
            {
              name: 'CORTEX_ANALYST_DATABASE'
              value: 'DEV_CURATE'
            }
            {
              name: 'CORTEX_ANALYST_SCHEMA'
              value: 'CORE'
            }
            {
              name: 'LOG_LEVEL'
              value: 'INFO'
            }
            {
              name: 'LOG_FORMAT'
              value: 'json'
            }
          ]
        }
      }
    ]
    osType: 'Linux'
    restartPolicy: restartPolicy
    imageRegistryCredentials: [
      {
        server: acrLoginServer
        identity: managedIdentityId
      }
    ]
    // No public IP needed - Socket Mode uses outbound connections only
    ipAddress: {
      type: 'Private'
      ports: []
    }
  }
}

@description('The resource ID of the container group')
output id string = containerGroup.id

@description('The name of the container group')
output name string = containerGroup.name
