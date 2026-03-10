# Microsoft.AgentGovernance — .NET SDK

[![NuGet](https://img.shields.io/nuget/v/Microsoft.AgentGovernance)](https://www.nuget.org/packages/Microsoft.AgentGovernance)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Runtime security governance for autonomous AI agents. Policy enforcement, rate limiting, zero-trust identity, OpenTelemetry metrics, and tamper-proof audit logging — all in a single .NET 8.0 package.

Part of the [Agent Governance Toolkit](https://github.com/microsoft/agent-governance-toolkit).

## Install

```bash
dotnet add package Microsoft.AgentGovernance
```

## Quick Start

```csharp
using AgentGovernance;
using AgentGovernance.Policy;

var kernel = new GovernanceKernel(new GovernanceOptions
{
    PolicyPaths = new() { "policies/default.yaml" },
    ConflictStrategy = ConflictResolutionStrategy.DenyOverrides,
});

// Evaluate a tool call before execution
var result = kernel.EvaluateToolCall(
    agentId: "did:mesh:analyst-001",
    toolName: "file_write",
    args: new() { ["path"] = "/etc/config" }
);

if (!result.Allowed)
{
    Console.WriteLine($"Blocked: {result.Reason}");
    return;
}
// Proceed with the tool call
```

## Policy File (YAML)

```yaml
version: "1.0"
default_action: deny
rules:
  - name: allow-read-tools
    condition: "tool_name in allowed_tools"
    action: allow
    priority: 10

  - name: block-dangerous
    condition: "tool_name in blocked_tools"
    action: deny
    priority: 100

  - name: rate-limit-api
    condition: "tool_name == 'http_request'"
    action: rate_limit
    limit: "100/minute"
```

## Features

### Policy Engine

YAML-based policy rules with conditions, priorities, and four conflict resolution strategies:

| Strategy | Behaviour |
|----------|-----------|
| `DenyOverrides` | Any deny wins |
| `AllowOverrides` | Any allow wins |
| `PriorityFirstMatch` | Highest priority rule wins |
| `MostSpecificWins` | Agent > Tenant > Global scope |

### Rate Limiting

Sliding window rate limiter integrated into the policy engine:

```csharp
// Parsed automatically from policy YAML "100/minute" expressions
var limiter = kernel.RateLimiter;
bool allowed = limiter.TryAcquire("agent:tool_key", maxCalls: 100, TimeSpan.FromMinutes(1));
```

### Zero-Trust Identity

DID-based agent identity with cryptographic signing (HMAC-SHA256, Ed25519 migration path for .NET 9+):

```csharp
using AgentGovernance.Trust;

var identity = AgentIdentity.Create("research-assistant");
// identity.Did → "did:mesh:a7f3b2c1..."

byte[] signature = identity.Sign("important data");
bool valid = identity.Verify(Encoding.UTF8.GetBytes("important data"), signature);
```

### File-Backed Trust Store

Persist agent trust scores with automatic time-based decay:

```csharp
using AgentGovernance.Trust;

using var store = new FileTrustStore("trust-scores.json", defaultScore: 500, decayRate: 10);

store.SetScore("did:mesh:agent-001", 850);
store.RecordPositiveSignal("did:mesh:agent-001", boost: 25);
store.RecordNegativeSignal("did:mesh:agent-001", penalty: 100);

double score = store.GetScore("did:mesh:agent-001"); // Decays over time without positive signals
```

### OpenTelemetry Metrics

Built-in `System.Diagnostics.Metrics` instrumentation — works with any OTEL exporter:

```csharp
using AgentGovernance.Telemetry;

// Metrics are auto-enabled via GovernanceKernel
var kernel = new GovernanceKernel(); // kernel.Metrics is populated

// Or use standalone
using var metrics = new GovernanceMetrics();
metrics.RecordDecision(allowed: true, "did:mesh:agent", "file_read", evaluationMs: 0.05);
```

**Exported metrics:**

| Metric | Type | Description |
|--------|------|-------------|
| `agent_governance.policy_decisions` | Counter | Total policy decisions |
| `agent_governance.tool_calls_allowed` | Counter | Allowed tool calls |
| `agent_governance.tool_calls_blocked` | Counter | Blocked tool calls |
| `agent_governance.rate_limit_hits` | Counter | Rate-limited requests |
| `agent_governance.evaluation_latency_ms` | Histogram | Governance overhead (p99 < 0.1ms) |
| `agent_governance.trust_score` | Gauge | Per-agent trust score |
| `agent_governance.active_agents` | Gauge | Tracked agent count |

### Audit Events

Thread-safe pub-sub event system for compliance logging:

```csharp
kernel.OnEvent(GovernanceEventType.ToolCallBlocked, evt =>
{
    logger.LogWarning("Blocked {Tool} for {Agent}: {Reason}",
        evt.Data["tool_name"], evt.AgentId, evt.Data["reason"]);
});

kernel.OnAllEvents(evt => auditLog.Append(evt));
```

## Microsoft Agent Framework Integration

Works as middleware in MAF / Azure AI Foundry Agent Service:

```csharp
using AgentGovernance.Integration;

var middleware = new GovernanceMiddleware(engine, emitter, rateLimiter, metrics);
var result = middleware.EvaluateToolCall("did:mesh:agent", "database_write", new() { ["table"] = "users" });
```

See the [MAF adapter](../../packages/agent-os/src/agent_os/integrations/maf_adapter.py) for the full Python middleware, or the [Foundry integration guide](../../docs/deployment/azure-foundry-agent-service.md) for Azure deployment.

## Requirements

- .NET 8.0+
- No external dependencies beyond `YamlDotNet` (for policy parsing)

## OWASP Agentic AI Top 10 Coverage

The .NET SDK addresses all 10 OWASP categories:

| Risk | Mitigation |
|------|-----------|
| Goal Hijacking | Semantic policy conditions |
| Tool Misuse | Capability allow/deny lists |
| Identity Abuse | DID-based identity + trust scoring |
| Supply Chain | Build provenance attestation |
| Code Execution | Rate limiting + policy enforcement |
| Memory Poisoning | Stateless evaluation (no shared context) |
| Insecure Comms | Cryptographic signing |
| Cascading Failures | Rate limiting + circuit-breaker patterns |
| Trust Exploitation | Approval workflows |
| Rogue Agents | Trust decay + behavioural detection |

## Contributing

See [CONTRIBUTING.md](../../CONTRIBUTING.md). The .NET SDK follows the same contribution process as the Python packages.

## License

[MIT](../../LICENSE) © Microsoft Corporation
