'use client';

import { useCallback, useEffect, useState } from 'react';
import { observer } from 'mobx-react-lite';
import { AnimatePresence, motion } from 'motion/react';
import { Menu } from 'lucide-react';
import { useUIStore, useAuthStore, useArtifactPanelStore } from '@/stores';
import { getAIStore } from '@/stores/ai/AIStore';
import { useResponsive } from '@/hooks/useMediaQuery';
import { useRouteArtifact } from '@/hooks/useRouteArtifact';
import { ConversationSidebar } from './conversation-sidebar';
import { ArtifactPanel } from './artifact-panel';
import { ChatView } from '@/features/ai/ChatView';
import { ChatEmptyState } from '@/features/ai/ChatView/ChatEmptyState';
import { CommandPalette } from '@/components/search/CommandPalette';
import { useCommandPaletteShortcut } from '@/hooks/useCommandPaletteShortcut';
import { useChatFirstShortcuts } from '@/hooks/useChatFirstShortcuts';
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from '@/components/ui/resizable';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { ReactNode } from 'react';

function AILoadingSkeleton() {
  const [showHint, setShowHint] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setShowHint(true), 5000);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="flex h-full flex-col items-center justify-center px-4 gap-4">
      {/* Shimmer skeleton matching ChatEmptyState layout */}
      <div className="w-full max-w-xl space-y-6 animate-pulse">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-2xl bg-muted" />
          <div className="space-y-2 flex-1">
            <div className="h-4 w-32 rounded bg-muted" />
            <div className="h-3 w-48 rounded bg-muted" />
          </div>
        </div>
        <div className="space-y-2">
          <div className="h-3 w-12 rounded bg-muted" />
          <div className="grid grid-cols-2 gap-2">
            <div className="h-10 rounded-xl bg-muted" />
            <div className="h-10 rounded-xl bg-muted" />
          </div>
        </div>
        <div className="space-y-2">
          <div className="h-3 w-10 rounded bg-muted" />
          <div className="grid grid-cols-2 gap-2">
            <div className="h-10 rounded-xl bg-muted" />
            <div className="h-10 rounded-xl bg-muted" />
          </div>
        </div>
      </div>
      {showHint && (
        <p className="text-xs text-muted-foreground text-center">
          Taking longer than expected.{' '}
          <button
            type="button"
            className="underline hover:text-foreground transition-colors"
            onClick={() => {
              // Navigate to settings via DOM event (settings modal is external)
              window.dispatchEvent(new CustomEvent('pilot:open-settings', { detail: { tab: 'ai-providers' } }));
            }}
          >
            Check AI provider settings
          </button>
        </p>
      )}
    </div>
  );
}

interface ChatFirstShellProps {
  children: ReactNode;
}

export const ChatFirstShell = observer(function ChatFirstShell({
  children,
}: ChatFirstShellProps) {
  const uiStore = useUIStore();
  const authStore = useAuthStore();
  const artifactPanelStore = useArtifactPanelStore();
  const { isMobile, isTablet } = useResponsive();
  const isSmallScreen = isMobile || isTablet;

  // Detect if current route maps to an artifact (notes, issues, etc.)
  const isRouteArtifact = useRouteArtifact(true);

  // Persistent AI store — lives in the shell, not in routing
  const aiStore = getAIStore();
  const pilotSpaceStore = aiStore.pilotSpace;

  // Prefill for ChatEmptyState prompt clicks
  const [prefillValue, setPrefillValue] = useState<string | undefined>(undefined);

  const handlePromptClick = useCallback((prompt: string) => {
    setPrefillValue(prompt);
  }, []);

  // Clear prefill after consumed by ChatView
  useEffect(() => {
    if (prefillValue) {
      const timer = setTimeout(() => setPrefillValue(undefined), 100);
      return () => clearTimeout(timer);
    }
  }, [prefillValue]);

  useEffect(() => {
    uiStore.hydrate();
  }, [uiStore]);

  useCommandPaletteShortcut();
  useChatFirstShortcuts();

  // Auto-collapse sidebar on mobile/tablet
  useEffect(() => {
    if (isSmallScreen) {
      uiStore.setSidebarCollapsed(true);
    }
  }, [isSmallScreen, uiStore]);

  const showArtifactPanel = uiStore.layoutMode !== 'chat-first' && !isSmallScreen;
  const sidebarCollapsed = uiStore.sidebarCollapsed;

  // Persistent ChatView component — always available in the chat column
  const chatViewElement = pilotSpaceStore ? (
    <ChatView
      store={pilotSpaceStore}
      approvalStore={aiStore.approval}
      userName={authStore.userDisplayName || 'User'}
      className="h-full"
      autoFocus={!isRouteArtifact}
      prefillValue={prefillValue}
      persistentMode
      emptyStateSlot={
        <ChatEmptyState
          onPromptClick={handlePromptClick}
          userName={authStore.userDisplayName || undefined}
          sidebarCollapsed={sidebarCollapsed}
          artifactContext={artifactPanelStore.activeTab?.type}
        />
      }
    />
  ) : (
    <AILoadingSkeleton />
  );

  return (
    <div className="flex h-screen w-full overflow-hidden bg-background">
      <CommandPalette />

      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:z-[100] focus:m-4 focus:rounded-md focus:bg-primary focus:px-4 focus:py-2 focus:text-primary-foreground"
      >
        Skip to main content
      </a>

      {/* Screen reader announcement for layout transitions */}
      <div aria-live="polite" className="sr-only">
        {showArtifactPanel && isRouteArtifact ? 'Artifact panel opened' : ''}
      </div>

      {/* Mobile sidebar overlay */}
      <AnimatePresence>
        {isMobile && !sidebarCollapsed && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            aria-hidden="true"
            className="fixed inset-0 z-40 bg-black/50"
            onClick={() => uiStore.setSidebarCollapsed(true)}
          />
        )}
      </AnimatePresence>

      {/* Sidebar — overlay on mobile, inline on desktop */}
      <div className={cn(isMobile && !sidebarCollapsed && 'fixed left-0 top-0 z-50 h-full')}>
        <ConversationSidebar />
      </div>

      {/* Sidebar expand button when collapsed (desktop only) */}
      {sidebarCollapsed && !isMobile && (
        <div className="flex shrink-0 items-start pt-2 pl-2">
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={() => uiStore.setSidebarCollapsed(false)}
            aria-label="Open sidebar"
          >
            <Menu className="h-4 w-4" />
          </Button>
        </div>
      )}

      {/* Mobile menu button */}
      {isMobile && sidebarCollapsed && (
        <div className="fixed top-2 left-2 z-30">
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 bg-background/80 backdrop-blur-sm"
            onClick={() => uiStore.setSidebarCollapsed(false)}
            aria-label="Open sidebar"
          >
            <Menu className="h-4 w-4" />
          </Button>
        </div>
      )}

      {/* Main content area */}
      {isSmallScreen ? (
        // Mobile/tablet: show route content full-screen, or ChatView on homepage
        <main id="main-content" className="flex-1 overflow-hidden">
          {isRouteArtifact ? children : chatViewElement}
        </main>
      ) : showArtifactPanel && isRouteArtifact ? (
        // Desktop with artifact: chat column (left) + artifact panel (right)
        <ResizablePanelGroup orientation="horizontal" className="flex-1">
          <ResizablePanel
            id="chat-column"
            defaultSize={`${uiStore.chatColumnSize}%`}
            minSize="15%"
            className="min-w-0"
          >
            <div className="h-full overflow-hidden">
              {chatViewElement}
            </div>
          </ResizablePanel>

          <ResizableHandle withHandle />

          <ResizablePanel
            id="artifact-panel"
            defaultSize={`${uiStore.artifactPanelSize}%`}
            minSize="30%"
            className="min-w-0"
          >
            <motion.div
              id="main-content"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.2, ease: [0.25, 0.1, 0.25, 1] }}
              className="h-full"
            >
              <ArtifactPanel>
                {children}
              </ArtifactPanel>
            </motion.div>
          </ResizablePanel>
        </ResizablePanelGroup>
      ) : (
        // Desktop without artifact: full-width ChatView (homepage)
        <main id="main-content" className="flex-1 overflow-hidden">
          {isRouteArtifact ? children : chatViewElement}
        </main>
      )}
    </div>
  );
});
