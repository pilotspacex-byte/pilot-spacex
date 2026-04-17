'use client';

import type { ReactNode } from 'react';
import { AppShell } from '@/components/layout';
import { WorkspaceGuard } from '@/components/workspace-guard';
import { SettingsModalProvider } from '@/features/settings/settings-modal-context';
import { SettingsModal } from '@/features/settings/settings-modal';
import { QuoteToChat } from '@/features/chat/QuoteToChat';
import { PeekDrawer } from '@/features/artifacts/PeekDrawer';

interface WorkspaceLayoutProps {
  children: ReactNode;
}

export default function WorkspaceLayout({ children }: WorkspaceLayoutProps) {
  return (
    <WorkspaceGuard>
      <SettingsModalProvider>
        <AppShell>{children}</AppShell>
        <SettingsModal />
        {/* Floating "Quote in chat" chip — globally mounted, activates when
            user selects text inside a [data-quote-scope] element. */}
        <QuoteToChat />
        {/* Universal peek drawer — any page can trigger via ?peek=<type>:<id>. */}
        <PeekDrawer />
      </SettingsModalProvider>
    </WorkspaceGuard>
  );
}
