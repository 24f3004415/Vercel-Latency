import json
import os
from typing import List

from fastapi import FastAPI, Request, Response
from pydantic import BaseModel

app = FastAPI()

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Expose-Headers": "Access-Control-Allow-Origin",
}


@app.middleware("http")
async def add_cors_headers(request: Request, call_next):
    if request.method == "OPTIONS":
        return Response(status_code=200, headers=CORS_HEADERS)
    response = await call_next(request)
    for key, value in CORS_HEADERS.items():
        response.headers[key] = value
    return response


DATA_PATH = os.path.join(os.path.dirname(__file__), "q-vercel-latency.json")
with open(DATA_PATH) as f:
    TELEMETRY = json.load(f)


class RequestPayload(BaseModel):
    regions: List[str]
    threshold_ms: float


def percentile(values, p):
    """Linear-interpolation percentile (same as numpy's default)."""
    s = sorted(values)
    k = (len(s) - 1) * p / 100
    lo = int(k)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


@app.get("/")
@app.get("/api")
@app.get("/api/index")
@app.get("/api/latency")
def root():
    return {"message": "Latency API is running"}


@app.post("/")
@app.post("/api")
@app.post("/api/index")
@app.post("/api/latency")
def latency(payload: RequestPayload):
    result = {}
    for reg in payload.regions:
        recs = [r for r in TELEMETRY if r["region"] == reg]
        if not recs:
            continue
        lat = [r["latency_ms"] for r in recs]
        up = [r["uptime_pct"] for r in recs]
        result[reg] = {
            "avg_latency": sum(lat) / len(lat),
            "p95_latency": percentile(lat, 95),
            "avg_uptime": sum(up) / len(up),
            "breaches": sum(1 for v in lat if v > payload.threshold_ms),
        }
    return result