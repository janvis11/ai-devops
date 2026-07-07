#!/usr/bin/env bash
# k8s/security/vault-auth-setup.sh
# Configures Vault Kubernetes auth method + axon-agent policy + role.
# Run once after: helm install vault is complete and Vault is initialized.
#
# Prerequisites:
#   - VAULT_ADDR   (e.g. http://localhost:32200)
#   - VAULT_TOKEN  (root token in dev mode: "root")
#   - KUBECONFIG pointing at the k3s cluster

set -euo pipefail

VAULT_ADDR="${VAULT_ADDR:-http://localhost:32200}"
VAULT_TOKEN="${VAULT_TOKEN:-root}"

echo "🔐 Configuring Vault at: $VAULT_ADDR"

# ── Enable Kubernetes auth method ─────────────────────────────────────────────
echo ">>> Enabling Kubernetes auth method..."
vault auth enable kubernetes 2>/dev/null || echo "Kubernetes auth already enabled"

# ── Configure Kubernetes auth method using the in-cluster service account ─────
echo ">>> Configuring Kubernetes auth method..."
vault write auth/kubernetes/config \
  kubernetes_host="https://kubernetes.default.svc"

# ── Write axon-agent policy ───────────────────────────────────────────────────
echo ">>> Writing axon-agent Vault policy..."
vault policy write axon-agent - <<'EOF'
# axon-agent can read all axon secrets
path "secret/data/axon/*" {
  capabilities = ["read"]
}

# axon-agent can list secret metadata
path "secret/metadata/axon/*" {
  capabilities = ["list"]
}

# axon-agent can renew its own token
path "auth/token/renew-self" {
  capabilities = ["update"]
}
EOF

# ── Create Kubernetes role bound to axon-agent service account ────────────────
echo ">>> Creating Vault role for axon-agent..."
vault write auth/kubernetes/role/axon-agent \
  bound_service_account_names=axon-agent \
  bound_service_account_namespaces=axon-system \
  policies=axon-agent \
  ttl=1h

# ── Enable KV v2 secrets engine ───────────────────────────────────────────────
echo ">>> Enabling KV v2 secrets engine..."
vault secrets enable -path=secret kv-v2 2>/dev/null || echo "KV v2 already enabled"

# ── Write placeholder secrets (fill in real values via bootstrap-secrets.yml) ─
echo ">>> Writing placeholder secrets (update with real values)..."
vault kv put secret/axon/config \
  claude_api_key="${CLAUDE_API_KEY:-changeme}" \
  kafka_password="${KAFKA_PASSWORD:-changeme}" \
  pg_password="${PG_PASSWORD:-changeme}" \
  slack_webhook_url="${SLACK_WEBHOOK_URL:-}" \
  pg_connection_string="postgresql://axon:${PG_PASSWORD:-changeme}@localhost:5432/axon"

vault kv put secret/axon/kafka \
  bootstrap_servers="${KAFKA_BOOTSTRAP_SERVERS:-localhost:9092}" \
  sasl_username="axon" \
  sasl_password="${KAFKA_PASSWORD:-changeme}"

echo ""
echo "✅ Vault auth setup complete!"
echo "   Policy: axon-agent"
echo "   K8s role: axon-agent → namespace: axon-system, SA: axon-agent"
echo "   Secrets: secret/axon/config, secret/axon/kafka"
echo ""
echo "Vault UI: $VAULT_ADDR/ui  (token: $VAULT_TOKEN)"
