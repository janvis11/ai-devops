# agent/graph/graph.py
# LangGraph FSM — wires all nodes into the remediation state machine.
# Topology:
#   ingest (external) → classify → [escalate | diagnose → decide → act → verify → audit]

import logging
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver

from agent.config import cfg
from agent.graph.state import AgentState
from agent.graph.nodes import (
    classify_node,
    should_escalate,
    diagnose_node,
    escalate_node,
    decide_node,
    act_node,
    verify_node,
    audit_node,
)

logger = logging.getLogger(__name__)


def build_graph(checkpointer: PostgresSaver | None = None) -> StateGraph:
    """
    Builds and compiles the devops.ai remediation LangGraph.

    interrupt_before=['act'] means the graph pauses before executing
    remediation — useful for HITL approval via Slack.
    """
    builder = StateGraph(AgentState)

    # ── Register nodes ────────────────────────────────────────────────────────
    builder.add_node("classify", classify_node)
    builder.add_node("escalate", escalate_node)
    builder.add_node("diagnose", diagnose_node)
    builder.add_node("decide", decide_node)
    builder.add_node("act", act_node)
    builder.add_node("verify", verify_node)
    builder.add_node("audit", audit_node)

    # ── Entry point ───────────────────────────────────────────────────────────
    builder.set_entry_point("classify")

    # ── Edges ─────────────────────────────────────────────────────────────────
    # classify → (escalate | diagnose) based on safe_to_automate
    builder.add_conditional_edges(
        "classify",
        should_escalate,
        {"escalate": "escalate", "diagnose": "diagnose"},
    )

    # escalate → audit (graph pauses at interrupt_before=['act'] before this)
    # After Slack approval, graph resumes from 'act'
    builder.add_edge("escalate", "diagnose")

    # Happy path
    builder.add_edge("diagnose", "decide")
    builder.add_edge("decide", "act")
    builder.add_edge("act", "verify")
    builder.add_edge("verify", "audit")
    builder.add_edge("audit", END)

    # ── Compile ───────────────────────────────────────────────────────────────
    compile_kwargs = {}
    if checkpointer:
        compile_kwargs["checkpointer"] = checkpointer
        # Pause before act to allow HITL review
        compile_kwargs["interrupt_before"] = ["act"]

    graph = builder.compile(**compile_kwargs)
    logger.info("[graph] LangGraph remediation FSM compiled")
    return graph


def get_graph_with_postgres() -> StateGraph:
    """Build graph with PostgreSQL checkpointer for persistence."""
    try:
        checkpointer = PostgresSaver.from_conn_string(cfg.postgres_url)
        checkpointer.setup()
        logger.info("[graph] PostgreSQL checkpointer initialized")
    except Exception as e:
        logger.warning(f"[graph] PostgreSQL unavailable: {e} — running without checkpointer")
        checkpointer = None

    return build_graph(checkpointer=checkpointer)
