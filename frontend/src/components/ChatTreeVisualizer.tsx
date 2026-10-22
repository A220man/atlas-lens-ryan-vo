import React, { useState, useEffect } from 'react';
import { api } from '../api';
import { ChatDetailResponse, ChatRecord } from '../types';

export const ChatTreeVisualizer: React.FC = () => {
  const [chats, setChats] = useState<ChatRecord[]>([]);
  const [selectedChat, setSelectedChat] = useState<ChatDetailResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [importJsonText, setImportJsonText] = useState<string>('');
  const [showImportModal, setShowImportModal] = useState<boolean>(false);

  const fetchChats = async () => {
    try {
      const data = await api.listChats();
      setChats(data);
      if (data.length > 0 && !selectedChat) {
        loadChatDetail(data[0].id);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      setStatusMessage(`Error loading chats: ${msg}`);
    } finally {
      setIsLoading(false);
    }
  };

  const loadChatDetail = async (id: string) => {
    try {
      const detail = await api.getChat(id);
      setSelectedChat(detail);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      setStatusMessage(`Error loading chat detail: ${msg}`);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchChats();
  }, []);

  const handleImportSample = async () => {
    setIsLoading(true);
    try {
      const sample = {
        id: 'sample-corrupted-001',
        title: 'Corrupted Tree Sample',
        history: {
          messages: {
            'msg-root': { id: 'msg-root', parentId: null, childrenIds: ['msg-reply-1'], role: 'user', content: 'Explain validation pattern.', timestamp: 1750304000 },
            'msg-reply-1': { id: 'msg-reply-1', parentId: 'msg-root', childrenIds: [], role: 'assistant', content: 'xxxUser wants validation pattern.xxxEncapsulate rules.', timestamp: 1750304050 },
            'msg-orphan': { id: 'msg-orphan', parentId: null, childrenIds: [], role: 'assistant', content: 'Orphan message.', timestamp: 1750304100 },
          },
          currentId: 'msg-orphan',
        },
        messages: [{ id: 'msg-root', parentId: null, childrenIds: ['msg-reply-1'], role: 'user', content: 'Explain validation pattern.', timestamp: 1750304000 }],
      };
      const res = await api.importChat(sample, true);
      setStatusMessage(`Imported and healed chat: ${res.title}`);
      await fetchChats();
      await loadChatDetail(res.id);
      setShowImportModal(false);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      setStatusMessage(`Import failed: ${msg}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCustomImport = async () => {
    if (!importJsonText.trim()) return;
    setIsLoading(true);
    try {
      const parsed = JSON.parse(importJsonText);
      const res = await api.importChat(parsed, true);
      setStatusMessage(`Imported chat successfully (Repaired: ${res.is_repaired})`);
      setImportJsonText('');
      setShowImportModal(false);
      await fetchChats();
      await loadChatDetail(res.id);
    } catch (err: any) {
      setStatusMessage(`Parse or import error: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRepairChat = async () => {
    if (!selectedChat) return;
    setIsLoading(true);
    try {
      await api.repairChat(selectedChat.id);
      setStatusMessage(`Chat '${selectedChat.title}' repaired successfully.`);
      await fetchChats();
      await loadChatDetail(selectedChat.id);
    } catch (err: any) {
      setStatusMessage(`Repair error: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const report = selectedChat?.validation_report;

  return (
    <div className="section-container">
      <div className="section-header">
        <div>
          <h2>Conversational Tree &amp; DAG Integrity Inspector</h2>
          <p className="section-desc">
            Detects orphan message nodes, missing parent links, and cyclic deadlocks (resolving Issue #15189).
          </p>
        </div>
        <div className="action-buttons">
          <button className="btn btn-secondary" onClick={() => setShowImportModal(true)}>
            Import Chat JSON
          </button>
          <button className="btn btn-primary" onClick={handleImportSample}>
            Load Malformed Sample
          </button>
        </div>
      </div>

      {statusMessage && <div className="status-banner">{statusMessage}</div>}

      <div className="two-column-layout">
        <div className="card chat-sidebar">
          <h3>Saved Sessions ({chats.length})</h3>
          {isLoading && chats.length === 0 && <p className="loading-text">Loading sessions...</p>}
          <ul className="chat-list">
            {chats.map((c) => (
              <li
                key={c.id}
                className={`chat-item ${selectedChat?.id === c.id ? 'selected' : ''}`}
                onClick={() => loadChatDetail(c.id)}
              >
                <div className="chat-item-header">
                  <span className="chat-item-title">{c.title}</span>
                  <span
                    className={`badge ${c.validation_summary.is_valid ? 'badge-success' : 'badge-warning'}`}
                  >
                    {c.validation_summary.is_valid ? 'Valid DAG' : 'Corrupt'}
                  </span>
                </div>
                <div className="chat-item-meta">
                  <span>{c.total_messages} msgs</span>
                  {c.is_repaired && <span className="badge badge-info">Auto-Healed</span>}
                  <span>{new Date(c.updated_at).toLocaleTimeString()}</span>
                </div>
              </li>
            ))}
            {chats.length === 0 && !isLoading && (
              <li className="empty-state">No chat records found. Click 'Load Malformed Sample' to test.</li>
            )}
          </ul>
        </div>

        <div className="card chat-main">
          {selectedChat ? (
            <div>
              <div className="chat-main-header">
                <div>
                  <h3>{selectedChat.title}</h3>
                  <span className="id-subtext">ID: {selectedChat.id}</span>
                </div>
                <div className="main-actions">
                  {report && !report.is_valid && (
                    <button className="btn btn-warning" onClick={handleRepairChat}>
                      Repair Structural Links
                    </button>
                  )}
                  {report && report.is_valid && (
                    <span className="badge badge-success">Acyclic &amp; Continuous</span>
                  )}
                </div>
              </div>

              {/* Diagnostic Box */}
              {report && (
                <div className={`diagnostics-box ${report.is_valid ? 'diag-healthy' : 'diag-alert'}`}>
                  <h4>DAG Diagnostic Health Report</h4>
                  <div className="diag-grid">
                    <div>
                      <strong>Cycles Detected:</strong> {report.cycles_detected ? 'Yes (Deadlock Risk)' : 'No'}
                    </div>
                    <div>
                      <strong>Orphan Messages:</strong> {report.orphan_messages.length}
                    </div>
                    <div>
                      <strong>Desynchronized Items:</strong> {report.out_of_sync_count}
                    </div>
                    <div>
                      <strong>Total Graph Nodes:</strong> {report.total_messages}
                    </div>
                  </div>
                  {report.details.length > 0 && (
                    <ul className="diag-details">
                      {report.details.map((d, i) => (
                        <li key={i}>{d}</li>
                      ))}
                    </ul>
                  )}
                </div>
              )}

              {/* Message Tree Trajectory */}
              <div className="trajectory-section">
                <h4>Linearized Trajectory ({selectedChat.linearized_trajectory.length} active turns)</h4>
                <div className="message-stream">
                  {selectedChat.linearized_trajectory.map((msg) => (
                    <div key={msg.id} className={`message-bubble role-${msg.role}`}>
                      <div className="message-meta">
                        <span className="role-tag">{msg.role.toUpperCase()}</span>
                        <span className="msg-id">ID: {msg.id}</span>
                        {msg.parentId && <span className="parent-tag">Parent: {msg.parentId}</span>}
                      </div>
                      <div className="message-content">{msg.content}</div>
                    </div>
                  ))}
                  {selectedChat.linearized_trajectory.length === 0 && (
                    <p className="empty-state">No messages in linearized trajectory.</p>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="empty-state-large">
              <p>Select a chat session or import new conversational data to inspect the tree.</p>
            </div>
          )}
        </div>
      </div>

      {/* Import Modal */}
      {showImportModal && (
        <div className="modal-backdrop">
          <div className="modal-card">
            <h3>Import Conversational JSON</h3>
            <p>Paste raw JSON payload containing `history.messages` or `messages` list.</p>
            <textarea
              className="json-input-area"
              rows={10}
              placeholder="Paste JSON structure here..."
              value={importJsonText}
              onChange={(e) => setImportJsonText(e.target.value)}
            />
            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={() => setShowImportModal(false)}>
                Cancel
              </button>
              <button className="btn btn-primary" onClick={handleCustomImport}>
                Import &amp; Validate
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
