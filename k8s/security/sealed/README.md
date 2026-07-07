# SealedSecrets — Encrypted Secrets Store
#
# This directory stores encrypted SealedSecret manifests.
# SealedSecrets can be safely committed to Git — only the cluster can decrypt them.
#
# Usage (after sealed-secrets controller is running):
#   kubectl create secret generic kafka-creds \
#     --from-literal=password=supersecret \
#     --dry-run=client -o yaml | \
#     kubeseal --controller-namespace security --format yaml \
#     > k8s/security/sealed/kafka-creds.yaml
#
# Then commit kafka-creds.yaml to Git — it's safe because only
# the sealed-secrets controller in your cluster holds the private key.
#
# For key backup:
#   kubectl get secret -n security -l sealedsecrets.bitnami.com/sealed-secrets-key \
#     -o yaml > sealed-secrets-backup.yaml
#   # Store this backup securely (NOT in git)
