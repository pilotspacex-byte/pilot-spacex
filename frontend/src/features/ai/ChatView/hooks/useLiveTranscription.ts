/**
 * useLiveTranscription - React hook for live speech-to-text via WebSocket proxy.
 *
 * Manages the AudioWorklet capture pipeline and WebSocket connection to the
 * backend live STT proxy. Audio is captured at 16kHz PCM mono via an
 * AudioWorklet, sent as base64-encoded chunks to the backend, which proxies
 * them to ElevenLabs Scribe v2 Realtime.
 *
 * Security: JWT token is sent as a query param (browsers cannot set WS headers).
 * The ElevenLabs API key never leaves the server.
 *
 * WebSocket protocol:
 *   Client -> Server: { message_type: "input_audio_chunk", audio_base_64: "...", commit: false, sample_rate: 16000 }
 *   Client -> Server: { message_type: "input_audio_chunk", audio_base_64: "", commit: true, sample_rate: 16000 }
 *   Server -> Client: { type: "partial", text: "..." }
 *   Server -> Client: { type: "committed", text: "..." }
 *   Server -> Client: { type: "error", message: "..." }
 */

import { useCallback, useEffect, useRef, useState } from 'react';

export interface UseLiveTranscriptionOptions {
  /** Workspace ID for workspace membership check and API key lookup */
  workspaceId: string;
  /** Called with each partial transcript as user speaks */
  onPartialTranscript: (text: string) => void;
  /** Called with the final committed transcript when user stops */
  onCommittedTranscript: (text: string) => void;
  /** Called on error (auth failure, key not configured, WS error) */
  onError: (error: string) => void;
}

export interface UseLiveTranscriptionResult {
  /** Whether the WebSocket connection is open */
  isConnected: boolean;
  /**
   * Start mic capture + open WS connection. Returns the MediaStream for
   * amplitude analysis in the parent hook.
   */
  startStreaming: () => Promise<MediaStream | null>;
  /** Send commit message and wait for final transcript via onCommittedTranscript */
  stopStreaming: () => void;
  /** Close WS without committing. No transcript callback fires. */
  cancelStreaming: () => void;
}

// 8 KB chunk size for safe String.fromCharCode.apply() calls
const BASE64_CHUNK_SIZE = 8192;

/**
 * Convert an ArrayBuffer (Int16 PCM) to a base64 string without overflowing
 * the call stack. Splits into 8 KB chunks to avoid stack overflow on large buffers.
 */
function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.length; i += BASE64_CHUNK_SIZE) {
    const chunk = bytes.subarray(i, Math.min(i + BASE64_CHUNK_SIZE, bytes.length));
    binary += String.fromCharCode(...chunk);
  }
  return btoa(binary);
}

/**
 * Determine the WebSocket base URL.
 *
 * Next.js rewrites do NOT proxy WebSocket connections. When NEXT_PUBLIC_API_URL
 * is set (e.g. http://localhost:8000/api/v1), derive the WS host from it.
 * In production, derive the WS host from the current window location
 * (assumes a reverse proxy forwards /api/v1/ to the backend).
 */
function getWsBaseUrl(): string {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? '';

  // Explicit API URL set — derive WS URL from it (works for any host/port)
  if (apiUrl) {
    try {
      const parsed = new URL(apiUrl);
      const proto = parsed.protocol === 'https:' ? 'wss:' : 'ws:';
      return `${proto}//${parsed.host}`;
    } catch {
      // Relative URL (e.g. "/api/v1") — fall through to window-based detection
    }
  }

  // Production: derive WS protocol from current page protocol
  if (typeof window !== 'undefined') {
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${proto}//${window.location.host}`;
  }

  return 'ws://localhost:8000';
}

export function useLiveTranscription({
  workspaceId,
  onPartialTranscript,
  onCommittedTranscript,
  onError,
}: UseLiveTranscriptionOptions): UseLiveTranscriptionResult {
  const [isConnected, setIsConnected] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const workletNodeRef = useRef<AudioWorkletNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const flushTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Keep callbacks in refs to avoid stale closures in WS event handlers
  const onPartialRef = useRef(onPartialTranscript);
  const onCommittedRef = useRef(onCommittedTranscript);
  const onErrorRef = useRef(onError);
  useEffect(() => {
    onPartialRef.current = onPartialTranscript;
  }, [onPartialTranscript]);
  useEffect(() => {
    onCommittedRef.current = onCommittedTranscript;
  }, [onCommittedTranscript]);
  useEffect(() => {
    onErrorRef.current = onError;
  }, [onError]);

  /** Tear down AudioContext, worklet, mic stream, and flush timer. */
  const cleanupAudio = useCallback(() => {
    if (flushTimeoutRef.current) {
      clearTimeout(flushTimeoutRef.current);
      flushTimeoutRef.current = null;
    }
    if (workletNodeRef.current) {
      workletNodeRef.current.port.onmessage = null;
      workletNodeRef.current.disconnect();
      workletNodeRef.current = null;
    }
    if (audioContextRef.current) {
      void audioContextRef.current.close();
      audioContextRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
  }, []);

  /** Close the WebSocket (if open) and clean up audio. */
  const closeAll = useCallback(() => {
    if (wsRef.current) {
      const ws = wsRef.current;
      wsRef.current = null;
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        ws.close();
      }
    }
    setIsConnected(false);
    cleanupAudio();
  }, [cleanupAudio]);

  /** Cleanup on unmount */
  useEffect(() => {
    return () => {
      closeAll();
    };
  }, [closeAll]);

  const startStreaming = useCallback(async (): Promise<MediaStream | null> => {
    // Get auth token
    const { getAuthProviderSync } = await import('@/services/auth/providers');
    const token = await getAuthProviderSync().getToken();
    if (!token) {
      onErrorRef.current('Not authenticated');
      return null;
    }

    // Build WS URL with auth and workspace params
    const wsBase = getWsBaseUrl();
    const url = `${wsBase}/api/v1/ai/transcribe/stream?token=${encodeURIComponent(token)}&workspace_id=${encodeURIComponent(workspaceId)}`;

    // Open WebSocket
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
    };

    ws.onmessage = (event: MessageEvent<string>) => {
      let msg: { type: string; text?: string; message?: string };
      try {
        msg = JSON.parse(event.data) as { type: string; text?: string; message?: string };
      } catch {
        return;
      }

      if (msg.type === 'partial') {
        onPartialRef.current(msg.text ?? '');
      } else if (msg.type === 'committed') {
        onCommittedRef.current(msg.text ?? '');
        closeAll();
      } else if (msg.type === 'error') {
        onErrorRef.current(msg.message ?? 'Unknown error from transcription service');
        closeAll();
      }
    };

    ws.onerror = () => {
      onErrorRef.current('WebSocket connection error');
      closeAll();
    };

    ws.onclose = (event: CloseEvent) => {
      setIsConnected(false);
      if (event.code === 4001) {
        onErrorRef.current('Authentication failed — please refresh and try again');
      } else if (event.code === 4003) {
        onErrorRef.current('Workspace access denied');
      } else if (event.code === 4022) {
        onErrorRef.current('ElevenLabs API key not configured for this workspace');
      }
      cleanupAudio();
      wsRef.current = null;
    };

    // Request mic access
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Could not access microphone';
      onErrorRef.current(msg);
      closeAll();
      return null;
    }
    streamRef.current = stream;

    // Set up AudioContext + AudioWorklet
    try {
      const audioCtx = new AudioContext();
      audioContextRef.current = audioCtx;

      await audioCtx.audioWorklet.addModule('/worklets/pcm-processor.js');
      const workletNode = new AudioWorkletNode(audioCtx, 'pcm-processor');
      workletNodeRef.current = workletNode;

      // Forward PCM chunks from worklet to WS.
      // Handles both regular ArrayBuffer audio and the {type:'flushed'} signal
      // sent after a flush command (see stopStreaming).
      workletNode.port.onmessage = (e: MessageEvent) => {
        const ws = wsRef.current;
        if (!ws || ws.readyState !== WebSocket.OPEN) return;

        if (e.data instanceof ArrayBuffer) {
          // Regular 1s chunk or flush tail — forward to backend
          const base64 = arrayBufferToBase64(e.data);
          ws.send(
            JSON.stringify({
              message_type: 'input_audio_chunk',
              audio_base_64: base64,
              commit: false,
              sample_rate: 16000,
            })
          );
        } else if (e.data?.type === 'flushed') {
          // Worklet finished flushing — all audio sent, now commit
          if (flushTimeoutRef.current) {
            clearTimeout(flushTimeoutRef.current);
            flushTimeoutRef.current = null;
          }
          ws.send(
            JSON.stringify({
              message_type: 'input_audio_chunk',
              audio_base_64: '',
              commit: true,
              sample_rate: 16000,
            })
          );
          cleanupAudio();
        }
      };

      // Connect mic -> worklet (worklet drives PCM to WS; no audio output needed)
      const source = audioCtx.createMediaStreamSource(stream);
      source.connect(workletNode);
      workletNode.connect(audioCtx.destination);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'AudioWorklet setup failed';
      onErrorRef.current(msg);
      closeAll();
      return null;
    }

    return stream;
  }, [workspaceId, closeAll, cleanupAudio]);

  const stopStreaming = useCallback(() => {
    const workletNode = workletNodeRef.current;
    const ws = wsRef.current;

    if (workletNode && ws && ws.readyState === WebSocket.OPEN) {
      // Ask worklet to flush its partial buffer. The onmessage handler
      // receives the tail audio, then the 'flushed' signal which triggers
      // the commit + cleanupAudio. This ensures the user's last word is
      // not silently dropped.
      workletNode.port.postMessage({ type: 'flush' });

      // Safety: if flush response doesn't arrive within 500ms, commit anyway.
      // cleanupAudio() clears this timeout if the flush arrives first.
      flushTimeoutRef.current = setTimeout(() => {
        flushTimeoutRef.current = null;
        const wsCurrent = wsRef.current;
        if (wsCurrent && wsCurrent.readyState === WebSocket.OPEN) {
          wsCurrent.send(
            JSON.stringify({
              message_type: 'input_audio_chunk',
              audio_base_64: '',
              commit: true,
              sample_rate: 16000,
            })
          );
        }
        cleanupAudio();
      }, 500);
    } else {
      // No worklet or WS not open — commit directly
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(
          JSON.stringify({
            message_type: 'input_audio_chunk',
            audio_base_64: '',
            commit: true,
            sample_rate: 16000,
          })
        );
      }
      cleanupAudio();
    }
    // WS stays open until committed_transcript arrives (handled in ws.onmessage)
  }, [cleanupAudio]);

  const cancelStreaming = useCallback(() => {
    // Close WS without committing — no transcript callback fires
    closeAll();
  }, [closeAll]);

  return {
    isConnected,
    startStreaming,
    stopStreaming,
    cancelStreaming,
  };
}

export default useLiveTranscription;
