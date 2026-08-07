# devops.ai — AI-Driven Kubernetes Remediation & GitOps Platform

Autonomous SRE platform that detects Kubernetes incidents, diagnoses root causes using **Claude 3.5 Sonnet**, and automatically executes self-healing remediation directly via Kubernetes APIs.

---

## ⚡ Quick Start

```bash
# 1. Start Kafka & PostgreSQL
cd kafka && docker compose up -d
bash topics/create-topics.sh && bash connectors/register-connectors.sh

# 2. Deploy Platform & Services via Helmfile
cd .. && helmfile apply

# 3. Start AI Agent
cd agent && pip install -r requirements.txt && python -m agent.main

# 4. Start Next.js Dashboard
cd services/frontend && npm install && npm run dev
```

---

## 🏗️ Architecture Stack

- **AI Reasoning**: 7-node LangGraph state machine (`classify` → `diagnose` → `escalate` → `decide` → `act` → `verify` → `audit`)
- **Event Mesh**: 3-broker KRaft Kafka (`infra.alerts`, `infra.logs`, `infra.traces`, `agent.actions`, `agent.decisions`)
- **Observability**: Prometheus, Alertmanager, Loki, Fluentd, OpenTelemetry Collector, Jaeger, Grafana
- **Security & GitOps**: ArgoCD, HashiCorp Vault Agent, OPA Gatekeeper, SealedSecrets
- **Developer UX**: Backstage IDP, Next.js real-time SSE dashboard

---

## 🧪 E2E Verification

```bash
# Run automated end-to-end chaos test
bash scripts/e2e-demo.sh
```

---

## 📜 License

MIT License © devops.ai