terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }

  backend "s3" {
    bucket = "axon-tfstate"
    key    = "axon/terraform.tfstate"
    region = "ap-south-1"
  }
}

provider "aws" {
  region = var.region
}

# ─── k3s Node ────────────────────────────────────────────────────────────────
module "k3s_node" {
  source = "./modules/k3s-node"

  ami_id       = var.ami_id
  key_name     = var.key_name
  k3s_version  = var.k3s_version
  cluster_name = var.cluster_name
  vpc_id       = var.vpc_id
  subnet_id    = var.subnet_id
}

# ─── Container Registry ───────────────────────────────────────────────────────
module "registry" {
  source = "./modules/registry"

  cluster_name = var.cluster_name
  region       = var.region
}

# ─── Vault ────────────────────────────────────────────────────────────────────
module "vault" {
  source = "./modules/vault"

  cluster_name = var.cluster_name
  node_ip      = module.k3s_node.node_ip
}

# ─── PostgreSQL ───────────────────────────────────────────────────────────────
module "database" {
  source = "./modules/database"

  cluster_name = var.cluster_name
  environment  = var.environment
  db_username  = var.db_username
  db_password  = var.db_password
}
