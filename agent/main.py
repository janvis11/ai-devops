# agent/main.py
# devops.ai Agent — FastAPI application entrypoint.
# Starts Kafka consumers in background threads + exposes all API routes.

import json
import logging
import asyncio
import asyncpg
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from kafka import KafkaConsumer

from agent.config import cfg
from agent.webhook.alertmanager_receiver import router as webhook_router
from agent.kafka.consumer import start_consumers
from agent.kafka.correlator import correlator

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("devops-ai.agent")

# ── OpenTelemetry setup ───────────────────────────────────────────────────────
provider = TracerProvider()
exporter = OTLPSpanExporter(
    endpoint="otel-collector.monitoring:4317", insecure=True
)
provider.add_span_processor(BatchSpanProcessor(exporter))
trace.set_tracer_provider(provider)

# ── Prometheus metrics ────────────────────────────────────────────────────────
AGENT_ACTIONS = Counter(
    "devops_ai_agent_actions_total",
    "Total remediation actions",
    ["action_type", "outcome"],
)
AGENT_PENDING = Gauge(
    "devops_ai_agent_pending_actions",
    "Currently active investigations",
)
LLM_LATENCY = Histogram(
    "devops_ai_llm_request_duration_seconds",
    "Claude API latency",
    buckets=[0.5, 1, 2, 5, 10, 30],
)
HITL_PENDING = Gauge(
    "devops_ai_agent_hitl_pending",
    "HITL approvals waiting on Slack",
)


# ── App lifecycle ─────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 devops.ai Agent starting...")
    # Start Kafka consumers in background threads
    start_consumers()
    logger.info("✅ Kafka consumers started")
    yield
    logger.info("🛑 devops.ai Agent shutting down")


app = FastAPI(
    title="devops.ai AI Agent",
    description="AI-driven Kubernetes remediation agent. LangGraph FSM + Claude API + K8s Python client.",
    version="1.0.0",
    lifespan=lifespan,
)

# Instrument for OTel tracing
FastAPIInstrumentor.instrument_app(app)

# CORS — allow React dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register webhook routes
app.include_router(webhook_router)


# ── Health / Ready ────────────────────────────────────────────────────────────

@app.get("/health", tags=["ops"])
def health():
    return {"status": "ok", "service": "devops-ai-agent", "ts": datetime.now(timezone.utc).isoformat()}


@app.get("/ready", tags=["ops"])
async def ready():
    """Checks Kafka and PostgreSQL connectivity."""
    checks = {}
    # Kafka
    try:
        from kafka import KafkaAdminClient
        admin = KafkaAdminClient(bootstrap_servers=cfg.kafka_bootstrap_servers, request_timeout_ms=3000)
        admin.list_topics()
        admin.close()
        checks["kafka"] = "ok"
    except Exception as e:
        checks["kafka"] = f"error: {e}"

    # PostgreSQL
    try:
        conn = await asyncpg.connect(cfg.postgres_url, timeout=3)
        await conn.execute("SELECT 1")
        await conn.close()
        checks["postgres"] = "ok"
    except Exception as e:
        checks["postgres"] = f"error: {e}"

    status = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": status, "checks": checks}


@app.get("/metrics", tags=["ops"])
def metrics():
    """Prometheus metrics endpoint."""
    from fastapi import Response
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ── SSE: Real-time decision stream ───────────────────────────────────────────

@app.get("/stream/decisions", tags=["dashboard"])
async def stream_decisions(request: Request):
    """
    Server-Sent Events stream of agent decisions.
    React dashboard connects here to receive real-time remediation updates.
    """
    async def event_generator():
        consumer = KafkaConsumer(
            "agent.decisions",
            bootstrap_servers=cfg.kafka_bootstrap_servers,
            group_id=f"devops-ai-sse-{id(request)}",
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            auto_offset_reset="latest",
            consumer_timeout_ms=1000,
        )

        try:
            while True:
                if await request.is_disconnected():
                    logger.info("[sse] Client disconnected")
                    break

                records = consumer.poll(timeout_ms=500)
                for _, messages in records.items():
                    for msg in messages:
                        payload = json.dumps(msg.value)
                        yield f"data: {payload}\n\n"

                # Heartbeat every second to keep connection alive
                yield ": heartbeat\n\n"
                await asyncio.sleep(0.5)
        finally:
            consumer.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ── Audit log query ───────────────────────────────────────────────────────────

@app.get("/audit", tags=["audit"])
async def get_audit(
    namespace: str = Query(None),
    pod: str = Query(None),
    limit: int = Query(20, le=100),
):
    """Query the agent_actions audit log from PostgreSQL."""
    try:
        conn = await asyncpg.connect(cfg.postgres_url)
        conditions = []
        params = []
        i = 1

        if namespace:
            conditions.append(f"namespace = ${i}")
            params.append(namespace)
            i += 1
        if pod:
            conditions.append(f"pod_name LIKE ${i}")
            params.append(f"%{pod}%")
            i += 1

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        rows = await conn.fetch(
            f"SELECT * FROM agent_actions {where} ORDER BY created_at DESC LIMIT ${i}",
            *params,
            limit,
        )
        await conn.close()
        return [dict(r) for r in rows]

    except Exception as e:
        logger.error(f"[audit] DB error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Chaos endpoint ────────────────────────────────────────────────────────────

@app.post("/chaos/kill-pod", tags=["chaos"])
async def kill_pod(request: Request):
    """
    Chaos endpoint — deletes a pod to simulate failure.
    Used by the React dashboard chaos button.
    """
    body = await request.json()
    pod_selector = body.get("pod_selector", "")
    namespace = body.get("namespace", "apps")

    try:
        from kubernetes import client as k8s_client, config as k8s_config
        try:
            k8s_config.load_incluster_config() if cfg.in_cluster else k8s_config.load_kube_config()
        except Exception:
            pass

        v1 = k8s_client.CoreV1Api()
        label_key, label_val = pod_selector.split("=", 1)
        pods = v1.list_namespaced_pod(
            namespace=namespace,
            label_selector=f"{label_key}={label_val}",
        )

        if not pods.items:
            return {"status": "no_pods_found", "selector": pod_selector}

        target = pods.items[0]
        pod_name = target.metadata.name
        v1.delete_namespaced_pod(pod_name, namespace, body=k8s_client.V1DeleteOptions())

        logger.info(f"[chaos] 💣 Killed pod={pod_name} ns={namespace}")
        return {
            "status": "killed",
            "pod": pod_name,
            "namespace": namespace,
            "message": f"Pod {pod_name} deleted. devops.ai agent should remediate shortly.",
        }

    except Exception as e:
        logger.error(f"[chaos] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Correlator status ─────────────────────────────────────────────────────────

@app.get("/status", tags=["ops"])
def status():
    """Returns agent runtime status including correlator stats."""
    return {
        "service": "devops-ai-agent",
        "version": "1.0.0",
        "correlator": correlator.stats,
        "config": {
            "kafka": cfg.kafka_bootstrap_servers,
            "prometheus": cfg.prometheus_url,
            "dedup_window": cfg.dedup_window_seconds,
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=cfg.api_host, port=cfg.api_port, log_level="info")
