/**
 * PromptBlock component tests.
 *
 * Tests for collapsible AI prompt blocks with copy functionality.
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { PromptBlock } from '../prompt-block';
import type { ContextPrompt } from '@/stores/ai/AIContextStore';

// Mock copy-context module
vi.mock('@/lib/copy-context', () => ({
  copyToClipboard: vi.fn().mockResolvedValue(true),
}));

import { copyToClipboard } from '@/lib/copy-context';

describe('PromptBlock', () => {
  const mockPrompt: ContextPrompt = {
    taskId: 1,
    title: 'Implement backend API for AI context aggregation',
    content: `Create a new FastAPI endpoint at /api/v1/ai/context/{issue_id} that:
- Aggregates related issues using semantic search
- Fetches relevant documentation from notes
- Generates implementation tasks using AI
- Returns structured JSON response`,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders collapsed by default (title visible, content NOT visible)', () => {
    render(<PromptBlock prompt={mockPrompt} />);

    expect(
      screen.getByText('Implement backend API for AI context aggregation')
    ).toBeInTheDocument();

    expect(screen.queryByText(/Create a new FastAPI endpoint/)).not.toBeInTheDocument();
  });

  it('expands on click (content becomes visible)', () => {
    render(<PromptBlock prompt={mockPrompt} />);

    const toggleButton = screen.getByRole('button', {
      name: /Implement backend API/,
    });
    fireEvent.click(toggleButton);

    expect(screen.getByText(/Create a new FastAPI endpoint/)).toBeInTheDocument();
  });

  it('starts expanded when defaultExpanded=true', () => {
    render(<PromptBlock prompt={mockPrompt} defaultExpanded={true} />);

    expect(
      screen.getByText('Implement backend API for AI context aggregation')
    ).toBeInTheDocument();
    expect(screen.getByText(/Create a new FastAPI endpoint/)).toBeInTheDocument();
  });

  it('copy button copies content and shows "Copied!" feedback', async () => {
    render(<PromptBlock prompt={mockPrompt} />);

    const copyButton = screen.getByRole('button', {
      name: /copy prompt to clipboard/i,
    });
    fireEvent.click(copyButton);

    await waitFor(() => {
      expect(copyToClipboard).toHaveBeenCalledWith(mockPrompt.content);
    });

    expect(screen.getByText('Copied!')).toBeInTheDocument();

    await waitFor(
      () => {
        expect(screen.queryByText('Copied!')).not.toBeInTheDocument();
      },
      { timeout: 3000 }
    );
  });

  it('has aria-expanded attribute', () => {
    render(<PromptBlock prompt={mockPrompt} />);

    const toggleButton = screen.getByRole('button', {
      name: /Implement backend API/,
    });

    expect(toggleButton).toHaveAttribute('aria-expanded', 'false');

    fireEvent.click(toggleButton);

    expect(toggleButton).toHaveAttribute('aria-expanded', 'true');
  });
});
