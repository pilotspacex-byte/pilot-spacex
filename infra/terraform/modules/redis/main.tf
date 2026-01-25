# Pilot Space Redis Module
# Documentation: docs/architect/infrastructure.md
#
# Creates an ElastiCache Redis cluster with:
#   - Multi-AZ deployment for high availability
#   - Encryption at rest and in transit
#   - Automatic failover
#   - CloudWatch monitoring
#
# Usage:
#   module "redis" {
#     source = "./modules/redis"
#     environment = "production"
#     vpc_id = module.vpc.vpc_id
#     subnet_ids = module.vpc.private_subnet_ids
#   }

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

locals {
  common_tags = merge(var.tags, {
    Project     = "pilot-space"
    Environment = var.environment
    ManagedBy   = "terraform"
  })
}

# Subnet group for ElastiCache
resource "aws_elasticache_subnet_group" "main" {
  name       = "pilot-space-${var.environment}-redis"
  subnet_ids = var.subnet_ids

  tags = merge(local.common_tags, {
    Name = "pilot-space-${var.environment}-redis-subnet-group"
  })
}

# Security group for Redis
resource "aws_security_group" "redis" {
  name        = "pilot-space-${var.environment}-redis-sg"
  description = "Security group for Pilot Space Redis cluster"
  vpc_id      = var.vpc_id

  # Allow Redis traffic from application subnets
  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = var.allowed_security_groups
    description     = "Redis from application"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "pilot-space-${var.environment}-redis-sg"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# Parameter group for Redis configuration
resource "aws_elasticache_parameter_group" "main" {
  name   = "pilot-space-${var.environment}-redis-params"
  family = "redis7"

  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"
  }

  parameter {
    name  = "tcp-keepalive"
    value = "60"
  }

  parameter {
    name  = "timeout"
    value = "0"
  }

  # Enable keyspace notifications for cache invalidation
  parameter {
    name  = "notify-keyspace-events"
    value = "Ex"
  }

  tags = local.common_tags
}

# Redis replication group (cluster mode disabled)
resource "aws_elasticache_replication_group" "main" {
  replication_group_id = "pilot-space-${var.environment}"
  description          = "Pilot Space Redis cluster for ${var.environment}"

  # Node configuration
  node_type            = var.node_type
  num_cache_clusters   = var.num_cache_clusters
  port                 = 6379
  parameter_group_name = aws_elasticache_parameter_group.main.name

  # Network configuration
  subnet_group_name  = aws_elasticache_subnet_group.main.name
  security_group_ids = [aws_security_group.redis.id]

  # High availability
  automatic_failover_enabled = var.num_cache_clusters > 1
  multi_az_enabled           = var.num_cache_clusters > 1

  # Encryption
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token                 = var.auth_token

  # Engine
  engine               = "redis"
  engine_version       = var.engine_version

  # Maintenance
  maintenance_window       = var.maintenance_window
  snapshot_window          = var.snapshot_window
  snapshot_retention_limit = var.snapshot_retention_limit
  auto_minor_version_upgrade = true

  # Notifications
  notification_topic_arn = var.sns_topic_arn

  tags = merge(local.common_tags, {
    Name = "pilot-space-${var.environment}-redis"
  })

  lifecycle {
    ignore_changes = [
      engine_version,
    ]
  }
}

# CloudWatch alarms for Redis monitoring
resource "aws_cloudwatch_metric_alarm" "cpu" {
  alarm_name          = "pilot-space-${var.environment}-redis-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ElastiCache"
  period              = 300
  statistic           = "Average"
  threshold           = 75
  alarm_description   = "Redis CPU utilization is high"
  alarm_actions       = var.alarm_actions

  dimensions = {
    CacheClusterId = aws_elasticache_replication_group.main.id
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "memory" {
  alarm_name          = "pilot-space-${var.environment}-redis-memory"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "DatabaseMemoryUsagePercentage"
  namespace           = "AWS/ElastiCache"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "Redis memory usage is high"
  alarm_actions       = var.alarm_actions

  dimensions = {
    CacheClusterId = aws_elasticache_replication_group.main.id
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "evictions" {
  alarm_name          = "pilot-space-${var.environment}-redis-evictions"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Evictions"
  namespace           = "AWS/ElastiCache"
  period              = 300
  statistic           = "Sum"
  threshold           = 100
  alarm_description   = "Redis evictions are high - consider scaling up"
  alarm_actions       = var.alarm_actions

  dimensions = {
    CacheClusterId = aws_elasticache_replication_group.main.id
  }

  tags = local.common_tags
}
