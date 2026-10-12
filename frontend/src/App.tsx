import React, { useState } from 'react';
import { AuthProvider } from './context/AuthContext';
import { Navbar } from './components/Navbar';
import { ChatTreeVisualizer } from './components/ChatTreeVisualizer';
import { HygieneWorkbench } from './components/HygieneWorkbench';
import { McpHeaderManager } from './components/McpHeaderManager';
import { EvaluationDashboard } from './components/EvaluationDashboard';
import { AuditLogView } from './components/AuditLogView';

export const MainContent: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>('dags');

  return (
    <div className="app-container">
      <Navbar activeTab={activeTab} setActiveTab={setActiveTab} />
      <main className="main-content">
        {activeTab === 'dags' && <ChatTreeVisualizer />}
        {activeTab === 'hygiene' && <HygieneWorkbench />}
        {activeTab === 'mcp' && <McpHeaderManager />}
        {activeTab === 'eval' && <EvaluationDashboard />}
        {activeTab === 'audit' && <AuditLogView />}
      </main>
      <footer className="footer">
        <div className="footer-content">
          <span>Atlas Lens &mdash; Observability and Prompt Hygiene Workbench</span>
          <span className="footer-author">
            Author: Ryan Vo &bull; <a href="mailto:ryandtvo@gmail.com">ryandtvo@gmail.com</a>
          </span>
        </div>
      </footer>
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <MainContent />
    </AuthProvider>
  );
};

export default App;
