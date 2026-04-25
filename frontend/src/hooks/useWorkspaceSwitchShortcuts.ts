'use client';

/**
 * useWorkspaceSwitchShortcuts - Registers global ⌘2 / ⌘3 listeners.
 *
 * Mirrors the shape of useCommandPaletteShortcut (Cmd+K). Reads the recency-ordered
 * workspace list from `getOrderedRecentWorkspaces(workspaceStore)` and navigates to
 * the workspace at index 1 (⌘2) or 2 (⌘3) — i.e. the second / third most recently
 * visited workspace. recents[0] is the current workspace, so ⌘1 (the current one)
 * is intentionally not bound.
 *
 * Falls back to `/${slug}` when `getLastWorkspacePath` has no stored path for
 * a workspace the user has never visited (common on a fresh session). Without
 * this fallback router.push(null) crashes — see Plan 90-01 deviations.
 *
 * Skips when focus is inside .ProseMirror, <input>, or <textarea> so the
 * shortcut never hijacks a normal "2"/"3" keystroke during text entry.
 *
 * Should be mounted ONCE at the workspace-shell level (Plan 04 wires this).
 */

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useWorkspaceStore } from '@/stores';
import { getLastWorkspacePath, getOrderedRecentWorkspaces } from '@/lib/workspace-nav';

export function useWorkspaceSwitchShortcuts(): void {
  const workspaceStore = useWorkspaceStore();
  const router = useRouter();

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      const platform =
        (navigator as Navigator & { userAgentData?: { platform?: string } }).userAgentData
          ?.platform ?? navigator.platform;
      const isMac = /mac/i.test(platform);
      const modifier = isMac ? event.metaKey : event.ctrlKey;

      if (!modifier) return;
      if (event.key !== '2' && event.key !== '3') return;

      // Editor / form-field guard — never hijack '2' / '3' while user is typing.
      const activeTag = document.activeElement?.tagName.toLowerCase();
      const isEditorFocused =
        document.activeElement?.closest('.ProseMirror') !== null ||
        activeTag === 'input' ||
        activeTag === 'textarea';
      if (isEditorFocused) return;

      const index = event.key === '2' ? 1 : 2;
      const recents = getOrderedRecentWorkspaces(workspaceStore);
      const target = recents[index];
      if (!target) return;

      event.preventDefault();
      const path = getLastWorkspacePath(target.slug) ?? `/${target.slug}`;
      router.push(path);
    }

    window.addEventListener('keydown', handleKeyDown, { capture: true });
    return () => window.removeEventListener('keydown', handleKeyDown, { capture: true });
  }, [workspaceStore, router]);
}
