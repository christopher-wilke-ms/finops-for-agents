########## Azure Front Door (Premium) + WAF — security layer in front of APIM
##########
## Front Door is the public entry point for Bot Service / Teams traffic. It
## terminates TLS with an auto-provisioned, publicly-trusted managed certificate
## on its *.azurefd.net endpoint (so the Azure Bot messaging endpoint is accepted
## without a custom domain), runs the WAF managed rule set, and forwards to the
## APIM gateway. APIM is locked down (see apim.tf) so only Front Door can reach
## it, making the WAF non-bypassable.
##
##   Teams -> Front Door (WAF, managed TLS) -> APIM (External, FD-locked)
##         -> Foundry private endpoint -> agent

resource "azurerm_cdn_frontdoor_profile" "fd" {
  name                = "fd-foundry-${random_string.unique.result}"
  resource_group_name = azurerm_resource_group.rg.name
  sku_name            = var.frontdoor_sku_name
}

resource "azurerm_cdn_frontdoor_endpoint" "fd" {
  name                     = "fde-foundry-${random_string.unique.result}"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.fd.id
}

## Origin group targeting APIM. Health probe hits APIM's built-in gateway health
## endpoint (returns 200 and is not subject to the foundry-agent-api policy, so
## probes stay green even though the API itself now requires the FDID header).
##
resource "azurerm_cdn_frontdoor_origin_group" "apim" {
  name                     = "og-apim"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.fd.id

  load_balancing {
    sample_size                        = 4
    successful_samples_required        = 3
    additional_latency_in_milliseconds = 50
  }

  health_probe {
    path                = "/healthz"
    protocol            = "Https"
    request_type        = "GET"
    interval_in_seconds = 100
  }
}

## APIM origin. host_name / origin_host_header are the APIM gateway FQDN so SNI
## and the Host header match APIM's managed *.azure-api.net certificate.
##
resource "azurerm_cdn_frontdoor_origin" "apim" {
  name                          = "origin-apim"
  cdn_frontdoor_origin_group_id = azurerm_cdn_frontdoor_origin_group.apim.id
  enabled                       = true

  host_name                      = "${azurerm_api_management.apim.name}.azure-api.net"
  origin_host_header             = "${azurerm_api_management.apim.name}.azure-api.net"
  https_port                     = 443
  http_port                      = 80
  priority                       = 1
  weight                         = 1000
  certificate_name_check_enabled = true
}

## Route: forward all paths to APIM over HTTPS. No caching (dynamic POST traffic).
##
resource "azurerm_cdn_frontdoor_route" "apim" {
  name                          = "route-apim"
  cdn_frontdoor_endpoint_id     = azurerm_cdn_frontdoor_endpoint.fd.id
  cdn_frontdoor_origin_group_id = azurerm_cdn_frontdoor_origin_group.apim.id
  cdn_frontdoor_origin_ids      = [azurerm_cdn_frontdoor_origin.apim.id]

  enabled                = true
  forwarding_protocol    = "HttpsOnly"
  https_redirect_enabled = true
  patterns_to_match      = ["/*"]
  supported_protocols    = ["Http", "Https"]
  link_to_default_domain = true
}

## WAF policy. Premium SKU enables the Microsoft-managed Default Rule Set.
## Firewall policy names must be alphanumeric only (no hyphens).
##
resource "azurerm_cdn_frontdoor_firewall_policy" "waf" {
  name                = "fdwafpolicy${random_string.unique.result}"
  resource_group_name = azurerm_resource_group.rg.name
  sku_name            = var.frontdoor_sku_name
  enabled             = true
  mode                = var.frontdoor_waf_mode

  # The only traffic here is the Bot Framework Activity POST, whose JSON body is
  # already authenticated (Bot Framework JWT validated at APIM) and FDID-gated.
  # The managed OWASP rules false-positive on that legitimate JSON body and block
  # it (HTTP 403), so the agent never receives the message. Disabling request-body
  # inspection stops those false positives while the WAF still inspects the request
  # line, query string, and headers in Prevention mode.
  request_body_check_enabled = false

  managed_rule {
    type    = "Microsoft_DefaultRuleSet"
    version = "2.1"
    action  = "Block"
  }
}

## Bind the WAF policy to the Front Door endpoint's default domain.
##
resource "azurerm_cdn_frontdoor_security_policy" "waf" {
  name                     = "secpol-waf"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.fd.id

  security_policies {
    firewall {
      cdn_frontdoor_firewall_policy_id = azurerm_cdn_frontdoor_firewall_policy.waf.id

      association {
        domain {
          cdn_frontdoor_domain_id = azurerm_cdn_frontdoor_endpoint.fd.id
        }
        patterns_to_match = ["/*"]
      }
    }
  }
}

## Send Front Door access + WAF logs to the existing Log Analytics workspace so
## WAF rule matches (including which managed rule blocks a request) are visible.
##
resource "azurerm_monitor_diagnostic_setting" "fd_diag" {
  name                       = "fd-diag"
  target_resource_id         = azurerm_cdn_frontdoor_profile.fd.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.shared_logs.id

  enabled_log {
    category = "FrontDoorWebApplicationFirewallLog"
  }
  enabled_log {
    category = "FrontDoorAccessLog"
  }
}
