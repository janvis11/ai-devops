#!/usr/bin/env bash
# kafka/topics/create-topics.sh
# Creates all devops.ai platform Kafka topics with correct partitions and retention.
# Run after: docker compose up -d && sleep 20
#
# Usage: bash kafka/topics/create-topics.sh [bootstrap-server]
# Default bootstrap: localhost:9092

set -euo pipefail

KAFKA_BOOTSTRAP="${1:-localhost:9092}"
TIMEOUT=120

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " devops.ai — Kafka Topic Provisioner"
echo " Broker: $KAFKA_BOOTSTRAP"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── Wait for Kafka to be ready ─────────────────────────────────────────────────
echo ">>> Waiting for Kafka broker at $KAFKA_BOOTSTRAP..."
ELAPSED=0
until docker exec kafka-broker-1 kafka-broker-api-versions \
        --bootstrap-server localhost:9092 &>/dev/null; do
  sleep 3
  ELAPSED=$((ELAPSED + 3))
  if [ "$ELAPSED" -ge "$TIMEOUT" ]; then
    echo "ERROR: Kafka did not become ready within ${TIMEOUT}s"
    exit 1
  fi
  echo "  ...waiting (${ELAPSED}s)"
done
echo "✅ Kafka is ready"
echo ""

# ── Helper function ────────────────────────────────────────────────────────────
create_topic() {
  local TOPIC=$1
  local PARTITIONS=$2
  local REPLICATION=$3
  local RETENTION_MS=$4
  local DESCRIPTION=$5

  docker exec kafka-broker-1 kafka-topics \
    --bootstrap-server localhost:9092 \
    --create \
    --if-not-exists \
    --topic "$TOPIC" \
    --partitions "$PARTITIONS" \
    --replication-factor "$REPLICATION" \
    --config "retention.ms=$RETENTION_MS" \
    --config "cleanup.policy=delete" \
    --config "compression.type=lz4" \
    && echo "  ✅  $TOPIC  ($DESCRIPTION)" \
    || echo "  ⚠️   $TOPIC already exists — skipped"
}

echo ">>> Creating devops.ai topics..."
echo ""

# ── Infrastructure signal topics ──────────────────────────────────────────────
#   infra.alerts    — Alertmanager webhook events (critical, needs 7d replay)
create_topic "infra.alerts"      3 2  604800000  "7d  | Alertmanager fired alerts"

#   infra.logs      — Fluentd log stream (high volume, 3d retention)
create_topic "infra.logs"        6 2  259200000  "3d  | Fluentd → Loki log stream"

#   infra.traces    — OTel span data (short-lived, 1d)
create_topic "infra.traces"      3 2   86400000  "1d  | OpenTelemetry trace spans"

#   infra.k8s-events — raw K8s event watcher output (3d)
create_topic "infra.k8s-events"  3 2  259200000  "3d  | Kubernetes event watcher"

# ── Agent topics ──────────────────────────────────────────────────────────────
#   agent.actions   — audit log of every remediation action (30d for compliance)
create_topic "agent.actions"     1 2 2592000000  "30d | devops.ai agent audit log → PostgreSQL via Connect"

#   agent.decisions — plain-English explanations streamed to React dashboard (1d)
create_topic "agent.decisions"   1 2   86400000  "1d  | LangGraph decisions → SSE dashboard"

# ── Developer portal topic ────────────────────────────────────────────────────
#   dev.env-requests — Backstage one-click env provisioning requests
create_topic "dev.env-requests"  1 2   86400000  "1d  | Backstage → agent env provisioning"

echo ""
echo ">>> Topic list:"
docker exec kafka-broker-1 kafka-topics \
  --bootstrap-server localhost:9092 \
  --list \
  | grep -v "^_" \
  | sort \
  | while read -r t; do echo "   • $t"; done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " ✅ All topics created. kafka-ui: http://localhost:8080"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
