# Pilot Space VPC Module - Outputs

output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "vpc_cidr_block" {
  description = "CIDR block of the VPC"
  value       = aws_vpc.main.cidr_block
}

output "public_subnet_ids" {
  description = "IDs of the public subnets"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "IDs of the private subnets"
  value       = aws_subnet.private[*].id
}

output "database_subnet_ids" {
  description = "IDs of the database subnets"
  value       = aws_subnet.database[*].id
}

output "nat_gateway_ids" {
  description = "IDs of the NAT gateways"
  value       = aws_nat_gateway.main[*].id
}

output "internet_gateway_id" {
  description = "ID of the Internet Gateway"
  value       = aws_internet_gateway.main.id
}

output "availability_zones" {
  description = "Availability zones used"
  value       = local.azs
}

output "vpc_endpoints_sg_id" {
  description = "Security group ID for VPC endpoints"
  value       = var.enable_vpc_endpoints ? aws_security_group.vpc_endpoints[0].id : null
}
