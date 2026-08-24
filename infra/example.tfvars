location = "germanywestcentral"

# Optional
virtual_network_address_space          = "192.168.0.0/16"
agent_subnet_address_prefix            = "192.168.0.0/24"
private_endpoint_subnet_address_prefix = "192.168.1.0/24"
apim_subnet_address_prefix             = "192.168.2.0/27"
function_app_subnet_address_prefix     = "192.168.3.0/24"

# APIM publisher metadata (shown in the Developer portal)
apim_publisher_name  = "Foundry Platform Team"
apim_publisher_email = "admin@example.com"

# Required for APIM JWT validation of Teams / Bot Service traffic.
# bot_app_id  = the Microsoft App ID of the Azure Bot Service that fronts the
#               'extreme-safe-agent' agent (find under the Bot's Configuration
#               blade in the Azure portal).
bot_app_id = ""

# OAuth redirect URI(s) shown by Microsoft Foundry when registering the Function
# App as an MCP tool (Authentication = OAuth Identity Passthrough). Click "Add
# tool", read the redirect URI Foundry displays, and paste it here so subsequent
# `terraform apply` runs do not strip it from the app registration. Leave the
# list empty on the very first apply (before Foundry has been wired up).
foundry_mcp_redirect_uris = [
  "",
]
