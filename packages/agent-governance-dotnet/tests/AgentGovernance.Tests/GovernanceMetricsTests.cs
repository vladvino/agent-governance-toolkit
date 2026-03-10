// Copyright (c) Microsoft Corporation. Licensed under the MIT License.

using System.Diagnostics.Metrics;
using AgentGovernance.Telemetry;
using Xunit;

namespace AgentGovernance.Tests;

public class GovernanceMetricsTests : IDisposable
{
    private readonly GovernanceMetrics _metrics = new();

    [Fact]
    public void MeterName_IsAgentGovernance()
    {
        Assert.Equal("AgentGovernance", GovernanceMetrics.MeterName);
    }

    [Fact]
    public void RecordDecision_AllowedIncrementsCounters()
    {
        long policyCount = 0;
        long allowedCount = 0;
        long blockedCount = 0;

        using var listener = new MeterListener();
        listener.InstrumentPublished = (instrument, listener) =>
        {
            if (instrument.Meter.Name == GovernanceMetrics.MeterName)
                listener.EnableMeasurementEvents(instrument);
        };
        listener.SetMeasurementEventCallback<long>((instrument, measurement, tags, state) =>
        {
            if (instrument.Name == "agent_governance.policy_decisions") policyCount += measurement;
            if (instrument.Name == "agent_governance.tool_calls_allowed") allowedCount += measurement;
            if (instrument.Name == "agent_governance.tool_calls_blocked") blockedCount += measurement;
        });
        listener.Start();

        _metrics.RecordDecision(allowed: true, "did:mesh:test", "file_read", 0.05);
        listener.RecordObservableInstruments();

        Assert.Equal(1, policyCount);
        Assert.Equal(1, allowedCount);
        Assert.Equal(0, blockedCount);
    }

    [Fact]
    public void RecordDecision_DeniedIncrementsBlockedCounter()
    {
        long blockedCount = 0;

        using var listener = new MeterListener();
        listener.InstrumentPublished = (instrument, listener) =>
        {
            if (instrument.Meter.Name == GovernanceMetrics.MeterName)
                listener.EnableMeasurementEvents(instrument);
        };
        listener.SetMeasurementEventCallback<long>((instrument, measurement, tags, state) =>
        {
            if (instrument.Name == "agent_governance.tool_calls_blocked") blockedCount += measurement;
        });
        listener.Start();

        _metrics.RecordDecision(allowed: false, "did:mesh:test", "shell_exec", 0.02);
        listener.RecordObservableInstruments();

        Assert.Equal(1, blockedCount);
    }

    [Fact]
    public void RecordDecision_RateLimitedIncrementsRateLimitCounter()
    {
        long rateLimitCount = 0;

        using var listener = new MeterListener();
        listener.InstrumentPublished = (instrument, listener) =>
        {
            if (instrument.Meter.Name == GovernanceMetrics.MeterName)
                listener.EnableMeasurementEvents(instrument);
        };
        listener.SetMeasurementEventCallback<long>((instrument, measurement, tags, state) =>
        {
            if (instrument.Name == "agent_governance.rate_limit_hits") rateLimitCount += measurement;
        });
        listener.Start();

        _metrics.RecordDecision(allowed: false, "did:mesh:test", "api_call", 0.01, rateLimited: true);
        listener.RecordObservableInstruments();

        Assert.Equal(1, rateLimitCount);
    }

    [Fact]
    public void RecordDecision_RecordsLatencyHistogram()
    {
        double latency = 0;

        using var listener = new MeterListener();
        listener.InstrumentPublished = (instrument, listener) =>
        {
            if (instrument.Meter.Name == GovernanceMetrics.MeterName)
                listener.EnableMeasurementEvents(instrument);
        };
        listener.SetMeasurementEventCallback<double>((instrument, measurement, tags, state) =>
        {
            if (instrument.Name == "agent_governance.evaluation_latency_ms") latency = measurement;
        });
        listener.Start();

        _metrics.RecordDecision(allowed: true, "did:mesh:test", "search", 0.087);

        Assert.Equal(0.087, latency, precision: 5);
    }

    [Fact]
    public void RegisterTrustScoreGauge_ReportsValues()
    {
        double observedScore = 0;

        _metrics.RegisterTrustScoreGauge(() => new[]
        {
            new Measurement<double>(850.0, new KeyValuePair<string, object?>("agent_id", "did:mesh:test"))
        });

        using var listener = new MeterListener();
        listener.InstrumentPublished = (instrument, listener) =>
        {
            if (instrument.Meter.Name == GovernanceMetrics.MeterName)
                listener.EnableMeasurementEvents(instrument);
        };
        listener.SetMeasurementEventCallback<double>((instrument, measurement, tags, state) =>
        {
            if (instrument.Name == "agent_governance.trust_score") observedScore = measurement;
        });
        listener.Start();
        listener.RecordObservableInstruments();

        Assert.Equal(850.0, observedScore);
    }

    [Fact]
    public void RegisterActiveAgentsGauge_ReportsCount()
    {
        int observedCount = 0;

        _metrics.RegisterActiveAgentsGauge(() => 42);

        using var listener = new MeterListener();
        listener.InstrumentPublished = (instrument, listener) =>
        {
            if (instrument.Meter.Name == GovernanceMetrics.MeterName)
                listener.EnableMeasurementEvents(instrument);
        };
        listener.SetMeasurementEventCallback<int>((instrument, measurement, tags, state) =>
        {
            if (instrument.Name == "agent_governance.active_agents") observedCount = measurement;
        });
        listener.Start();
        listener.RecordObservableInstruments();

        Assert.Equal(42, observedCount);
    }

    public void Dispose() => _metrics.Dispose();
}
