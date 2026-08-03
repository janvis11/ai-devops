'use client';

import { useState } from 'react';

export default function ChaosPage() {
  const [logs, setLogs] = useState([
    `[${new Date().toLocaleTimeString()}] chaos.sh initialized. Ready for failure injection.`,
    `[INFO] Triggers invoke live cluster endpoints on devops-ai-agent or microservices.`,
  ]);
  const [loading, setLoading] = useState(false);

  const addLog = (msg) => {
    setLogs((prev) => [`[${new Date().toLocaleTimeString()}] ${msg}`, ...prev]);
  };

  const triggerOOM = async () => {
    setLoading(true);
    addLog('💣 GET /chaos/oom — Triggering memory leak on devops-ai-api (http://localhost:8000/chaos/oom)...');
    try {
      const res = await fetch('http://localhost:8000/chaos/oom', { method: 'GET' });
      const text = await res.text();
      addLog(`[HTTP ${res.status}] Response: ${text.slice(0, 100)}`);
    } catch (err) {
      addLog(`❌ Connection Error: ${err.message} (Is API running on http://localhost:8000?)`);
    } finally {
      setLoading(false);
    }
  };

  const triggerKillPod = async () => {
    setLoading(true);
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    addLog(`💣 POST ${apiUrl}/chaos/kill-pod — Deleting pod app=devops-ai-api...`);
    try {
      const res = await fetch(`${apiUrl}/chaos/kill-pod`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pod_selector: 'app=devops-ai-api', namespace: 'apps' }),
      });
      const data = await res.json();
      if (res.ok) {
        addLog(`✅ [HTTP ${res.status}] Pod killed: ${data.pod || 'devops-ai-api'} (Status: ${data.status})`);
      } else {
        addLog(`⚠️ [HTTP ${res.status}] ${data.detail || JSON.stringify(data)}`);
      }
    } catch (err) {
      addLog(`❌ Connection Error: ${err.message} (Is devops-ai-agent running?)`);
    } finally {
      setLoading(false);
    }
  };

  const triggerConfigDrift = async () => {
    setLoading(true);
    addLog('💣 Simulating Config Drift — injecting invalid config parameter...');
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const res = await fetch(`${apiUrl}/chaos/kill-pod`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pod_selector: 'app=devops-ai-frontend', namespace: 'apps' }),
      });
      const data = await res.json();
      addLog(`✅ Experiment executed: ${JSON.stringify(data)}`);
    } catch (err) {
      addLog(`❌ Connection Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="section section--ice">
      <div className="container">
        <div className="section-label">chaos.sh</div>

        <div style={{ marginBottom: 'var(--space-xl)' }}>
          <h1 className="h2">Chaos Control Panel</h1>
          <p className="body" style={{ color: 'var(--navy-70)', marginTop: 'var(--space-xs)' }}>
            Inject live failure experiments into the cluster to validate Prometheus alerting and AI Agent auto-remediation.
          </p>
        </div>

        {/* ── Chaos Trigger Buttons (REAL ENDPOINTS ONLY) ────────────────── */}
        <div className="grid-3" style={{ marginBottom: 'var(--space-xl)' }}>
          <div className="hard-card">
            <div className="badge badge--failed" style={{ marginBottom: 'var(--space-md)' }}>
              Experiment 01
            </div>
            <h3 className="h3" style={{ marginBottom: 'var(--space-xs)' }}>
              Trigger OOM Leak
            </h3>
            <p className="body" style={{ color: 'var(--navy-70)', marginBottom: 'var(--space-md)', fontSize: '14px' }}>
              Invokes GET <code className="mono">/chaos/oom</code> on devops-ai-api to leak memory and trigger Prometheus <code className="mono">PodOOMKilled</code> alert.
            </p>
            <button
              className="hard-btn hard-btn--danger"
              onClick={triggerOOM}
              disabled={loading}
            >
              <span>{loading ? 'Executing...' : 'Execute OOM Leak'}</span>
              <span className="mono">→</span>
            </button>
          </div>

          <div className="hard-card">
            <div className="badge badge--failed" style={{ marginBottom: 'var(--space-md)' }}>
              Experiment 02
            </div>
            <h3 className="h3" style={{ marginBottom: 'var(--space-xs)' }}>
              Kill API Pod
            </h3>
            <p className="body" style={{ color: 'var(--navy-70)', marginBottom: 'var(--space-md)', fontSize: '14px' }}>
              Invokes POST <code className="mono">/chaos/kill-pod</code> to issue pod deletion for app=devops-ai-api in apps namespace.
            </p>
            <button
              className="hard-btn hard-btn--danger"
              onClick={triggerKillPod}
              disabled={loading}
            >
              <span>{loading ? 'Executing...' : 'Kill API Pod'}</span>
              <span className="mono">→</span>
            </button>
          </div>

          <div className="hard-card">
            <div className="badge badge--escalated" style={{ marginBottom: 'var(--space-md)' }}>
              Experiment 03
            </div>
            <h3 className="h3" style={{ marginBottom: 'var(--space-xs)' }}>
              Config Drift / Kill Frontend
            </h3>
            <p className="body" style={{ color: 'var(--navy-70)', marginBottom: 'var(--space-md)', fontSize: '14px' }}>
              Invokes POST <code className="mono">/chaos/kill-pod</code> targeting app=devops-ai-frontend to test multi-app remediation.
            </p>
            <button
              className="hard-btn hard-btn--outline"
              onClick={triggerConfigDrift}
              disabled={loading}
            >
              <span>{loading ? 'Executing...' : 'Kill Frontend Pod'}</span>
              <span className="mono">→</span>
            </button>
          </div>
        </div>

        {/* ── Chaos Execution Log Terminal ─────────────────────────────────── */}
        <div className="hard-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 'var(--space-sm)' }}>
            <span className="mono" style={{ fontWeight: '600' }}>Live Output Console — stdout</span>
            <span className="mono" style={{ color: 'var(--navy-40)' }}>bash chaos.sh</span>
          </div>

          <div className="terminal-box">
            {logs.map((log, idx) => (
              <div key={idx} className="mono terminal-line">
                {log}
              </div>
            ))}
          </div>
        </div>
      </div>

      <style jsx>{`
        .terminal-box {
          background: var(--navy);
          color: var(--ice);
          padding: var(--space-md);
          border-radius: 6px;
          min-height: 180px;
          max-height: 280px;
          overflow-y: auto;
        }
        .terminal-line {
          font-size: 13px;
          line-height: 1.6;

        }
      `}</style>
    </div>
  );
}
