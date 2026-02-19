/**
 * SupabaseYjsProvider — Yjs provider over Supabase Realtime channels.
 *
 * T-102: y-supabase provider integration (Realtime channel, awareness, auto-reconnect).
 *
 * Replaces y-websocket by using Supabase Realtime broadcast for document syncing
 * and presence (awareness). Each note gets its own Realtime channel:
 *   `yjs:note:{noteId}`
 *
 * Sync protocol:
 *   1. On connect: broadcast full Yjs state vector to peers
 *   2. Peers respond with their own diff (missing updates)
 *   3. Ongoing: each local Y.Doc update is broadcast as an incremental update
 *   4. Awareness: separate broadcast event `awareness` for cursor/presence data
 *
 * Auto-reconnect:
 *   - Supabase Realtime handles reconnection automatically
 *   - On reconnect, re-broadcast state vector to catch up on missed updates
 *
 * Limitations (flagged for production):
 *   - Supabase Realtime has 4MB message size limit — large docs need chunking
 *   - No server-side persistence: state is lost if all clients disconnect
 *     (mitigated by backend persistence via noteYjsStateApi)
 *
 * @module features/notes/collab/SupabaseYjsProvider
 */
import * as Y from 'yjs';
import * as encoding from 'lib0/encoding';
import * as decoding from 'lib0/decoding';
import * as syncProtocol from 'y-protocols/sync';
import * as awarenessProtocol from 'y-protocols/awareness';
import type { RealtimeChannel, SupabaseClient } from '@supabase/supabase-js';
import type { Awareness } from 'y-protocols/awareness';

export type ProviderStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

export interface SupabaseYjsProviderOptions {
  supabase: SupabaseClient;
  noteId: string;
  ydoc: Y.Doc;
  awareness: Awareness;
  /** User display info for awareness */
  user: { id: string; name: string; color: string };
  onStatusChange?: (status: ProviderStatus) => void;
  onError?: (error: Error) => void;
}

/** Message type tags for the Realtime broadcast */
const MSG_SYNC_STEP1 = 0;
const MSG_SYNC_STEP2 = 1;
const MSG_UPDATE = 2;
const MSG_AWARENESS = 3;

/**
 * Yjs provider backed by Supabase Realtime broadcast.
 *
 * Usage:
 * ```ts
 * const provider = new SupabaseYjsProvider({ supabase, noteId, ydoc, awareness, user });
 * await provider.connect();
 * // ... editor use ...
 * provider.destroy();
 * ```
 */
export class SupabaseYjsProvider {
  private channel: RealtimeChannel | null = null;
  private status: ProviderStatus = 'disconnected';
  private destroyed = false;

  private readonly supabase: SupabaseClient;
  private readonly noteId: string;
  private readonly ydoc: Y.Doc;
  private readonly awareness: Awareness;
  private readonly user: SupabaseYjsProviderOptions['user'];
  private readonly onStatusChange?: (status: ProviderStatus) => void;
  private readonly onError?: (error: Error) => void;

  // Cleanup refs
  private docUpdateHandler: ((update: Uint8Array, origin: unknown) => void) | null = null;
  private awarenessUpdateHandler:
    | ((
        changes: { added: number[]; updated: number[]; removed: number[] },
        origin: unknown
      ) => void)
    | null = null;

  constructor(options: SupabaseYjsProviderOptions) {
    this.supabase = options.supabase;
    this.noteId = options.noteId;
    this.ydoc = options.ydoc;
    this.awareness = options.awareness;
    this.user = options.user;
    this.onStatusChange = options.onStatusChange;
    this.onError = options.onError;
  }

  get channelName(): string {
    return `yjs:note:${this.noteId}`;
  }

  /** Connect to the Realtime channel and start syncing. */
  async connect(): Promise<void> {
    if (this.destroyed) return;
    this._setStatus('connecting');

    // Set local awareness state with user info
    this.awareness.setLocalStateField('user', this.user);

    this.channel = this.supabase.channel(this.channelName, {
      config: { broadcast: { self: false } },
    });

    // Handle incoming sync messages
    this.channel.on(
      'broadcast',
      { event: 'yjs' },
      ({ payload }: { payload: { msg: number[]; sender: string } }) => {
        if (payload.sender === this.user.id) return; // Ignore own messages
        this._handleMessage(new Uint8Array(payload.msg));
      }
    );

    // Handle presence changes (connection count)
    this.channel.on('presence', { event: 'sync' }, () => {
      // Presence sync — could be used to show participant count
    });

    await new Promise<void>((resolve, reject) => {
      this.channel!.subscribe((status, err) => {
        if (status === 'SUBSCRIBED') {
          this._setStatus('connected');
          this._broadcastSyncStep1();
          this._setupDocListener();
          this._setupAwarenessListener();
          resolve();
        } else if (status === 'CHANNEL_ERROR' || status === 'TIMED_OUT') {
          const error = new Error(`Realtime channel error: ${status}${err ? ` — ${err}` : ''}`);
          this._setStatus('error');
          this.onError?.(error);
          reject(error);
        } else if (status === 'CLOSED') {
          this._setStatus('disconnected');
        }
      });
    });
  }

  /** Gracefully disconnect and clean up listeners. */
  destroy(): void {
    if (this.destroyed) return;
    this.destroyed = true;

    // Remove local awareness state
    awarenessProtocol.removeAwarenessStates(this.awareness, [this.ydoc.clientID], 'destroy');

    // Remove doc update listener
    if (this.docUpdateHandler) {
      this.ydoc.off('update', this.docUpdateHandler);
      this.docUpdateHandler = null;
    }

    // Remove awareness listener
    if (this.awarenessUpdateHandler) {
      this.awareness.off('update', this.awarenessUpdateHandler);
      this.awarenessUpdateHandler = null;
    }

    // Unsubscribe Realtime channel
    if (this.channel) {
      this.supabase.removeChannel(this.channel);
      this.channel = null;
    }

    this._setStatus('disconnected');
  }

  // ──────────────────────────────────────────────────────────────────
  // Private: sync protocol
  // ──────────────────────────────────────────────────────────────────

  private _setStatus(status: ProviderStatus): void {
    if (this.status !== status) {
      this.status = status;
      this.onStatusChange?.(status);
    }
  }

  /** Step 1: broadcast our state vector so peers can send us their diff. */
  private _broadcastSyncStep1(): void {
    const encoder = encoding.createEncoder();
    encoding.writeVarUint(encoder, MSG_SYNC_STEP1);
    syncProtocol.writeSyncStep1(encoder, this.ydoc);
    this._broadcast(encoding.toUint8Array(encoder));
  }

  /** Handle incoming binary message. */
  private _handleMessage(msg: Uint8Array): void {
    const decoder = decoding.createDecoder(msg);
    const msgType = decoding.readVarUint(decoder);

    switch (msgType) {
      case MSG_SYNC_STEP1: {
        // Peer sent their state vector — send them our diff
        const encoder = encoding.createEncoder();
        encoding.writeVarUint(encoder, MSG_SYNC_STEP2);
        syncProtocol.writeSyncStep2(
          encoder,
          this.ydoc,
          decoding.readUint8Array(decoder, decoder.arr.length - decoder.pos)
        );
        this._broadcast(encoding.toUint8Array(encoder));
        break;
      }
      case MSG_SYNC_STEP2: {
        // Peer sent us their diff — apply it
        Y.applyUpdate(
          this.ydoc,
          decoding.readUint8Array(decoder, decoder.arr.length - decoder.pos)
        );
        break;
      }
      case MSG_UPDATE: {
        // Incremental update
        Y.applyUpdate(
          this.ydoc,
          decoding.readUint8Array(decoder, decoder.arr.length - decoder.pos)
        );
        break;
      }
      case MSG_AWARENESS: {
        // Awareness update from peer
        awarenessProtocol.applyAwarenessUpdate(
          this.awareness,
          decoding.readUint8Array(decoder, decoder.arr.length - decoder.pos),
          this
        );
        break;
      }
      default:
        break;
    }
  }

  /** Listen for local Y.Doc updates and broadcast them. */
  private _setupDocListener(): void {
    this.docUpdateHandler = (update: Uint8Array, origin: unknown) => {
      if (origin === this) return; // Don't re-broadcast our own applied updates
      const encoder = encoding.createEncoder();
      encoding.writeVarUint(encoder, MSG_UPDATE);
      encoding.writeUint8Array(encoder, update);
      this._broadcast(encoding.toUint8Array(encoder));
    };
    this.ydoc.on('update', this.docUpdateHandler);
  }

  /** Listen for awareness updates and broadcast them. */
  private _setupAwarenessListener(): void {
    this.awarenessUpdateHandler = ({ added, updated, removed }) => {
      const changedClients = added.concat(updated).concat(removed);
      const encoder = encoding.createEncoder();
      encoding.writeVarUint(encoder, MSG_AWARENESS);
      encoding.writeUint8Array(
        encoder,
        awarenessProtocol.encodeAwarenessUpdate(this.awareness, changedClients)
      );
      this._broadcast(encoding.toUint8Array(encoder));
    };
    this.awareness.on('update', this.awarenessUpdateHandler);
  }

  /** Broadcast a binary message via Realtime. */
  private _broadcast(msg: Uint8Array): void {
    if (!this.channel || this.status !== 'connected') return;
    this.channel.send({
      type: 'broadcast',
      event: 'yjs',
      payload: { msg: Array.from(msg), sender: this.user.id },
    });
  }
}
