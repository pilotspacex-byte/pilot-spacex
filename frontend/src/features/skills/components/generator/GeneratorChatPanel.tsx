/**
 * GeneratorChatPanel -- Lightweight AI chat panel for the skill generator page.
 *
 * Renders chat messages from SkillGeneratorPageStore and provides a text input.
 * Streams from the dedicated /api/v1/skills/generator/chat SSE endpoint.
 *
 * This IS wrapped in observer() -- it is OUTSIDE the ReactFlow tree, safe from
 * the flushSync conflict (Phase 52 decision).
 *
 * @module features/skills/components/generator/GeneratorChatPanel
 */

'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { observer } from 'mobx-react-lite';
import { Loader2, Send } from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';
import type { SkillGeneratorPageStore, ChatMessage } from '@/features/skills/stores/SkillGeneratorPageStore';

// ---------------------------------------------------------------------------
// SSE Stream Helper
// ---------------------------------------------------------------------------

interface SSEParsedEvent {
  event?: string;
  data?: string;
}

function parseSSEChunk(chunk: string): SSEParsedEvent[] {
  const events: SSEParsedEvent[] = [];
  const blocks = chunk.split('\n\n');
  for (const block of blocks) {
    if (!block.trim()) continue;
    const lines = block.split('\n');
    const evt: SSEParsedEvent = {};
    for (const line of lines) {
      if (line.startsWith('event: ')) {
        evt.event = line.slice(7).trim();
      } else if (line.startsWith('data: ')) {
        evt.data = line.slice(6);
      }
    }
    if (evt.data !== undefined) {
      events.push(evt);
    }
  }
  return events;
}

async function streamGeneratorChat(
  message: string,
  context: Record<string, unknown>,
  workspaceId: string,
  store: SkillGeneratorPageStore,
  abortSignal: AbortSignal,
): Promise<void> {
  const { supabase } = await import('@/lib/supabase');
  const { data: sessionData } = await supabase.auth.getSession();
  const token = sessionData.session?.access_token;

  if (!token) {
    toast.error('Authentication required. Please log in again.');
    return;
  }

  store.setStreaming(true);
  // Add a placeholder assistant message to stream into
  store.addAssistantMessage('');

  try {
    const response = await fetch('/api/v1/skills/generator/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        'X-Workspace-Id': workspaceId,
      },
      body: JSON.stringify({ message, context }),
      signal: abortSignal,
    });

    if (!response.ok) {
      const errorText = await response.text().catch(() => 'Unknown error');
      throw new Error(`Generator chat failed: ${response.status} ${errorText}`);
    }

    const reader = response.body?.getReader();
    if (!reader) throw new Error('No response body');

    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // Parse complete SSE events from the buffer
      const lastDoubleNewline = buffer.lastIndexOf('\n\n');
      if (lastDoubleNewline === -1) continue;

      const complete = buffer.slice(0, lastDoubleNewline + 2);
      buffer = buffer.slice(lastDoubleNewline + 2);

      const events = parseSSEChunk(complete);
      for (const evt of events) {
        if (!evt.data) continue;

        try {
          const parsed = JSON.parse(evt.data);
          const eventType = evt.event || parsed.type;

          switch (eventType) {
            case 'content_delta':
            case 'text_delta': {
              const delta = parsed.data?.delta ?? parsed.delta ?? '';
              if (delta) {
                store.appendToLastAssistant(delta);
              }
              break;
            }
            case 'skill_draft': {
              const content = parsed.data?.content ?? parsed.content ?? '';
              if (content) {
                store.setSkillContent(content);
              }
              break;
            }
            case 'skill_preview': {
              const preview = parsed.data ?? parsed;
              if (preview.skillContent) {
                store.setSkillContent(preview.skillContent);
              }
              if (preview.name) {
                store.setSkillName(preview.name);
              }
              if (preview.description) {
                store.setSkillDescription(preview.description);
              }
              // Auto-open preview panel when skill is ready
              if (!store.isPreviewOpen) {
                store.togglePreview();
              }
              break;
            }
            case 'graph_update': {
              // Future: integrate with ReactFlow graph
              console.log('[GeneratorChat] graph_update:', parsed.data);
              break;
            }
            case 'done':
            case 'message_stop': {
              store.setStreaming(false);
              break;
            }
            case 'error': {
              const errorMsg = parsed.data?.message ?? parsed.message ?? 'Unknown error';
              toast.error(errorMsg);
              store.setStreaming(false);
              break;
            }
            default:
              // Ignore unknown events
              break;
          }
        } catch {
          // Skip malformed JSON lines
        }
      }
    }
  } catch (err) {
    if (abortSignal.aborted) return; // User cancelled, not an error
    const message = err instanceof Error ? err.message : 'Failed to connect to AI';
    toast.error(message);
  } finally {
    store.setStreaming(false);
  }
}

// ---------------------------------------------------------------------------
// Message Bubble
// ---------------------------------------------------------------------------

function ChatBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user';

  return (
    <div className={cn('flex w-full', isUser ? 'justify-end' : 'justify-start')}>
      <div
        className={cn(
          'max-w-[85%] rounded-lg px-3 py-2 text-sm whitespace-pre-wrap',
          isUser
            ? 'bg-primary/10 text-foreground'
            : 'bg-muted text-foreground',
        )}
      >
        {message.content}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Chat Panel
// ---------------------------------------------------------------------------

interface GeneratorChatPanelProps {
  store: SkillGeneratorPageStore;
  workspaceId: string;
}

export const GeneratorChatPanel = observer(function GeneratorChatPanel({
  store,
  workspaceId,
}: GeneratorChatPanelProps) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Auto-scroll on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [store.chatMessages.length]);

  // Cleanup abort controller on unmount
  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  const handleSend = useCallback(() => {
    const trimmed = input.trim();
    if (!trimmed || store.isStreaming) return;

    store.addUserMessage(trimmed);
    setInput('');

    // Build context from current store state
    const context: Record<string, unknown> = {};
    if (store.skillContent) {
      context.current_draft = store.skillContent;
    }
    if (store.skillName) {
      context.skill_name = store.skillName;
    }

    // Abort any in-flight request
    abortControllerRef.current?.abort();
    const controller = new AbortController();
    abortControllerRef.current = controller;

    void streamGeneratorChat(trimmed, context, workspaceId, store, controller.signal);
  }, [input, store, workspaceId]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend],
  );

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="shrink-0 flex items-center px-4 py-2.5 border-b">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          AI Assistant
        </h2>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-3">
        {store.chatMessages.map((msg) => (
          <ChatBubble key={msg.id} message={msg} />
        ))}

        {store.isStreaming && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground px-1">
            <Loader2 className="h-3 w-3 animate-spin" />
            Typing...
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="shrink-0 border-t p-3">
        <div className="flex gap-2">
          <Textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Describe the skill you want..."
            className="min-h-[40px] max-h-[120px] resize-none text-sm"
            rows={1}
          />
          <Button
            size="icon"
            className="shrink-0 h-10 w-10"
            disabled={!input.trim() || store.isStreaming}
            onClick={handleSend}
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
});
