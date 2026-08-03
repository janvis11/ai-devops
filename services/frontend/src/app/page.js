'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { HelmWheel } from '@/components/HelmWheel';

export default function OverviewPage() {
  const [status, setStatus] = useState(null);
  const [auditCount, setAuditCount] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

    Promise.all([
      fetch(`${apiUrl}/status`).then((res) => (res.ok ? res.json() : null)),
      fetch(`${apiUrl}/audit?limit=100`).then((res) => (res.ok ? res.json() : null)),
    ])
      .then(([statusData, auditData]) => {
        if (statusData) setStatus(statusData);
        if (Array.isArray(auditData)) setAuditCount(auditData.length);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      {/* ── Section 1: Hero ────────────────────────────────────────────────── */}
      <section className="section section--white">
        <div className="container hero-grid">
          <div className="hero-content">
            <div className="section-label">overview.mdx</div>
            <h1 className="h1 hero-title">
              Nobody paged.<br />It was already fixed.
            </h1>
            <p className="subhead hero-subhead">
              Autonomous incident detection, root-cause diagnosis, and self-healing remediation for Kubernetes clusters. Powered by LangGraph &amp; Claude.
            </p>
            <div className="hero-ctas">
              <Link href="/feed" className="hard-btn">
                <span>View Live Feed</span>
                <span className="mono">feed.log →</span>
              </Link>
              <Link href="/pipeline" className="hard-btn hard-btn--outline">
                <span>Explore Pipeline</span>
                <span className="mono">pipeline.yaml</span>
              </Link>
            </div>
          </div>
          <div className="hero-illustration">
            <HelmWheel size={300} />
          </div>
        </div>
      </section>

      {/* ── Section 2: Metrics Strip (REAL DATA ONLY) ────────────────────────── */}
      <section className="section section--ice">
        <div className="container">
          <div className="section-label">cluster_telemetry.stat</div>
          <div className="grid-4">
            <div className="hard-card stat-card">
              <span className="mono stat-label">Correlator Window</span>
              <span className="h1 stat-value" style={{ color: 'var(--k8s-blue)' }}>
                {status?.config?.dedup_window ? `${status.config.dedup_window}s` : '--'}
              </span>
              <span className="mono stat-desc">Sliding event buffer</span>
            </div>

            <div className="hard-card stat-card">
              <span className="mono stat-label">Active Investigations</span>
              <span className="h1 stat-value" style={{ color: 'var(--signal-green)' }}>
                {status?.correlator?.active_investigations ?? 0}
              </span>
              <span className="mono stat-desc">Pods currently analyzing</span>
            </div>

            <div className="hard-card stat-card">
              <span className="mono stat-label">Audit DB Records</span>
              <span className="h1 stat-value" style={{ color: 'var(--navy)' }}>
                {auditCount !== null ? auditCount : '--'}
              </span>
              <span className="mono stat-desc">PostgreSQL agent_actions</span>
            </div>

            <div className="hard-card stat-card">
              <span className="mono stat-label">AI Agent Service</span>
              <span className="h1 stat-value" style={{ color: status ? 'var(--signal-green)' : 'var(--signal-amber)' }}>
                {status ? 'ONLINE' : 'OFFLINE'}
              </span>
              <span className="mono stat-desc">{status?.version ? `v${status.version}` : 'Connecting to API...'}</span>
            </div>
          </div>
        </div>
      </section>

      {/* ── Section 3: Key Features ─────────────────────────────────────────── */}
      <section className="section section--white">
        <div className="container">
          <div className="section-label">architecture_features.md</div>
          <h2 className="h2" style={{ marginBottom: 'var(--space-xl)' }}>
            Built for total cluster autonomy with safety guardrails.
          </h2>

          <div className="grid-3">
            <div className="hard-card">
              <div className="badge badge--info" style={{ marginBottom: 'var(--space-md)' }}>01. Telemetry</div>
              <h3 className="h3" style={{ marginBottom: 'var(--space-sm)' }}>Kafka Event Mesh</h3>
              <p className="body" style={{ color: 'var(--navy-70)' }}>
                Streams Prometheus alerts, pod stdout/stderr logs, OTel traces, and K8s API events across dedicated Kafka topics in real time.
              </p>
            </div>

            <div className="hard-card">
              <div className="badge badge--info" style={{ marginBottom: 'var(--space-md)' }}>02. AI Reasoning</div>
              <h3 className="h3" style={{ marginBottom: 'var(--space-sm)' }}>7-Node LangGraph FSM</h3>
              <p className="body" style={{ color: 'var(--navy-70)' }}>
                Classifies incidents with Claude 3.5 Sonnet, correlates metrics/logs, maps playbooks, and safely executes mutations via K8s Python client.
              </p>
            </div>

            <div className="hard-card">
              <div className="badge badge--info" style={{ marginBottom: 'var(--space-md)' }}>03. Safety &amp; Audit</div>
              <h3 className="h3" style={{ marginBottom: 'var(--space-sm)' }}>Slack HITL &amp; Postgres</h3>
              <p className="body" style={{ color: 'var(--navy-70)' }}>
                High-risk actions route to Slack for human approval. Every single decision is immutably logged into PostgreSQL via Kafka Connect JDBC.
              </p>
            </div>
          </div>
        </div>
      </section>

      <style jsx>{`
        .hero-grid {
          display: grid;
          grid-template-columns: 1.2fr 0.8fr;
          gap: var(--space-xl);
          align-items: center;
          padding: var(--space-xl) 0;
        }
        .hero-title {
          margin-bottom: var(--space-md);
        }
        .hero-subhead {
          margin-bottom: var(--space-xl);
          max-width: 540px;
        }
        .hero-ctas {
          display: flex;
          gap: var(--space-md);
        }
        .hero-illustration {
          display: flex;
          justify-content: center;
        }
        .stat-card {
          display: flex;
          flex-direction: column;
          gap: var(--space-xs);
        }
        .stat-label {
          color: var(--navy-70);
          text-transform: uppercase;
        }
        .stat-value {
          font-size: 38px;
          margin: var(--space-xs) 0;
        }
        .stat-desc {
          color: var(--navy-40);
        }
        @media (max-width: 768px) {
          .hero-grid {
            grid-template-columns: 1fr;
          }
          .hero-ctas {
            flex-direction: column;
          }
        }
      `}</style>
    </div>
  );
}
