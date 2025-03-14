param name string
metadata description = 'Creates an Azure Cognitive Services instance.'
param location string = resourceGroup().location
param tags object = {}
param vnetId string = ''
param subnetId string = ''
param logAnalyticsWorkspaceId string = ''
param enableMetrics bool = true


resource documentIntelligence 'Microsoft.CognitiveServices/accounts@2024-10-01' = if (!empty(vnetId) && !empty(subnetId)) {
  name: name
  location: 'japaneast'
  sku: {
    name: 'F0'
  }
  kind: 'FormRecognizer'
  identity: {
    type: 'None'
  }
  properties: {
    customSubDomainName: name
    networkAcls: {
      defaultAction: 'Allow'
      virtualNetworkRules: []
      ipRules: []
    }
    publicNetworkAccess: 'Enabled'
  }
}

resource diagnosticSettings 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = if (!empty(logAnalyticsWorkspaceId)) {
  name: 'diag-${name}'
  scope: documentIntelligence
  properties: {
    workspaceId: logAnalyticsWorkspaceId
    metrics: enableMetrics
      ? [
          {
            category: 'AllMetrics'
            enabled: true
          }
        ]
      : []
  }
}


//Create the private endpoint
resource privateDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' = if (!empty(vnetId) && !empty(subnetId)) {
  name: 'privatelink.documentIntelligence.azure.com'
  location: 'global'
  tags: {}
  properties: {}

  resource virtualNetworkLink 'virtualNetworkLinks' = {
    name: '${privateDnsZone.name}-link'
    location: 'global'
    properties: {
      virtualNetwork: {
        id: vnetId
      }
      registrationEnabled: false
    }
  }
}

resource privateEndpointAoai 'Microsoft.Network/privateEndpoints@2023-04-01' = if (!empty(vnetId) && !empty(subnetId)) {
  name: 'pep-${name}'
  location: location
  properties: {
    subnet: {
      id: subnetId
    }
    customNetworkInterfaceName: 'pep-nic-documentIntelligence'
    privateLinkServiceConnections: [
      {
        name: 'link-${name}'
        properties: {
          privateLinkServiceId: documentIntelligence.id
          groupIds: [
            'documentintelligence'
          ]
        }
      }
    ]
  }
  tags: tags
  dependsOn: [privateDnsZone]

  resource privateDnsZoneGroup 'privateDnsZoneGroups' = {
    name: '${privateDnsZone.name}-group'
    properties: {
      privateDnsZoneConfigs: [
        {
          name: privateDnsZone.name
          properties: {
            privateDnsZoneId: privateDnsZone.id
          }
        }
      ]
    }
  }
}

output endpoint string = documentIntelligence.properties.endpoint
output id string = documentIntelligence.id
output name string = documentIntelligence.name
