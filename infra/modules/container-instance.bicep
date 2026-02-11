// Azure Container Instance Module
// Runs Elli Slack Bot in a Docker container

@description('Name of the container group')
param containerGroupName string

@description('Location for the container')
param location string = resourceGroup().location

@description('Container image to deploy (e.g., elliacr.azurecr.io/elli:latest)')
param containerImage string

@description('Container registry login server')
param acrLoginServer string

@description('Resource ID of the user-assigned managed identity')
param managedIdentityId string

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

@description('DNS name label for public IP')
param dnsNameLabel string = 'elli-slack-bot'

@description('Tags to apply to the resource')
param tags object = {}

// Secrets passed from main.bicep via Key Vault getSecret()
@secure()
@description('Slack bot token')
param slackBotToken string

@secure()
@description('Slack app token')
param slackAppToken string

@secure()
@description('Salesforce consumer key')
param sfConsumerKey string

@secure()
@description('Salesforce consumer secret')
param sfConsumerSecret string

@secure()
@description('Salesforce refresh token')
param sfRefreshToken string

@secure()
@description('Salesforce org ID')
param sfOrgId string

@secure()
@description('Snowflake private key path')
param snowflakePrivKeyPath string

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
              secureValue: slackBotToken
            }
            {
              name: 'SLACK_APP_TOKEN'
              secureValue: slackAppToken
            }
            // Salesforce OAuth Configuration
            {
              name: 'SF_CONSUMER_KEY'
              secureValue: sfConsumerKey
            }
            {
              name: 'SF_CONSUMER_SECRET'
              secureValue: sfConsumerSecret
            }
            {
              name: 'SF_REFRESH_TOKEN'
              secureValue: sfRefreshToken
            }
            {
              name: 'SF_ORG_ID'
              secureValue: sfOrgId
            }
            // Snowflake Configuration
            {
              name: 'SNOWFLAKE_PRIVATE_KEY_PATH'
              secureValue: snowflakePrivKeyPath
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
          ports: [
            {
              port: 8000
              protocol: 'TCP'
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
    // Public IP with DNS name label and port 8000
    ipAddress: {
      type: 'Public'
      dnsNameLabel: dnsNameLabel
      ports: [
        {
          port: 8000
          protocol: 'TCP'
        }
      ]
    }
  }
}

@description('The resource ID of the container group')
output id string = containerGroup.id

@description('The name of the container group')
output name string = containerGroup.name

@description('The FQDN of the container group')
output fqdn string = containerGroup.properties.ipAddress.fqdn
