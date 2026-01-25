# Pilot Space VPC Module
# Documentation: docs/architect/infrastructure.md
#
# Creates a production-ready VPC with:
#   - Public and private subnets across 3 AZs
#   - NAT Gateways for private subnet egress
#   - VPC Flow Logs for security monitoring
#   - VPC Endpoints for AWS services
#
# Usage:
#   module "vpc" {
#     source = "./modules/vpc"
#     environment = "production"
#     vpc_cidr = "10.0.0.0/16"
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

# Data sources for availability zones
data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  azs = slice(data.aws_availability_zones.available.names, 0, 3)

  # Subnet CIDR calculation
  public_subnets  = [for i, az in local.azs : cidrsubnet(var.vpc_cidr, 4, i)]
  private_subnets = [for i, az in local.azs : cidrsubnet(var.vpc_cidr, 4, i + 4)]
  db_subnets      = [for i, az in local.azs : cidrsubnet(var.vpc_cidr, 4, i + 8)]

  common_tags = merge(var.tags, {
    Project     = "pilot-space"
    Environment = var.environment
    ManagedBy   = "terraform"
  })
}

# VPC
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = merge(local.common_tags, {
    Name = "pilot-space-${var.environment}-vpc"
  })
}

# Internet Gateway
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = merge(local.common_tags, {
    Name = "pilot-space-${var.environment}-igw"
  })
}

# Public Subnets
resource "aws_subnet" "public" {
  count = length(local.azs)

  vpc_id                  = aws_vpc.main.id
  cidr_block              = local.public_subnets[count.index]
  availability_zone       = local.azs[count.index]
  map_public_ip_on_launch = true

  tags = merge(local.common_tags, {
    Name                                        = "pilot-space-${var.environment}-public-${local.azs[count.index]}"
    Type                                        = "public"
    "kubernetes.io/role/elb"                    = "1"
    "kubernetes.io/cluster/pilot-space-${var.environment}" = "shared"
  })
}

# Private Subnets (for application workloads)
resource "aws_subnet" "private" {
  count = length(local.azs)

  vpc_id            = aws_vpc.main.id
  cidr_block        = local.private_subnets[count.index]
  availability_zone = local.azs[count.index]

  tags = merge(local.common_tags, {
    Name                                        = "pilot-space-${var.environment}-private-${local.azs[count.index]}"
    Type                                        = "private"
    "kubernetes.io/role/internal-elb"           = "1"
    "kubernetes.io/cluster/pilot-space-${var.environment}" = "shared"
  })
}

# Database Subnets (isolated, no NAT)
resource "aws_subnet" "database" {
  count = length(local.azs)

  vpc_id            = aws_vpc.main.id
  cidr_block        = local.db_subnets[count.index]
  availability_zone = local.azs[count.index]

  tags = merge(local.common_tags, {
    Name = "pilot-space-${var.environment}-db-${local.azs[count.index]}"
    Type = "database"
  })
}

# Elastic IP for NAT Gateway
resource "aws_eip" "nat" {
  count  = var.single_nat_gateway ? 1 : length(local.azs)
  domain = "vpc"

  tags = merge(local.common_tags, {
    Name = "pilot-space-${var.environment}-nat-eip-${count.index + 1}"
  })

  depends_on = [aws_internet_gateway.main]
}

# NAT Gateway
resource "aws_nat_gateway" "main" {
  count = var.single_nat_gateway ? 1 : length(local.azs)

  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id

  tags = merge(local.common_tags, {
    Name = "pilot-space-${var.environment}-nat-${count.index + 1}"
  })

  depends_on = [aws_internet_gateway.main]
}

# Public Route Table
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = merge(local.common_tags, {
    Name = "pilot-space-${var.environment}-public-rt"
  })
}

# Private Route Tables
resource "aws_route_table" "private" {
  count  = var.single_nat_gateway ? 1 : length(local.azs)
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main[count.index].id
  }

  tags = merge(local.common_tags, {
    Name = "pilot-space-${var.environment}-private-rt-${count.index + 1}"
  })
}

# Route Table Associations - Public
resource "aws_route_table_association" "public" {
  count = length(local.azs)

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# Route Table Associations - Private
resource "aws_route_table_association" "private" {
  count = length(local.azs)

  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[var.single_nat_gateway ? 0 : count.index].id
}

# VPC Flow Logs
resource "aws_cloudwatch_log_group" "vpc_flow_logs" {
  count = var.enable_flow_logs ? 1 : 0

  name              = "/aws/vpc/pilot-space-${var.environment}/flow-logs"
  retention_in_days = 30

  tags = local.common_tags
}

resource "aws_iam_role" "flow_logs" {
  count = var.enable_flow_logs ? 1 : 0

  name = "pilot-space-${var.environment}-vpc-flow-logs-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "vpc-flow-logs.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy" "flow_logs" {
  count = var.enable_flow_logs ? 1 : 0

  name = "pilot-space-${var.environment}-vpc-flow-logs-policy"
  role = aws_iam_role.flow_logs[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams"
        ]
        Effect   = "Allow"
        Resource = "*"
      }
    ]
  })
}

resource "aws_flow_log" "main" {
  count = var.enable_flow_logs ? 1 : 0

  iam_role_arn    = aws_iam_role.flow_logs[0].arn
  log_destination = aws_cloudwatch_log_group.vpc_flow_logs[0].arn
  traffic_type    = "ALL"
  vpc_id          = aws_vpc.main.id

  tags = merge(local.common_tags, {
    Name = "pilot-space-${var.environment}-flow-logs"
  })
}

# VPC Endpoints for AWS services (cost optimization)
resource "aws_vpc_endpoint" "s3" {
  count = var.enable_vpc_endpoints ? 1 : 0

  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.${data.aws_region.current.name}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = aws_route_table.private[*].id

  tags = merge(local.common_tags, {
    Name = "pilot-space-${var.environment}-s3-endpoint"
  })
}

resource "aws_vpc_endpoint" "ecr_api" {
  count = var.enable_vpc_endpoints ? 1 : 0

  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${data.aws_region.current.name}.ecr.api"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints[0].id]
  private_dns_enabled = true

  tags = merge(local.common_tags, {
    Name = "pilot-space-${var.environment}-ecr-api-endpoint"
  })
}

resource "aws_vpc_endpoint" "ecr_dkr" {
  count = var.enable_vpc_endpoints ? 1 : 0

  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${data.aws_region.current.name}.ecr.dkr"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints[0].id]
  private_dns_enabled = true

  tags = merge(local.common_tags, {
    Name = "pilot-space-${var.environment}-ecr-dkr-endpoint"
  })
}

resource "aws_security_group" "vpc_endpoints" {
  count = var.enable_vpc_endpoints ? 1 : 0

  name        = "pilot-space-${var.environment}-vpc-endpoints-sg"
  description = "Security group for VPC endpoints"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "pilot-space-${var.environment}-vpc-endpoints-sg"
  })
}

data "aws_region" "current" {}
