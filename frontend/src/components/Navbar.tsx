import React from 'react';
import { useAuth } from '../context/AuthContext';
import { RoleType } from '../types';

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({ activeTab, setActiveTab }) => {
  const { user, loginDemo, logout } = useAuth();

  const handleRoleChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    await loginDemo(e.target.value as RoleType);
  };

  return (
    <header className="navbar">
      <div className="navbar-brand">
        <div className="logo-badge">AL</div>
        <div>
          <h1 className="brand-title">Atlas Lens</h1>
          <span className="brand-subtitle">AI & ML Observability Workbench</span>
        </div>
      </div>

      <nav className="navbar-links">
        <button
          className={`nav-btn ${activeTab === 'dags' ? 'active' : ''}`}
          onClick={() => setActiveTab('dags')}
        >
          Chat DAG Visualizer
        </button>
        <button
          className={`nav-btn ${activeTab === 'hygiene' ? 'active' : ''}`}
          onClick={() => setActiveTab('hygiene')}
        >
          Prompt Hygiene &amp; &lt;think&gt;
        </button>
        <button
          className={`nav-btn ${activeTab === 'mcp' ? 'active' : ''}`}
          onClick={() => setActiveTab('mcp')}
        >
          MCP User Headers
        </button>
        <button
          className={`nav-btn ${activeTab === 'eval' ? 'active' : ''}`}
          onClick={() => setActiveTab('eval')}
        >
          Evaluation Benchmark
        </button>
        <button
          className={`nav-btn ${activeTab === 'audit' ? 'active' : ''}`}
          onClick={() => setActiveTab('audit')}
        >
          Audit Trail
        </button>
      </nav>

      <div className="navbar-user">
        {user ? (
          <div className="user-profile">
            <span className="user-email">{user.email}</span>
            <span className={`role-badge role-${user.role}`}>{user.role.toUpperCase()}</span>
            <div className="role-switcher">
              <label htmlFor="role-select">Role:</label>
              <select
                id="role-select"
                value={user.role}
                onChange={handleRoleChange}
                className="role-dropdown"
              >
                <option value="viewer">Viewer</option>
                <option value="operator">Operator</option>
                <option value="admin">Admin</option>
              </select>
            </div>
            <button onClick={logout} className="logout-btn">
              Logout
            </button>
          </div>
        ) : (
          <button onClick={() => loginDemo('operator')} className="login-btn">
            Demo Login
          </button>
        )}
      </div>
    </header>
  );
};
