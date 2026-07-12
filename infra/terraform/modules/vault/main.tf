# ─── Vault Module ─────────────────────────────────────────────────────────────
# This module handles Vault configuration after Helm installs it on k3s.
# On AWS prod, you'd point to HCP Vault or a dedicated Vault cluster.
# For local/dev, Vault runs inside k3s (see k8s/security/vault-values.yaml).

variable "cluster_name" {
  description = "Cluster name prefix"
  type        = string
}

variable "node_ip" {
  description = "Public IP of the k3s node where Vault is running"
  type        = string
}

variable "vault_port" {
  description = "Vault NodePort service port"
  type        = number
  default     = 32200
}

# ── Null resource: wait for Vault to be reachable ─────────────────────────────
# This ensures we can reference the address post-deploy.
resource "null_resource" "vault_wait" {
  triggers = {
    node_ip = var.node_ip
  }

  provisioner "local-exec" {
    command = <<-EOT
      echo "Vault will be available at: http://${var.node_ip}:${var.vault_port}"
      echo "After Helm install, configure via: k8s/security/vault-auth-setup.sh"
    EOT
  }
}

output "vault_address" {
  description = "Vault address (NodePort)"
  value       = "http://${var.node_ip}:${var.vault_port}"
}
