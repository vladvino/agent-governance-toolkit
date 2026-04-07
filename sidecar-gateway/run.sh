#!/usr/bin/env bash
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
#
# Starts a policy sidecar and gateway for the chosen engine, runs the agent
# demo, then shuts everything down.
#
#   Sidecar: :8001   Gateway: :8002
#
# Requires: uv  (https://github.com/astral-sh/uv)
#
# Usage:
#   cd demo/sidecar-gateway
#   bash run.sh yaml
#   bash run.sh rego
#   bash run.sh cedar

set -euo pipefail
cd "$(dirname "$0")"

# ---------------------------------------------------------------------------
# Argument validation
# ---------------------------------------------------------------------------

ENGINE="${1:-}"
if [[ -z "$ENGINE" || ! "$ENGINE" =~ ^(yaml|rego|cedar)$ ]]; then
    echo "Usage: bash run.sh <engine>"
    echo "  engine: yaml | rego | cedar"
    exit 1
fi

VENV=.venv
PYTHON="$VENV/bin/python"
UVICORN="$VENV/bin/uvicorn"

# Create venv and install deps on first run (idempotent afterwards).
if [ ! -f "$PYTHON" ]; then
    echo "Creating virtual environment with uv..."
    uv venv "$VENV" --python 3.13
    echo "Installing dependencies..."
    uv pip install --python "$PYTHON" -r requirements.txt
    echo "Installing local agentmesh package..."
    uv pip install --python "$PYTHON" -e "../packages/agent-mesh"
fi

# ---------------------------------------------------------------------------
# Start sidecar and gateway
# ---------------------------------------------------------------------------

cleanup() {
    echo ""
    echo "Stopping sidecar (PID $SIDECAR_PID) and gateway (PID $GATEWAY_PID)..."
    kill "$SIDECAR_PID" "$GATEWAY_PID" 2>/dev/null || true
}
trap cleanup EXIT

echo "Starting $ENGINE sidecar on :8001..."
POLICY_ENGINE="$ENGINE" \
    "$UVICORN" sidecar:app --port 8001 --log-level warning &
SIDECAR_PID=$!

echo "Starting $ENGINE gateway on :8002..."
SIDECAR_URL=http://localhost:8001 \
    "$UVICORN" gateway:app --port 8002 --log-level warning &
GATEWAY_PID=$!

# Wait for the sidecar to be ready (poll /health rather than sleeping a fixed interval).
echo "Waiting for sidecar to be ready..."
for i in $(seq 1 40); do
    curl -sf http://localhost:8001/health > /dev/null 2>&1 && break
    sleep 0.25
done

# ---------------------------------------------------------------------------
# Run the demo
# ---------------------------------------------------------------------------

POLICY_ENGINE="$ENGINE" "$PYTHON" agent.py
