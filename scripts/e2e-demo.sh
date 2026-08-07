#!/usr/bin/env bash
# scripts/e2e-demo.sh — End-to-End Chaos Simulation and Verification Script

set -euo pipefail

AGENT_URL="${AGENT_URL:-http://localhost:8000}"

echo "================================================================="
echo "  🚀 devops.ai — End-to-End Autonomous Remediation Demo"
echo "================================================================="

# 1. Health & Readiness Verification
echo -e "\n[1/5] Checking Agent Health & Connectivity..."
HEALTH=$(curl -sf "${AGENT_URL}/health" || echo '{"status":"offline"}')
echo "Agent Health: ${HEALTH}"

READY=$(curl -sf "${AGENT_URL}/ready" || echo '{"status":"degraded"}')
echo "Agent Readiness: ${READY}"

# 2. Status & Correlator Check
echo -e "\n[2/5] Inspecting Correlator Status..."
STATUS=$(curl -sf "${AGENT_URL}/status")
echo "Correlator Info: ${STATUS}"

# 3. Trigger Chaos Experiment: Kill Pod
echo -e "\n[3/5] Triggering Chaos Experiment (Kill API Pod)..."
KILL_RESP=$(curl -sf -X POST "${AGENT_URL}/chaos/kill-pod" \
  -H "Content-Type: application/json" \
  -d '{"pod_selector": "app=devops-ai-api", "namespace": "apps"}')
echo "Chaos Trigger Response: ${KILL_RESP}"

# 4. Wait for AI Agent Auto-remediation Loop
echo -e "\n[4/5] Monitoring AI Agent Remediation Loop (15s wait)..."
sleep 15

# 5. Query Audit Trail from PostgreSQL
echo -e "\n[5/5] Querying PostgreSQL Audit Log (/audit)..."
AUDIT_LOGS=$(curl -sf "${AGENT_URL}/audit?limit=5")
echo "Latest Audit Records:"
echo "${AUDIT_LOGS}" | python -m json.tool || echo "${AUDIT_LOGS}"

echo -e "\n================================================================="
echo "  ✅ End-to-End Chaos Verification Complete!"
echo "================================================================="
