# Policy Sidecar Gateway — Demo

A runnable prototype showing how to enforce agent governance policy at the gateway layer using the [Agent Governance Toolkit](../../README.md). The same policy is expressed in three languages (YAML DSL, OPA/Rego, Cedar) — any one can be selected at runtime.

---

## What it demonstrates

An agent receives the prompt _"Get the weather in London, then email me the results."_ and plans two tool calls:

| Tool | Expected outcome |
|------|-----------------|
| `get_weather` | **Allowed** — policy explicitly permits it |
| `send_email` | **Denied** — requires human approval; blocked at the gateway |

The policy is enforced **before** the tool executes. The agent never reaches the tool implementation for denied calls.

---

## Architecture

```
Agent (agent.py)
  │
  │  POST /tool/{tool_name}
  ▼
Gateway (gateway.py :8002)
  │
  │  POST /check  {"agent_id", "action", "context"}
  ▼
Policy Sidecar (sidecar.py :8001)
  │
  │  engine.evaluate(action, context)
  ▼
Policy Engine  ← policy.yaml / policy.rego / policy.cedar
```

### Components

| File | Role |
|------|------|
| `sidecar.py` | Standalone HTTP service (ASGI). Wraps the chosen policy engine behind three endpoints: `POST /check`, `GET /health`, `GET /policies`. Engine is selected via the `POLICY_ENGINE` env var. |
| `gateway.py` | FastAPI proxy. For every `POST /tool/{name}`, consults the sidecar and either executes the tool (200) or returns the denial reason (403). Sidecar URL is set via `SIDECAR_URL` env var. |
| `agent.py` | Simulates an agent executing a two-step plan. Calls the gateway and prints allow/deny results. |
| `run.sh` | Orchestration script. Starts the sidecar and gateway, waits for readiness, runs the agent, then shuts everything down. |

### Policy files

| File | Language | Notes |
|------|----------|-------|
| `policy.yaml` | Toolkit YAML DSL | `default_action: deny`; rules match on `context["tool"]` |
| `policy.rego` | OPA / Rego | `default allow = false`; evaluated via `data.agentmesh.allow` |
| `policy.cedar` | Cedar | `permit` for `get_weather`; `forbid` for `send_email` |

All three files express identical policy semantics.

---

## Prerequisites

- **[uv](https://github.com/astral-sh/uv)** — used to create the virtual environment and install dependencies
- **Python 3.13** — must be installed (`uv` will locate it automatically via `--python 3.13`)

Install `uv` if needed:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Install Python 3.13 via Homebrew if needed:
```bash
brew install python@3.13
```

> **Note:** Python 3.14+ is not supported because `pydantic-core` does not yet publish pre-built wheels for it. The `run.sh` script pins the venv to Python 3.13 explicitly.

---

## Running the demo

```bash
cd sidecar-gateway
bash run.sh yaml    # YAML DSL engine
bash run.sh rego    # OPA/Rego engine
bash run.sh cedar   # Cedar engine
```

On the first run, `run.sh` creates a `.venv` and installs all dependencies automatically. Subsequent runs reuse the existing venv.

### Expected output

```
=======================================================
  Policy Sidecar Gateway — Demo  [YAML]
=======================================================

User prompt: "Get the weather in London, then email me the results."

Agent plan: call get_weather, then send_email

-------------------------------------------------------

→ Agent calls tool: 'get_weather'  params={'city': 'London'}
  ✅ ALLOWED  — result: {'weather': 'Sunny, 22°C', 'city': 'London'}

→ Agent calls tool: 'send_email'  params={'to': 'user@example.com', ...}
  🚫 DENIED   — Email requires human approval workflow

=======================================================
  Demo complete.
=======================================================
```

The engine label in the header (`[YAML]`, `[REGO]`, `[CEDAR]`) reflects the engine selected. The allow/deny outcome is identical across all three.

---

## How the sidecar wiring works

`PolicyProviderHandler` (from `agentmesh.gateway.policy_provider`) expects the policy engine to expose an `evaluate()` method whose return value has a `label()` method returning `"allow"` or `"deny"`. Each engine returns a different decision type, so `sidecar.py` contains a thin `_DecisionAdapter` and a per-engine factory that bridges this gap:

```
_build_yaml_adapter()   → wraps PolicyEngine      → PolicyDecision.action
_build_rego_adapter()   → wraps OPAEvaluator       → OPADecision.allowed
_build_cedar_adapter()  → wraps CedarEvaluator     → CedarDecision.allowed
```

`PolicyProviderHandler.handle_check` passes the `action` field (the tool name) as the first argument to `engine.evaluate()`. Policy rules therefore match on `context["tool"]`, not on `agent_id`.

---

## Extending the demo

**Add a new tool:** Register it in `_TOOLS` in `gateway.py` and add a rule for it in all three policy files.

**Use a real OPA server:**
```bash
POLICY_ENGINE=rego OPA_URL=http://my-opa:8181 bash run.sh rego
```
The `OPAEvaluator` auto-detects a running OPA server when `mode="remote"` is set.

**Use the Cedar CLI or cedarpy bindings:** Install `cedarpy` (`pip install cedarpy`) or the Cedar CLI; `CedarEvaluator(mode="auto")` will prefer them over the built-in parser automatically.
