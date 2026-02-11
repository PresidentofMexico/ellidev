// Azure Key Vault Module
// Stores secrets for Elli Slack Bot (Slack tokens, Salesforce credentials, etc.)

@description('Name of the key vault')
param keyVaultName string

@description('Location for the key vault')
param location string = resourceGroup().location

@description('SKU for the key vault')
@allowed([
  'standard'
  'premium'
])
param sku string = 'standard'

@description('Tenant ID for the key vault')
param tenantId string = subscription().tenantId

@description('Principal IDs that need access to secrets')
param accessPolicies array = []

@description('Enable RBAC authorization (recommended)')
param enableRbacAuthorization bool = true

@description('Enable soft delete')
param enableSoftDelete bool = true

@description('Soft delete retention in days')
param softDeleteRetentionInDays int = 90

@description('Tags to apply to the resource')
param tags object = {}

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  tags: tags
  properties: {
    sku: {
      family: 'A'
      name: sku
    }
    tenantId: tenantId
    enableRbacAuthorization: enableRbacAuthorization
    enableSoftDelete: enableSoftDelete
    softDeleteRetentionInDays: softDeleteRetentionInDays
    enabledForDeployment: false
    enabledForDiskEncryption: false
    enabledForTemplateDeployment: true
    publicNetworkAccess: 'Enabled'
    accessPolicies: enableRbacAuthorization ? [] : accessPolicies
  }
}

@description('The resource ID of the key vault')
output id string = keyVault.id

@description('The name of the key vault')
output name string = keyVault.name

@description('The URI of the key vault')
output vaultUri string = keyVault.properties.vaultUri
