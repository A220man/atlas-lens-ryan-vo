import React, { useState, useEffect } from 'react';
import { api } from '../api';
import { AuditLogEntry } from '../types';
import { useAuth } from '../context/AuthContext';

export const AuditLogView: React.FC = () => {
  const { user } = useAuth();
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchLogs = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.getAuditLogs(50);
      setLogs(data);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch audit logs');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (user?.role === 'admin') {
      fetchLogs();
    }
  }, [user]);

  if (user?.role !== 'admin') {
    return (
      <div className="section-container">
        <div className="card empty-state-large">
          <h3>Admin Role Required</h3>
          <p>
            Audit trail inspection requires administrative privileges. Use the role switcher in the top right to switch to <strong>Admin</strong>.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="section-container">
      <div className="section-header">
        <div>
          <h2>System Audit Trail &amp; Compliance Log</h2>
          <p className="section-desc">
            Immutable log recording transactional state changes, repairs, and tool executions with credential redaction.
          </p>
        </div>
        <div className="action-buttons">
          <button className="btn btn-secondary" onClick={fetchLogs} disabled={isLoading}>
            {isLoading ? 'Refreshing...' : 'Refresh Logs'}
          </button>
        </div>
      </div>

      {error && <div className="status-banner banner-error">{error}</div>}

      <div className="card">
        <h3>Audit Records ({logs.length})</h3>
        <table className="nodes-table mt-3">
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>User ID</th>
              <th>Action</th>
              <th>Resource</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((log) => (
              <tr key={log.id}>
                <td className="code-font">{new Date(log.timestamp).toLocaleTimeString()}</td>
                <td>{log.user_id}</td>
                <td>
                  <span className="badge badge-info">{log.action}</span>
                </td>
                <td className="code-font">{log.resource_type}:{log.resource_id}</td>
                <td className="code-font truncate-cell">{JSON.stringify(log.details)}</td>
              </tr>
            ))}
            {logs.length === 0 && !isLoading && (
              <tr>
                <td colSpan={5} className="empty-state">No audit logs found.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
