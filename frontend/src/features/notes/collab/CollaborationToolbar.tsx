/**
 * CollaborationToolbar — Shows live collaborator count, presence dots, and
 * connection status for collaborative note editing.
 *
 * T-120: Collaboration toolbar (collaborator count badge, presence avatars,
 *        "N editing" label, ConnectionStatus indicator).
 *
 * Layout (left → right):
 *   [ConnectionStatus] [PresenceIndicator avatars] ["N editing" badge]
 *
 * Design: compact, sits in the note toolbar area.
 * Accessibility: group role, aria-label summarising all collaborators.
 *
 * @module features/notes/collab/CollaborationToolbar
 */
'use client';

import { cn } from '@/lib/utils';
import { PresenceIndicator } from './PresenceIndicator';
import { ConnectionStatus } from './ConnectionStatus';
import type { PeerState } from './useYjsProvider';
import type { ConnectionStatusValue } from './ConnectionStatus';

export interface CollaborationToolbarProps {
  /** All peers currently in the session (excludes current user) */
  peers: PeerState[];
  /** Current authenticated user id — excluded from peer display */
  currentUserId?: string;
  /** CRDT sync connection status */
  connectionStatus: ConnectionStatusValue;
  /** Called when a peer avatar is clicked — scroll editor to their cursor */
  onScrollToPeer?: (peerId: string) => void;
  /** Max peer avatars before +N overflow (default: 4) */
  maxVisible?: number;
  className?: string;
}

/**
 * Compact collaboration bar for the note toolbar.
 * Shows connection status, presence avatars, and editing count.
 * Returns null when no peers and connection is online (nothing to show).
 */
export function CollaborationToolbar({
  peers,
  currentUserId,
  connectionStatus,
  onScrollToPeer,
  maxVisible = 4,
  className,
}: CollaborationToolbarProps) {
  const visiblePeers = peers.filter((p) => p.id !== currentUserId);
  const humanCount = visiblePeers.filter((p) => !p.isAI).length;

  // Only hide when online AND no peers — show connection status when offline/error
  if (connectionStatus === 'online' && visiblePeers.length === 0) return null;

  const editingLabel =
    humanCount === 0 ? null : humanCount === 1 ? '1 editing' : `${humanCount} editing`;

  return (
    <div
      role="group"
      aria-label={
        humanCount > 0
          ? `${humanCount} collaborator${humanCount !== 1 ? 's' : ''} editing this note`
          : 'Collaboration status'
      }
      className={cn('flex items-center gap-2', className)}
    >
      {/* Connection status indicator */}
      <ConnectionStatus status={connectionStatus} showLabel={false} />

      {/* Peer presence avatars */}
      {visiblePeers.length > 0 && (
        <PresenceIndicator
          peers={visiblePeers}
          currentUserId={currentUserId}
          onScrollToPeer={onScrollToPeer}
          maxVisible={maxVisible}
        />
      )}

      {/* "N editing" label */}
      {editingLabel && (
        <span
          className="text-xs text-[var(--muted-foreground)] font-medium leading-none whitespace-nowrap"
          aria-hidden="true"
        >
          {editingLabel}
        </span>
      )}

      {/*
        COL-H3: Single live region — ConnectionStatus above already owns
        role="status" aria-live="polite" for connection-state announcements.
        Collaborator count is conveyed via the group aria-label on this container.
        No duplicate aria-live region here.
      */}
    </div>
  );
}
