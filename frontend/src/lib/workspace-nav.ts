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
