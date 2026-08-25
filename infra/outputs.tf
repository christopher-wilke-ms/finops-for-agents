output "foundry_account_url" {
  description = "AI Foundry account public URL"
  value       = "https://${azapi_resource.ai_foundry.name}.services.ai.azure.com"
}

output "foundry_project_name" {
  description = "AI Foundry project name"
  value       = azapi_resource.ai_foundry_project.name
}

output "agent_endpoint" {
  description = "Bot Service messaging endpoint for Foundry agent"
  value       = "https://${azapi_resource.ai_foundry.name}.services.ai.azure.com/api/projects/${azapi_resource.ai_foundry_project.name}/agents/{agent-name}/endpoint/protocols/activityprotocol?api-version=2025-05-15-preview"
}

output "storage_account_name" {
  description = "Storage account name for agent data"
  value       = azurerm_storage_account.storage.name
}

output "cosmosdb_endpoint" {
  description = "Cosmos DB endpoint"
  value       = azurerm_cosmosdb_account.cosmosdb.endpoint
}

output "aisearch_name" {
  description = "AI Search service name"
  value       = azapi_resource.ai_search.name
}
