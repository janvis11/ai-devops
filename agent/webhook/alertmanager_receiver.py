# agent/webhook/alertmanager_receiver.py
# FastAPI routes for receiving Alertmanager webhook + Slack HITL callbacks.

import json
import hashlib
import hmac
import logging
import time
from datetime import datetime, timezone
from kafka import KafkaProducer
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks

from agent.config import cfg
from agent.kafka.correlator import correlator

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Kafka producer (shared) ───────────────────────────────────────────────────
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
        )
    return _producer


# ── Alertmanager webhook ──────────────────────────────────────────────────────

@router.post("/webhook/alertmanager")
async def receive_alertmanager(request: Request, background_tasks: BackgroundTasks):
    """
    Receives Alertmanager webhook payload.
    For each alert, normalizes and publishes to infra.alerts Kafka topic.
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    alerts = payload.get("alerts", [])
    published = 0

    for alert in alerts:
        # Skip resolved alerts — we only act on firing
        if alert.get("status") == "resolved":
            continue

        labels = alert.get("labels", {})
        annotations = alert.get("annotations", {})

        event = {
            "version": "1.0",
            "source": "alertmanager",
            "alert_name": labels.get("alertname", ""),
            "severity": labels.get("severity", "warning"),
            "pod_name": labels.get("pod", ""),
            "namespace": labels.get("namespace", ""),
            "node": labels.get("node", ""),
            "labels": labels,
            "annotations": annotations,
            "timestamp": alert.get("startsAt", datetime.now(timezone.utc).isoformat()),
            "generator_url": alert.get("generatorURL", ""),
        }

        pod_name = event["pod_name"]
        try:
            producer = _get_producer()
            producer.send(
                "infra.alerts",
                key=pod_name or None,
                value=event,
            )
            published += 1
            logger.info(
                f"[webhook/alertmanager] Published alert={event['alert_name']} "
                f"pod={pod_name} severity={event['severity']}"
            )
        except Exception as e:
            logger.error(f"[webhook/alertmanager] Kafka publish failed: {e}")

    return {"status": "accepted", "alerts_received": len(alerts), "published": published}


# ── Slack HITL callback ───────────────────────────────────────────────────────

# Store pending HITL approvals: action_id → asyncio.Event + approval
_pending_approvals: dict[str, dict] = {}


def register_pending_approval(action_id: str) -> None:
    """Called by escalate_node to register a pending approval."""
    _pending_approvals[action_id] = {"approved": None, "ts": time.time()}


def get_approval_result(action_id: str) -> bool | None:
    """Called by the graph to check if approved."""
    entry = _pending_approvals.get(action_id)
    return entry["approved"] if entry else None


@router.post("/webhook/slack")
async def receive_slack_callback(request: Request):
    """
    Receives Slack interactive button callbacks (Approve/Reject).
    Verifies the Slack signature, then records the approval decision.
    The Kafka consumer thread polls this to resume the LangGraph.
    """
    # ── Verify Slack signature ────────────────────────────────────────────────
    if cfg.slack_signing_secret:
        timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
        body = await request.body()
        sig_basestring = f"v0:{timestamp}:{body.decode()}"
        expected = "v0=" + hmac.new(
            cfg.slack_signing_secret.encode(),
            sig_basestring.encode(),
            hashlib.sha256,
        ).hexdigest()
        received = request.headers.get("X-Slack-Signature", "")
        if not hmac.compare_digest(expected, received):
            raise HTTPException(status_code=401, detail="Invalid Slack signature")
        body_str = body.decode()
    else:
        body_str = (await request.body()).decode()

    # Parse Slack payload
    from urllib.parse import parse_qs, unquote_plus
    parsed = parse_qs(body_str)
    payload_raw = parsed.get("payload", ["{}"])[0]
    payload = json.loads(unquote_plus(payload_raw))

    actions = payload.get("actions", [])
    if not actions:
        return {"status": "no_actions"}

    action = actions[0]
    action_type = action.get("action_id", "")  # approve_action | reject_action
    action_id = action.get("value", "")
    approved = action_type == "approve_action"

    logger.info(f"[webhook/slack] action_id={action_id} approved={approved}")

    if action_id in _pending_approvals:
        _pending_approvals[action_id]["approved"] = approved
    else:
        _pending_approvals[action_id] = {"approved": approved, "ts": time.time()}

    # Respond to Slack (replace the message)
    result_emoji = "✅" if approved else "❌"
    result_text = "Approved" if approved else "Rejected"
    user = payload.get("user", {}).get("name", "unknown")

    return {
        "response_action": "update",
        "view": {
            "type": "modal",
            "title": {"type": "plain_text", "text": "Decision Recorded"},
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{result_emoji} *{result_text}* by @{user}\nAction ID: `{action_id}`",
                    },
                }
            ],
        },
    }
