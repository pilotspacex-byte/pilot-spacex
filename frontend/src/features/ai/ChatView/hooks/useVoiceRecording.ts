/**
 * useVoiceRecording - Hook for MediaRecorder-based voice input with ElevenLabs transcription.
 *
 * Manages microphone permission, audio recording lifecycle, and transcription flow.
 * Transcription is proxied through the backend to ElevenLabs STT with result caching.
 */

import { useState, useRef, useCallback, useEffect, useMemo } from 'react';
import { toast } from 'sonner';
import { transcriptionApi } from '@/services/api/transcription';

export type VoiceRecordingStatus = 'idle' | 'recording' | 'transcribing' | 'error';

export interface UseVoiceRecordingOptions {
  /** Workspace ID for transcription API call */
  workspaceId: string;
  /** Called with transcript text and audio URL when transcription succeeds */
  onTranscript: (text: string, audioUrl: string | null) => void;
  /** Optional ISO 639-1 language hint */
  language?: string;
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

  const startRecording = useCallback(async () => {
    if (status !== 'idle') return;

    if (!isSupported) {
      toast.error('Voice recording not supported', {
        description: 'Your browser does not support audio recording. Try Chrome, Firefox, or Edge.',
      });
      return;
    }

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

      // Start recording and duration timer
      recorder.start(250); // collect chunks every 250ms
      startTimeRef.current = Date.now();
      setDurationMs(0);
      timerRef.current = setInterval(() => {
        setDurationMs(Date.now() - startTimeRef.current);
      }, 1000);
      setStatus('recording');

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
      } else {
        const msg = err instanceof Error ? err.message : 'Could not start recording';
        toast.error('Could not start recording', { description: msg });
      }
      const msg = err instanceof Error ? err.message : 'Microphone access denied';
      setErrorWithAutoReset(msg);
    }
  }, [
    status,
    isSupported,
    workspaceId,
    language,
    onTranscript,
    cleanupMedia,
    setErrorWithAutoReset,
    startAmplitudeAnalysis,
  ]);

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
