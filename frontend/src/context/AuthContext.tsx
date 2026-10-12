import React, { createContext, useContext, useState, useEffect } from 'react';
import { RoleType, User } from '../types';
import { api } from '../api';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  loginDemo: (role: RoleType) => Promise<void>;
  logout: () => Promise<void>;
  error: string | null;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Auto-login to demo operator mode initially in local dev
    const initAuth = async () => {
      try {
        const resp = await api.demoLogin('operator', 'operator@atlas-lens.local');
        setToken(resp.access_token);
        api.setToken(resp.access_token);
        const me = await api.getMe();
        setUser(me);
      } catch (err: any) {
        // Not in demo mode or server starting up
        console.warn('Auto-login demo skipped:', err.message);
      } finally {
        setIsLoading(false);
      }
    };
    initAuth();
  }, []);

  const loginDemo = async (role: RoleType) => {
    setIsLoading(true);
    setError(null);
    try {
      const resp = await api.demoLogin(role, `${role}@atlas-lens.local`);
      setToken(resp.access_token);
      api.setToken(resp.access_token);
      const me = await api.getMe();
      setUser(me);
    } catch (err: any) {
      setError(err.message || 'Login failed');
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    try {
      if (token) {
        await api.logout();
      }
    } catch (err) {
      console.warn('Logout notification error:', err);
    } finally {
      setToken(null);
      setUser(null);
      api.setToken(null);
    }
  };

  return (
    <AuthContext.Provider value={{ user, token, isLoading, loginDemo, logout, error }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
