'use client';

/**
 * useIssueSyncListener - Supabase Realtime subscription for linked issue changes
 * Displays sync indicator badge on blocks, auto-dismiss after 10s
 */
import { useCallback, useEffect, useState, useRef } from 'react';
import { supabase } from '@/lib/supabase';
import type { RealtimeChannel, RealtimePostgresChangesPayload } from '@supabase/supabase-js';

export interface IssueSyncEvent {
  issueId: string;
  blockId: string;
  changeType: 'update' | 'state_change' | 'assignment';
  timestamp: Date;
}

export interface UseIssueSyncListenerOptions {
  /** Note ID to subscribe for */
  noteId: string;
  /** Workspace ID */
  workspaceId: string;
  /** Block IDs with linked issues */
  linkedBlockIds: string[];
  /** Auto-dismiss delay in ms (default: 10000) */
  dismissDelayMs?: number;
  /** Enable subscription */
  enabled?: boolean;
  /** Callback when sync event occurs */
  onSync?: (event: IssueSyncEvent) => void;
}

export interface UseIssueSyncListenerReturn {
  /** Map of block IDs to their sync events */
  syncEvents: Map<string, IssueSyncEvent>;
  /** Whether subscription is active */
  isConnected: boolean;
  /** Clear sync event for a block */
  clearEvent: (blockId: string) => void;
  /** Clear all sync events */
  clearAllEvents: () => void;
}

/**
 * Hook for subscribing to issue changes linked to note blocks
 */
export function useIssueSyncListener({
  noteId,
  workspaceId,
  linkedBlockIds,
  dismissDelayMs = 10000,
  enabled = true,
  onSync,
}: UseIssueSyncListenerOptions): UseIssueSyncListenerReturn {
  const [syncEvents, setSyncEvents] = useState<Map<string, IssueSyncEvent>>(new Map());
  const [isConnected, setIsConnected] = useState(false);

  const channelRef = useRef<RealtimeChannel | null>(null);
  const dismissTimersRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());

  /**
   * Handle incoming issue change event
   */
  const handleIssueChange = useCallback(
    (payload: RealtimePostgresChangesPayload<Record<string, unknown>>) => {
      const newRecord = payload.new as Record<string, unknown> | null;
      const issueId = newRecord?.id as string | undefined;
      const sourceNoteId = newRecord?.source_note_id as string | undefined;
      const sourceBlockId = newRecord?.source_block_id as string | undefined;

      // Only process events for our note and linked blocks
      if (!issueId || sourceNoteId !== noteId || !sourceBlockId) {
        return;
      }

      if (!linkedBlockIds.includes(sourceBlockId)) {
        return;
      }

      // Determine change type
      let changeType: IssueSyncEvent['changeType'] = 'update';
      if (payload.old && payload.new) {
        if (
          (payload.old as Record<string, unknown>).state !==
          (payload.new as Record<string, unknown>).state
        ) {
          changeType = 'state_change';
        } else if (
          (payload.old as Record<string, unknown>).assignee_id !==
          (payload.new as Record<string, unknown>).assignee_id
        ) {
          changeType = 'assignment';
        }
      }

      const event: IssueSyncEvent = {
        issueId,
        blockId: sourceBlockId,
        changeType,
        timestamp: new Date(),
      };

      // Update state
      setSyncEvents((prev) => {
        const next = new Map(prev);
        next.set(sourceBlockId, event);
        return next;
      });

      // Trigger callback
      onSync?.(event);

      // Set auto-dismiss timer
      const existingTimer = dismissTimersRef.current.get(sourceBlockId);
      if (existingTimer) {
        clearTimeout(existingTimer);
      }

      const timer = setTimeout(() => {
        setSyncEvents((prev) => {
          const next = new Map(prev);
          next.delete(sourceBlockId);
          return next;
        });
        dismissTimersRef.current.delete(sourceBlockId);
      }, dismissDelayMs);

      dismissTimersRef.current.set(sourceBlockId, timer);
    },
    [noteId, linkedBlockIds, dismissDelayMs, onSync]
  );

  /**
   * Clear sync event for a specific block
   */
  const clearEvent = useCallback((blockId: string) => {
    const timer = dismissTimersRef.current.get(blockId);
    if (timer) {
      clearTimeout(timer);
      dismissTimersRef.current.delete(blockId);
    }
    setSyncEvents((prev) => {
      const next = new Map(prev);
      next.delete(blockId);
      return next;
    });
  }, []);

  /**
   * Clear all sync events
   */
  const clearAllEvents = useCallback(() => {
    dismissTimersRef.current.forEach((timer) => clearTimeout(timer));
    dismissTimersRef.current.clear();
    setSyncEvents(new Map());
  }, []);

  // Set up Supabase Realtime subscription
  useEffect(() => {
    if (!enabled || !noteId || !workspaceId || linkedBlockIds.length === 0) {
      return;
    }

    // Copy ref to variable for cleanup function
    const dismissTimers = dismissTimersRef.current;

    // Create channel for issue changes
    const channel = supabase
      .channel(`note-issues-${noteId}`)
      .on(
        'postgres_changes',
        {
          event: 'UPDATE',
          schema: 'public',
          table: 'issues',
          filter: `source_note_id=eq.${noteId}`,
        },
        handleIssueChange
      )
      .subscribe((status) => {
        setIsConnected(status === 'SUBSCRIBED');
      });

    channelRef.current = channel;

    return () => {
      // Cleanup subscription
      if (channelRef.current) {
        supabase.removeChannel(channelRef.current);
        channelRef.current = null;
      }
      setIsConnected(false);

      // Clear all timers using the captured variable
      dismissTimers.forEach((timer) => clearTimeout(timer));
      dismissTimers.clear();
    };
  }, [enabled, noteId, workspaceId, linkedBlockIds, handleIssueChange]);

  return {
    syncEvents,
    isConnected,
    clearEvent,
    clearAllEvents,
  };
}

/**
 * Sync indicator badge component helper
 */
export function getSyncIndicatorConfig(event: IssueSyncEvent | undefined): {
  visible: boolean;
  label: string;
  variant: 'default' | 'warning' | 'info';
} | null {
  if (!event) {
    return null;
  }

  switch (event.changeType) {
    case 'state_change':
      return {
        visible: true,
        label: 'Status changed',
        variant: 'info',
      };
    case 'assignment':
      return {
        visible: true,
        label: 'Assignee changed',
        variant: 'info',
      };
    case 'update':
    default:
      return {
        visible: true,
        label: 'Issue updated',
        variant: 'default',
      };
  }
}
