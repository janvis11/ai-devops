# agent/config.py
# Centralized configuration — loaded from environment variables / Vault secrets.

import os
from dataclasses import dataclass


@dataclass
class Config:
    # ── Claude / Anthropic ────────────────────────────────────────────────────
    claude_api_key: str = os.getenv("CLAUDE_API_KEY", "")
    claude_model: str = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")
    claude_max_tokens: int = int(os.getenv("CLAUDE_MAX_TOKENS", "2048"))

    # ── Kafka ────────────────────────────────────────────────────────────────
    kafka_bootstrap_servers: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    kafka_group_id_alerts: str = "devops-ai-alert-consumer"
    kafka_group_id_k8s: str = "devops-ai-k8s-event-consumer"

    # ── PostgreSQL ───────────────────────────────────────────────────────────
    postgres_url: str = os.getenv(
        "POSTGRES_URL", "postgresql://devops_ai:password@localhost:5432/devops_ai"
    )

    # ── Kubernetes ───────────────────────────────────────────────────────────
    in_cluster: bool = os.getenv("IN_CLUSTER", "false").lower() == "true"

    # ── Prometheus ───────────────────────────────────────────────────────────
    prometheus_url: str = os.getenv(
        "PROMETHEUS_URL",
        "http://kube-prometheus-stack-prometheus.monitoring.svc.cluster.local:9090",
    )

    # ── Slack (HITL) ─────────────────────────────────────────────────────────
    slack_token: str = os.getenv("SLACK_BOT_TOKEN", "")
    slack_channel: str = os.getenv("SLACK_CHANNEL", "#devops-ai-alerts")
    slack_signing_secret: str = os.getenv("SLACK_SIGNING_SECRET", "")

    # ── Agent behavior ───────────────────────────────────────────────────────
    dedup_window_seconds: int = int(os.getenv("DEDUP_WINDOW_SECONDS", "120"))
    correlation_window_seconds: int = int(os.getenv("CORRELATION_WINDOW_SECONDS", "60"))
    verify_timeout_seconds: int = int(os.getenv("VERIFY_TIMEOUT_SECONDS", "60"))
    verify_poll_interval: int = int(os.getenv("VERIFY_POLL_INTERVAL", "5"))

    # ── API ──────────────────────────────────────────────────────────────────
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", "8000"))


cfg = Config()
