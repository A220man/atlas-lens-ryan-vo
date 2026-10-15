import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
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
      if (url.includes('/api/mcp/servers')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve([]),
        });
      }
      if (url.includes('/api/hygiene/inspect')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            model_id: 'deepseek-r1-qwen-7b',
            reinject_reasoning: false,
            original_estimated_tokens: 150,
            sanitized_estimated_tokens: 75,
            token_savings_pct: 50.0,
            contains_think_tags: true,
            imitation_risk_score: 0.1,
            sanitized_messages: [
              { role: 'user', content: 'How do I prevent SQL injection?', stripped_reasoning: null },
              { role: 'assistant', content: 'Use parameterized queries.', stripped_reasoning: 'Need to explain parameterization' },
            ],
          }),
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
    // Wait for initial auth and child component fetches to settle
    await waitFor(() => {
      expect(screen.getByText('Atlas Lens')).toBeInTheDocument();
    });
    expect(screen.getByText('AI & ML Observability Workbench')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Chat DAG Visualizer' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Prompt Hygiene/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'MCP User Headers' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Evaluation Benchmark' })).toBeInTheDocument();
  });

  it('switches views when clicking tabs', async () => {
    render(<App />);
    // Wait for initial auth and child component fetches to settle
    await waitFor(() => {
      expect(screen.getByText('Atlas Lens')).toBeInTheDocument();
    });
    const hygieneBtn = screen.getByRole('button', { name: /Prompt Hygiene/i });
    fireEvent.click(hygieneBtn);
    await waitFor(() => {
      expect(screen.getByText(/Mitigates pathological.*tag imitation/i)).toBeInTheDocument();
    });

    const mcpBtn = screen.getByRole('button', { name: 'MCP User Headers' });
    fireEvent.click(mcpBtn);
    await waitFor(() => {
      expect(screen.getByText(/Attach personal authentication credentials/i)).toBeInTheDocument();
    });
  });
});