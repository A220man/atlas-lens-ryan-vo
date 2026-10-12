import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ChatTreeVisualizer } from '../components/ChatTreeVisualizer';

describe('ChatTreeVisualizer Component', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn().mockImplementation((url: string) => {
      if (url.includes('/api/chats/import')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            id: 'sample-healed-1',
            title: 'Sample Healed Session',
            total_messages: 2,
            is_repaired: true,
            validation_report: {
              is_valid: true,
              total_messages: 2,
              cycles_detected: false,
              orphan_messages: [],
              missing_children_links: 0,
              out_of_sync_count: 0,
              repaired: true,
              details: [],
            },
          }),
        });
      }
      if (url.match(/\/api\/chats\/[a-zA-Z0-9_-]+/)) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            id: 'sample-healed-1',
            title: 'Sample Healed Session',
            user_id: 'user-1',
            is_repaired: true,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            validation_report: {
              is_valid: true,
              total_messages: 2,
              cycles_detected: false,
              orphan_messages: [],
              missing_children_links: 0,
              out_of_sync_count: 0,
              repaired: true,
              details: [],
            },
            chat_data: {
              history: {
                messages: {
                  'm-1': { id: 'm-1', parentId: null, childrenIds: ['m-2'], role: 'user', content: 'Hi' },
                  'm-2': { id: 'm-2', parentId: 'm-1', childrenIds: [], role: 'assistant', content: 'Hello' },
                },
                currentId: 'm-2',
              },
            },
            linearized_trajectory: [
              { id: 'm-1', parentId: null, childrenIds: ['m-2'], role: 'user', content: 'Hi' },
              { id: 'm-2', parentId: 'm-1', childrenIds: [], role: 'assistant', content: 'Hello' },
            ],
          }),
        });
      }
      if (url.includes('/api/chats')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve([]),
        });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
    }));
  });

  it('renders section title and action buttons', () => {
    render(<ChatTreeVisualizer />);
    expect(screen.getByText(/Conversational Tree & DAG Integrity Inspector/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Load Malformed Sample/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Import Chat JSON/i })).toBeInTheDocument();
  });

  it('opens import modal when clicking Import Chat JSON', () => {
    render(<ChatTreeVisualizer />);
    const importBtn = screen.getByRole('button', { name: /Import Chat JSON/i });
    fireEvent.click(importBtn);
    expect(screen.getByText('Import Conversational JSON')).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Paste JSON structure here/i)).toBeInTheDocument();
  });

  it('triggers sample import and displays status message', async () => {
    render(<ChatTreeVisualizer />);
    const loadSampleBtn = screen.getByRole('button', { name: /Load Malformed Sample/i });
    fireEvent.click(loadSampleBtn);
    await waitFor(() => {
      expect(screen.getByText(/Imported and healed chat/i)).toBeInTheDocument();
    });
  });
});
