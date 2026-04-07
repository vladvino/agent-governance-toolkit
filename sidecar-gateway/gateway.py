# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
"""Gateway — HTTP proxy on port 8002.

For every POST /tool/{tool_name}:
  1. Ask the policy sidecar (port 8001) whether the call is allowed.
  2. If allowed  → execute the mock tool and return the result (200).
  3. If denied   → return the reason (403).

Start with:
  uvicorn gateway:app --port 8002
"""

from __future__ import annotations

import os
from typing import Annotated, Any

import httpx
from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import JSONResponse

SIDECAR_URL = os.environ.get("SIDECAR_URL", "http://localhost:8001")
AGENT_ID = "demo-agent"

app = FastAPI(title="Policy-Gated Tool Gateway")


# ---------------------------------------------------------------------------
# Mock tools
# ---------------------------------------------------------------------------

def _get_weather(params: dict[str, Any]) -> dict[str, Any]:
    city = params.get("city", "unknown")
    return {"weather": "Sunny, 22°C", "city": city}


def _send_email(params: dict[str, Any]) -> dict[str, Any]:  # pragma: no cover
    # Reached only if policy allows it — blocked in this demo.
    return {"sent": True, "to": params.get("to")}


_TOOLS: dict[str, Any] = {
    "get_weather": _get_weather,
    "send_email": _send_email,
}


# ---------------------------------------------------------------------------
# Gateway endpoint
# ---------------------------------------------------------------------------

@app.post("/tool/{tool_name}")
async def call_tool(
    tool_name: str,
    params: Annotated[dict[str, Any], Body()] = {},  # noqa: B006  -- FastAPI owns this default
) -> JSONResponse:
    # 1. Consult the policy sidecar.
    #    PolicyProviderHandler passes `action` (not `agent_id`) to engine.evaluate();
    #    `agent_id` is used only for trust scoring and audit.
    #    Rules match on context["tool"], so the context dict is what drives allow/deny.
    check_payload = {
        "agent_id": AGENT_ID,
        "action": tool_name,
        "context": {"tool": tool_name, **params},
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{SIDECAR_URL}/check", json=check_payload, timeout=5.0)
    decision = resp.json()

    # 2. Enforce.
    if not decision.get("allowed", False):
        reason = decision.get("reason") or "denied by policy"
        raise HTTPException(status_code=403, detail={"error": reason})

    # 3. Execute the tool.
    tool_fn = _TOOLS.get(tool_name)
    if tool_fn is None:
        raise HTTPException(status_code=404, detail={"error": f"Unknown tool: {tool_name}"})

    result = tool_fn(params)
    return JSONResponse(content=result)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
