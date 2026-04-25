import type { Workspace } from '@/types';
import { getRecentWorkspaces } from '@/components/workspace-selector';

const LAST_PATH_PREFIX = 'pilot-space:last-path:';

/**
 * Persist the last visited path for a workspace.
 * Settings paths (/settings/*) are ignored — we don't restore into settings on switch.
 */
export function saveLastWorkspacePath(slug: string, path: string): void {
  if (typeof window === 'undefined') return;
  if (path.includes('/settings/')) return;
  try {
    localStorage.setItem(`${LAST_PATH_PREFIX}${slug}`, path);
  } catch {
    // localStorage may be unavailable (private mode, quota exceeded) — fail silently
  }
}

/**
 * Read the last visited path for a workspace.
 * Returns null if never visited or localStorage unavailable.
 */
export function getLastWorkspacePath(slug: string): string | null {
  if (typeof window === 'undefined') return null;
  try {
    return localStorage.getItem(`${LAST_PATH_PREFIX}${slug}`);
  } catch {
    return null;
  }
}

/**
 * Returns workspaces in recency order (most recent first).
 *
 * Source of truth for ⌘2/⌘3 shortcut and the Switcher popover WORKSPACES list.
 * Joins the localStorage recency slug list (from `getRecentWorkspaces`) to the
 * `WorkspaceStore.workspaces` Map values, filtering out slugs whose workspace is
 * unknown to the store (e.g. user lost access, workspace deleted).
 *
 * Pure function — no side effects, no localStorage write.
 */
export function getOrderedRecentWorkspaces(
  store: { workspaces: Map<string, Workspace> }
): Workspace[] {
  const recents = getRecentWorkspaces();
  const ordered: Workspace[] = [];
  for (const { slug } of recents) {
    for (const ws of store.workspaces.values()) {
      if (ws.slug === slug) {
        ordered.push(ws);
        break;
      }
    }
  }
  return ordered;
}
