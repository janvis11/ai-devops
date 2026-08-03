# agent/graph/nodes/verify.py
# LangGraph node: verify
# Polls pod status for up to verify_timeout_seconds to confirm recovery.

import time
import logging
from kubernetes import client, config as k8s_config
from kubernetes.client.rest import ApiException

from agent.config import cfg
from agent.graph.state import AgentState

logger = logging.getLogger(__name__)


def verify_node(state: AgentState) -> AgentState:
    """
    Polls pod status until Running+Ready or timeout.
    Sets: verified, verify_attempts.
    """
    pod_name = state.get("pod_name", "")
    namespace = state.get("namespace", "")
    action = state.get("action", "")

    # manual_review actions don't need verification
    if action == "manual_review":
        return {**state, "verified": True, "verify_attempts": 0}

    logger.info(
        f"[verify] Watching pod={pod_name} ns={namespace} "
        f"timeout={cfg.verify_timeout_seconds}s"
    )

    try:
        if cfg.in_cluster:
            k8s_config.load_incluster_config()
        else:
            k8s_config.load_kube_config()
    except Exception as e:
        logger.warning(f"[verify] kubeconfig load failed: {e}")

    v1 = client.CoreV1Api()
    deadline = time.time() + cfg.verify_timeout_seconds
    attempts = 0

    while time.time() < deadline:
        attempts += 1
        try:
            # List pods matching name prefix (pod was deleted+recreated)
            pod_list = v1.list_namespaced_pod(
                namespace=namespace,
                label_selector=f"app={pod_name.rsplit('-', 2)[0]}",
            )

            if not pod_list.items:
                # Try direct name lookup for the short window before recreation
                logger.debug(f"[verify] No pods found with app label, retrying...")
                time.sleep(cfg.verify_poll_interval)
                continue

            for pod in pod_list.items:
                phase = pod.status.phase
                conditions = pod.status.conditions or []
                ready = any(
                    c.type == "Ready" and c.status == "True" for c in conditions
                )

                logger.debug(
                    f"[verify] attempt={attempts} pod={pod.metadata.name} "
                    f"phase={phase} ready={ready}"
                )

                if phase == "Running" and ready:
                    logger.info(f"[verify] ✅ Pod healthy after {attempts} attempts")
                    return {**state, "verified": True, "verify_attempts": attempts}

        except ApiException as e:
            logger.warning(f"[verify] K8s API error: {e.status}")

        time.sleep(cfg.verify_poll_interval)

    logger.warning(f"[verify] ⚠️ Pod not healthy after {cfg.verify_timeout_seconds}s")
    return {**state, "verified": False, "verify_attempts": attempts}
