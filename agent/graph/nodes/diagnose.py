# agent/graph/nodes/diagnose.py
# LangGraph node: diagnose
# Fetches pod logs + PromQL metrics, then calls Claude for root-cause analysis.

import json
import logging
from anthropic import Anthropic

from agent.config import cfg
from agent.graph.state import AgentState
from agent.tools.k8s_tools import fetch_pod_logs_sync
from agent.tools.promql_tools import run_promql

logger = logging.getLogger(__name__)
client = Anthropic(api_key=cfg.claude_api_key)

DIAGNOSE_PROMPT = """You are a Kubernetes SRE performing root-cause analysis.

Event type: {event_type}
Pod: {pod_name} in namespace: {namespace}

Pod logs (last 200 lines):
```
{logs}
```

Prometheus metrics at time of incident:
{metrics}

Provide a concise technical root-cause analysis and the most likely fix.
Respond in JSON only:
{{
  "root_cause": "<technical one-paragraph root cause>",
  "contributing_factors": ["factor1", "factor2"],
  "recommended_action": "increase_memory_limit|restart_pod|scale_deployment|cordon_reschedule|manual_review",
  "confidence": <float 0.0-1.0>,
  "explanation_for_human": "<plain English explanation for dashboard, 2-3 sentences>"
}}
"""

# PromQL queries to run for context
PROMQL_QUERIES = {
    "memory_usage_1h": 'container_memory_working_set_bytes{{pod="{pod}", namespace="{ns}"}}[1h]',
    "cpu_usage_30m": 'rate(container_cpu_usage_seconds_total{{pod="{pod}", namespace="{ns}"}}[30m])',
    "restart_count": 'kube_pod_container_status_restarts_total{{pod="{pod}", namespace="{ns}"}}',
    "oom_events": 'kube_pod_container_status_last_terminated_reason{{pod="{pod}", namespace="{ns}"}}',
}


def diagnose_node(state: AgentState) -> AgentState:
    """
    Fetches logs + metrics and calls Claude for diagnosis.
    Sets: logs, metrics, diagnosis.
    """
    pod_name = state.get("pod_name", "")
    namespace = state.get("namespace", "")
    event_type = state.get("event_type", "Unknown")

    logger.info(f"[diagnose] Starting for pod={pod_name} type={event_type}")

    # ── Fetch pod logs ────────────────────────────────────────────────────────
    try:
        logs = fetch_pod_logs_sync(pod_name, namespace, lines=200)
    except Exception as e:
        logs = state.get("logs", f"[log fetch failed: {e}]")

    # ── Run PromQL queries ────────────────────────────────────────────────────
    metrics = {}
    for key, query_template in PROMQL_QUERIES.items():
        query = query_template.format(pod=pod_name, ns=namespace)
        try:
            result = run_promql(query)
            if result:
                metrics[key] = result
        except Exception as e:
            logger.warning(f"[diagnose] PromQL {key} failed: {e}")
            metrics[key] = None

    # ── Claude root-cause analysis ────────────────────────────────────────────
    prompt = DIAGNOSE_PROMPT.format(
        event_type=event_type,
        pod_name=pod_name,
        namespace=namespace,
        logs=logs[:6000],
        metrics=json.dumps(metrics, indent=2)[:2000],
    )

    try:
        response = client.messages.create(
            model=cfg.claude_model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        result = json.loads(raw)

        diagnosis = result.get("root_cause", "Unknown root cause")
        explanation = result.get("explanation_for_human", diagnosis)

        logger.info(f"[diagnose] Root cause identified. confidence={result.get('confidence', 0):.2f}")

        return {
            **state,
            "logs": logs,
            "metrics": metrics,
            "diagnosis": diagnosis,
            "explanation": explanation,
        }

    except Exception as e:
        logger.error(f"[diagnose] LLM failed: {e}")
        return {
            **state,
            "logs": logs,
            "metrics": metrics,
            "diagnosis": f"Diagnosis failed: {e}",
            "explanation": f"Unable to diagnose {event_type} for pod {pod_name}.",
            "error": f"diagnose failed: {e}",
        }
