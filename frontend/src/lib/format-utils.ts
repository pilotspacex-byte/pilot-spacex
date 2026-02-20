import { formatDistanceToNow } from 'date-fns';

/**
 * Safely format a date string as relative distance (e.g. "about 2 hours ago").
 * Returns "recently" for null, undefined, or invalid date strings.
 */
export function safeFormatDistance(dateStr: string | null | undefined): string {
  if (!dateStr) return 'recently';
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return 'recently';
  return formatDistanceToNow(d, { addSuffix: true });
}

/**
 * Abbreviated relative time (e.g. "8h", "3d", "2w", "now").
 * Compact format for space-constrained UIs like the Daily Brief.
 */
export function abbreviatedTimeAgo(dateStr: string | null | undefined): string {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return '';
  const now = Date.now();
  const diffMs = Math.max(0, now - d.getTime());
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return 'now';
  if (diffMin < 60) return `${diffMin}m`;
  const diffH = Math.floor(diffMin / 60);
  if (diffH < 24) return `${diffH}h`;
  const diffD = Math.floor(diffH / 24);
  if (diffD < 7) return `${diffD}d`;
  const diffW = Math.floor(diffD / 7);
  return `${diffW}w`;
}
