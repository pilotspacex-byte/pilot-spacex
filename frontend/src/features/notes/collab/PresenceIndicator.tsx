/**
 * PresenceIndicator — Shows who is currently editing a note.
 *
 * T-121: User presence via Yjs awareness (cursors, names, colors).
 * T-122: AI skill presence (awareness entry for active skills).
 * T-123: Presence indicator UI (avatars + AI icons, click to scroll, +N overflow).
 *
 * Spec: specs/016-note-collaboration/spec.md §M7
 *
 * Layout: avatar stack (rightmost = most recent), +N overflow badge,
 *         AI skill slots at right-most position with bot icon.
 *
 * Accessibility: ARIA label listing all peer names, title tooltip per avatar.
 * Click: scrolls to the peer's cursor in the editor (via awareness clientID).
 *
 * @module features/notes/collab/PresenceIndicator
 */
'use client';

import { Bot } from 'lucide-react';
import type { PeerState } from './useYjsProvider';

export interface PresenceIndicatorProps {
  peers: PeerState[];
  /** Current user (excluded from peer list) */
  currentUserId?: string;
  /** Called when a human avatar is clicked — editor should scroll to cursor */
  onScrollToPeer?: (peerId: string) => void;
  /** Max avatars to show before +N overflow */
  maxVisible?: number;
  className?: string;
}

/** Generate initials from display name (up to 2 chars) */
function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/);
  const first = parts[0] ?? '';
  if (parts.length === 1) return first.slice(0, 2).toUpperCase();
  const last = parts[parts.length - 1] ?? '';
  return ((first[0] ?? '') + (last[0] ?? '')).toUpperCase();
}

/**
 * Stack of presence avatars for real-time collaborative note editing.
 * Human peers show color-coded initials; AI peers show a bot icon.
 */
export function PresenceIndicator({
  peers,
  currentUserId,
  onScrollToPeer,
  maxVisible = 5,
  className = '',
}: PresenceIndicatorProps) {
  const filtered = peers.filter((p) => p.id !== currentUserId);
  const humanPeers = filtered.filter((p) => !p.isAI);
  const aiPeers = filtered.filter((p) => p.isAI);

  // Visible humans: show up to maxVisible - (aiPeers.length capped at 1 slot)
  const aiSlot = aiPeers.length > 0 ? 1 : 0;
  const humanSlots = Math.max(0, maxVisible - aiSlot);
  const visibleHumans = humanPeers.slice(0, humanSlots);
  const overflowCount = humanPeers.length - visibleHumans.length;

  if (filtered.length === 0) return null;

  const allNames = filtered.map((p) => p.name).join(', ');

  return (
    <div
      className={`flex items-center gap-0.5 ${className}`}
      aria-label={`${filtered.length} people editing: ${allNames}`}
      role="group"
    >
      {/* Human avatars */}
      {visibleHumans.map((peer) => (
        <button
          key={peer.id}
          type="button"
          title={peer.name}
          aria-label={`${peer.name} is editing — click to scroll to cursor`}
          onClick={() => onScrollToPeer?.(peer.id)}
          className="relative -ml-1 first:ml-0 focus:z-10 focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-[var(--primary)] rounded-full transition-transform hover:scale-110"
          style={{ color: peer.color }}
        >
          <span
            className="flex h-7 w-7 items-center justify-center rounded-full text-[10px] font-semibold text-white ring-2 ring-white select-none"
            style={{ backgroundColor: peer.color }}
          >
            {getInitials(peer.name)}
          </span>
        </button>
      ))}

      {/* Overflow badge */}
      {overflowCount > 0 && (
        <span
          className="-ml-1 flex h-7 w-7 items-center justify-center rounded-full bg-[var(--muted)] ring-2 ring-white text-[10px] font-semibold text-[var(--muted-foreground)] select-none"
          aria-label={`${overflowCount} more people editing`}
          title={humanPeers
            .slice(humanSlots)
            .map((p) => p.name)
            .join(', ')}
        >
          +{overflowCount}
        </span>
      )}

      {/* AI presence slots */}
      {aiPeers.length > 0 && (
        <span
          className="-ml-1 flex h-7 w-7 items-center justify-center rounded-full bg-[var(--ai)] ring-2 ring-white text-white"
          title={
            aiPeers.length === 1
              ? `${aiPeers[0]?.name ?? 'AI'} (AI) is active`
              : `${aiPeers.length} AI skills active: ${aiPeers.map((a) => a.name).join(', ')}`
          }
          aria-label={`${aiPeers.length} AI skill${aiPeers.length !== 1 ? 's' : ''} active`}
        >
          <Bot className="h-3.5 w-3.5" aria-hidden />
          {aiPeers.length > 1 && (
            <span className="absolute -top-0.5 -right-0.5 flex h-3.5 w-3.5 items-center justify-center rounded-full bg-[var(--primary)] text-[8px] font-bold text-white ring-1 ring-white">
              {aiPeers.length}
            </span>
          )}
        </span>
      )}
    </div>
  );
}
