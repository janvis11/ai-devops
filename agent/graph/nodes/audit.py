# agent/graph/nodes/audit.py
# LangGraph node: audit
# Publishes the complete remediation record to Kafka agent.actions topic.
# Kafka Connect JDBC sink then writes it to PostgreSQL agent_actions table.

import json
import uuid
import logging
from datetime import datetime, timezone
from kafka import KafkaProducer
from kafka.errors import KafkaError

from agent.config import cfg
from agent.graph.state import AgentState

logger = logging.getLogger(__name__)

# Singleton producer — reused across calls
_producer: KafkaProducer | None = None


def _get_producer() -> KafkaProducer:
    global _producer
    if _producer is None:
        _producer = KafkaProducer(
            bootstrap_servers=cfg.kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
            acks="all",
            retries=3,
            max_block_ms=5000,
        )
    return _producer


def audit_node(state: AgentState) -> AgentState:
    """
    Publishes remediation audit record to Kafka agent.actions.
    Sets: action_id, explanation (if not already set).
    """
    action_id = state.get("action_id") or str(uuid.uuid4())
    pod_name = state.get("pod_name", "unknown")
    namespace = state.get("namespace", "unknown")
    now = datetime.now(timezone.utc).isoformat()

    action_result = state.get("action_result", {})
    outcome = "success" if state.get("verified") else "unverified"
    if action_result.get("status") == "failed":
        outcome = "failed"

    record = {
        "action_id": action_id,
        "pod_name": pod_name,
        "namespace": namespace,
        "action_type": state.get("action", "unknown"),
        "triggered_by": state.get("event", {}).get("alert_name", "kafka_event"),
        "severity": state.get("event", {}).get("severity", "unknown"),
        "classification": state.get("event_type", "Unknown"),
        "diagnosis": state.get("diagnosis", ""),
        "decision": state.get("action", ""),
        "outcome": outcome,
        "llm_latency_ms": None,  # TODO: instrument timing
        "created_at": now,
        "metadata": {
            "confidence": state.get("confidence", 0.0),
            "safe_to_automate": state.get("safe_to_automate", False),
            "requires_approval": state.get("requires_approval", False),
            "approved": state.get("approved"),
            "verify_attempts": state.get("verify_attempts", 0),
            "action_result": action_result,
        },
    }

    # Publish to agent.decisions (for React SSE dashboard)
    decision_record = {
        "action_id": action_id,
        "pod_name": pod_name,
        "namespace": namespace,
        "event_type": state.get("event_type", "Unknown"),
        "action": state.get("action", ""),
        "outcome": outcome,
        "explanation": state.get("explanation", ""),
        "verified": state.get("verified", False),
        "timestamp": now,
    }

    try:
        producer = _get_producer()

        # agent.actions → Kafka Connect JDBC sink → PostgreSQL
        future = producer.send(
            "agent.actions",
            key=pod_name,
            value=record,
        )
        future.get(timeout=5)
        logger.info(f"[audit] Published to agent.actions action_id={action_id}")

        # agent.decisions → React SSE dashboard
        future2 = producer.send(
            "agent.decisions",
            key=pod_name,
            value=decision_record,
        )
        future2.get(timeout=5)
        logger.info(f"[audit] Published to agent.decisions")

    except KafkaError as e:
        logger.error(f"[audit] Kafka publish failed: {e}")
        return {**state, "action_id": action_id, "error": f"audit kafka failed: {e}"}

    return {
        **state,
        "action_id": action_id,
    }
