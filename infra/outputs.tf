output "apim_gateway_url" {
  description = "Public HTTPS gateway URL for the APIM instance. Use this as the host portion of the Bot Service messaging endpoint."
  value       = azurerm_api_management.apim.gateway_url
}

output "foundry_account_hostname" {
  description = "Foundry account hostname (resolves to its private endpoint inside this VNet)."
  value       = "${azapi_resource.ai_foundry.name}.services.ai.azure.com"
}

output "foundry_project_name" {
  description = "Name of the Foundry project hosting the agent."
  value       = azapi_resource.ai_foundry_project.name
}

output "next_step_messaging_endpoint_hint" {
  description = "Template for the new Bot Service messaging endpoint. Replace <agent-id> and any trailing path with the values from your current 'extreme-safe-agent' messaging endpoint."
  value       = "${azurerm_api_management.apim.gateway_url}/api/projects/${azapi_resource.ai_foundry_project.name}/channelAdapter/<agent-id>/..."
}

########## Front Door (WAF) outputs
##########

output "frontdoor_endpoint_hostname" {
  description = "Public Front Door endpoint hostname (*.azurefd.net) with a managed, publicly-trusted TLS certificate. This is the new public entry point in front of APIM."
  value       = azurerm_cdn_frontdoor_endpoint.fd.host_name
}

output "frontdoor_bot_messaging_endpoint" {
  description = "New Azure Bot messaging endpoint routed through Front Door (WAF). Set this on the bot with 'az bot update --endpoint'."
  value       = "https://${azurerm_cdn_frontdoor_endpoint.fd.host_name}/api/projects/${azapi_resource.ai_foundry_project.name}/agents/SuperFunnyRustAgent/endpoint/protocols/activityprotocol?api-version=2025-05-15-preview"
}
