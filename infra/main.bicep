// Main Bicep Template for Elli Slack Bot Infrastructure
// Orchestrates deployment of all Azure resources

@description('Environment name (dev, staging, prod)')
@allowed([
  'dev'
  'staging'
  'prod'
])
param environment string = 'prod'

@description('Location for all resources')
param location string = resourceGroup().location

@description('Base name for resources')
param baseName string = 'elli'

@description('Container image tag')
param imageTag string = 'latest'

@description('Container image name (repository name in ACR)')
param containerImageName string = 'elli'

@description('DNS name label for the container instance')
param dnsNameLabel string = 'elli-slack-bot'

@description('Number of CPU cores for the container')
param cpuCores int = 1

@description('Memory in GB for the container')
param memoryInGb int = 2

// Generate resource names based on environment
// ACR name matches actual Azure resource: 'elliacr'
var acrName = '${baseName}acr'
var keyVaultName = 'kv-${baseName}-secrets'
var identityName = 'id-${baseName}-${environment}'
var containerGroupName = 'aci-${baseName}-${environment}'

var tags = {
  application: 'elli-slack-bot'
  environment: environment
  managedBy: 'bicep'
}

// Deploy User-Assigned Managed Identity first
module identity 'modules/user-assigned-identity.bicep' = {
  name: 'identity-deployment'
  params: {
    identityName: identityName
    location: location
    tags: tags
  }
}

// Deploy Azure Container Registry
module acr 'modules/acr.bicep' = {
  name: 'acr-deployment'
  params: {
    acrName: acrName
    location: location
    sku: 'Basic'
    adminUserEnabled: true
    tags: tags
  }
}

// Deploy Key Vault
module keyVault 'modules/keyvault.bicep' = {
  name: 'keyvault-deployment'
  params: {
    keyVaultName: keyVaultName
    location: location
    sku: 'standard'
    enableRbacAuthorization: true
    tags: tags
  }
}

// Reference the Key Vault resource for getSecret() calls
resource keyVaultRef 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
  dependsOn: [
    keyVault
  ]
}

// Assign Key Vault Secrets User role to the managed identity
resource keyVaultSecretsUserRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, identityName, 'Key Vault Secrets User')
  scope: resourceGroup()
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6') // Key Vault Secrets User
    principalId: identity.outputs.principalId
    principalType: 'ServicePrincipal'
  }
}

// Assign AcrPull role to the managed identity
resource acrPullRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, identityName, 'AcrPull')
  scope: resourceGroup()
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d') // AcrPull
    principalId: identity.outputs.principalId
    principalType: 'ServicePrincipal'
  }
}

// Deploy Container Instance (depends on Key Vault secrets being populated manually)
// NOTE: Before deploying container, ensure Key Vault secrets are populated!
module container 'modules/container-instance.bicep' = {
  name: 'container-deployment'
  params: {
    containerGroupName: containerGroupName
    location: location
    containerImage: '${acr.outputs.loginServer}/${containerImageName}:${imageTag}'
    acrLoginServer: acr.outputs.loginServer
    managedIdentityId: identity.outputs.id
    cpuCores: cpuCores
    memoryInGb: memoryInGb
    restartPolicy: 'Always'
    dnsNameLabel: dnsNameLabel
    tags: tags
    // Pass secrets from Key Vault to container module
    slackBotToken: keyVaultRef.getSecret('slack-bot-token')
    slackAppToken: keyVaultRef.getSecret('slack-app-token')
    sfConsumerKey: keyVaultRef.getSecret('sf-consumer-key')
    sfConsumerSecret: keyVaultRef.getSecret('sf-consumer-secret')
    sfRefreshToken: keyVaultRef.getSecret('sf-refresh-token')
    sfOrgId: keyVaultRef.getSecret('sf-org-id')
    snowflakePrivKeyPath: keyVaultRef.getSecret('snowflake-priv-key-path')
  }
  dependsOn: [
    keyVaultSecretsUserRole
    acrPullRole
  ]
}

// Outputs
@description('Container Registry login server')
output acrLoginServer string = acr.outputs.loginServer

@description('Container Registry name')
output acrName string = acr.outputs.name

@description('Key Vault name')
output keyVaultName string = keyVault.outputs.name

@description('Key Vault URI')
output keyVaultUri string = keyVault.outputs.vaultUri

@description('Container Group name')
output containerGroupName string = container.outputs.name

@description('Container Group FQDN')
output containerFqdn string = container.outputs.fqdn

@description('Managed Identity name')
output identityName string = identity.outputs.name

@description('Managed Identity principal ID')
output identityPrincipalId string = identity.outputs.principalId
