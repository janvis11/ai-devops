from fastapi import FastAPI, Response, HTTPException
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
import time

# Metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP Requests', ['method', 'endpoint', 'status'])

# Tracing setup
provider = TracerProvider()
# Exporter uses grpc. It will silently fail if Jaeger is not up (which is fine for phase 1).
exporter = OTLPSpanExporter(endpoint="otel-collector.monitoring:4317", insecure=True)
provider.add_span_processor(BatchSpanProcessor(exporter))
trace.set_tracer_provider(provider)
tracer = trace.get_tracer(__name__)

app = FastAPI(title="AIGitOps API")

# Instrument FastAPI for OTel
FastAPIInstrumentor.instrument_app(app)

@app.middleware("http")
async def prometheus_middleware(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path, status=response.status_code).inc()
    return response

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/metrics")
def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/chaos/kill-pod")
def kill_pod():
    # Simulated chaos endpoint
    return {"message": "Chaos triggered", "status": "simulated"}

@app.get("/chaos/oom")
def oom_spike():
    # Intentionally leak memory to cause OOMKill
    leak = []
    while True:
        leak.append('A' * 10**6)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
