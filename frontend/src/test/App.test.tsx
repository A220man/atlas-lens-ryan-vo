import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { App } from '../App';

describe('App Component', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn().mockImplementation((url: string) => {
      if (url.includes('/api/auth/demo-login')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            access_token: 'test-token',
            role: 'operator',
            user_id: 'op-1',
            email: 'operator@atlas-lens.local',
          }),
        });
      }
      if (url.includes('/api/auth/me')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            id: 'op-1',
            email: 'operator@atlas-lens.local',
            role: 'operator',
            is_demo: true,
          }),
        });
      }
      if (url.includes('/api/chats')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve([]),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({}),
      });
    }));
  });

  it('renders the brand title and navigation links', async () => {
    render(<App />);
    expect(screen.getByText('Atlas Lens')).toBeInTheDocument();
    expect(screen.getByText('AI & ML Observability Workbench')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Chat DAG Visualizer' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Prompt Hygiene/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'MCP User Headers' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Evaluation Benchmark' })).toBeInTheDocument();
  });

  it('switches views when clicking tabs', async () => {
    render(<App />);
    const hygieneBtn = screen.getByRole('button', { name: /Prompt Hygiene/i });
    fireEvent.click(hygieneBtn);
    expect(screen.getByText(/Mitigates pathological <think> tag imitation/)).toBeInTheDocument();

    const mcpBtn = screen.getByRole('button', { name: 'MCP User Headers' });
    fireEvent.click(mcpBtn);
    expect(screen.getByText(/Attach personal authentication credentials/)).toBeInTheDocument();
  });
});
