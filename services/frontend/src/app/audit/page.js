'use client';

import { useEffect, useState } from 'react';

export default function AuditPage() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterSeverity, setFilterSeverity] = useState('ALL');

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    fetch(`${apiUrl}/audit?limit=50`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => {
        if (Array.isArray(data)) {
          setLogs(data);
        }
      })
      .catch((err) => {
        setError(err.message);
      })
      .finally(() => setLoading(false));
  }, []);

  const filteredLogs = logs.filter((log) => {
    const matchesSearch =
      (log.pod_name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (log.action_type || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (log.namespace || '').toLowerCase().includes(searchTerm.toLowerCase());

    const matchesSeverity =
      filterSeverity === 'ALL' || (log.severity || '').toLowerCase() === filterSeverity.toLowerCase();

    return matchesSearch && matchesSeverity;
  });

  return (
    <div className="section section--white">
      <div className="container">
        <div className="section-label">audit.sql</div>

        <div className="audit-header">
          <div>
            <h1 className="h2">PostgreSQL Audit Trail</h1>
            <p className="body" style={{ color: 'var(--navy-70)', marginTop: 'var(--space-xs)' }}>
              Immutable record of every cluster event, diagnosis, decision, and K8s API mutation synced via Kafka Connect JDBC.
            </p>
          </div>
        </div>

        {/* ── Search & Filters ─────────────────────────────────────────────── */}
        <div className="hard-card filter-bar" style={{ marginBottom: 'var(--space-xl)' }}>
          <div className="filter-group">
            <label className="mono" style={{ fontSize: '12px', color: 'var(--navy-70)' }}>
              Search Pod / Action / Namespace:
            </label>
            <input
              type="text"
              placeholder="e.g. devops-ai-api or increase_memory_limit..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="mono filter-input"
            />
          </div>

          <div className="filter-group">
            <label className="mono" style={{ fontSize: '12px', color: 'var(--navy-70)' }}>
              Filter Severity:
            </label>
            <select
              value={filterSeverity}
              onChange={(e) => setFilterSeverity(e.target.value)}
              className="mono filter-select"
            >
              <option value="ALL">ALL SEVERITIES</option>
              <option value="critical">CRITICAL</option>
              <option value="warning">WARNING</option>
            </select>
          </div>
        </div>

        {/* ── Mono Data Table (REAL POSTGRESQL DATA ONLY) ────────────────── */}
        <div className="hard-card" style={{ padding: 0, overflow: 'hidden' }}>
          {loading ? (
            <div className="empty-state" style={{ border: 'none' }}>
              <div className="empty-state-icon">⏳</div>
              <p className="mono">Querying PostgreSQL agent_actions table...</p>
            </div>
          ) : error ? (
            <div className="empty-state" style={{ border: 'none' }}>
              <div className="empty-state-icon">⚠️</div>
              <h3 className="h3" style={{ marginBottom: 'var(--space-xs)' }}>
                Database Offline
              </h3>
              <p className="body" style={{ color: 'var(--navy-70)', fontSize: '14px' }}>
                Unable to query PostgreSQL at <code className="mono">/audit</code> endpoint. Ensure <code className="mono">devops-ai-agent</code> and PostgreSQL are running.
              </p>
            </div>
          ) : filteredLogs.length === 0 ? (
            <div className="empty-state" style={{ border: 'none' }}>
              <div className="empty-state-icon">📄</div>
              <h3 className="h3" style={{ marginBottom: 'var(--space-xs)' }}>
                No Audit Records Found
              </h3>
              <p className="body" style={{ color: 'var(--navy-70)', fontSize: '14px' }}>
                No records match your query. Execute a chaos test in <code className="mono">chaos.sh</code> to generate live remediation audit logs.
              </p>
            </div>
          ) : (
            <table className="audit-table">
              <thead>
                <tr>
                  <th>Action ID</th>
                  <th>Pod Name</th>
                  <th>Namespace</th>
                  <th>Triggered By</th>
                  <th>Classification</th>
                  <th>Action Type</th>
                  <th>Outcome</th>
                  <th>Timestamp</th>
                </tr>
              </thead>
              <tbody>
                {filteredLogs.map((row) => (
                  <tr key={row.action_id || row.created_at}>
                    <td>
                      <span className="mono" style={{ color: 'var(--k8s-blue)' }}>
                        {row.action_id?.slice(0, 12) || 'N/A'}
                      </span>
                    </td>
                    <td style={{ fontWeight: '500' }}>{row.pod_name || 'N/A'}</td>
                    <td>{row.namespace || 'default'}</td>
                    <td>
                      <span className="badge badge--info" style={{ fontSize: '11px' }}>
                        {row.triggered_by || 'alert'}
                      </span>
                    </td>
                    <td>{row.classification || 'Incident'}</td>
                    <td>
                      <code>{row.action_type || row.action || 'remediate'}</code>
                    </td>
                    <td>
                      <OutcomeBadge outcome={row.outcome} />
                    </td>
                    <td style={{ color: 'var(--navy-40)' }}>
                      {row.created_at ? new Date(row.created_at).toLocaleString() : 'N/A'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <style jsx>{`
        .audit-header {
          margin-bottom: var(--space-xl);
        }
        .filter-bar {
          display: flex;
          gap: var(--space-lg);
          align-items: center;
        }
        .filter-group {
          display: flex;
          flex-direction: column;
          gap: 4px;
          flex: 1;
        }
        .filter-input, .filter-select {
          padding: 8px 12px;
          border: 2px solid var(--navy);
          border-radius: 6px;
          background: var(--white);
          color: var(--navy);
          outline: none;
        }
        .filter-input:focus, .filter-select:focus {
          border-color: var(--k8s-blue);
        }
      `}</style>
    </div>
  );
}

function OutcomeBadge({ outcome }) {
  if (outcome === 'success') {
    return <span className="badge badge--verified">✓ SUCCESS</span>;
  }
  if (outcome === 'unverified') {
    return <span className="badge badge--escalated">⚠️ ESCALATED</span>;
  }
  return <span className="badge badge--failed">✕ FAILED</span>;
}
