'use client';

/**
 * CompactChatView (H039) — Coordinator managing collapsed/expanded state.
 * Collapsed: renders CompactChatInput. Expanded: renders CompactChatPanel.
 * Integrates PilotSpaceStore with homepage context.
 *
 * H-4: Animated expand/collapse with CSS height transition (200ms).
 * H-5: Auto-focus textarea on expand.
 * H-3: Mobile bottom sheet via fixed positioning on sm breakpoint.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { observer } from 'mobx-react-lite';
import { cn } from '@/lib/utils';
import { useHomepageStore, useWorkspaceStore } from '@/stores/RootStore';
import { useCompactChat } from '../../hooks/useCompactChat';
import { CompactChatInput } from './CompactChatInput';
import { CompactChatPanel } from './CompactChatPanel';

interface CompactChatViewProps {
  /** Ref for focusing via keyboard shortcuts */
  inputRef?: React.RefObject<HTMLInputElement | null>;
}

export const CompactChatView = observer(function CompactChatView({
  inputRef,
}: CompactChatViewProps) {
  const homepageStore = useHomepageStore();
  const workspaceStore = useWorkspaceStore();
  const workspaceId = workspaceStore.currentWorkspace?.id ?? '';
  const containerRef = useRef<HTMLDivElement>(null);
  const localInputRef = useRef<HTMLInputElement>(null);
  const chatInputRef = inputRef ?? localInputRef;

  // H-4: Track animation state to keep panel in DOM during collapse
  const [showPanel, setShowPanel] = useState(false);
  const [animating, setAnimating] = useState(false);

  const { messages, isStreaming, streamContent, sendMessage, abort } = useCompactChat(workspaceId);

  const handleFocus = useCallback(() => {
    homepageStore.expandChat();
  }, [homepageStore]);

  const handleMinimize = useCallback(() => {
    homepageStore.collapseChat();
  }, [homepageStore]);

  // H-4: Animate expand/collapse transitions
  useEffect(() => {
    if (homepageStore.chatExpanded) {
      setShowPanel(true);
      // Trigger expand animation on next frame
      requestAnimationFrame(() => setAnimating(true));
    } else {
      setAnimating(false);
      // Keep panel in DOM during collapse animation
      const timer = setTimeout(() => setShowPanel(false), 200);
      return () => clearTimeout(timer);
    }
  }, [homepageStore.chatExpanded]);

  // Close on outside click
  useEffect(() => {
    if (!homepageStore.chatExpanded) return;

    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        homepageStore.collapseChat();
      }
    };

    // Delay to avoid immediate close on the focus event that triggered expand
    const timer = setTimeout(() => {
      document.addEventListener('mousedown', handleClickOutside);
    }, 0);

    return () => {
      clearTimeout(timer);
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [homepageStore.chatExpanded, homepageStore]);

  // Close on Escape
  useEffect(() => {
    if (!homepageStore.chatExpanded) return;

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        homepageStore.collapseChat();
        chatInputRef.current?.focus();
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [homepageStore.chatExpanded, homepageStore, chatInputRef]);

  return (
    <div ref={containerRef} className="w-full">
      {/* H-4: Animated height transition wrapper */}
      <div
        className={cn(
          'grid motion-safe:transition-[grid-template-rows] motion-safe:duration-200 motion-safe:ease-out',
          animating ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'
        )}
      >
        <div className="overflow-hidden">
          {showPanel && (
            <div
              className={cn(
                // H-3: Mobile bottom sheet
                'md:relative md:rounded-lg',
                'max-md:fixed max-md:inset-x-0 max-md:bottom-0 max-md:z-50',
                'max-md:rounded-t-xl max-md:shadow-lg max-md:max-h-[60vh]'
              )}
            >
              <CompactChatPanel
                messages={messages}
                isStreaming={isStreaming}
                streamContent={streamContent}
                onSendMessage={sendMessage}
                onAbort={abort}
                onMinimize={handleMinimize}
                autoFocus
              />
            </div>
          )}
        </div>
      </div>

      {/* Collapsed input — hidden when panel is showing */}
      {!showPanel && <CompactChatInput ref={chatInputRef} onFocus={handleFocus} />}
    </div>
  );
});
