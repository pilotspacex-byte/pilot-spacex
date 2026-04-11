'use client';

import type { ReactNode } from 'react';
import { observer } from 'mobx-react-lite';
import { AppShell, ChatFirstShell } from '@/components/layout';
import { WorkspaceGuard } from '@/components/workspace-guard';
import { SettingsModalProvider } from '@/features/settings/settings-modal-context';
import { SettingsModal } from '@/features/settings/settings-modal';
import { useWorkspaceStore } from '@/stores';

interface WorkspaceLayoutProps {
  children: ReactNode;
}

const WorkspaceLayoutInner = observer(function WorkspaceLayoutInner({
  children,
}: WorkspaceLayoutProps) {
  const workspaceStore = useWorkspaceStore();
  const useV2Layout = workspaceStore.isFeatureEnabled('layout_v2');
  const Shell = useV2Layout ? ChatFirstShell : AppShell;

  return <Shell>{children}</Shell>;
});

export default function WorkspaceLayout({ children }: WorkspaceLayoutProps) {
  return (
    <WorkspaceGuard>
      <SettingsModalProvider>
        <WorkspaceLayoutInner>{children}</WorkspaceLayoutInner>
        <SettingsModal />
      </SettingsModalProvider>
    </WorkspaceGuard>
  );
}
