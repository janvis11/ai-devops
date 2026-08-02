# agent/graph/nodes/classify.py
# LangGraph node: classify
# Uses Claude to classify the K8s event type and decide if safe to auto-remediate.

import json
import logging
from anthropic import Anthropic

from agent.config import cfg
from agent.graph.state import AgentState
from agent.tools.k8s_tools import fetch_pod_logs_sync

logger = logging.getLogger(__name__)
client = Anthropic(api_key=cfg.claude_api_key)

CLASSIFY_PROMPT = """You are a senior Site Reliability Engineer.
Classify this Kubernetes infrastructure event and decide if it is safe to auto-remediate.

Event data:
{event}

Recent pod logs (last 50 lines):
{logs_preview}

Correlated events from the same pod (last 60s):
{correlated}

Respond ONLY with valid JSON — no markdown, no extra text:
{{
  "event_type": "OOMKill|CrashLoop|SchedulingFailure|ResourceExhaustion|NetworkIssue|ConfigError|Unknown",
  "confidence": <float 0.0-1.0>,
  "safe_to_automate": <true|false>,
  "reason": "<one sentence explaining the classification>",
  "urgency": "critical|high|medium|low"
}}

Rules for safe_to_automate=false (send to human approval):
- ConfigError (likely needs code fix)
- Unknown with confidence < 0.6
- Events involving production-critical deployments (if namespace=prod)
- NetworkIssue (may affect multiple services)
"""


def classify_node(state: AgentState) -> AgentState:
    """
    Classifies the K8s event using Claude.
    Sets: event_type, confidence, safe_to_automate.
    """
    pod_name = state.get("pod_name", "")
    namespace = state.get("namespace", "")

    # Fetch a small log preview for context (non-blocking best-effort)
    try:
        logs_preview = fetch_pod_logs_sync(pod_name, namespace, lines=50)
    except Exception as e:
        logs_preview = f"[log fetch failed: {e}]"

    correlated_summary = json.dumps(
        state.get("correlated_events", [])[:5], indent=2
    )

    prompt = CLASSIFY_PROMPT.format(
        event=json.dumps(state.get("event", {}), indent=2),
        logs_preview=logs_preview[:3000],
        correlated=correlated_summary,
    )

    logger.info(f"[classify] Classifying event for pod={pod_name} ns={namespace}")

    try:
        response = client.messages.create(
            model=cfg.claude_model,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        result = json.loads(raw)

        logger.info(
            f"[classify] type={result['event_type']} "
            f"confidence={result['confidence']:.2f} "
            f"safe={result['safe_to_automate']}"
        )

        return {
            **state,
            "event_type": result["event_type"],
            "confidence": float(result["confidence"]),
            "safe_to_automate": bool(result["safe_to_automate"]),
            "logs": logs_preview,
        }

    except Exception as e:
        logger.error(f"[classify] Failed: {e}")
        return {
            **state,
            "event_type": "Unknown",
            "confidence": 0.0,
            "safe_to_automate": False,
            "error": f"classify failed: {e}",
        }


def should_escalate(state: AgentState) -> str:
    """Conditional edge: route to escalate or diagnose."""
    if not state.get("safe_to_automate", False):
        return "escalate"
    return "diagnose"
