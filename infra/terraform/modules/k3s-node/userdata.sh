#!/bin/bash
# userdata.sh — bootstraps a k3s server on first boot
# Variables are interpolated by Terraform templatefile()
set -euo pipefail

K3S_VERSION="${k3s_version}"
CLUSTER_NAME="${cluster_name}"

echo ">>> AXON k3s bootstrap — version: $K3S_VERSION  cluster: $CLUSTER_NAME"

# ── system packages ──────────────────────────────────────────────────────────
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y curl wget git jq unzip

# ── k3s install ──────────────────────────────────────────────────────────────
curl -sfL https://get.k3s.io | \
  INSTALL_K3S_VERSION="$K3S_VERSION" \
  K3S_KUBECONFIG_MODE="644" \
  sh -s - server \
    --disable traefik \
    --disable servicelb \
    --cluster-init \
    --write-kubeconfig-mode=644 \
    --tls-san "$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)"

# ── wait for k3s ready ────────────────────────────────────────────────────────
echo ">>> Waiting for k3s API server..."
until kubectl --kubeconfig /etc/rancher/k3s/k3s.yaml get nodes &>/dev/null; do
  sleep 5
done
echo ">>> k3s ready!"

# ── Helm install ──────────────────────────────────────────────────────────────
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# ── core namespaces ───────────────────────────────────────────────────────────
KUBECONFIG=/etc/rancher/k3s/k3s.yaml kubectl create namespace axon-system  || true
KUBECONFIG=/etc/rancher/k3s/k3s.yaml kubectl create namespace monitoring   || true
KUBECONFIG=/etc/rancher/k3s/k3s.yaml kubectl create namespace apps         || true
KUBECONFIG=/etc/rancher/k3s/k3s.yaml kubectl create namespace gitops       || true
KUBECONFIG=/etc/rancher/k3s/k3s.yaml kubectl create namespace security     || true
KUBECONFIG=/etc/rancher/k3s/k3s.yaml kubectl create namespace backstage    || true

echo ">>> Bootstrap complete. Cluster: $CLUSTER_NAME"
