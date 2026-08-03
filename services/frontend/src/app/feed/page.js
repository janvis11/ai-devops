'use client';

import { useEffect, useState } from 'react';

export default function FeedPage() {
  const [events, setEvents] = useState([]);
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

    // 1. Fetch initial real history from audit endpoint
    fetch(`${apiUrl}/audit?limit=20`)
      .then((res) => (res.ok ? res.json() : []))
      .then((data) => {
        if (Array.isArray(data)) {
          setEvents(data);
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));

    // 2. Connect to SSE stream for live decisions
    const eventSource = new EventSource(`${apiUrl}/stream/decisions`);

    eventSource.onopen = () => setConnected(true);

    eventSource.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (data.action_id) {
          setEvents((prev) => [data, ...prev.filter((item) => item.action_id !== data.action_id)]);
        }
      } catch (err) {
        // Heartbeat or comment line
      }
    };

    eventSource.onerror = () => {
      setConnected(false);
      eventSource.close();
    };

    return () => eventSource.close();
  }, []);

  const verifiedCount = events.filter((e) => e.outcome === 'success' || e.verified === true).length;
  const successRate = events.length > 0 ? Math.round((verifiedCount / events.length) * 100) : 100;

  return (
    <div className="section section--white">
      <div className="container">
        <div className="feed-header">
          <div>
            <div className="section-label">feed.log</div>
            <h1 className="h2">Real-Time Remediation Stream</h1>
          </div>
          <div className="connection-status">
            <span
              className={`status-dot ${connected ? '' : 'status-dot--idle'}`}
              style={{ background: connected ? 'var(--signal-green)' : 'var(--signal-amber)' }}
            />
            <span className="mono">
              {connected ? 'SSE STREAM ACTIVE (agent.decisions)' : 'SSE DISCONNECTED'}
            </span>
          </div>
        </div>

        <div className="grid-2" style={{ gridTemplateColumns: '1.4fr 0.6fr' }}>
          {/* ── Main Decision Stream (REAL DATA) ───────────────────────────── */}
          <div className="feed-stream">
            {loading ? (
              <div className="empty-state">
                <div className="empty-state-icon">⏳</div>
                <p className="mono">Loading decision feed from cluster...</p>
              </div>
            ) : events.length === 0 ? (
              <div className="empty-state">
                <div className="empty-state-icon">🛡️</div>
                <h3 className="h3" style={{ marginBottom: 'var(--space-xs)' }}>
                  Cluster Healthy — No Incidents
                </h3>
                <p className="body" style={{ color: 'var(--navy-70)', fontSize: '14px' }}>
                  Watching cluster events. Trigger a chaos test in <code className="mono">chaos.sh</code> to generate live remediation decisions.
                </p>
              </div>
            ) : (
              events.map((evt) => (
                <div key={evt.action_id || evt.created_at} className="hard-card feed-card feed-card-enter">
                  <div className="feed-card-header">
                    <span className="mono pod-tag">pod: {evt.pod_name || 'N/A'}</span>
                    <Badge outcome={evt.outcome} verified={evt.verified} action={evt.action_type || evt.action} />
                  </div>

                  <p className="body" style={{ margin: 'var(--space-sm) 0', color: 'var(--navy)' }}>
                    {evt.explanation || evt.diagnosis || evt.classification || 'Action recorded by agent.'}
                  </p>

                  <div className="feed-card-footer mono">
                    <span>ns: {evt.namespace || 'default'}</span>
                    <span>type: {evt.classification || evt.event_type || 'Alert'}</span>
                    <span>action: {evt.action_type || evt.action || 'remediate'}</span>
                    <span>{evt.created_at || evt.timestamp ? new Date(evt.created_at || evt.timestamp).toLocaleTimeString() : 'now'}</span>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* ── Sidebar Telemetry (REAL DATA) ─────────────────────────────── */}
          <div className="feed-sidebar">
            <div className="hard-card" style={{ marginBottom: 'var(--space-lg)' }}>
              <h3 className="h3" style={{ marginBottom: 'var(--space-md)' }}>Stream Telemetry</h3>
              <div className="side-metric">
                <span className="mono" style={{ color: 'var(--navy-70)' }}>Buffered Events</span>
                <span className="mono" style={{ fontWeight: '600' }}>{events.length}</span>
              </div>
              <div className="side-metric">
                <span className="mono" style={{ color: 'var(--navy-70)' }}>Success Rate</span>
                <span className="mono" style={{ fontWeight: '600', color: 'var(--signal-green)' }}>
                  {successRate}%
                </span>
              </div>
              <div className="side-metric">
                <span className="mono" style={{ color: 'var(--navy-70)' }}>Kafka Topic</span>
                <span className="mono">agent.decisions</span>
              </div>
            </div>

            <div className="hard-card">
              <h3 className="h3" style={{ marginBottom: 'var(--space-sm)' }}>How it works</h3>
              <p className="body" style={{ color: 'var(--navy-70)', fontSize: '14px' }}>
                When Alertmanager fires an alert, the AI Agent diagnoses root causes, executes K8s actions, verifies health, and emits live decisions to this stream.
              </p>
            </div>
          </div>
        </div>
      </div>

      <style jsx>{`
        .feed-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-end;
          margin-bottom: var(--space-xl);
        }
        .connection-status {
          display: flex;
          align-items: center;
          gap: var(--space-xs);
          padding: 6px 12px;
          border: var(--border);
          border-radius: 6px;
          background: var(--ice);
          box-shadow: 2px 2px 0 var(--navy);
        }
        .status-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
        }
        .feed-stream {
          display: flex;
          flex-direction: column;
          gap: var(--space-md);
        }
        .feed-card {
          border-left: 6px solid var(--k8s-blue);
        }
        .feed-card-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        .pod-tag {
          font-weight: 600;
          color: var(--navy);
        }
        .feed-card-footer {
          display: flex;
          gap: var(--space-md);
          font-size: 11px;
          color: var(--navy-40);
          border-top: 1px solid var(--ice);
          padding-top: var(--space-xs);
        }
        .side-metric {
          display: flex;
          justify-content: space-between;
          padding: 8px 0;
          border-bottom: 1px solid var(--ice);
        }
      `}</style>
    </div>
  );
}

function Badge({ outcome, verified, action }) {
  if (action === 'manual_review' || outcome === 'unverified') {
    return <span className="badge badge--escalated">⚠️ Escalated to Slack</span>;
  }
  if (verified || outcome === 'success') {
    return <span className="badge badge--verified">✓ Verified Healthy</span>;
  }
  return <span className="badge badge--failed">✕ Failed</span>;
}
