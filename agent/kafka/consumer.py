# agent/kafka/consumer.py
# Multi-topic Kafka consumer that feeds events into the LangGraph FSM.

import json
import uuid
import logging
import threading
from kafka import KafkaConsumer
from kafka.errors import KafkaError

from agent.config import cfg
from agent.kafka.correlator import correlator
from agent.graph.graph import get_graph_with_postgres

logger = logging.getLogger(__name__)


def _normalize_event(topic: str, raw: dict) -> dict:
    """Normalize events from different topics into a common schema."""
    base = {
        "source_topic": topic,
        "pod_name": raw.get("pod_name") or raw.get("pod") or raw.get("labels", {}).get("pod", ""),
        "namespace": raw.get("namespace") or raw.get("labels", {}).get("namespace", "default"),
        "alert_name": raw.get("alert_name") or raw.get("alertname") or raw.get("reason", ""),
        "severity": raw.get("severity") or raw.get("labels", {}).get("severity", "warning"),
        "message": raw.get("message") or raw.get("annotations", {}).get("summary", ""),
        "timestamp": raw.get("timestamp") or raw.get("startsAt", ""),
        "labels": raw.get("labels", {}),
        "raw": raw,
    }
    return base


def _run_agent(event: dict, graph):
    """Run the LangGraph FSM for a single event in a thread."""
    pod_name = event.get("pod_name", "unknown")
    namespace = event.get("namespace", "default")
    thread_id = str(uuid.uuid4())

    # Dedup check
    if not correlator.should_investigate(pod_name):
        logger.info(f"[consumer] Skipping duplicate investigation for pod={pod_name}")
        return

    correlated = correlator.get_correlated(pod_name)
    logger.info(
        f"[consumer] 🚀 Starting investigation for pod={pod_name} "
        f"thread_id={thread_id} correlated_events={len(correlated)}"
    )

    initial_state = {
        "event": event,
        "correlated_events": correlated,
        "pod_name": pod_name,
        "namespace": namespace,
        "event_type": "",
        "confidence": 0.0,
        "safe_to_automate": False,
        "requires_approval": False,
        "approved": None,
        "action_id": thread_id,
        "explanation": "",
        "error": None,
        "logs": "",
        "metrics": {},
        "diagnosis": "",
        "action": "",
        "action_params": {},
        "action_result": {},
        "verified": False,
        "verify_attempts": 0,
        "slack_thread_ts": None,
    }

    try:
        config = {"configurable": {"thread_id": thread_id}}
        for output in graph.stream(initial_state, config=config):
            node_name = list(output.keys())[0]
            logger.info(f"[consumer] ✓ node={node_name} completed")

        correlator.mark_resolved(pod_name)
        logger.info(f"[consumer] ✅ Investigation complete for pod={pod_name}")

    except Exception as e:
        logger.error(f"[consumer] ❌ Graph failed for pod={pod_name}: {e}")
        correlator.mark_resolved(pod_name)  # release dedup lock on failure


def start_consumers():
    """Start Kafka consumers for infra.alerts and infra.k8s-events topics."""
    graph = get_graph_with_postgres()

    def consume_alerts():
        consumer = KafkaConsumer(
            "infra.alerts",
            bootstrap_servers=cfg.kafka_bootstrap_servers,
            group_id=cfg.kafka_group_id_alerts,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            auto_offset_reset="latest",
            enable_auto_commit=True,
            consumer_timeout_ms=-1,
        )
        logger.info("[consumer] infra.alerts consumer started")
        for msg in consumer:
            try:
                event = _normalize_event("infra.alerts", msg.value)
                correlator.add("infra.alerts", event)
                if event.get("pod_name"):
                    thread = threading.Thread(
                        target=_run_agent,
                        args=(event, graph),
                        daemon=True,
                        name=f"agent-{event['pod_name'][:20]}",
                    )
                    thread.start()
            except Exception as e:
                logger.error(f"[consumer] Alert processing error: {e}")

    def consume_k8s_events():
        consumer = KafkaConsumer(
            "infra.k8s-events",
            bootstrap_servers=cfg.kafka_bootstrap_servers,
            group_id=cfg.kafka_group_id_k8s,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            auto_offset_reset="latest",
            enable_auto_commit=True,
        )
        logger.info("[consumer] infra.k8s-events consumer started")
        for msg in consumer:
            try:
                event = _normalize_event("infra.k8s-events", msg.value)
                correlator.add("infra.k8s-events", event)
                # K8s events are also fed to the correlator so classify has full context.
                # Only trigger investigation if not already running for this pod.
                if event.get("pod_name") and not correlator._active.get(event["pod_name"]):
                    thread = threading.Thread(
                        target=_run_agent,
                        args=(event, graph),
                        daemon=True,
                    )
                    thread.start()
            except Exception as e:
                logger.error(f"[consumer] K8s event processing error: {e}")

    # Start both consumers in daemon threads
    threading.Thread(target=consume_alerts, daemon=True, name="kafka-alerts").start()
    threading.Thread(target=consume_k8s_events, daemon=True, name="kafka-k8s-events").start()
    logger.info("[consumer] All Kafka consumers started")
