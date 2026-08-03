# agent/graph/nodes/escalate.py
# LangGraph node: escalate
# Posts a Slack message with Approve/Reject buttons for HITL decisions.
# The graph pauses here via LangGraph interrupt() until Slack callback resumes it.

import logging
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from agent.config import cfg
from agent.graph.state import AgentState

logger = logging.getLogger(__name__)
slack = WebClient(token=cfg.slack_token)


def _build_approval_blocks(state: AgentState) -> list[dict]:
    """Build Slack Block Kit message with Approve/Reject buttons."""
    pod = state.get("pod_name", "unknown")
    namespace = state.get("namespace", "unknown")
    event_type = state.get("event_type", "Unknown")
    diagnosis = state.get("diagnosis", "No diagnosis available.")
    action_id = state.get("action_id", "")
    confidence = state.get("confidence", 0.0)

    return [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"⚠️ devops.ai Agent — Approval Required",
            },
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Pod:*\n`{pod}`"},
                {"type": "mrkdwn", "text": f"*Namespace:*\n`{namespace}`"},
                {"type": "mrkdwn", "text": f"*Event Type:*\n`{event_type}`"},
                {"type": "mrkdwn", "text": f"*Confidence:*\n{confidence:.0%}"},
            ],
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Diagnosis:*\n{diagnosis[:500]}",
            },
        },
        {
            "type": "actions",
            "block_id": f"hitl_{action_id}",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "✅ Approve"},
                    "style": "primary",
                    "action_id": "approve_action",
                    "value": action_id,
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "❌ Reject"},
                    "style": "danger",
                    "action_id": "reject_action",
                    "value": action_id,
                },
            ],
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Action ID: `{action_id}` | POST to `/webhook/slack` to resume",
                }
            ],
        },
    ]


def escalate_node(state: AgentState) -> AgentState:
    """
    Posts a Slack HITL approval message.
    Returns state with requires_approval=True.
    The graph pauses at interrupt_before=['act'] until /webhook/slack resumes it.
    """
    pod_name = state.get("pod_name", "unknown")
    logger.info(f"[escalate] Posting HITL approval for pod={pod_name}")

    if not cfg.slack_token:
        logger.warning("[escalate] SLACK_BOT_TOKEN not set — skipping Slack notification")
        return {
            **state,
            "requires_approval": True,
            "approved": None,
            "slack_thread_ts": None,
        }

    try:
        blocks = _build_approval_blocks(state)
        response = slack.chat_postMessage(
            channel=cfg.slack_channel,
            text=f"devops.ai Agent needs approval for pod `{pod_name}`",
            blocks=blocks,
        )
        thread_ts = response["ts"]
        logger.info(f"[escalate] Slack message sent ts={thread_ts}")

        return {
            **state,
            "requires_approval": True,
            "approved": None,  # Will be set by /webhook/slack
            "slack_thread_ts": thread_ts,
        }

    except SlackApiError as e:
        logger.error(f"[escalate] Slack API error: {e.response['error']}")
        return {
            **state,
            "requires_approval": True,
            "approved": None,
            "error": f"slack escalate failed: {e.response['error']}",
        }
