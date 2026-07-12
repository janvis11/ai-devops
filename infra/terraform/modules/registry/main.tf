# ─── Container Registry Module ────────────────────────────────────────────────
# For local/dev setups GHCR is used (no AWS infra needed).
# For AWS prod: optionally create an ECR repository.

variable "cluster_name" {
  description = "Cluster name prefix"
  type        = string
}

variable "region" {
  description = "AWS region"
  type        = string
}

variable "use_ecr" {
  description = "Set to true to create an ECR repository (AWS). False = GHCR (no AWS resource)"
  type        = bool
  default     = false
}

# ── ECR (optional) ────────────────────────────────────────────────────────────
resource "aws_ecr_repository" "services" {
  for_each = var.use_ecr ? toset(["api", "worker", "frontend"]) : []

  name                 = "${var.cluster_name}-${each.key}"
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = {
    Project   = var.cluster_name
    ManagedBy = "terraform"
  }
}

# ── Lifecycle policy: keep last 20 images per repo ────────────────────────────
resource "aws_ecr_lifecycle_policy" "services" {
  for_each   = aws_ecr_repository.services
  repository = each.value.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 20 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 20
      }
      action = { type = "expire" }
    }]
  })
}

# ── Outputs ───────────────────────────────────────────────────────────────────
output "registry_url" {
  description = "Registry URL. ECR when use_ecr=true, else GHCR."
  value = var.use_ecr ? (
    length(aws_ecr_repository.services) > 0 ?
    "${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.region}.amazonaws.com/${var.cluster_name}" :
    "ghcr.io"
  ) : "ghcr.io"
}

data "aws_caller_identity" "current" {}
