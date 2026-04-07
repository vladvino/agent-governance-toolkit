# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
#
# AgentMesh demo policy — OPA/Rego equivalent of policy.yaml
#
# Deny by default: only tools with an explicit allow rule are permitted.
# Evaluated via data.agentmesh.allow

package agentmesh

default allow = false

# Weather queries are safe to call autonomously.
allow {
    input.tool == "get_weather"
}

# send_email has no allow rule — denied by default.
# (No explicit deny needed; absence of an allow rule is sufficient.)
