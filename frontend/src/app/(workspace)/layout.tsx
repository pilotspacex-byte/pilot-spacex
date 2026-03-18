'use client';

import type { ReactNode } from 'react';
import { AppShell } from '@/components/layout';
import { WorkspaceGuard } from '@/components/workspace-guard';
import { SettingsModalProvider } from '@/features/settings/settings-modal-context';
import { SettingsModal } from '@/features/settings/settings-modal';

interface WorkspaceLayoutProps {
  children: ReactNode;
}

export default function WorkspaceLayout({ children }: WorkspaceLayoutProps) {
  return (
    <WorkspaceGuard>
      <SettingsModalProvider>
        <AppShell>{children}</AppShell>
        <SettingsModal />
      </SettingsModalProvider>
    </WorkspaceGuard>
  );
}
