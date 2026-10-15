import React, { useState, useEffect } from 'react';
import { api } from '../api';
import { PromptHygieneResponse, PromptMessageItem } from '../types';

const INITIAL_PROMPTS: PromptMessageItem[] = [
  {
    role: 'user',
    content: 'How do I prevent SQL injection in Python SQLite?',
  },
  {
    role: 'assistant',
    content:
      '<think>Need to explain parameterized queries using ? placeholders.</think>Use parameterized queries with `?` placeholders:\n\n```python\ncursor.execute("SELECT * FROM users WHERE username = ?", (username,))\n```',
  },
  {
    role: 'user',
    content: 'Show a multiple parameter example.',
  },
  {
    role: 'assistant',
    content:
      '<think>Formulating multi-parameter example.</think>Pass a tuple of arguments:\n\n```python\ncursor.execute("SELECT * FROM items WHERE status = ? AND price <= ?", (status, max_price))\n```',
  },
];

export const HygieneWorkbench: React.FC = () => {
  const [messages] = useState<PromptMessageItem[]>(INITIAL_PROMPTS);
  const [reinjectReasoning, setReinjectReasoning] = useState<boolean>(false);
  const [modelId, setModelId] = useState<string>('deepseek-r1-qwen-7b');
  const [filterTags, setFilterTags] = useState<string>('think,thought');
  const [analysis, setAnalysis] = useState<PromptHygieneResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const runAnalysis = async (toggleVal = reinjectReasoning) => {
    setIsLoading(true);
    setError(null);
    try {
      const parsedTags = filterTags
        .split(',')
        .map(t => t.trim())
        .filter(t => t.length > 0);
      const res = await api.inspectHygiene(messages, toggleVal, modelId, parsedTags);
      setAnalysis(res);
    } catch (err: any) {
      setError(err.message || 'Inspection failed');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    runAnalysis(reinjectReasoning);
  }, [reinjectReasoning, filterTags]);

  const handleToggle = (checked: boolean) => {
    setReinjectReasoning(checked);
  };

  return (
    <div className="section-container">
      <div className="section-header">
        <div>
          <h2>Prompt Hygiene &amp; Reasoning Tag Sanitizer</h2>
          <p className="section-desc">
            Mitigates pathological &lt;think&gt; tag imitation and context window bloat (resolving Issue #23339).
          </p>
        </div>
        <div className="action-buttons">
          <button className="btn btn-primary" onClick={() => runAnalysis(reinjectReasoning)}>
            Re-Analyze Prompt
          </button>
        </div>
      </div>

      {error && <div className="status-banner banner-error">{error}</div>}

      {/* Model Policy Control Bar */}
      <div className="card control-bar">
        <div className="control-group">
          <label htmlFor="model-input">Target Model:</label>
          <input
            id="model-input"
            type="text"
            className="input-field"
            value={modelId}
            onChange={(e) => setModelId(e.target.value)}
          />
        </div>
        <div className="control-group">
          <label htmlFor="filter-tags-input">Custom Filter Tags:</label>
          <input
            id="filter-tags-input"
            type="text"
            className="input-field"
            value={filterTags}
            onChange={(e) => setFilterTags(e.target.value)}
            placeholder="e.g. think, thought, scratchpad"
          />
          <span className="subtext">Comma-separated tag names to extract and strip from assistant outputs.</span>
        </div>

        <div className="control-group toggle-group">
          <label className="toggle-label" htmlFor="reinject-toggle">
            <input
              id="reinject-toggle"
              type="checkbox"
              checked={reinjectReasoning}
              onChange={(e) => handleToggle(e.target.checked)}
            />
            <span className="toggle-text">
              Reinject Reasoning / Thinking into Prompt History
              <span className="toggle-subtext">
                (Default: OFF - Recommended to prevent recursive imitation and frontend parsing failures)
              </span>
            </span>
          </label>
        </div>
      </div>

      {/* Metric Cards */}
      {analysis && (
        <div className="metric-cards-grid">
          <div className="metric-card">
            <span className="metric-title">Original Estimated Tokens</span>
            <span className="metric-val">{analysis.original_estimated_tokens}</span>
            <span className="metric-sub">Raw chain-of-thought included</span>
          </div>

          <div className="metric-card">
            <span className="metric-title">Sanitized Prompt Tokens</span>
            <span className="metric-val">{analysis.sanitized_estimated_tokens}</span>
            <span className="metric-sub">Processed by Atlas Lens</span>
          </div>

          <div className="metric-card card-accent">
            <span className="metric-title">Context Window Savings</span>
            <span className="metric-val text-green">{analysis.token_savings_pct}%</span>
            <span className="metric-sub">Capacity preserved for context</span>
          </div>

          <div className="metric-card">
            <span className="metric-title">Tag Imitation Risk</span>
            <span
              className={`metric-val ${
                analysis.imitation_risk_score > 0.5 ? 'text-red' : 'text-green'
              }`}
            >
              {(analysis.imitation_risk_score * 100).toFixed(0)}%
            </span>
            <span className="metric-sub">
              {analysis.imitation_risk_score > 0.5 ? 'High imitation probability' : 'Low hallucination risk'}
            </span>
          </div>
        </div>
      )}

      {/* Side-by-Side Prompt Comparator */}
      <div className="two-column-layout">
        {/* Left: Raw Prompt History */}
        <div className="card">
          <div className="column-header">
            <h3>Raw Stored Output (Unsanitized)</h3>
            <span className="badge badge-warning">Contains &lt;think&gt; tags</span>
          </div>
          <div className="turns-list">
            {messages.map((m, idx) => (
              <div key={idx} className={`turn-card role-${m.role}`}>
                <div className="turn-meta">
                  <span className="turn-role">{m.role.toUpperCase()}</span>
                </div>
                <pre className="turn-content">{m.content}</pre>
              </div>
            ))}
          </div>
        </div>

        {/* Right: Sanitized Prompt Sent to Next Turn */}
        <div className="card">
          <div className="column-header">
            <h3>Sanitized History for Next Turn</h3>
            <span
              className={`badge ${reinjectReasoning ? 'badge-warning' : 'badge-success'}`}
            >
              {reinjectReasoning ? 'Reinjection Active' : 'Cleaned History'}
            </span>
          </div>
          <div className="turns-list">
            {analysis?.sanitized_messages.map((sm, idx) => (
              <div key={idx} className={`turn-card role-${sm.role}`}>
                <div className="turn-meta">
                  <span className="turn-role">{sm.role.toUpperCase()}</span>
                  {sm.stripped_reasoning && (
                    <span className="badge badge-info">Thinking Trace Isolated</span>
                  )}
                </div>
                <pre className="turn-content">{sm.content}</pre>
                {sm.stripped_reasoning && (
                  <div className="isolated-trace">
                    <strong>Isolated Reasoning Trace:</strong>
                    <p>{sm.stripped_reasoning}</p>
                  </div>
                )}
              </div>
            ))}
            {isLoading && <p className="loading-text">Analyzing prompt transformation...</p>}
          </div>
        </div>
      </div>
    </div>
  );
};
