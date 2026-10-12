import React, { useState, useEffect } from 'react';
import { api } from '../api';
import { McpServerResponse, McpToolExecuteResponse, UserMcpHeaderResponse } from '../types';

export const McpHeaderManager: React.FC = () => {
  const [servers, setServers] = useState<McpServerResponse[]>([]);
  const [selectedServerId, setSelectedServerId] = useState<string>('');
  const [userHeaders, setUserHeaders] = useState<UserMcpHeaderResponse[]>([]);
  const [headerKey, setHeaderKey] = useState<string>('Authorization');
  const [headerVal, setHeaderVal] = useState<string>('');
  const [newServerName, setNewServerName] = useState<string>('github-mcp-server');
  const [newServerUrl, setNewServerUrl] = useState<string>('http://127.0.0.1:8080/mcp');
  const [executionResult, setExecutionResult] = useState<McpToolExecuteResponse | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const fetchServers = async () => {
    try {
      let list = await api.listMcpServers();
      if (list.length === 0) {
        // Register default sample MCP server
        const created = await api.registerMcpServer(
          'internal-code-search',
          'http://127.0.0.1:9090/tools',
          'Enterprise code search MCP gateway'
        );
        list = [created];
      }
      setServers(list);
      if (list.length > 0 && !selectedServerId) {
        setSelectedServerId(list[0].id);
      }
    } catch (err: any) {
      setStatusMessage(`Error fetching MCP servers: ${err.message}`);
    }
  };

  const fetchUserHeaders = async (srvId: string) => {
    if (!srvId) return;
    try {
      const headers = await api.getUserMcpHeaders(srvId);
      setUserHeaders(headers);
    } catch (err: any) {
      setStatusMessage(`Error fetching headers: ${err.message}`);
    }
  };

  useEffect(() => {
    fetchServers();
  }, []);

  useEffect(() => {
    if (selectedServerId) {
      fetchUserHeaders(selectedServerId);
    }
  }, [selectedServerId]);

  const handleSaveHeader = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedServerId || !headerKey || !headerVal) return;
    setIsLoading(true);
    try {
      await api.setUserMcpHeader(selectedServerId, headerKey, headerVal);
      setStatusMessage(`Header '${headerKey}' stored securely for your user profile.`);
      setHeaderVal('');
      await fetchUserHeaders(selectedServerId);
    } catch (err: any) {
      setStatusMessage(`Failed to set header: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRegisterServer = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newServerName || !newServerUrl) return;
    setIsLoading(true);
    try {
      const srv = await api.registerMcpServer(newServerName, newServerUrl);
      setStatusMessage(`MCP Server '${srv.name}' registered globally.`);
      await fetchServers();
      setSelectedServerId(srv.id);
    } catch (err: any) {
      setStatusMessage(`Server registration error: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleTestDispatch = async () => {
    if (!selectedServerId) return;
    setIsLoading(true);
    setExecutionResult(null);
    try {
      const res = await api.executeMcpTool(selectedServerId, 'query_codebase', {
        query: 'ChatDagEngine',
      });
      setExecutionResult(res);
      setStatusMessage(`Tool dispatch completed in ${res.execution_time_ms} ms`);
    } catch (err: any) {
      setStatusMessage(`Tool execution error: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="section-container">
      <div className="section-header">
        <div>
          <h2>User-Scoped MCP Headers &amp; Tool Proxy</h2>
          <p className="section-desc">
            Attach personal authentication credentials to global MCP servers without tenant leaks (resolving Issue #19313).
          </p>
        </div>
      </div>

      {statusMessage && <div className="status-banner">{statusMessage}</div>}

      <div className="two-column-layout">
        {/* Left: Server List & Registration */}
        <div className="card">
          <h3>Configured MCP Servers ({servers.length})</h3>
          <div className="server-select-box">
            <label htmlFor="server-select">Active Server:</label>
            <select
              id="server-select"
              className="input-field"
              value={selectedServerId}
              onChange={(e) => setSelectedServerId(e.target.value)}
            >
              {servers.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.url})
                </option>
              ))}
            </select>
          </div>

          <h4 className="mt-4">Register New MCP Server</h4>
          <form onSubmit={handleRegisterServer} className="form-stack">
            <div>
              <label>Server Name:</label>
              <input
                type="text"
                className="input-field"
                value={newServerName}
                onChange={(e) => setNewServerName(e.target.value)}
                required
              />
            </div>
            <div>
              <label>Endpoint URL:</label>
              <input
                type="text"
                className="input-field"
                value={newServerUrl}
                onChange={(e) => setNewServerUrl(e.target.value)}
                required
              />
            </div>
            <button type="submit" className="btn btn-secondary" disabled={isLoading}>
              Add MCP Server
            </button>
          </form>
        </div>

        {/* Right: Personal Scoped Headers & Test Execution */}
        <div className="card">
          <h3>Your Scoped Credentials &amp; Headers</h3>
          <p className="subtext">
            Headers entered here are isolated strictly to your user session and injected dynamically by the proxy.
          </p>

          <form onSubmit={handleSaveHeader} className="form-stack">
            <div className="form-row">
              <div className="flex-1">
                <label>Header Key:</label>
                <input
                  type="text"
                  className="input-field"
                  value={headerKey}
                  placeholder="e.g. Authorization or X-User-Token"
                  onChange={(e) => setHeaderKey(e.target.value)}
                  required
                />
              </div>
              <div className="flex-2">
                <label>Header Value (Masked in Logs):</label>
                <input
                  type="password"
                  className="input-field"
                  value={headerVal}
                  placeholder="Secret token or credential"
                  onChange={(e) => setHeaderVal(e.target.value)}
                  required
                />
              </div>
            </div>
            <button type="submit" className="btn btn-primary" disabled={isLoading}>
              Save Scoped Header
            </button>
          </form>

          <div className="saved-headers-table mt-4">
            <h4>Active Personal Headers for Selected Server</h4>
            {userHeaders.length > 0 ? (
              <table className="nodes-table">
                <thead>
                  <tr>
                    <th>Header Key</th>
                    <th>Masked Value</th>
                    <th>Configured At</th>
                  </tr>
                </thead>
                <tbody>
                  {userHeaders.map((h) => (
                    <tr key={h.id}>
                      <td className="code-font">{h.header_key}</td>
                      <td className="code-font">{h.header_value_masked}</td>
                      <td>{new Date(h.created_at).toLocaleTimeString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="empty-state">No scoped personal headers configured for this server yet.</p>
            )}
          </div>

          <div className="test-dispatch mt-4">
            <h4>Simulate Tool Dispatch with Injected Headers</h4>
            <button className="btn btn-warning" onClick={handleTestDispatch} disabled={isLoading}>
              Execute Test Tool Call via Proxy
            </button>

            {executionResult && (
              <div className="execution-result-box mt-3">
                <div className="result-meta">
                  <span className="badge badge-success">Status: {executionResult.status}</span>
                  <span>Latency: {executionResult.execution_time_ms} ms</span>
                  <span>Injected: {executionResult.injected_header_keys.join(', ')}</span>
                </div>
                <pre className="result-json">
                  {JSON.stringify(executionResult.result, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
