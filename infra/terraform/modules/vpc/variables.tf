# Pilot Space VPC Module - Variables

variable "environment" {
  description = "Environment name (staging, production)"
  type        = string

  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "Environment must be 'staging' or 'production'."
  }
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"

  validation {
    condition     = can(cidrhost(var.vpc_cidr, 0))
    error_message = "VPC CIDR must be a valid IPv4 CIDR block."
  }
}

variable "single_nat_gateway" {
  description = "Use a single NAT gateway for all AZs (cost savings for non-production)"
  type        = bool
  default     = false
}

variable "enable_flow_logs" {
  description = "Enable VPC flow logs for security monitoring"
  type        = bool
  default     = true
}

variable "enable_vpc_endpoints" {
  description = "Enable VPC endpoints for AWS services (reduces NAT costs)"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}
