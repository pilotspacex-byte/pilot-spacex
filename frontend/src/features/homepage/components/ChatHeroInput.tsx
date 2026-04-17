'use client';

/**
 * ChatHeroInput — Gemini-style AI Prompt Hero wired to PilotSpace stores.
 *
 * Two-zone layout per design.md §4.1:
 *   Zone 1: Input row (textarea + send button)
 *   Zone 2: Toolbar (+ | sliders | connector pills | model pill | Plan selector)
 *
 * Store wiring:
 *   - Model pill → AISettingsStore.availableModels + PilotSpaceStore.selectedModel
 *   - Connector pills → MCPServersStore.servers (enabled servers)
 *   - Submit → navigates to /chat?prefill= (full ChatInput takes over there)
 *   - / prefix → navigates to /chat?prefill=/skill (skill discovery via ChatInput)
 *
 * This is a lightweight gateway — full skill/agent/entity/attachment functionality
 * lives in features/ai/ChatView/ChatInput/ChatInput.tsx and activates on navigation.
 */

import { useState, useCallback, useMemo, type KeyboardEvent } from 'react';
import { useRouter } from 'next/navigation';
import { observer } from 'mobx-react-lite';
import { useAIStore } from '@/stores/RootStore';
import {
  ArrowUp,
  ChevronDown,
  Loader2,
  Plus,
  SlidersHorizontal,
  Plug,
  Sparkles,
  X,
} from 'lucide-react';

interface ChatHeroInputProps {
  workspaceSlug: string;
}

export const ChatHeroInput = observer(function ChatHeroInput({
  workspaceSlug,
}: ChatHeroInputProps) {
  const router = useRouter();
  const aiStore = useAIStore();
  const [value, setValue] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // ── Model from store ─────────────────────────────────────────────────
  const selectedModel = aiStore.pilotSpace?.selectedModel;
  const availableModels = aiStore.settings?.availableModels ?? [];

  const modelDisplayName = useMemo(() => {
    if (!selectedModel) return 'Claude Sonnet';
    const match = availableModels.find(
      (m) => m.model_id === selectedModel.modelId && m.provider === selectedModel.provider
    );
    return match?.display_name ?? selectedModel.modelId.replace(/-\d{8}$/, '').replace(/-/g, ' ');
  }, [selectedModel, availableModels]);

  // ── Enabled MCP connectors ───────────────────────────────────────────
  const mcpServers = aiStore.mcpServers?.servers ?? [];
  const enabledConnectors = useMemo(
    () => mcpServers.filter((s) => s.is_enabled && s.last_status === 'enabled'),
    [mcpServers]
  );

  // ── Handlers ─────────────────────────────────────────────────────────
  const navigateToChat = useCallback(
    (message: string) => {
      setIsSubmitting(true);
      router.push(`/${workspaceSlug}/chat?prefill=${encodeURIComponent(message)}`);
    },
    [router, workspaceSlug]
  );

  const handleSubmit = useCallback(() => {
    const trimmed = value.trim();
    if (!trimmed || isSubmitting) return;
    navigateToChat(trimmed);
  }, [value, isSubmitting, navigateToChat]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit]
  );

  const hasValue = value.trim().length > 0;

  return (
    <div
      className="w-full rounded-[28px] transition-all duration-150 focus-within:ring-2 focus-within:ring-ring"
      style={{ backgroundColor: 'var(--surface-chatbox, #f0f4f9)' }}
    >
      {/* Zone 1 — Input Row */}
      <div className="flex items-center gap-3 px-6 pb-3 pt-5">
        <textarea
          role="textbox"
          aria-label="Chat with AI"
          aria-multiline="true"
          rows={1}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isSubmitting}
          placeholder="What would you like to work on?"
          className="min-h-[24px] flex-1 resize-none bg-transparent text-base leading-6 text-foreground placeholder:text-muted-foreground focus:outline-none disabled:opacity-50"
          style={{ fieldSizing: 'content' } as React.CSSProperties}
        />

        {/* Send button — 34px pill */}
        <button
          type="button"
          onClick={handleSubmit}
          disabled={!hasValue || isSubmitting}
          aria-label="Send message"
          className={[
            'flex h-[34px] w-[34px] shrink-0 items-center justify-center rounded-full transition-all duration-150',
            hasValue && !isSubmitting
              ? 'bg-primary text-primary-foreground hover:bg-primary/90'
              : 'bg-primary/40 text-primary-foreground cursor-not-allowed',
          ].join(' ')}
        >
          {isSubmitting ? (
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          ) : (
            <ArrowUp className="h-4 w-4" aria-hidden="true" />
          )}
        </button>
      </div>

      {/* Zone 2 — Toolbar (Gemini pattern) */}
      <div className="flex items-center gap-3.5 px-5 pb-3.5">
        {/* Attachment — navigates to chat for full attachment UI */}
        <button
          type="button"
          aria-label="Add attachment"
          onClick={() => navigateToChat('')}
          className="flex h-5 w-5 items-center justify-center text-muted-foreground transition-colors hover:text-foreground"
        >
          <Plus className="h-5 w-5" strokeWidth={1.5} aria-hidden="true" />
        </button>

        {/* Settings — navigates to AI settings */}
        <button
          type="button"
          aria-label="AI settings"
          onClick={() => router.push(`/${workspaceSlug}/settings/ai`)}
          className="flex h-5 w-5 items-center justify-center text-muted-foreground transition-colors hover:text-foreground"
        >
          <SlidersHorizontal className="h-5 w-5" strokeWidth={1.5} aria-hidden="true" />
        </button>

        {/* Connector pills — real MCP servers from store */}
        {enabledConnectors.length > 0 ? (
          enabledConnectors.slice(0, 2).map((server) => (
            <span
              key={server.id}
              className="inline-flex items-center gap-1.5 rounded-full border border-[var(--border-toolbar,#c8d1db)] px-3.5 py-1.5"
            >
              <Plug
                className="h-[13px] w-[13px] text-primary"
                strokeWidth={1.5}
                aria-hidden="true"
              />
              <span className="text-xs font-medium text-primary">{server.display_name}</span>
              <X
                className="h-[11px] w-[11px] text-muted-foreground"
                strokeWidth={1.5}
                aria-hidden="true"
              />
            </span>
          ))
        ) : (
          <span className="inline-flex items-center gap-1.5 rounded-full border border-[var(--border-toolbar,#c8d1db)] px-3.5 py-1.5">
            <Plug
              className="h-[13px] w-[13px] text-primary"
              strokeWidth={1.5}
              aria-hidden="true"
            />
            <span className="text-xs font-medium text-primary">Codebase</span>
            <X
              className="h-[11px] w-[11px] text-muted-foreground"
              strokeWidth={1.5}
              aria-hidden="true"
            />
          </span>
        )}

        {/* Model pill — wired to AISettingsStore + PilotSpaceStore */}
        <button
          type="button"
          className="inline-flex items-center gap-1.5 rounded-full border border-[var(--border-toolbar,#c8d1db)] px-3.5 py-1.5 transition-colors hover:border-primary/40"
        >
          <Sparkles
            className="h-[13px] w-[13px] text-[#8b5cf6]"
            strokeWidth={1.5}
            aria-hidden="true"
          />
          <span className="text-xs font-medium text-secondary-foreground">{modelDisplayName}</span>
        </button>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Mode selector — static (no mode state in store yet) */}
        <button
          type="button"
          className="inline-flex items-center gap-1 text-[13px] font-medium text-muted-foreground transition-colors hover:text-foreground"
        >
          <span>Plan</span>
          <ChevronDown className="h-3.5 w-3.5" strokeWidth={1.5} aria-hidden="true" />
        </button>
      </div>
    </div>
  );
});
