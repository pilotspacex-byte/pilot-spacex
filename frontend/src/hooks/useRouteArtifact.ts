'use client';

import { useEffect, useRef } from 'react';
import { usePathname } from 'next/navigation';
import { useArtifactPanelStore, useUIStore } from '@/stores';
import type { ArtifactTab } from '@/stores/ArtifactPanelStore';

interface RouteArtifactMapping {
  type: ArtifactTab['type'];
  entityId: string;
  title: string;
}

/**
 * Parse the current pathname to determine if it maps to an artifact.
 * Returns null for the workspace root (homepage) and unsupported routes.
 */
function parseRouteToArtifact(pathname: string): RouteArtifactMapping | null {
  const segments = pathname.split('/').filter(Boolean);
  // segments: [workspaceSlug, feature?, entityId?, ...]
  if (segments.length < 2) return null;

  const feature = segments[1];
  const entityId = segments[2];

  switch (feature) {
    case 'notes':
      if (entityId) {
        return { type: 'note', entityId, title: 'Note' };
      }
      return { type: 'note', entityId: 'list', title: 'Notes' };

    case 'issues':
      if (entityId) {
        return { type: 'issue', entityId, title: 'Issue' };
      }
      return { type: 'issue-list', entityId: 'list', title: 'Issues' };

    case 'projects':
      if (entityId) {
        return { type: 'project', entityId, title: 'Project' };
      }
      return { type: 'project', entityId: 'list', title: 'Projects' };

    case 'members':
      return { type: 'members', entityId: 'list', title: 'Members' };

    case 'settings':
      return { type: 'settings', entityId: 'settings', title: 'Settings' };

    default:
      return null;
  }
}

/**
 * Hook that syncs the current route to the ArtifactPanelStore and UIStore.
 * When navigating to a sub-route (notes, issues, etc.), it opens the
 * corresponding artifact tab AND transitions layoutMode to 'chat-artifact'.
 * When navigating back to homepage, transitions to 'chat-first'.
 */
export function useRouteArtifact(enabled: boolean): boolean {
  const pathname = usePathname();
  const artifactPanel = useArtifactPanelStore();
  const uiStore = useUIStore();
  const lastPathRef = useRef<string>('');

  useEffect(() => {
    if (!enabled) return;
    if (pathname === lastPathRef.current) return;
    lastPathRef.current = pathname;

    const mapping = parseRouteToArtifact(pathname);

    if (mapping) {
      const tabId = `${mapping.type}:${mapping.entityId}`;
      artifactPanel.openTab({
        id: tabId,
        type: mapping.type,
        entityId: mapping.entityId,
        title: mapping.title,
      });
      // Transition to split view so the artifact panel mounts
      if (uiStore.layoutMode === 'chat-first') {
        uiStore.setLayoutMode('chat-artifact');
      }
    } else {
      // Navigated to homepage or non-artifact route — collapse artifact panel
      if (uiStore.layoutMode !== 'chat-first') {
        uiStore.setLayoutMode('chat-first');
      }
    }
  }, [pathname, enabled, artifactPanel, uiStore]);

  // Return whether the current route maps to an artifact
  return enabled && parseRouteToArtifact(pathname) !== null;
}
