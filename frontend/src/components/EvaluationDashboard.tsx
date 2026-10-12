import React, { useState, useEffect } from 'react';
import { api } from '../api';
import { EvaluationMetricSummary } from '../types';

export const EvaluationDashboard: React.FC = () => {
  const [latestSummary, setLatestSummary] = useState<EvaluationMetricSummary | null>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [sampleCount, setSampleCount] = useState<number>(20);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const fetchHistory = async () => {
    try {
      const runs = await api.listEvaluations();
      setHistory(runs);
      if (runs.length > 0 && !latestSummary) {
        setLatestSummary(runs[0].results);
      }
    } catch (err: any) {
      console.warn('Could not load history:', err);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  const handleRunEvaluation = async () => {
    setIsRunning(true);
    setStatusMessage(null);
    try {
      const summary = await api.runEvaluation(sampleCount);
      setLatestSummary(summary);
      setStatusMessage(`Evaluation run completed successfully (${summary.sample_count} samples).`);
      await fetchHistory();
    } catch (err: any) {
      setStatusMessage(`Evaluation run error: ${err.message}`);
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="section-container">
      <div className="section-header">
        <div>
          <h2>AI/ML Evaluation Suite &amp; Empirical Baselines</h2>
          <p className="section-desc">
            Reproducible benchmark quantifying reasoning tag contamination suppression, context token reduction, and Chat DAG structural healing.
          </p>
        </div>
        <div className="action-buttons">
          <div className="sample-selector">
            <label htmlFor="sample-count">Samples:</label>
            <input
              id="sample-count"
              type="number"
              min="5"
              max="50"
              value={sampleCount}
              onChange={(e) => setSampleCount(Number(e.target.value))}
              className="input-field input-narrow"
            />
          </div>
          <button className="btn btn-primary" onClick={handleRunEvaluation} disabled={isRunning}>
            {isRunning ? 'Running Benchmark...' : 'Run Empirical Evaluation'}
          </button>
        </div>
      </div>

      {statusMessage && <div className="status-banner">{statusMessage}</div>}

      {/* Metric Cards */}
      {latestSummary ? (
        <div>
          <div className="metric-cards-grid">
            <div className="metric-card card-accent">
              <span className="metric-title">Mean Token Reduction</span>
              <span className="metric-val text-green">{latestSummary.mean_token_savings_pct}%</span>
              <span className="metric-sub">Context bloat eliminated</span>
            </div>

            <div className="metric-card">
              <span className="metric-title">Tag Imitation Suppression</span>
              <span className="metric-val text-green">{latestSummary.imitation_suppression_pct}%</span>
              <span className="metric-sub">Zero leakage into downstream turns</span>
            </div>

            <div className="metric-card">
              <span className="metric-title">DAG Structural Healing</span>
              <span className="metric-val text-green">{latestSummary.dag_healing_success_pct}%</span>
              <span className="metric-sub">Cycles severed &amp; orphans linked</span>
            </div>

            <div className="metric-card">
              <span className="metric-title">Validation Latency</span>
              <span className="metric-val">{latestSummary.mean_repair_latency_ms} ms</span>
              <span className="metric-sub">Sub-millisecond offline throughput</span>
            </div>
          </div>

          {/* Observations and Provenance */}
          <div className="card mt-4">
            <h3>Benchmark Methodology &amp; Data Provenance</h3>
            <p className="subtext">
              Dataset: <code>{latestSummary.dataset_name}</code> | Run ID: <code>{latestSummary.run_id}</code> | Timestamp: {new Date(latestSummary.timestamp).toLocaleString()}
            </p>

            <ul className="observations-list mt-3">
              {latestSummary.observations.map((obs, idx) => (
                <li key={idx} className="observation-item">
                  <span className="bullet-icon">&#10003;</span>
                  <span>{obs}</span>
                </li>
              ))}
            </ul>

            <div className="eval-callout mt-4">
              <h4>Reproducibility Notice</h4>
              <p>
                This benchmark operates deterministically without external LLM API dependencies. It runs directly via:
              </p>
              <pre className="code-block">
                pytest backend/tests/test_api_workflows.py -k test_evaluation_benchmark_workflow
              </pre>
            </div>
          </div>

          {/* Past Runs Table */}
          <div className="card mt-4">
            <h3>Historical Benchmark Runs ({history.length})</h3>
            <table className="nodes-table">
              <thead>
                <tr>
                  <th>Run ID</th>
                  <th>Dataset</th>
                  <th>Samples</th>
                  <th>Token Savings</th>
                  <th>Imitation Suppressed</th>
                  <th>Healing Rate</th>
                  <th>Recorded At</th>
                </tr>
              </thead>
              <tbody>
                {history.map((h) => (
                  <tr key={h.id}>
                    <td className="code-font">{h.id.slice(0, 8)}...</td>
                    <td>{h.name}</td>
                    <td>{h.sample_count}</td>
                    <td className="text-green">{h.results.mean_token_savings_pct}%</td>
                    <td>{h.results.imitation_suppression_pct}%</td>
                    <td>{h.results.dag_healing_success_pct}%</td>
                    <td>{new Date(h.created_at).toLocaleTimeString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="card empty-state-large">
          <p>Click 'Run Empirical Evaluation' to execute the benchmark suite and generate metrics.</p>
        </div>
      )}
    </div>
  );
};
