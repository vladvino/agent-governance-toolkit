# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
"""Agent — simulates an agent acting on a user prompt.

The agent calls two tools (get_weather, send_email) via the gateway.
The gateway enforces policy: one call is allowed, the other is blocked.
The active policy engine is shown in the header (set by run.sh via
the POLICY_ENGINE environment variable).

Usage (gateway must already be running on port 8002):
  python agent.py
"""

from __future__ import annotations

import os

import httpx

GATEWAY_URL = "http://localhost:8002"
ENGINE_LABEL = os.environ.get("POLICY_ENGINE", "yaml").upper()

PROMPT = "Get the weather in London, then email me the results."

# The agent's plan: call these two tools in sequence.
TOOL_CALLS = [
    ("get_weather", {"city": "London"}),
    ("send_email",  {"to": "user@example.com", "subject": "Weather report"}),
]


def main() -> None:
    print("=" * 55)
    print(f"  Policy Sidecar Gateway — Demo  [{ENGINE_LABEL}]")
    print("=" * 55)
    print(f'\nUser prompt: "{PROMPT}"\n')
    print("Agent plan: call get_weather, then send_email\n")
    print("-" * 55)

    for tool_name, params in TOOL_CALLS:
        print(f"\n→ Agent calls tool: {tool_name!r}  params={params}")
        try:
            r = httpx.post(f"{GATEWAY_URL}/tool/{tool_name}", json=params, timeout=5.0)
        except httpx.ConnectError:
            print("  ERROR: gateway not reachable on port 8002")
            return

        if r.status_code == 200:
            print(f"  ✅ ALLOWED  — result: {r.json()}")
        else:
            detail = r.json().get("detail", {})
            error = detail.get("error", r.text) if isinstance(detail, dict) else r.text
            print(f"  🚫 DENIED   — {error}")

    print("\n" + "=" * 55)
    print("  Demo complete.")
    print("=" * 55)


if __name__ == "__main__":
    main()
