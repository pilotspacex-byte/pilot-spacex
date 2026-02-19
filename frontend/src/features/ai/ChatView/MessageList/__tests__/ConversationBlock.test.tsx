/**
 * Unit tests for ConversationBlock component.
 * T-064
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConversationBlock } from '../ConversationBlock';

describe('ConversationBlock', () => {
  let onReply: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    onReply = vi.fn().mockResolvedValue(undefined);
  });

  describe('pending state', () => {
    it('renders with correct ARIA role and label', () => {
      render(
        <ConversationBlock
          questionId="q-1"
          question="Should the OAuth integration support PKCE flow?"
          onReply={onReply}
        />
      );
      const article = screen.getByRole('article');
      expect(article).toHaveAttribute('aria-label', 'AI clarification question');
    });

    it('renders the question text', () => {
      render(
        <ConversationBlock
          questionId="q-1"
          question="Should the OAuth integration support PKCE flow?"
          onReply={onReply}
        />
      );
      expect(
        screen.getByText('Should the OAuth integration support PKCE flow?')
      ).toBeInTheDocument();
    });

    it('renders reply input when not answered', () => {
      render(
        <ConversationBlock
          questionId="q-1"
          question="Should the OAuth integration support PKCE flow?"
          onReply={onReply}
        />
      );
      const input = screen.getByRole('textbox', { name: /reply/i });
      expect(input).toBeInTheDocument();
    });

    it('calls onReply with questionId and answer when sent', async () => {
      const user = userEvent.setup();
      render(
        <ConversationBlock
          questionId="q-1"
          question="Should the OAuth integration support PKCE flow?"
          onReply={onReply}
        />
      );

      const input = screen.getByRole('textbox', { name: /reply/i });
      await user.type(input, 'Browser-only for MVP');
      await user.click(screen.getByRole('button', { name: /send/i }));

      await waitFor(() => {
        expect(onReply).toHaveBeenCalledWith('q-1', 'Browser-only for MVP');
      });
    });

    it('sends on Enter key', async () => {
      const user = userEvent.setup();
      render(
        <ConversationBlock
          questionId="q-1"
          question="Should the OAuth integration support PKCE flow?"
          onReply={onReply}
        />
      );

      const input = screen.getByRole('textbox', { name: /reply/i });
      await user.type(input, 'Browser-only{Enter}');

      await waitFor(() => {
        expect(onReply).toHaveBeenCalledWith('q-1', 'Browser-only');
      });
    });

    it('does not send when input is empty', async () => {
      const user = userEvent.setup();
      render(
        <ConversationBlock
          questionId="q-1"
          question="Should the OAuth integration support PKCE flow?"
          onReply={onReply}
        />
      );

      await user.click(screen.getByRole('button', { name: /send/i }));
      expect(onReply).not.toHaveBeenCalled();
    });
  });

  describe('answered state', () => {
    it('hides reply input when answered', () => {
      render(
        <ConversationBlock
          questionId="q-1"
          question="Should the OAuth integration support PKCE flow?"
          onReply={onReply}
          isAnswered
        />
      );
      expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
    });

    it('renders thread entries', () => {
      render(
        <ConversationBlock
          questionId="q-1"
          question="Should the OAuth integration support PKCE flow?"
          onReply={onReply}
          isAnswered
          thread={[
            { role: 'user', content: 'Browser-only for MVP', timestamp: new Date() },
            {
              role: 'ai',
              content: 'Noted. Browser-only added as constraint.',
              timestamp: new Date(),
            },
          ]}
        />
      );
      expect(screen.getByText('Browser-only for MVP')).toBeInTheDocument();
      expect(screen.getByText('Noted. Browser-only added as constraint.')).toBeInTheDocument();
    });

    it('thread has role="list"', () => {
      render(
        <ConversationBlock
          questionId="q-1"
          question="Should the OAuth integration support PKCE flow?"
          onReply={onReply}
          isAnswered
          thread={[{ role: 'user', content: 'Reply', timestamp: new Date() }]}
        />
      );
      expect(screen.getByRole('list')).toBeInTheDocument();
    });
  });

  describe('processing state', () => {
    it('shows processing indicator', () => {
      render(
        <ConversationBlock
          questionId="q-1"
          question="Should the OAuth integration support PKCE flow?"
          onReply={onReply}
          isProcessing
        />
      );
      expect(screen.getByText(/AI is thinking/i)).toBeInTheDocument();
    });
  });
});
