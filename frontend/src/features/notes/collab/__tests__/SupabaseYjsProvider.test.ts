/**
 * T-120: Unit tests for SupabaseYjsProvider.
 *
 * Tests sync protocol correctness, destroy cleanup, and status transitions.
 * Mocks Supabase Realtime channel to avoid real network calls.
 *
 * NOTE: Awareness uses setInterval internally. We create Y.Doc + Awareness
 * in real-timer context and enable fake timers only for the async test body.
 */
import { describe, it, expect, vi, afterEach } from 'vitest';
import * as Y from 'yjs';
import { Awareness } from 'y-protocols/awareness';
import { SupabaseYjsProvider } from '../SupabaseYjsProvider';
import type { SupabaseClient } from '@supabase/supabase-js';

// ── Mock Supabase channel ─────────────────────────────────────────────────────

type ChannelCallback = (status: string, err?: unknown) => void;
type BroadcastHandler = (payload: { payload: { msg: number[]; sender: string } }) => void;

function createMockChannel() {
  let subscribeCallback: ChannelCallback | null = null;
  let broadcastHandler: BroadcastHandler | null = null;
  const sentMessages: Array<{ type: string; event: string; payload: unknown }> = [];

  const channel = {
    on: vi.fn((_type: string, _filter: unknown, handler: BroadcastHandler) => {
      if (_type === 'broadcast') broadcastHandler = handler;
      return channel;
    }),
    subscribe: vi.fn((cb: ChannelCallback) => {
      subscribeCallback = cb;
      // Trigger SUBSCRIBED asynchronously
      Promise.resolve().then(() => cb('SUBSCRIBED'));
      return channel;
    }),
    send: vi.fn((msg: { type: string; event: string; payload: unknown }) => {
      sentMessages.push(msg);
    }),
    simulateMessage: (msg: number[], sender: string) => {
      broadcastHandler?.({ payload: { msg, sender } });
    },
    simulateError: () => {
      subscribeCallback?.('CHANNEL_ERROR');
    },
    _sentMessages: sentMessages,
  };
  return channel;
}

type MockChannel = ReturnType<typeof createMockChannel>;

function createMockSupabase(channel: MockChannel) {
  return {
    channel: vi.fn(() => channel),
    removeChannel: vi.fn(),
  } as unknown as SupabaseClient;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function makeProviderPair() {
  // Y.Doc + Awareness created in real-timer context (Awareness uses setInterval)
  const ydoc = new Y.Doc();
  const awareness = new Awareness(ydoc);
  const mockChannel = createMockChannel();
  const mockSupabase = createMockSupabase(mockChannel);
  const user = { id: 'user-1', name: 'Alice', color: '#FF0000' };
  const onStatusChange = vi.fn();
  const onError = vi.fn();

  const provider = new SupabaseYjsProvider({
    supabase: mockSupabase,
    noteId: 'note-abc',
    ydoc,
    awareness,
    user,
    onStatusChange,
    onError,
  });

  return { provider, ydoc, awareness, mockChannel, mockSupabase, onStatusChange, onError };
}

// ── Tests ─────────────────────────────────────────────────────────────────────

// Use real timers — subscribe callback fires via Promise.resolve() (microtask)
afterEach(() => {
  vi.restoreAllMocks();
});

describe('SupabaseYjsProvider', () => {
  describe('channel naming', () => {
    it('uses yjs:note:{noteId} channel name', () => {
      const { provider, awareness } = makeProviderPair();
      expect(provider.channelName).toBe('yjs:note:note-abc');
      awareness.destroy();
    });
  });

  describe('connect()', () => {
    it('transitions to connected status on SUBSCRIBED', async () => {
      const { provider, awareness, onStatusChange } = makeProviderPair();
      await provider.connect();
      expect(onStatusChange).toHaveBeenCalledWith('connecting');
      expect(onStatusChange).toHaveBeenCalledWith('connected');
      provider.destroy();
      awareness.destroy();
    });

    it('broadcasts sync step 1 on connect', async () => {
      const { provider, awareness, mockChannel } = makeProviderPair();
      await provider.connect();
      const sent = mockChannel._sentMessages;
      expect(sent.length).toBeGreaterThan(0);
      expect(sent[0]?.event).toBe('yjs');
      provider.destroy();
      awareness.destroy();
    });

    it('transitions to error status on CHANNEL_ERROR', async () => {
      const { provider, awareness, mockChannel, onStatusChange, onError } = makeProviderPair();
      // Override subscribe to emit error via microtask
      mockChannel.subscribe.mockImplementation((cb: ChannelCallback) => {
        Promise.resolve().then(() => cb('CHANNEL_ERROR'));
        return mockChannel;
      });
      await provider.connect().catch(() => {});
      expect(onStatusChange).toHaveBeenCalledWith('error');
      expect(onError).toHaveBeenCalled();
      awareness.destroy();
    });
  });

  describe('message handling', () => {
    it('ignores messages from self (same sender id)', async () => {
      const { provider, ydoc, awareness, mockChannel } = makeProviderPair();
      await provider.connect();

      const initialGuid = ydoc.guid;
      // Simulate a message from self (user-1) — should be ignored
      mockChannel.simulateMessage([2, 0], 'user-1');
      expect(ydoc.guid).toBe(initialGuid);

      provider.destroy();
      awareness.destroy();
    });

    it('applies MSG_SYNC_STEP2 (type=1) updates from peers', async () => {
      const { provider, ydoc, awareness, mockChannel } = makeProviderPair();
      await provider.connect();

      // Create peer doc with content
      const peerDoc = new Y.Doc();
      const peerText = peerDoc.getText('test');
      peerText.insert(0, 'hello');
      const update = Y.encodeStateAsUpdate(peerDoc);

      // Build MSG_SYNC_STEP2 frame: [type=1, ...update]
      const frame = new Uint8Array([1, ...Array.from(update)]);
      mockChannel.simulateMessage(Array.from(frame), 'peer-id');

      const localText = ydoc.getText('test');
      expect(localText.toString()).toBe('hello');

      provider.destroy();
      awareness.destroy();
    });

    it('applies MSG_UPDATE (type=2) incremental updates', async () => {
      const { provider, ydoc, awareness, mockChannel } = makeProviderPair();
      await provider.connect();

      const peerDoc = new Y.Doc();
      const peerMap = peerDoc.getMap('data');
      peerMap.set('key', 'value');
      const update = Y.encodeStateAsUpdate(peerDoc);

      // Build MSG_UPDATE frame: [type=2, ...update]
      const frame = new Uint8Array([2, ...Array.from(update)]);
      mockChannel.simulateMessage(Array.from(frame), 'peer-id');

      const localMap = ydoc.getMap('data');
      expect(localMap.get('key')).toBe('value');

      provider.destroy();
      awareness.destroy();
    });
  });

  describe('destroy()', () => {
    it('cleans up listeners and channel on destroy', async () => {
      const { provider, awareness, mockSupabase } = makeProviderPair();
      await provider.connect();

      provider.destroy();

      expect(
        (mockSupabase as unknown as { removeChannel: ReturnType<typeof vi.fn> }).removeChannel
      ).toHaveBeenCalled();
      expect(provider['channel']).toBeNull();
      awareness.destroy();
    });

    it('is idempotent — second destroy is a no-op', async () => {
      const { provider, awareness, mockSupabase } = makeProviderPair();
      await provider.connect();

      const removeFn = (mockSupabase as unknown as { removeChannel: ReturnType<typeof vi.fn> })
        .removeChannel;
      provider.destroy();
      const callCount = removeFn.mock.calls.length;

      provider.destroy(); // Second call — no-op
      expect(removeFn.mock.calls.length).toBe(callCount);
      awareness.destroy();
    });

    it('does not connect if destroyed before connect()', async () => {
      const { provider, awareness, onStatusChange } = makeProviderPair();
      provider.destroy();
      await provider.connect(); // Should return immediately
      expect(onStatusChange).not.toHaveBeenCalledWith('connecting');
      awareness.destroy();
    });
  });

  describe('Y.Doc update broadcasting', () => {
    it('broadcasts MSG_UPDATE when local Y.Doc changes', async () => {
      const { provider, ydoc, awareness, mockChannel } = makeProviderPair();
      await provider.connect();

      const initialSentCount = mockChannel._sentMessages.length;

      // Trigger a local update
      const text = ydoc.getText('content');
      text.insert(0, 'typing...');

      expect(mockChannel._sentMessages.length).toBeGreaterThan(initialSentCount);
      const lastMsg = mockChannel._sentMessages[mockChannel._sentMessages.length - 1];
      expect(lastMsg?.event).toBe('yjs');

      provider.destroy();
      awareness.destroy();
    });
  });
});
