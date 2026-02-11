// Azure Container Registry Module
// Stores Docker images for Elli Slack Bot

@description('Name of the container registry')
param acrName string

@description('Location for the registry')
param location string = resourceGroup().location

@description('SKU for the container registry')
@allowed([
  'Basic'
  'Standard'
  'Premium'
])
param sku string = 'Basic'

@description('Enable admin user for initial testing')
param adminUserEnabled bool = true

@description('Tags to apply to the resource')
param tags object = {}

resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  tags: tags
  sku: {
    name: sku
  }
  properties: {
    adminUserEnabled: adminUserEnabled
    publicNetworkAccess: 'Enabled'
  }
}

@description('The login server URL for the container registry')
output loginServer string = containerRegistry.properties.loginServer

@description('The resource ID of the container registry')
output id string = containerRegistry.id

@description('The name of the container registry')
output name string = containerRegistry.name
