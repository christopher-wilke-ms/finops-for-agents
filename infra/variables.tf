## As of 6/2025 this is limited to RFC1918 Class B and Class C address space
variable "virtual_network_address_space" {
  description = "The address space for the virtual network"
  type        = string
  default     = "192.168.0.0/16"
}

variable "agent_subnet_address_prefix" {
  description = "The address prefix for the subnet that will be delegated to the Standard Agent"
  type        = string
  default     = "192.168.0.0/24"
}

variable "private_endpoint_subnet_address_prefix" {
  description = "The address prefix for the subnet that contains the private endpoints"
  type        = string
  default     = "192.168.1.0/24"
}

variable "location" {
  description = "The name of the location to provision the resources to"
  type        = string
}

variable "apim_subnet_address_prefix" {
  description = "Address prefix for the APIM subnet (minimum /29, /27 recommended for Developer/Premium)"
  type        = string
  default     = "192.168.2.0/27"
}

variable "apim_publisher_name" {
  description = "Organization name shown as the APIM publisher"
  type        = string
  default     = "Foundry Platform Team"
}

variable "apim_publisher_email" {
  description = "Admin contact email for the APIM instance"
  type        = string
}

variable "bot_app_id" {
  description = "Microsoft App ID (client ID) of the Azure Bot Service fronting the Foundry agent. Used as the JWT audience that APIM validates on inbound Teams traffic."
  type        = string
}

variable "frontdoor_sku_name" {
  description = "Azure Front Door SKU. 'Premium_AzureFrontDoor' is required for the Microsoft-managed WAF rule set. 'Standard_AzureFrontDoor' is cheaper but supports custom WAF rules only (the managed_rule block in frontdoor.tf must then be replaced)."
  type        = string
  default     = "Premium_AzureFrontDoor"
}

variable "frontdoor_waf_mode" {
  description = "Front Door WAF mode: 'Prevention' blocks matching requests, 'Detection' only logs them."
  type        = string
  default     = "Prevention"
}
