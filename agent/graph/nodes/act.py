# agent/graph/nodes/act.py
# LangGraph node: act
# Executes the chosen remediation action using the Kubernetes Python client.

import logging
from kubernetes import client, config as k8s_config
from kubernetes.client.rest import ApiException

from agent.config import cfg
from agent.graph.state import AgentState

logger = logging.getLogger(__name__)


def _get_k8s_clients() -> tuple:
    """Load kubeconfig — in-cluster when deployed, local kube config for dev."""
    try:
        if cfg.in_cluster:
            k8s_config.load_incluster_config()
        else:
            k8s_config.load_kube_config()
    except Exception as e:
        logger.warning(f"[act] kubeconfig load failed: {e}")

    return client.CoreV1Api(), client.AppsV1Api(), client.AutoscalingV1Api()


# ── Action implementations ─────────────────────────────────────────────────────

def _restart_pod(v1: client.CoreV1Api, pod_name: str, namespace: str) -> dict:
    """Delete the pod — kubelet will recreate it from the ReplicaSet."""
    v1.delete_namespaced_pod(
        name=pod_name,
        namespace=namespace,
        body=client.V1DeleteOptions(grace_period_seconds=0),
    )
    return {"action": "restart_pod", "pod": pod_name, "status": "deleted"}


def _increase_memory_limit(
    apps_v1: client.AppsV1Api, pod_name: str, namespace: str, factor: float = 1.5
) -> dict:
    """
    Find the deployment owning this pod and patch its memory limit.
    Increases by `factor` (e.g., 1.5 = +50%).
    """
    # Find deployment by label selector matching the pod name prefix
    deploy_name = "-".join(pod_name.split("-")[:-2])  # strip pod hash + suffix
    try:
        deploy = apps_v1.read_namespaced_deployment(deploy_name, namespace)
    except ApiException:
        # Try listing deployments and finding the one whose selector matches
        deploys = apps_v1.list_namespaced_deployment(namespace)
        deploy = next(
            (d for d in deploys.items if pod_name.startswith(d.metadata.name)),
            None,
        )
        if not deploy:
            return {"action": "increase_memory_limit", "status": "deployment_not_found"}

    containers = deploy.spec.template.spec.containers
    for container in containers:
        if container.resources and container.resources.limits:
            current_mem = container.resources.limits.get("memory", "256Mi")
            # Parse and scale: "256Mi" → integer MiB
            multiplier = 1 if "Gi" in current_mem else 1
            raw = current_mem.replace("Mi", "").replace("Gi", "").strip()
            new_val = int(float(raw) * factor)
            unit = "Gi" if "Gi" in current_mem else "Mi"
            container.resources.limits["memory"] = f"{new_val}{unit}"
            container.resources.requests = container.resources.requests or client.V1ResourceRequirements()
            if not container.resources.requests.requests:
                container.resources.requests.requests = {}

    apps_v1.patch_namespaced_deployment(deploy_name, namespace, deploy)
    return {
        "action": "increase_memory_limit",
        "deployment": deploy_name,
        "factor": factor,
        "status": "patched",
    }


def _scale_deployment(
    apps_v1: client.AppsV1Api, pod_name: str, namespace: str, delta: int = 2
) -> dict:
    """Scale the deployment by `delta` replicas."""
    deploy_name = "-".join(pod_name.split("-")[:-2])
    try:
        deploy = apps_v1.read_namespaced_deployment(deploy_name, namespace)
        current = deploy.spec.replicas or 1
        new_replicas = max(1, current + delta)
        apps_v1.patch_namespaced_deployment(
            deploy_name,
            namespace,
            {"spec": {"replicas": new_replicas}},
        )
        return {
            "action": "scale_deployment",
            "deployment": deploy_name,
            "from": current,
            "to": new_replicas,
            "status": "scaled",
        }
    except ApiException as e:
        return {"action": "scale_deployment", "status": "failed", "error": str(e)}


def _trigger_hpa(
    hpa_v1: client.AutoscalingV1Api, pod_name: str, namespace: str
) -> dict:
    """Annotate HPA to force immediate scale evaluation."""
    deploy_name = "-".join(pod_name.split("-")[:-2])
    try:
        hpa = hpa_v1.read_namespaced_horizontal_pod_autoscaler(deploy_name, namespace)
        # Bump minReplicas by 1 temporarily
        current_min = hpa.spec.min_replicas or 1
        hpa.spec.min_replicas = current_min + 1
        hpa_v1.patch_namespaced_horizontal_pod_autoscaler(deploy_name, namespace, hpa)
        return {"action": "trigger_hpa", "hpa": deploy_name, "status": "triggered"}
    except ApiException as e:
        return {"action": "trigger_hpa", "status": "failed", "error": str(e)}


# ── Main node ─────────────────────────────────────────────────────────────────

def act_node(state: AgentState) -> AgentState:
    """
    Executes the remediation action chosen by decide_node.
    Sets: action_result.
    """
    action = state.get("action", "")
    params = state.get("action_params", {})
    pod_name = state.get("pod_name", "")
    namespace = state.get("namespace", "")

    logger.info(f"[act] Executing action={action} pod={pod_name} ns={namespace}")

    try:
        v1, apps_v1, hpa_v1 = _get_k8s_clients()

        match action:
            case "restart_pod":
                result = _restart_pod(v1, pod_name, namespace)

            case "increase_memory_limit":
                factor = params.get("factor", 1.5)
                result = _increase_memory_limit(apps_v1, pod_name, namespace, factor)

            case "scale_deployment":
                delta = params.get("delta", 2)
                result = _scale_deployment(apps_v1, pod_name, namespace, delta)

            case "trigger_hpa":
                result = _trigger_hpa(hpa_v1, pod_name, namespace)

            case "manual_review":
                logger.info(f"[act] Action is manual_review — no automated action taken")
                result = {"action": "manual_review", "status": "skipped_manual"}

            case _:
                logger.warning(f"[act] Unknown action: {action}")
                result = {"action": action, "status": "unknown_action"}

        logger.info(f"[act] Result: {result}")
        return {**state, "action_result": result}

    except Exception as e:
        logger.error(f"[act] Unexpected error: {e}")
        return {
            **state,
            "action_result": {"status": "failed", "error": str(e)},
            "error": f"act failed: {e}",
        }
