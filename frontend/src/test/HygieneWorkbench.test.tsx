import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { HygieneWorkbench } from '../components/HygieneWorkbench';

describe('HygieneWorkbench Component', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn().mockImplementation((url: string) => {
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
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
    }));
  });

  it('renders reinject toggle with default OFF', async () => {
    render(<HygieneWorkbench />);
    // Wait for initial analysis to complete to avoid act() warnings
    await waitFor(() => {
      const toggle = screen.getByRole('checkbox', { name: /Reinject Reasoning/i });
      expect(toggle).not.toBeChecked();
    });
  });

  it('displays calculated token savings and metrics after analysis', async () => {
    render(<HygieneWorkbench />);
    await waitFor(() => {
      expect(screen.getByText('50%')).toBeInTheDocument();
      expect(screen.getByText('150')).toBeInTheDocument();
      expect(screen.getByText('75')).toBeInTheDocument();
    });
  });

  it('toggles reinject reasoning state', async () => {
    render(<HygieneWorkbench />);
    // Wait for initial analysis to complete
    await waitFor(() => {
      const toggle = screen.getByRole('checkbox', { name: /Reinject Reasoning/i });
      expect(toggle).not.toBeChecked();
    });
    const toggle = screen.getByRole('checkbox', { name: /Reinject Reasoning/i });
    fireEvent.click(toggle);
    // Wait for state update and re-analysis to complete
    await waitFor(() => {
      expect(toggle).toBeChecked();
    });
  });
});