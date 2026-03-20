'use client';

/**
 * Workspace-slug-scoped layout — client component.
 *
 * Mounts the AiNotConfiguredBanner at the top of every workspace page (AIGOV-05).
 * Banner is only visible to Owners when BYOK is not configured.
 *
 * Also mounts the TerminalPanel (Tauri desktop only) at the bottom of the layout.
 * The panel is toggled via terminalStore.isOpen or the Ctrl+` keyboard shortcut.
 *
 * Extracted from layout.tsx so that layout.tsx can be a Server Component
 * and export generateStaticParams() for static export (NEXT_TAURI=true) compatibility.
 */

import type { ReactNode } from 'react';
import dynamic from 'next/dynamic';
import { useEffect } from 'react';
import { observer } from 'mobx-react-lite';
import { usePathname } from 'next/navigation';
import { useWorkspace } from '@/components/workspace-guard';
import { useWorkspaceStore } from '@/stores';
import { saveLastWorkspacePath } from '@/lib/workspace-nav';
import { AiNotConfiguredBanner } from '@/components/workspace/ai-not-configured-banner';
import { isTauri } from '@/lib/tauri';

// Dynamic import with ssr: false — xterm.js requires DOM APIs unavailable during SSG
const TerminalPanel = dynamic(
  () => import('@/features/terminal/components/TerminalPanel').then((m) => m.TerminalPanel),
  { ssr: false }
);

// Dynamic import with ssr: false — listens for implement-complete DOM events and fires
// native OS notifications. Only mounted in Tauri desktop mode.
const TrayNotificationListener = dynamic(
  () =>
    import('@/components/desktop/tray-notification-listener').then((m) => ({
      default: m.TrayNotificationListener,
    })),
  { ssr: false }
);

interface WorkspaceSlugLayoutProps {
  children: ReactNode;
}

export const WorkspaceSlugLayout = observer(function WorkspaceSlugLayout({
  children,
}: WorkspaceSlugLayoutProps) {
  const { workspaceSlug } = useWorkspace();
  const workspaceStore = useWorkspaceStore();
  const isOwner = workspaceStore.isOwner;
  const pathname = usePathname();

  useEffect(() => {
    saveLastWorkspacePath(workspaceSlug, pathname);
  }, [pathname, workspaceSlug]);

  return (
    <>
      <AiNotConfiguredBanner workspaceSlug={workspaceSlug} isOwner={isOwner} />
      {children}
      {isTauri() && <TerminalPanel />}
      {isTauri() && <TrayNotificationListener />}
    </>
  );
});
