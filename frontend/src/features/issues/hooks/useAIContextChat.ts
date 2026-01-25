/**
 * useAIContextChat - Hook for SSE-based chat with AI context refinement.
 *
 * T215: Provides chat messages, streaming state, and conversation management.
 */

import * as React from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import type { ChatMessage, SuggestedQuestion } from '@/components/issues/ContextChat';
import { aiContextKeys } from './useAIContext';

// ============================================================================
// Types
// ============================================================================

interface SSEChunk {
  type: 'text' | 'done' | 'error' | 'context_updated';
  content?: string;
  error?: string;
}

// ============================================================================
// Helper Functions
// ============================================================================

function generateMessageId(): string {
  return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

// Default suggested questions
const DEFAULT_SUGGESTED_QUESTIONS: SuggestedQuestion[] = [
  { id: 'q1', text: 'What files should I modify?', category: 'implementation' },
  { id: 'q2', text: 'Are there any related tests?', category: 'testing' },
  { id: 'q3', text: 'What dependencies does this require?', category: 'architecture' },
  { id: 'q4', text: 'What is the acceptance criteria?', category: 'requirements' },
];

// ============================================================================
// Hook
// ============================================================================

export interface UseAIContextChatOptions {
  /** API base URL */
  apiBaseUrl?: string;
  /** Initial suggested questions */
  initialQuestions?: SuggestedQuestion[];
}

export interface UseAIContextChatReturn {
  /** Chat messages */
  messages: ChatMessage[];
  /** Suggested questions */
  suggestedQuestions: SuggestedQuestion[];
  /** Whether AI is typing/streaming */
  isTyping: boolean;
  /** Send a message */
  sendMessage: (content: string) => void;
  /** Clear conversation */
  clearConversation: () => void;
  /** Error from last request */
  error: Error | null;
}

export function useAIContextChat(
  issueId: string,
  options?: UseAIContextChatOptions
): UseAIContextChatReturn {
  const { apiBaseUrl = '/api/v1', initialQuestions = DEFAULT_SUGGESTED_QUESTIONS } = options ?? {};

  const queryClient = useQueryClient();
  const [messages, setMessages] = React.useState<ChatMessage[]>([]);
  const [suggestedQuestions, setSuggestedQuestions] =
    React.useState<SuggestedQuestion[]>(initialQuestions);
  const [isTyping, setIsTyping] = React.useState(false);
  const [error, setError] = React.useState<Error | null>(null);
  const abortControllerRef = React.useRef<AbortController | null>(null);

  // Clean up on unmount
  React.useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  const sendMessage = React.useCallback(
    async (content: string) => {
      if (!content.trim() || isTyping) return;

      // Abort any existing request
      abortControllerRef.current?.abort();
      abortControllerRef.current = new AbortController();

      // Add user message
      const userMessage: ChatMessage = {
        id: generateMessageId(),
        role: 'user',
        content: content.trim(),
        timestamp: new Date(),
      };

      // Create placeholder for AI message
      const aiMessageId = generateMessageId();
      const aiMessage: ChatMessage = {
        id: aiMessageId,
        role: 'assistant',
        content: '',
        timestamp: new Date(),
        isStreaming: true,
      };

      setMessages((prev) => [...prev, userMessage, aiMessage]);
      setIsTyping(true);
      setError(null);

      // Hide suggested questions after first message
      setSuggestedQuestions([]);

      try {
        const response = await fetch(`${apiBaseUrl}/issues/${issueId}/ai-context/chat`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ query: content }),
          signal: abortControllerRef.current.signal,
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        if (!response.body) {
          throw new Error('No response body');
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let fullContent = '';

        while (true) {
          const { done, value } = await reader.read();

          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          // Process complete SSE events
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6);

              if (data === '[DONE]') {
                continue;
              }

              try {
                const chunk: SSEChunk = JSON.parse(data);

                if (chunk.type === 'text' && chunk.content) {
                  fullContent += chunk.content;

                  // Update message content
                  setMessages((prev) =>
                    prev.map((msg) =>
                      msg.id === aiMessageId ? { ...msg, content: fullContent } : msg
                    )
                  );
                } else if (chunk.type === 'error' && chunk.error) {
                  throw new Error(chunk.error);
                } else if (chunk.type === 'context_updated') {
                  // Invalidate context query to refetch updated context
                  queryClient.invalidateQueries({
                    queryKey: aiContextKeys.detail(issueId),
                  });
                }
              } catch (parseError) {
                // Skip invalid JSON chunks
                console.warn('Failed to parse SSE chunk:', parseError);
              }
            }
          }
        }

        // Mark message as complete
        setMessages((prev) =>
          prev.map((msg) => (msg.id === aiMessageId ? { ...msg, isStreaming: false } : msg))
        );
      } catch (err) {
        if (err instanceof Error && err.name === 'AbortError') {
          // Request was aborted, remove the placeholder message
          setMessages((prev) => prev.filter((msg) => msg.id !== aiMessageId));
          return;
        }

        const errorObj = err instanceof Error ? err : new Error('Unknown error');
        setError(errorObj);

        // Update message to show error
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === aiMessageId
              ? {
                  ...msg,
                  content: `Sorry, I encountered an error: ${errorObj.message}`,
                  isStreaming: false,
                }
              : msg
          )
        );

        toast.error('Failed to get AI response', {
          description: errorObj.message,
        });
      } finally {
        setIsTyping(false);
        abortControllerRef.current = null;
      }
    },
    [issueId, apiBaseUrl, isTyping, queryClient]
  );

  const clearConversation = React.useCallback(() => {
    // Abort any ongoing request
    abortControllerRef.current?.abort();

    setMessages([]);
    setSuggestedQuestions(initialQuestions);
    setError(null);
  }, [initialQuestions]);

  return {
    messages,
    suggestedQuestions,
    isTyping,
    sendMessage,
    clearConversation,
    error,
  };
}

export default useAIContextChat;
