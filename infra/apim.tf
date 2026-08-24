########## Azure API Management — security layer in front of Foundry
##########
## APIM acts as the validation gateway for Bot Service traffic targeting the
## Foundry agent. Teams -> Bot Service -> APIM (validate-jwt + managed identity
## token exchange) -> Foundry private endpoint.

## Subnet dedicated to APIM (Developer SKU, External VNet mode).
##
resource "azurerm_subnet" "subnet_apim" {
  name                 = "snet-apim"
  resource_group_name  = azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes = [
    var.apim_subnet_address_prefix
  ]
}

## NSG required by APIM in VNet integration mode.
## Reference: https://learn.microsoft.com/azure/api-management/virtual-network-reference
##
resource "azurerm_network_security_group" "nsg_apim" {
  name                = "nsg-apim-${random_string.unique.result}"
  location            = var.location
  resource_group_name = azurerm_resource_group.rg.name

  security_rule {
    name                       = "AllowAPIMManagementInbound"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "3443"
    source_address_prefix      = "ApiManagement"
    destination_address_prefix = "VirtualNetwork"
  }

  security_rule {
    name                       = "AllowAzureLoadBalancerInbound"
    priority                   = 110
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "6390"
    source_address_prefix      = "AzureLoadBalancer"
    destination_address_prefix = "VirtualNetwork"
  }

  security_rule {
    name                       = "AllowClientHttpsInbound"
    priority                   = 120
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "AzureFrontDoor.Backend"
    destination_address_prefix = "VirtualNetwork"
  }
}

resource "azurerm_subnet_network_security_group_association" "nsg_apim_assoc" {
  subnet_id                 = azurerm_subnet.subnet_apim.id
  network_security_group_id = azurerm_network_security_group.nsg_apim.id
}

## APIM instance — Developer SKU, External VNet integration.
## Public gateway is reachable from Microsoft's Bot Service; outbound traffic
## resolves the Foundry private endpoint via the private DNS zones linked to
## this VNet.
##
resource "azurerm_api_management" "apim" {
  depends_on = [
    azurerm_subnet_network_security_group_association.nsg_apim_assoc,
    azurerm_private_dns_zone_virtual_network_link.plz_ai_services_link,
    azurerm_private_dns_zone_virtual_network_link.plz_cognitive_services_link,
    azurerm_private_dns_zone_virtual_network_link.plz_openai_link,
    azurerm_private_endpoint.pe_aifoundry
  ]

  name                = "apim-foundry-${random_string.unique.result}"
  location            = var.location
  resource_group_name = azurerm_resource_group.rg.name
  publisher_name      = var.apim_publisher_name
  publisher_email     = var.apim_publisher_email
  sku_name            = "Developer_1"

  virtual_network_type = "External"
  virtual_network_configuration {
    subnet_id = azurerm_subnet.subnet_apim.id
  }

  identity {
    type = "SystemAssigned"
  }
}

## API that proxies all paths to the Foundry account hostname.
## Keeping path = "" so the inbound URL maps 1:1 to the Foundry endpoint —
## clients (Bot Service / Teams channel adapter) point at the APIM gateway URL
## but otherwise use the same path they would on Foundry directly.
##
resource "azurerm_api_management_api" "foundry_agent_api" {
  name                  = "foundry-agent-api"
  resource_group_name   = azurerm_resource_group.rg.name
  api_management_name   = azurerm_api_management.apim.name
  revision              = "1"
  display_name          = "Foundry Agent API"
  path                  = ""
  protocols             = ["https"]
  service_url           = "https://${azapi_resource.ai_foundry.name}.services.ai.azure.com"
  subscription_required = false
}

## Catch-all operation. APIM only routes requests that match a defined
## operation; without this, every request returns 404. The url_template
## matches the activity-protocol path of any agent in any project.
##
resource "azurerm_api_management_api_operation" "activity_protocol" {
  operation_id        = "activity-protocol"
  api_name            = azurerm_api_management_api.foundry_agent_api.name
  api_management_name = azurerm_api_management.apim.name
  resource_group_name = azurerm_resource_group.rg.name
  display_name        = "Activity Protocol"
  method              = "POST"
  url_template        = "/api/projects/{project}/agents/{agent}/endpoint/protocols/activityprotocol"

  template_parameter {
    name     = "project"
    type     = "string"
    required = true
  }

  template_parameter {
    name     = "agent"
    type     = "string"
    required = true
  }
}

## Inbound policy (matches the pattern from
## https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/foundry-agents-and-custom-engine-agents-through-the-corporate-firewall/4502218):
##  1) validate-jwt: confirm the caller is the Bot Framework, signed by the
##     Microsoft Bot IdP, with the audience matching our Bot App ID.
##  2) set-backend-service: forward to the Foundry account, which resolves
##     to the private endpoint via the linked private DNS zones.
##
## Notes:
##  - The original Bot Framework JWT is passed through unchanged. Foundry's
##    Azure Bot integration validates it on the messaging endpoint — do NOT
##    replace it with an AAD token (e.g. via authentication-managed-identity),
##    or the channel adapter call will fail.
##  - Optional extra hardening (not in the Microsoft blog): a <required-claims>
##    block validating the 'serviceurl' claim points at your tenant's reply URL
##    (https://smba.trafficmanager.net/<tenant_id>/). Add if you need to assert
##    the reply path is tenant-scoped.
##
resource "azurerm_api_management_api_policy" "foundry_agent_policy" {
  api_name            = azurerm_api_management_api.foundry_agent_api.name
  api_management_name = azurerm_api_management.apim.name
  resource_group_name = azurerm_resource_group.rg.name

  xml_content = <<XML
<policies>
  <inbound>
    <base />
    <check-header name="X-Azure-FDID" failed-check-httpcode="403" failed-check-error-message="Forbidden: request did not originate from the expected Front Door" ignore-case="true">
      <value>${azurerm_cdn_frontdoor_profile.fd.resource_guid}</value>
    </check-header>
    <validate-jwt header-name="Authorization" require-scheme="Bearer" failed-validation-httpcode="401" failed-validation-error-message="Unauthorized: invalid Bot Framework token">
      <openid-config url="https://login.botframework.com/v1/.well-known/openidconfiguration" />
      <audiences>
        <audience>${var.bot_app_id}</audience>
      </audiences>
      <issuers>
        <issuer>https://api.botframework.com</issuer>
      </issuers>
    </validate-jwt>
    <set-backend-service base-url="https://${azapi_resource.ai_foundry.name}.services.ai.azure.com" />
  </inbound>
  <backend>
    <base />
  </backend>
  <outbound>
    <base />
  </outbound>
  <on-error>
    <base />
  </on-error>
</policies>
XML
}

## Dedicated health endpoint for the Front Door origin probe.
## APIM's built-in /status endpoint is intermittently shadowed by the catch-all
## foundry-agent-api (path = ""), which makes it flap between 200 and 404 and
## causes Front Door to drop the origin from rotation. A dedicated API on the
## more-specific path "healthz" is matched deterministically and always returns
## 200 (no JWT / FDID required, since Front Door health probes are unauthenticated
## and carry no FDID header). It exposes nothing sensitive.
##
resource "azurerm_api_management_api" "health" {
  name                  = "fd-health-api"
  resource_group_name   = azurerm_resource_group.rg.name
  api_management_name   = azurerm_api_management.apim.name
  revision              = "1"
  display_name          = "Front Door Health"
  path                  = "healthz"
  protocols             = ["https"]
  subscription_required = false
}

resource "azurerm_api_management_api_operation" "health_get" {
  operation_id        = "health-get"
  api_name            = azurerm_api_management_api.health.name
  api_management_name = azurerm_api_management.apim.name
  resource_group_name = azurerm_resource_group.rg.name
  display_name        = "Health"
  method              = "GET"
  url_template        = "/"
}

resource "azurerm_api_management_api_policy" "health_policy" {
  api_name            = azurerm_api_management_api.health.name
  api_management_name = azurerm_api_management.apim.name
  resource_group_name = azurerm_resource_group.rg.name

  xml_content = <<XML
<policies>
  <inbound>
    <base />
    <return-response>
      <set-status code="200" reason="OK" />
      <set-header name="Content-Type" exists-action="override">
        <value>text/plain</value>
      </set-header>
      <set-body>OK</set-body>
    </return-response>
  </inbound>
  <backend>
    <base />
  </backend>
  <outbound>
    <base />
  </outbound>
  <on-error>
    <base />
  </on-error>
</policies>
XML
}
