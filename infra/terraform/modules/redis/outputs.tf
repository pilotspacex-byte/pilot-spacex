# Pilot Space Redis Module - Outputs

output "replication_group_id" {
  description = "ID of the ElastiCache replication group"
  value       = aws_elasticache_replication_group.main.id
}

output "primary_endpoint" {
  description = "Primary endpoint address for the Redis cluster"
  value       = aws_elasticache_replication_group.main.primary_endpoint_address
}

output "reader_endpoint" {
  description = "Reader endpoint address for read replicas"
  value       = aws_elasticache_replication_group.main.reader_endpoint_address
}

output "port" {
  description = "Redis port"
  value       = 6379
}

output "connection_string" {
  description = "Redis connection string (without auth token)"
  value       = "rediss://${aws_elasticache_replication_group.main.primary_endpoint_address}:6379"
}

output "security_group_id" {
  description = "Security group ID for the Redis cluster"
  value       = aws_security_group.redis.id
}

output "parameter_group_id" {
  description = "ID of the Redis parameter group"
  value       = aws_elasticache_parameter_group.main.id
}
