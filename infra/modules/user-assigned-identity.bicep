// User-Assigned Managed Identity Module
// Used by Container Instance to securely access Key Vault secrets

@description('Name of the managed identity')
param identityName string

@description('Location for the identity')
param location string = resourceGroup().location

@description('Tags to apply to the resource')
param tags object = {}

resource managedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: identityName
  location: location
  tags: tags
}

@description('The resource ID of the managed identity')
output id string = managedIdentity.id

@description('The principal ID of the managed identity')
output principalId string = managedIdentity.properties.principalId

@description('The client ID of the managed identity')
output clientId string = managedIdentity.properties.clientId

@description('The name of the managed identity')
output name string = managedIdentity.name
