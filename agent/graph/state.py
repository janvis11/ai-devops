# agent/graph/state.py
# LangGraph AgentState TypedDict — the single shared state object
# passed between every node in the remediation FSM.

from typing import Any, TypedDict, Optional


class AgentState(TypedDict):
    # ── Ingest ────────────────────────────────────────────────────────────────
    event: dict                      # raw Kafka event payload
    correlated_events: list[dict]    # all events for this pod within 60s window
    pod_name: str
    namespace: str

    # ── Classify ─────────────────────────────────────────────────────────────
    event_type: str                  # OOMKill | CrashLoop | SchedulingFailure | ...
    confidence: float                # 0.0–1.0
    safe_to_automate: bool           # if False → escalate to Slack HITL

    # ── Diagnose ─────────────────────────────────────────────────────────────
    logs: str                        # last N lines of pod logs
    metrics: dict[str, Any]          # PromQL query results
    diagnosis: str                   # LLM root-cause analysis

    # ── Decide ───────────────────────────────────────────────────────────────
    action: str                      # chosen remediation action
    action_params: dict[str, Any]    # parameters for the action

    # ── Escalate (HITL) ──────────────────────────────────────────────────────
    requires_approval: bool
    slack_thread_ts: Optional[str]   # Slack thread timestamp for reply
    approved: Optional[bool]         # set by Slack webhook callback

    # ── Act ──────────────────────────────────────────────────────────────────
    action_result: dict[str, Any]    # result from K8s Python client

    # ── Verify ───────────────────────────────────────────────────────────────
    verified: bool                   # True if pod recovered after action
    verify_attempts: int

    # ── Audit + Explain ──────────────────────────────────────────────────────
    action_id: str                   # UUID for this remediation event
    explanation: str                 # plain-English summary for dashboard
    error: Optional[str]             # set if any node fails
