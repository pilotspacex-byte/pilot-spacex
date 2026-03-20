/**
 * useVoiceRecording - Hook for MediaRecorder-based voice input with ElevenLabs transcription.
 *
 * Manages microphone permission, audio recording lifecycle, and transcription flow.
 * Transcription is proxied through the backend to ElevenLabs STT with result caching.
 */

import { useState, useRef, useCallback, useEffect } from 'react';
import { toast } from 'sonner';
import { transcriptionApi } from '@/services/api/transcription';

export type VoiceRecordingStatus = 'idle' | 'recording' | 'transcribing' | 'error';

export interface UseVoiceRecordingOptions {
  /** Workspace ID for transcription API call */
  workspaceId: string;
  /** Called with transcript text when transcription succeeds */
  onTranscript: (text: string) => void;
  /** Optional ISO 639-1 language hint */
  language?: string;
}

export interface UseVoiceRecordingResult {
  status: VoiceRecordingStatus;
  transcript: string | null;
  error: string | null;
  /** Elapsed recording time in milliseconds */
  durationMs: number;
  startRecording: () => Promise<void>;
  stopRecording: () => void;
  cancelRecording: () => void;
}

/**
 * Pick the best supported audio MIME type for MediaRecorder.
 */
function getSupportedMimeType(): string {
  const types = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/ogg'];
  for (const type of types) {
    if (typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported(type)) {
      return type;
    }
  }
  return '';
}

export function useVoiceRecording({
  workspaceId,
  onTranscript,
  language,
}: UseVoiceRecordingOptions): UseVoiceRecordingResult {
  const [status, setStatus] = useState<VoiceRecordingStatus>('idle');
  const [transcript, setTranscript] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [durationMs, setDurationMs] = useState(0);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const startTimeRef = useRef<number>(0);

  /** Stop all media tracks and clear the timer. */
  const cleanupMedia = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    mediaRecorderRef.current = null;
    chunksRef.current = [];
  }, []);

  /** Cleanup on unmount. */
  useEffect(() => {
    return () => {
      cleanupMedia();
    };
  }, [cleanupMedia]);

  const startRecording = useCallback(async () => {
    if (status !== 'idle') return;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      chunksRef.current = [];

      const mimeType = getSupportedMimeType();
      const options: MediaRecorderOptions = mimeType ? { mimeType } : {};
      const recorder = new MediaRecorder(stream, options);
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };

      recorder.onstop = async () => {
        const chunks = chunksRef.current;
        cleanupMedia();

        if (chunks.length === 0) {
          setStatus('idle');
          return;
        }

        const blob = new Blob(chunks, { type: mimeType || 'audio/webm' });
        setStatus('transcribing');

        try {
          const result = await transcriptionApi.transcribe(blob, workspaceId, language);
          setTranscript(result.text);
          setStatus('idle');
          onTranscript(result.text);
        } catch (err) {
          const msg =
            err instanceof Error ? err.message : 'Transcription failed — please try again';
          setError(msg);
          setStatus('error');
          toast.error('Voice transcription failed', { description: msg });
          // Auto-reset to idle after showing error
          setTimeout(() => {
            setStatus('idle');
            setError(null);
          }, 3000);
        }
      };

      // Start recording and duration timer
      recorder.start(250); // collect chunks every 250ms
      startTimeRef.current = Date.now();
      setDurationMs(0);
      timerRef.current = setInterval(() => {
        setDurationMs(Date.now() - startTimeRef.current);
      }, 100);
      setStatus('recording');
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Microphone access denied';
      const isPermissionDenied =
        msg.toLowerCase().includes('permission') ||
        msg.toLowerCase().includes('denied') ||
        msg.toLowerCase().includes('notallowed');

      if (isPermissionDenied) {
        toast.error('Microphone access denied', {
          description: 'Please allow microphone access in your browser settings.',
        });
      } else {
        toast.error('Could not start recording', { description: msg });
      }
      setError(msg);
      setStatus('error');
      setTimeout(() => {
        setStatus('idle');
        setError(null);
      }, 3000);
    }
  }, [status, workspaceId, language, onTranscript, cleanupMedia]);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      mediaRecorderRef.current.stop();
      // onstop handler continues the flow
    }
  }, []);

  const cancelRecording = useCallback(() => {
    if (mediaRecorderRef.current) {
      // Override onstop to discard chunks
      mediaRecorderRef.current.onstop = null;
      if (mediaRecorderRef.current.state === 'recording') {
        mediaRecorderRef.current.stop();
      }
    }
    cleanupMedia();
    setStatus('idle');
    setError(null);
    setDurationMs(0);
  }, [cleanupMedia]);

  return {
    status,
    transcript,
    error,
    durationMs,
    startRecording,
    stopRecording,
    cancelRecording,
  };
}
