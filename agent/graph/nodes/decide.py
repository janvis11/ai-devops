# agent/graph/nodes/decide.py
# LangGraph node: decide
# Maps event_type + diagnosis to a concrete remediation action using a playbook,
# with Claude as the final arbiter when the playbook is ambiguous.

import json
import logging
from anthropic import Anthropic

from agent.config import cfg
from agent.graph.state import AgentState

logger = logging.getLogger(__name__)
client = Anthropic(api_key=cfg.claude_api_key)

# ── Remediation Playbook ───────────────────────────────────────────────────────
PLAYBOOKS: dict[str, list[dict]] = {
    "OOMKill": [
        {"action": "increase_memory_limit", "params": {"factor": 1.5}},
        {"action": "restart_pod", "params": {}},
    ],
    "CrashLoop": [
        {"action": "restart_pod", "params": {}},
        {"action": "scale_deployment", "params": {"delta": 0}},  # force rollout
    ],
    "ResourceExhaustion": [
        {"action": "scale_deployment", "params": {"delta": 2}},
        {"action": "trigger_hpa", "params": {}},
    ],
    "SchedulingFailure": [
        {"action": "describe_node", "params": {}},
        {"action": "cordon_reschedule", "params": {}},
    ],
    "NetworkIssue": [
        {"action": "restart_pod", "params": {}},
    ],
    "ConfigError": [
        {"action": "manual_review", "params": {}},  # always escalate
    ],
    "Unknown": [
        {"action": "restart_pod", "params": {}},
    ],
}

DECIDE_PROMPT = """You are a Kubernetes SRE. Given the diagnosis and available playbook actions,
choose the SINGLE best action to remediate this incident.

Event type: {event_type}
Diagnosis: {diagnosis}
Confidence: {confidence}

Available playbook actions for this event type:
{playbook}

Choose ONE action. Respond in JSON only:
{{
  "action": "<action name from playbook>",
  "params": {{}},
  "rationale": "<one sentence why this action>",
  "risk": "low|medium|high"
}}
"""


def decide_node(state: AgentState) -> AgentState:
    """
    Selects the remediation action via playbook lookup + Claude validation.
    Sets: action, action_params.
    """
    event_type = state.get("event_type", "Unknown")
    diagnosis = state.get("diagnosis", "")
    confidence = state.get("confidence", 0.0)

    playbook = PLAYBOOKS.get(event_type, PLAYBOOKS["Unknown"])
    logger.info(f"[decide] Deciding action for event_type={event_type}")

    # ── Fast path: single unambiguous playbook entry ──────────────────────────
    if len(playbook) == 1:
        chosen = playbook[0]
        logger.info(f"[decide] Single playbook entry: action={chosen['action']}")
        return {
            **state,
            "action": chosen["action"],
            "action_params": chosen.get("params", {}),
        }

    # ── Claude decides between playbook options ───────────────────────────────
    prompt = DECIDE_PROMPT.format(
        event_type=event_type,
        diagnosis=diagnosis[:2000],
        confidence=f"{confidence:.0%}",
        playbook=json.dumps(playbook, indent=2),
    )

    try:
        response = client.messages.create(
            model=cfg.claude_model,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        result = json.loads(raw)

        action = result.get("action", playbook[0]["action"])
        params = result.get("params", {})

        # Validate action is in playbook
        valid_actions = {p["action"] for p in playbook}
        if action not in valid_actions:
            logger.warning(f"[decide] Claude chose invalid action '{action}', using playbook default")
            action = playbook[0]["action"]
            params = playbook[0].get("params", {})

        logger.info(f"[decide] Action decided: {action} risk={result.get('risk', 'unknown')}")
        return {**state, "action": action, "action_params": params}

    except Exception as e:
        logger.error(f"[decide] Failed: {e}, falling back to playbook default")
        fallback = playbook[0]
        return {
            **state,
            "action": fallback["action"],
            "action_params": fallback.get("params", {}),
            "error": f"decide failed: {e}",
        }
