# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
"""Policy sidecar — runs as a standalone HTTP service.

Supports three policy engines selected via the POLICY_ENGINE env var:
  yaml  (default) — custom YAML DSL via PolicyEngine
  rego            — OPA/Rego via OPAEvaluator  (query: data.agentmesh.allow)
  cedar           — Cedar via CedarEvaluator   (builtin → cedarpy → CLI)

Override the policy file with POLICY_FILE (defaults to policy.{yaml,rego,cedar}).

Endpoints:
  POST /check    — evaluate a tool call against policy
  GET  /health   — liveness probe
  GET  /policies — list loaded policies

Start with:
  POLICY_ENGINE=yaml  uvicorn sidecar:app --port 8001
  POLICY_ENGINE=rego  uvicorn sidecar:app --port 8003
  POLICY_ENGINE=cedar uvicorn sidecar:app --port 8005
"""

from __future__ import annotations

import os
from pathlib import Path

from agentmesh.gateway.policy_provider import PolicyProviderHandler

_ENGINE_TYPE = os.environ.get("POLICY_ENGINE", "yaml")
_HERE = Path(__file__).parent


class _DecisionAdapter:
    """Uniform label()/str interface that PolicyProviderHandler expects."""

    def __init__(self, allowed: bool, reason: str = "") -> None:
        self._allowed = allowed
        self._reason = reason

    def label(self) -> str:
        return "allow" if self._allowed else "deny"

    def __str__(self) -> str:
        return self._reason or self.label()


# ---------------------------------------------------------------------------
# Per-engine adapter factories
# ---------------------------------------------------------------------------

def _build_yaml_adapter():
    from agentmesh.governance.policy import PolicyEngine
    policy_file = Path(os.environ.get("POLICY_FILE", str(_HERE / "policy.yaml")))
    _engine = PolicyEngine()
    _engine.load_yaml(policy_file.read_text(encoding="utf-8"))

    class _Adapter:
        def evaluate(self, agent_did: str, context: dict) -> _DecisionAdapter:
            d = _engine.evaluate(agent_did, context)
            return _DecisionAdapter(d.action == "allow", d.reason or "")

        def list_policies(self) -> list[str]:
            return _engine.list_policies()

    return _Adapter()


def _build_rego_adapter():
    from agentmesh.governance.opa import OPAEvaluator
    policy_file = os.environ.get("POLICY_FILE", str(_HERE / "policy.rego"))
    _evaluator = OPAEvaluator(mode="local", rego_path=policy_file)
    _QUERY = "data.agentmesh.allow"

    class _Adapter:
        def evaluate(self, agent_did: str, context: dict) -> _DecisionAdapter:
            d = _evaluator.evaluate(_QUERY, context)
            reason = d.error or ("denied by rego policy" if not d.allowed else "")
            return _DecisionAdapter(d.allowed, reason)

        def list_policies(self) -> list[str]:
            return ["rego"]

    return _Adapter()


def _build_cedar_adapter():
    from agentmesh.governance.cedar import CedarEvaluator
    policy_file = os.environ.get("POLICY_FILE", str(_HERE / "policy.cedar"))
    _evaluator = CedarEvaluator(mode="auto", policy_path=policy_file)

    class _Adapter:
        def evaluate(self, agent_did: str, context: dict) -> _DecisionAdapter:
            # agent_did carries the tool name (Action::"<tool>") from PolicyProviderHandler
            d = _evaluator.evaluate(agent_did, context)
            reason = d.error or ("denied by cedar policy" if not d.allowed else "")
            return _DecisionAdapter(d.allowed, reason)

        def list_policies(self) -> list[str]:
            return ["cedar"]

    return _Adapter()


# ---------------------------------------------------------------------------
# Boot
# ---------------------------------------------------------------------------

_BUILDERS = {
    "yaml": _build_yaml_adapter,
    "rego": _build_rego_adapter,
    "cedar": _build_cedar_adapter,
}

if _ENGINE_TYPE not in _BUILDERS:
    raise ValueError(
        f"Unknown POLICY_ENGINE={_ENGINE_TYPE!r}. Choose from: {list(_BUILDERS)}"
    )

_engine_adapter = _BUILDERS[_ENGINE_TYPE]()
handler = PolicyProviderHandler(_engine_adapter)
_asgi = handler.to_asgi_app()


async def app(scope: dict, receive, send) -> None:  # type: ignore[type-arg]
    """Top-level ASGI v3 entry point (uvicorn requires a standalone coroutine)."""
    await _asgi(scope, receive, send)
