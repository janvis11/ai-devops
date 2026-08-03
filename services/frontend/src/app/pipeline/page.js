'use client';

import { useState } from 'react';

const NODES = [
  {
    id: 'classify',
    name: 'classify',
    type: 'LLM Node',
    tool: 'Claude 3.5 Sonnet',
    description: 'Categorizes K8s event (OOMKill, CrashLoop, ResourceExhaustion) and determines if safe_to_automate=true.',
    inputs: ['raw_kafka_event', 'correlated_events_60s', 'logs_preview'],
    outputs: ['event_type', 'confidence', 'safe_to_automate'],
  },
  {
    id: 'escalate',
    name: 'escalate',
    type: 'HITL Node',
    tool: 'Slack SDK (Block Kit)',
    description: 'Triggered when safe_to_automate=false. Posts Approve/Reject buttons to Slack and pauses graph via LangGraph interrupt().',
    inputs: ['event_type', 'confidence', 'diagnosis'],
    outputs: ['slack_thread_ts', 'requires_approval', 'approved'],
  },
  {
    id: 'diagnose',
    name: 'diagnose',
    type: 'Analysis Node',
    tool: 'Claude 3.5 + PromQL + Log Fetcher',
    description: 'Fetches 200 lines of pod stdout/stderr logs and 4 PromQL queries, then generates technical root-cause analysis.',
    inputs: ['pod_logs', 'promql_metrics', 'event_type'],
    outputs: ['diagnosis', 'explanation'],
  },
  {
    id: 'decide',
    name: 'decide',
    type: 'Playbook Node',
    tool: 'Playbook Engine + Claude',
    description: 'Selects optimal remediation action from playbook (increase_memory_limit, restart_pod, scale_deployment, trigger_hpa).',
    inputs: ['diagnosis', 'playbook_options'],
    outputs: ['chosen_action', 'action_params'],
  },
  {
    id: 'act',
    name: 'act',
    type: 'K8s Mutation Node',
    tool: 'Kubernetes Python Client',
    description: 'Executes direct API mutation against k3s cluster (patches memory limits, deletes pods for recreate, scales replicas).',
    inputs: ['chosen_action', 'action_params', 'pod_name'],
    outputs: ['k8s_api_response', 'action_result'],
  },
  {
    id: 'verify',
    name: 'verify',
    type: 'Health Check Node',
    tool: 'K8s API Poller',
    description: 'Polls Kubernetes API every 5s for up to 60s to verify pod returns to Running phase with Ready=True.',
    inputs: ['pod_name', 'namespace', 'timeout_seconds'],
    outputs: ['verified', 'verify_attempts'],
  },
  {
    id: 'audit',
    name: 'audit',
    type: 'Persistence Node',
    tool: 'Kafka Producer → JDBC Sink',
    description: 'Emits complete execution record to agent.actions (PostgreSQL JDBC sink) and agent.decisions (React SSE feed).',
    inputs: ['full_execution_state'],
    outputs: ['action_id', 'audit_table_row'],
  },
];

export default function PipelinePage() {
  const [selectedNode, setSelectedNode] = useState(NODES[0]);

  return (
    <div className="section section--ice">
      <div className="container">
        <div className="section-label">pipeline.yaml</div>

        <div className="pipeline-header">
          <h1 className="h2">LangGraph Remediation FSM Engine</h1>
          <p className="body" style={{ color: 'var(--navy-70)', marginTop: 'var(--space-xs)' }}>
            7-node deterministic state machine orchestrating incident classification, root-cause diagnosis, Slack HITL, and automated K8s recovery.
          </p>
        </div>

        {/* ── FSM Graph Flow ─────────────────────────────────────────────────── */}
        <div className="hard-card graph-canvas" style={{ marginBottom: 'var(--space-xl)' }}>
          <div className="graph-flow">
            {NODES.map((node, index) => {
              const isSelected = selectedNode.id === node.id;
              return (
                <div key={node.id} className="graph-step">
                  <button
                    className={`node-pill ${isSelected ? 'node-pill--active' : ''}`}
                    onClick={() => setSelectedNode(node)}
                  >
                    <span className="mono node-step-num">0{index + 1}</span>
                    <span className="mono node-title">[{node.name}]</span>
                  </button>

                  {index < NODES.length - 1 && (
                    <div className="flow-arrow">
                      <span className="mono">──►</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* ── Node Detail Inspector ────────────────────────────────────────── */}
        <div className="grid-2">
          <div className="hard-card">
            <div className="badge badge--info" style={{ marginBottom: 'var(--space-md)' }}>
              {selectedNode.type}
            </div>
            <h3 className="h2" style={{ fontSize: '24px', marginBottom: 'var(--space-xs)' }}>
              node: [{selectedNode.name}]
            </h3>
            <p className="mono" style={{ color: 'var(--navy-40)', marginBottom: 'var(--space-md)' }}>
              Engine: {selectedNode.tool}
            </p>
            <p className="body" style={{ color: 'var(--navy-70)', marginBottom: 'var(--space-lg)' }}>
              {selectedNode.description}
            </p>

            <div className="mono" style={{ background: 'var(--ice)', padding: 'var(--space-md)', borderRadius: '6px', border: '1px solid var(--navy-40)' }}>
              <strong>Execution Contract:</strong>
              <br />
              • Entry: Event correlated &amp; deduped
              <br />
              • Timeout: 30s max per node
              <br />
              • Checkpointer: PostgresSaver (thread_id persistence)
            </div>
          </div>

          <div className="hard-card">
            <h3 className="h3" style={{ marginBottom: 'var(--space-md)' }}>
              State Inputs &amp; Outputs
            </h3>

            <div style={{ marginBottom: 'var(--space-md)' }}>
              <span className="mono" style={{ color: 'var(--navy-40)' }}>Inputs (TypedDict State):</span>
              <ul className="mono-list">
                {selectedNode.inputs.map((inp) => (
                  <li key={inp} className="mono">
                    <span style={{ color: 'var(--k8s-blue)' }}>←</span> {inp}
                  </li>
                ))}
              </ul>
            </div>

            <div>
              <span className="mono" style={{ color: 'var(--navy-40)' }}>Outputs (State Mutation):</span>
              <ul className="mono-list">
                {selectedNode.outputs.map((out) => (
                  <li key={out} className="mono">
                    <span style={{ color: 'var(--signal-green)' }}>→</span> {out}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </div>

      <style jsx>{`
        .pipeline-header {
          margin-bottom: var(--space-xl);
        }
        .graph-canvas {
          padding: var(--space-xl) var(--space-lg);
          overflow-x: auto;
        }
        .graph-flow {
          display: flex;
          align-items: center;
          justify-content: space-between;
          min-width: 900px;
        }
        .graph-step {
          display: flex;
          align-items: center;
          gap: var(--space-sm);
        }
        .node-pill {
          display: flex;
          flex-direction: column;
          align-items: center;
          padding: 12px 18px;
          border: var(--border);
          border-radius: var(--radius);
          background: var(--white);
          cursor: pointer;
          transition: all 150ms;
          box-shadow: 3px 3px 0 var(--navy);
        }
        .node-pill:hover {
          transform: translate(-1px, -1px);
          box-shadow: 4px 4px 0 var(--navy);
        }
        .node-pill--active {
          background: var(--k8s-blue);
          color: var(--white);
          box-shadow: 3px 3px 0 var(--navy);
        }
        .node-step-num {
          font-size: 11px;
          opacity: 0.7;
        }
        .node-title {
          font-weight: 600;
          font-size: 14px;
        }
        .flow-arrow {
          color: var(--navy-40);
          font-size: 14px;
        }
        .mono-list {
          list-style: none;
          margin-top: var(--space-xs);
        }
        .mono-list li {
          padding: 4px 0;
          font-size: 13px;
        }
      `}</style>
    </div>
  );
}
