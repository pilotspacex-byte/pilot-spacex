/**
 * useVoiceRecording - Hook for voice input with ElevenLabs transcription.
 *
 * Supports two modes:
 * - 'live' (default): Streams PCM audio via AudioWorklet + WebSocket to the backend
 *   live STT proxy (ElevenLabs Scribe v2 Realtime). Partial transcripts appear as
 *   the user speaks; committed transcript is returned on stop.
 * - 'batch': Records audio via MediaRecorder, uploads to backend on stop, receives
 *   full transcript. Legacy mode kept for fallback/compatibility.
 */

import { useState, useRef, useCallback, useEffect, useMemo } from 'react';
import { toast } from 'sonner';
import { transcriptionApi } from '@/services/api/transcription';
import { useLiveTranscription } from './useLiveTranscription';

export type VoiceRecordingStatus = 'idle' | 'recording' | 'transcribing' | 'error';

export interface UseVoiceRecordingOptions {
  /** Workspace ID for transcription API call */
  workspaceId: string;
  /** Called with transcript text and audio URL when transcription succeeds */
  onTranscript: (text: string, audioUrl: string | null) => void;
  /** Optional ISO 639-1 language hint (batch mode only) */
  language?: string;
  /**
   * Recording mode:
   * - 'live' (default): WebSocket streaming with real-time partial transcripts.
   * - 'batch': MediaRecorder upload; full transcript on stop.
   */
  mode?: 'live' | 'batch';
  /** Called with each partial transcript in live mode (visual feedback only) */
  onPartialTranscript?: (text: string) => void;
}

export interface UseVoiceRecordingResult {
  status: VoiceRecordingStatus;
  /** Whether voice recording is supported in this browser */
  isSupported: boolean;
  /** Whether microphone permission has been permanently denied */
  isPermissionDenied: boolean;
  error: string | null;
  /** Elapsed recording time in milliseconds */
  durationMs: number;
  /** Real-time amplitude level during recording (0.0 to 1.0). Zero when not recording. */
  amplitudeLevel: number;
  startRecording: () => Promise<void>;
  stopRecording: () => void;
  cancelRecording: () => void;
}

/** Max recording duration: 5 minutes (matches 25MB backend limit at typical audio bitrate). */
const MAX_RECORDING_MS = 5 * 60 * 1000;

/** Check if browser supports MediaRecorder + getUserMedia. */
function checkBrowserSupport(): boolean {
  return (
    typeof navigator !== 'undefined' &&
    typeof navigator.mediaDevices !== 'undefined' &&
    typeof navigator.mediaDevices.getUserMedia === 'function' &&
    typeof MediaRecorder !== 'undefined'
  );
}

/**
 * Pick the best supported audio MIME type for MediaRecorder.
 */
function getSupportedMimeType(): string {
  if (typeof MediaRecorder === 'undefined') return '';
  const types = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/ogg'];
  for (const type of types) {
    if (MediaRecorder.isTypeSupported(type)) {
      return type;
    }
  }
  return '';
}

export function useVoiceRecording({
  workspaceId,
  onTranscript,
  language,
  mode = 'live',
  onPartialTranscript,
}: UseVoiceRecordingOptions): UseVoiceRecordingResult {
  const [status, setStatus] = useState<VoiceRecordingStatus>('idle');
  const [isPermissionDenied, setIsPermissionDenied] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [durationMs, setDurationMs] = useState(0);
  const [amplitudeLevel, setAmplitudeLevel] = useState(0);

  const isSupported = useMemo(() => checkBrowserSupport(), []);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const startTimeRef = useRef<number>(0);
  const maxDurationTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const errorResetTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Amplitude analysis refs
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationFrameRef = useRef<number | null>(null);

  /** Clear the 5-minute max-duration timer (shared by live stop/cancel/error/committed). */
  const clearMaxDurationTimer = useCallback(() => {
    if (maxDurationTimerRef.current) {
      clearTimeout(maxDurationTimerRef.current);
      maxDurationTimerRef.current = null;
    }
  }, []);

  // Live transcription hook (only used when mode === 'live')
  const liveTranscription = useLiveTranscription({
    workspaceId,
    onPartialTranscript: (text) => {
      onPartialTranscript?.(text);
    },
    onCommittedTranscript: (text) => {
      clearMaxDurationTimer();
      setStatus('idle');
      setDurationMs(0);
      onTranscript(text, null);
    },
    onError: (msg) => {
      clearMaxDurationTimer();
      setErrorWithAutoReset(msg);
    },
  });

  // Check microphone permission state on mount (non-blocking)
  useEffect(() => {
    if (!isSupported) return;

    let permStatus: PermissionStatus | null = null;
    const onChange = () => {
      if (permStatus) setIsPermissionDenied(permStatus.state === 'denied');
    };

    navigator.permissions
      ?.query({ name: 'microphone' as PermissionName })
      .then((result) => {
        permStatus = result;
        setIsPermissionDenied(result.state === 'denied');
        result.addEventListener('change', onChange);
      })
      .catch(() => {
        // permissions API not supported — we'll find out on getUserMedia
      });

    return () => {
      permStatus?.removeEventListener('change', onChange);
    };
  }, [isSupported]);

  /** Stop amplitude analysis loop. */
  const stopAmplitudeAnalysis = useCallback(() => {
    if (animationFrameRef.current !== null) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }
    if (audioContextRef.current) {
      void audioContextRef.current.close();
      audioContextRef.current = null;
    }
    analyserRef.current = null;
    setAmplitudeLevel(0);
  }, []);

  /** Stop all media tracks and clear timers. */
  const cleanupMedia = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (maxDurationTimerRef.current) {
      clearTimeout(maxDurationTimerRef.current);
      maxDurationTimerRef.current = null;
    }
    if (errorResetTimerRef.current) {
      clearTimeout(errorResetTimerRef.current);
      errorResetTimerRef.current = null;
    }
    stopAmplitudeAnalysis();
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    mediaRecorderRef.current = null;
    chunksRef.current = [];
  }, [stopAmplitudeAnalysis]);

  /** Auto-reset error state to idle after a delay. */
  const setErrorWithAutoReset = useCallback((msg: string) => {
    setError(msg);
    setStatus('error');
    if (errorResetTimerRef.current) {
      clearTimeout(errorResetTimerRef.current);
    }
    errorResetTimerRef.current = setTimeout(() => {
      setStatus('idle');
      setError(null);
      errorResetTimerRef.current = null;
    }, 3000);
  }, []);

  /** Cleanup on unmount. */
  useEffect(() => cleanupMedia, [cleanupMedia]);

  /** Start real-time amplitude measurement using AnalyserNode + requestAnimationFrame. */
  const startAmplitudeAnalysis = useCallback((stream: MediaStream) => {
    try {
      const audioCtx = new AudioContext();
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      const source = audioCtx.createMediaStreamSource(stream);
      source.connect(analyser);

      audioContextRef.current = audioCtx;
      analyserRef.current = analyser;

      const dataArray = new Uint8Array(analyser.frequencyBinCount);
      let lastReported = 0;

      const measureAmplitude = () => {
        if (!analyserRef.current) return;

        analyserRef.current.getByteTimeDomainData(dataArray);

        // Compute RMS amplitude normalized to 0-1 range
        let sumOfSquares = 0;
        for (const sample of dataArray) {
          const normalized = (sample - 128) / 128; // -1 to 1
          sumOfSquares += normalized * normalized;
        }
        const rms = Math.sqrt(sumOfSquares / dataArray.length);
        // Scale up slightly so typical speech reaches 0.5-0.8 range
        const scaled = Math.min(1, rms * 3);

        // Only trigger re-render when amplitude changes meaningfully
        if (Math.abs(scaled - lastReported) > 0.02) {
          lastReported = scaled;
          setAmplitudeLevel(scaled);
        }

        animationFrameRef.current = requestAnimationFrame(measureAmplitude);
      };

      animationFrameRef.current = requestAnimationFrame(measureAmplitude);
    } catch {
      // AudioContext not available — amplitude visualization silently disabled
    }
  }, []);

  /** Start recording timer (shared between live and batch modes). */
  const startDurationTimer = useCallback(() => {
    startTimeRef.current = Date.now();
    setDurationMs(0);
    timerRef.current = setInterval(() => {
      setDurationMs(Date.now() - startTimeRef.current);
    }, 1000);
  }, []);

  /** Stop and clear recording timer. */
  const stopDurationTimer = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const startRecording = useCallback(async () => {
    if (status !== 'idle') return;

    if (!isSupported) {
      toast.error('Voice recording not supported', {
        description: 'Your browser does not support audio recording. Try Chrome, Firefox, or Edge.',
      });
      return;
    }

    // ---------------------------------------------------------------- LIVE MODE
    if (mode === 'live') {
      try {
        const stream = await liveTranscription.startStreaming();
        if (!stream) return; // startStreaming already called onError

        // Run amplitude analysis on the live mic stream
        startAmplitudeAnalysis(stream);
        startDurationTimer();
        setStatus('recording');

        // Auto-stop at max duration
        maxDurationTimerRef.current = setTimeout(() => {
          toast.info('Recording stopped', { description: 'Maximum 5 minutes reached.' });
          liveTranscription.stopStreaming();
          stopDurationTimer();
          stopAmplitudeAnalysis();
          setStatus('idle');
        }, MAX_RECORDING_MS);
      } catch (err) {
        const isDenied =
          (err instanceof DOMException &&
            (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError')) ||
          (err instanceof Error && err.name === 'NotAllowedError');

        if (isDenied) {
          setIsPermissionDenied(true);
          toast.error('Microphone access denied', {
            description: 'Please allow microphone access in your browser settings.',
          });
          setErrorWithAutoReset('Microphone access denied');
        } else {
          const msg = err instanceof Error ? err.message : 'Could not start recording';
          toast.error('Could not start recording', { description: msg });
          setErrorWithAutoReset(msg);
        }
      }
      return;
    }

    // --------------------------------------------------------------- BATCH MODE
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
          setStatus('idle');
          onTranscript(result.text, result.audioUrl);
        } catch (err) {
          const msg =
            err instanceof Error ? err.message : 'Transcription failed — please try again';
          toast.error('Voice transcription failed', { description: msg });
          setErrorWithAutoReset(msg);
        }
      };

      // Start amplitude analysis
      startAmplitudeAnalysis(stream);
      startDurationTimer();
      setStatus('recording');

      // Start recording in 250ms chunks
      recorder.start(250);

      // Auto-stop at max duration to prevent oversized uploads
      maxDurationTimerRef.current = setTimeout(() => {
        if (mediaRecorderRef.current?.state === 'recording') {
          toast.info('Recording stopped', { description: 'Maximum 5 minutes reached.' });
          mediaRecorderRef.current.stop();
        }
      }, MAX_RECORDING_MS);
    } catch (err) {
      // Use DOMException.name for reliable cross-browser permission detection
      const isDenied =
        (err instanceof DOMException &&
          (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError')) ||
        (err instanceof Error && err.name === 'NotAllowedError');

      if (isDenied) {
        setIsPermissionDenied(true);
        toast.error('Microphone access denied', {
          description: 'Please allow microphone access in your browser settings.',
        });
        setErrorWithAutoReset('Microphone access denied');
      } else {
        const msg = err instanceof Error ? err.message : 'Could not start recording';
        toast.error('Could not start recording', { description: msg });
        setErrorWithAutoReset(msg);
      }
    }
  }, [
    status,
    isSupported,
    mode,
    workspaceId,
    language,
    onTranscript,
    cleanupMedia,
    setErrorWithAutoReset,
    startAmplitudeAnalysis,
    stopAmplitudeAnalysis,
    startDurationTimer,
    stopDurationTimer,
    liveTranscription,
  ]);

  const stopRecording = useCallback(() => {
    stopDurationTimer();
    clearMaxDurationTimer();

    if (mode === 'live') {
      liveTranscription.stopStreaming();
      stopAmplitudeAnalysis();
      // Status transitions to 'idle' when onCommittedTranscript fires
      return;
    }

    // Batch mode
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
      // onstop handler continues the flow
    }
  }, [mode, stopDurationTimer, clearMaxDurationTimer, stopAmplitudeAnalysis, liveTranscription]);

  const cancelRecording = useCallback(() => {
    stopDurationTimer();
    clearMaxDurationTimer();

    if (mode === 'live') {
      liveTranscription.cancelStreaming();
      stopAmplitudeAnalysis();
      setStatus('idle');
      setError(null);
      setDurationMs(0);
      return;
    }

    // Batch mode
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
  }, [
    mode,
    stopDurationTimer,
    clearMaxDurationTimer,
    stopAmplitudeAnalysis,
    liveTranscription,
    cleanupMedia,
  ]);

  return {
    status,
    isSupported,
    isPermissionDenied,
    error,
    durationMs,
    amplitudeLevel,
    startRecording,
    stopRecording,
    cancelRecording,
  };
}
