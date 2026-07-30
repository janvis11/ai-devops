variable "region" {
  description = "AWS region for all resources"
  type        = string
  default     = "ap-south-1"
}

variable "cluster_name" {
  description = "Name prefix used for all devops.ai resources"
  type        = string
  default     = "devops.ai"
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "k3s_version" {
  description = "k3s version to install"
  type        = string
  default     = "v1.29.0+k3s1"
}

variable "ami_id" {
  description = "AMI ID for the k3s EC2 node (Ubuntu 22.04 LTS)"
  type        = string
  default     = "ami-0f5ee92e2d63afc18" # Ubuntu 22.04 ap-south-1
}

variable "key_name" {
  description = "EC2 key pair name for SSH access"
  type        = string
  default     = "devops.ai-key"
}

variable "vpc_id" {
  description = "VPC ID where the k3s node will be placed"
  type        = string
  default     = ""  # leave empty to use default VPC
}

variable "subnet_id" {
  description = "Subnet ID for the k3s node"
  type        = string
  default     = ""  # leave empty to use default subnet
}

variable "db_username" {
  description = "PostgreSQL master username"
  type        = string
  default     = "devops.ai"
  sensitive   = true
}

variable "db_password" {
  description = "PostgreSQL master password"
  type        = string
  sensitive   = true
  default     = ""  # Must be set via TF_VAR_db_password or tfvars
}
