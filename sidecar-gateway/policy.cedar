// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.
//
// AgentMesh demo policy — Cedar equivalent of policy.yaml
//
// Deny by default; only get_weather is explicitly permitted.
// Evaluated via CedarEvaluator (cedarpy → CLI → builtin, auto-detected).

// Weather queries are safe to call autonomously.
permit(
    principal,
    action == Action::"get_weather",
    resource
);

// Email requires human approval — blocked at the gateway.
forbid(
    principal,
    action == Action::"send_email",
    resource
);
