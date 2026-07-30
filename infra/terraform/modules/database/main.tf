# ─── Database Module (PostgreSQL) ─────────────────────────────────────────────
# Local dev: Docker-based PostgreSQL (no AWS).
# AWS prod:  RDS PostgreSQL (toggle with var.use_rds).

variable "cluster_name" {
  description = "Cluster name prefix"
  type        = string
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "dev"
}

variable "db_username" {
  description = "PostgreSQL master username"
  type        = string
  sensitive   = true
}

variable "db_password" {
  description = "PostgreSQL master password"
  type        = string
  sensitive   = true
}

variable "use_rds" {
  description = "Set to true to create an AWS RDS instance. False = local docker."
  type        = bool
  default     = false
}

variable "db_instance_class" {
  description = "RDS instance class (only used when use_rds=true)"
  type        = string
  default     = "db.t3.micro"
}

# ── Random suffix for unique naming ──────────────────────────────────────────
resource "random_id" "suffix" {
  byte_length = 4
}

# ── RDS PostgreSQL (prod path) ────────────────────────────────────────────────
resource "aws_db_instance" "postgresql" {
  count = var.use_rds ? 1 : 0

  identifier        = "${var.cluster_name}-pg-${random_id.suffix.hex}"
  engine            = "postgres"
  engine_version    = "15.4"
  instance_class    = var.db_instance_class
  allocated_storage = 20
  storage_encrypted = true

  db_name  = "devops.ai"
  username = var.db_username
  password = var.db_password

  skip_final_snapshot       = var.environment != "prod"
  final_snapshot_identifier = "${var.cluster_name}-pg-final-${random_id.suffix.hex}"
  deletion_protection       = var.environment == "prod"

  backup_retention_period = var.environment == "prod" ? 7 : 1
  multi_az                = var.environment == "prod"

  tags = {
    Name        = "${var.cluster_name}-postgresql"
    Project     = var.cluster_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# ── Local note resource (dev path) ────────────────────────────────────────────
resource "null_resource" "local_pg_note" {
  count = var.use_rds ? 0 : 1

  triggers = { always = timestamp() }

  provisioner "local-exec" {
    command = "echo 'PostgreSQL running via docker-compose. Endpoint: localhost:5432'"
  }
}

# ── Outputs ───────────────────────────────────────────────────────────────────
output "endpoint" {
  description = "PostgreSQL endpoint (RDS address or localhost for dev)"
  value = var.use_rds ? (
    length(aws_db_instance.postgresql) > 0 ?
    aws_db_instance.postgresql[0].endpoint : "localhost"
  ) : "localhost"
  sensitive = true
}

output "db_name" {
  description = "Database name"
  value       = "devops.ai"
}
