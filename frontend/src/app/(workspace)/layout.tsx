'use client';

import type { ReactNode } from 'react';
import { AppShell } from '@/components/layout';
import { WorkspaceGuard } from '@/components/workspace-guard';

interface WorkspaceLayoutProps {
  children: ReactNode;
}

export default function WorkspaceLayout({ children }: WorkspaceLayoutProps) {
  return (
    <WorkspaceGuard>
      <AppShell>{children}</AppShell>
    </WorkspaceGuard>
  );
}
