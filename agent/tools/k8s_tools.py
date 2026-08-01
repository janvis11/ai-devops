# agent/tools/k8s_tools.py
# Kubernetes helper tools used by diagnose and act nodes.

import logging
from kubernetes import client, config as k8s_config
from kubernetes.client.rest import ApiException

from agent.config import cfg

logger = logging.getLogger(__name__)


def _load_config():
    try:
        if cfg.in_cluster:
            k8s_config.load_incluster_config()
        else:
            k8s_config.load_kube_config()
    except Exception as e:
        logger.warning(f"[k8s_tools] Config load failed: {e}")


def fetch_pod_logs_sync(
    pod_name: str, namespace: str, lines: int = 200, container: str | None = None
) -> str:
    """
    Fetch pod logs synchronously.
    Returns log string or error message.
    """
    _load_config()
    v1 = client.CoreV1Api()
    kwargs = {
        "name": pod_name,
        "namespace": namespace,
        "tail_lines": lines,
        "timestamps": True,
    }
    if container:
        kwargs["container"] = container

    try:
        # Try current pod first
        logs = v1.read_namespaced_pod_log(**kwargs)
        return logs
    except ApiException as e:
        if e.status == 404:
            # Pod was restarted — try to get previous container logs
            try:
                kwargs["previous"] = True
                logs = v1.read_namespaced_pod_log(**kwargs)
                return f"[Previous container logs]\n{logs}"
            except ApiException:
                return f"[Pod {pod_name} not found — may have restarted]"
        return f"[Log fetch error: {e.status} {e.reason}]"
    except Exception as e:
        return f"[Log fetch failed: {e}]"


def describe_pod(pod_name: str, namespace: str) -> dict:
    """Return pod spec + status as a dict for diagnosis context."""
    _load_config()
    v1 = client.CoreV1Api()
    try:
        pod = v1.read_namespaced_pod(pod_name, namespace)
        return {
            "name": pod.metadata.name,
            "namespace": pod.metadata.namespace,
            "phase": pod.status.phase,
            "conditions": [
                {"type": c.type, "status": c.status, "reason": c.reason}
                for c in (pod.status.conditions or [])
            ],
            "container_statuses": [
                {
                    "name": cs.name,
                    "ready": cs.ready,
                    "restart_count": cs.restart_count,
                    "state": str(cs.state),
                }
                for cs in (pod.status.container_statuses or [])
            ],
            "node_name": pod.spec.node_name,
            "labels": pod.metadata.labels,
        }
    except ApiException as e:
        return {"error": f"{e.status} {e.reason}"}


def get_pod_events(pod_name: str, namespace: str, limit: int = 20) -> list[dict]:
    """Get K8s events related to the pod."""
    _load_config()
    v1 = client.CoreV1Api()
    try:
        events = v1.list_namespaced_event(
            namespace=namespace,
            field_selector=f"involvedObject.name={pod_name}",
        )
        return [
            {
                "reason": e.reason,
                "message": e.message,
                "type": e.type,
                "count": e.count,
                "last_timestamp": str(e.last_timestamp),
            }
            for e in events.items[:limit]
        ]
    except Exception as e:
        return [{"error": str(e)}]
