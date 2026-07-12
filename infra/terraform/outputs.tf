output "k3s_node_ip" {
  description = "Public IP of the k3s node"
  value       = module.k3s_node.node_ip
}

output "k3s_node_private_ip" {
  description = "Private IP of the k3s node"
  value       = module.k3s_node.private_ip
}

output "registry_url" {
  description = "Container registry URL"
  value       = module.registry.registry_url
}

output "vault_address" {
  description = "Vault server address"
  value       = module.vault.vault_address
}

output "postgresql_endpoint" {
  description = "PostgreSQL connection endpoint"
  value       = module.database.endpoint
  sensitive   = true
}

output "postgresql_connection_string" {
  description = "Full PostgreSQL connection string"
  value       = "postgresql://${var.db_username}@${module.database.endpoint}:5432/axon"
  sensitive   = true
}
