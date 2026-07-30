#!/usr/bin/env bash
# kafka/connectors/register-connectors.sh
# Registers all Kafka Connect connectors via the REST API.
# Run after: docker compose up -d && kafka-connect is healthy.

set -euo pipefail

CONNECT_URL="${CONNECT_URL:-http://localhost:8083}"
CONNECTORS_DIR="$(dirname "$0")"
TIMEOUT=120

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " devops.ai — Kafka Connect Provisioner"
echo " Connect REST: $CONNECT_URL"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── Wait for Kafka Connect REST API ───────────────────────────────────────────
echo ">>> Waiting for Kafka Connect..."
ELAPSED=0
until curl -sf "$CONNECT_URL/connectors" &>/dev/null; do
  sleep 5
  ELAPSED=$((ELAPSED + 5))
  if [ "$ELAPSED" -ge "$TIMEOUT" ]; then
    echo "ERROR: Kafka Connect not ready after ${TIMEOUT}s"
    exit 1
  fi
  echo "  ...waiting (${ELAPSED}s)"
done
echo "✅ Kafka Connect ready"
echo ""

# ── Register connector helper ──────────────────────────────────────────────────
register_connector() {
  local JSON_FILE=$1
  local NAME
  NAME=$(jq -r '.name' "$JSON_FILE")

  echo ">>> Registering connector: $NAME"

  # Check if it already exists
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$CONNECT_URL/connectors/$NAME")
  if [ "$STATUS" -eq 200 ]; then
    echo "  ↺  Already exists — updating config..."
    curl -s -X PUT \
      -H "Content-Type: application/json" \
      --data-binary "@$JSON_FILE" \
      "$CONNECT_URL/connectors/$NAME/config" | jq .
  else
    echo "  ✨ Creating new connector..."
    curl -s -X POST \
      -H "Content-Type: application/json" \
      --data-binary "@$JSON_FILE" \
      "$CONNECT_URL/connectors" | jq .
  fi
  echo ""
}

# ── Register all connector configs in this directory ──────────────────────────
for f in "$CONNECTORS_DIR"/*.json; do
  register_connector "$f"
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ">>> Connector status:"
curl -s "$CONNECT_URL/connectors?expand=status" | \
  jq -r 'to_entries[] | "  \(.key): \(.value.status.connector.state)"'
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
