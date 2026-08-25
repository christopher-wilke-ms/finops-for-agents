variable "location" {
  description = "The Azure region to deploy resources"
  type        = string
}

variable "virtual_network_address_space" {
  description = "The address space for the virtual network"
  type        = string
  default     = "192.168.0.0/16"
}

variable "agent_subnet_address_prefix" {
  description = "The address prefix for the agent subnet"
  type        = string
  default     = "192.168.0.0/24"
}

variable "bot_app_id" {
  description = "Microsoft App ID of the Azure Bot Service"
  type        = string
}
