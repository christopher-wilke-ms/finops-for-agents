########## Create infrastructure resources
##########

data "azurerm_client_config" "current" {}

resource "random_string" "unique" {
  length      = 4
  min_numeric = 4
  numeric     = true
  special     = false
  lower       = true
  upper       = false
}

resource "azurerm_resource_group" "rg" {
  name     = "ms-hackathon-finops-agent-rg"
  location = var.location
}

########## Create Log Analytics for monitoring
##########

resource "azurerm_log_analytics_workspace" "logs" {
  name                = "log-foundry-${random_string.unique.result}"
  location            = var.location
  resource_group_name = azurerm_resource_group.rg.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

########## Create storage and data services
##########

resource "azurerm_storage_account" "storage" {
  name                = "aifoundry${random_string.unique.result}storage"
  resource_group_name = azurerm_resource_group.rg.name
  location            = var.location

  account_kind             = "StorageV2"
  account_tier             = "Standard"
  account_replication_type = "LRS"

  shared_access_key_enabled       = false
  min_tls_version                 = "TLS1_2"
  allow_nested_items_to_be_public = false
  public_network_access_enabled   = true
}

resource "azurerm_cosmosdb_account" "cosmosdb" {
  name                = "aifoundry${random_string.unique.result}cosmosdb"
  location            = var.location
  resource_group_name = azurerm_resource_group.rg.name

  offer_type        = "Standard"
  kind              = "GlobalDocumentDB"
  free_tier_enabled = false

  local_authentication_enabled = false
  public_network_access_enabled = true

  automatic_failover_enabled       = false
  multiple_write_locations_enabled = false

  consistency_policy {
    consistency_level = "Session"
  }

  geo_location {
    location          = var.location
    failover_priority = 0
    zone_redundant    = false
  }
}

resource "azapi_resource" "ai_search" {
  type                      = "Microsoft.Search/searchServices@2025-05-01"
  name                      = "aifoundry${random_string.unique.result}search"
  parent_id                 = azurerm_resource_group.rg.id
  location                  = var.location
  schema_validation_enabled = true

  body = {
    sku = {
      name = "standard"
    }

    identity = {
      type = "SystemAssigned"
    }

    properties = {
      replicaCount   = 1
      partitionCount = 1
      hostingMode    = "Default"
      semanticSearch = "disabled"

      disableLocalAuth = false
      authOptions = {
        aadOrApiKey = {
          aadAuthFailureMode = "http401WithBearerChallenge"
        }
      }
      publicNetworkAccess = "Enabled"
      networkRuleSet = {
        bypass = "AzureServices"
      }
    }
  }
}

########## Create AI Foundry resource
##########

resource "azapi_resource" "ai_foundry" {
  type                      = "Microsoft.CognitiveServices/accounts@2025-06-01"
  name                      = "aifoundry${random_string.unique.result}"
  parent_id                 = azurerm_resource_group.rg.id
  location                  = var.location
  schema_validation_enabled = false

  body = {
    kind = "AIServices"
    sku = {
      name = "S0"
    }
    identity = {
      type = "SystemAssigned"
    }

    properties = {
      disableLocalAuth       = true
      allowProjectManagement = true
      customSubDomainName    = "aifoundry${random_string.unique.result}"
      publicNetworkAccess    = "Enabled"
      networkAcls = {
        defaultAction = "Allow"
      }
    }
  }
}

resource "azurerm_cognitive_deployment" "gpt_deployment" {
  depends_on = [
    azapi_resource.ai_foundry
  ]

  name                 = "gpt-5-mini"
  cognitive_account_id = azapi_resource.ai_foundry.id

  sku {
    name     = "GlobalStandard"
    capacity = 449
  }

  model {
    format  = "OpenAI"
    name    = "gpt-5-mini"
    version = "2025-08-07"
  }
}

resource "time_sleep" "wait_foundry" {
  depends_on = [
    azurerm_cognitive_deployment.gpt_deployment
  ]
  create_duration = "30s"
}

########## Create AI Foundry project
##########

resource "azapi_resource" "ai_foundry_project" {
  depends_on = [
    time_sleep.wait_foundry
  ]

  type                      = "Microsoft.CognitiveServices/accounts/projects@2025-06-01"
  name                      = "project${random_string.unique.result}"
  parent_id                 = azapi_resource.ai_foundry.id
  location                  = var.location
  schema_validation_enabled = false

  body = {
    sku = {
      name = "S0"
    }
    identity = {
      type = "SystemAssigned"
    }

    properties = {
      displayName = "finops-agent-project"
      description = "Project for FinOps agent"
    }
  }

  response_export_values = [
    "identity.principalId",
    "properties.internalId"
  ]
}

resource "time_sleep" "wait_project" {
  depends_on = [
    azapi_resource.ai_foundry_project
  ]
  create_duration = "60s"
}

########## Create project connections
##########

resource "azapi_resource" "conn_storage" {
  type                      = "Microsoft.CognitiveServices/accounts/projects/connections@2025-06-01"
  name                      = azurerm_storage_account.storage.name
  parent_id                 = azapi_resource.ai_foundry_project.id
  schema_validation_enabled = false

  body = {
    name = azurerm_storage_account.storage.name
    properties = {
      category = "AzureStorageAccount"
      target   = azurerm_storage_account.storage.primary_blob_endpoint
      authType = "AAD"
      metadata = {
        ApiType    = "Azure"
        ResourceId = azurerm_storage_account.storage.id
        location   = var.location
      }
    }
  }
}

resource "azapi_resource" "conn_cosmosdb" {
  type                      = "Microsoft.CognitiveServices/accounts/projects/connections@2025-06-01"
  name                      = azurerm_cosmosdb_account.cosmosdb.name
  parent_id                 = azapi_resource.ai_foundry_project.id
  schema_validation_enabled = false

  body = {
    name = azurerm_cosmosdb_account.cosmosdb.name
    properties = {
      category = "CosmosDb"
      target   = azurerm_cosmosdb_account.cosmosdb.endpoint
      authType = "AAD"
      metadata = {
        ApiType    = "Azure"
        ResourceId = azurerm_cosmosdb_account.cosmosdb.id
        location   = var.location
      }
    }
  }
}

resource "azapi_resource" "conn_aisearch" {
  type                      = "Microsoft.CognitiveServices/accounts/projects/connections@2025-06-01"
  name                      = azapi_resource.ai_search.name
  parent_id                 = azapi_resource.ai_foundry_project.id
  schema_validation_enabled = false

  body = {
    name = azapi_resource.ai_search.name
    properties = {
      category = "CognitiveSearch"
      target   = "https://${azapi_resource.ai_search.name}.search.windows.net"
      authType = "AAD"
      metadata = {
        ApiType    = "Azure"
        ApiVersion = "2025-05-01-preview"
        ResourceId = azapi_resource.ai_search.id
        location   = var.location
      }
    }
  }
}

########## Create role assignments
##########

resource "azurerm_role_assignment" "project_storage" {
  depends_on = [
    time_sleep.wait_project
  ]

  scope              = azurerm_storage_account.storage.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id       = azapi_resource.ai_foundry_project.output.identity.principalId
}

resource "azurerm_role_assignment" "project_cosmosdb" {
  depends_on = [
    time_sleep.wait_project
  ]

  scope                = azurerm_cosmosdb_account.cosmosdb.id
  role_definition_name = "Cosmos DB Operator"
  principal_id         = azapi_resource.ai_foundry_project.output.identity.principalId
}

resource "azurerm_role_assignment" "project_search" {
  depends_on = [
    time_sleep.wait_project
  ]

  scope                = azapi_resource.ai_search.id
  role_definition_name = "Search Index Data Contributor"
  principal_id         = azapi_resource.ai_foundry_project.output.identity.principalId
}

resource "time_sleep" "wait_rbac" {
  depends_on = [
    azurerm_role_assignment.project_storage,
    azurerm_role_assignment.project_cosmosdb,
    azurerm_role_assignment.project_search
  ]
  create_duration = "30s"
}
