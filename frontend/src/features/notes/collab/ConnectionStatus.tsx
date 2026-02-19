/**
 * ConnectionStatus — Visual indicator for Yjs CRDT connection state.
 *
 * T-125: Real-time connection status badge showing online/offline/syncing/error.
 *
 * States:
 *   online   — green dot, "Live" label
 *   syncing  — animated pulse dot, "Syncing" label
 *   offline  — grey dot, "Offline" label (changes saved locally via IndexedDB)
 *   error    — red dot, "Connection error" label
 *
 * Accessibility: role="status" + aria-live="polite" for screen readers.
 * Design: small pill, consistent with pilot-space warm neutral design system.
 *
 * @module features/notes/collab/ConnectionStatus
 */
'use client';

import { cn } from '@/lib/utils';

export type ConnectionStatusValue = 'online' | 'offline' | 'syncing' | 'error';

export interface ConnectionStatusProps {
  status: ConnectionStatusValue;
  /** Show label text alongside the dot (default: true) */
  showLabel?: boolean;
  className?: string;
}

interface StatusConfig {
  label: string;
  dotClass: string;
  textClass: string;
  ariaLabel: string;
}

const STATUS_CONFIG: Record<ConnectionStatusValue, StatusConfig> = {
  online: {
    label: 'Live',
    dotClass: 'bg-primary',
    textClass: 'text-primary',
    ariaLabel: 'Connected — changes sync in real time',
  },
  syncing: {
    label: 'Syncing',
    dotClass: 'bg-yellow-400 animate-pulse',
    textClass: 'text-yellow-700 dark:text-yellow-400',
    ariaLabel: 'Syncing — connecting to collaboration server',
  },
  offline: {
    label: 'Offline',
    dotClass: 'bg-gray-400',
    textClass: 'text-gray-500 dark:text-gray-400',
    ariaLabel: 'Offline — changes saved locally and will sync when reconnected',
  },
  error: {
    label: 'Connection error',
    dotClass: 'bg-red-500',
    textClass: 'text-red-600 dark:text-red-400',
    ariaLabel: 'Connection error — unable to reach collaboration server',
  },
};

/**
 * Small status pill showing CRDT sync state for collaborative note editing.
 */
export function ConnectionStatus({ status, showLabel = true, className }: ConnectionStatusProps) {
  const config = STATUS_CONFIG[status];

  return (
    <span
      role="status"
      aria-live="polite"
      aria-label={config.ariaLabel}
      title={config.ariaLabel}
      className={cn('inline-flex items-center gap-1.5', className)}
    >
      <span
        className={cn('h-2 w-2 rounded-full flex-shrink-0', config.dotClass)}
        aria-hidden="true"
      />
      {showLabel && (
        <span className={cn('text-xs font-medium leading-none', config.textClass)}>
          {config.label}
        </span>
      )}
    </span>
  );
}
