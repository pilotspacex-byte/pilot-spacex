/**
 * RecordButton - Mic button with amplitude visualization for live voice-to-text input.
 *
 * Integrates with useVoiceRecording hook (live mode) to manage recording lifecycle.
 * Shows mic icon (idle), recording pill with timer + amplitude bars + cancel (recording),
 * and spinner (transcribing). Requires ElevenLabs API key — prompts user to open settings if missing.
 *
 * In live mode: partial transcripts appear in the recording pill while user speaks.
 * Committed transcript is passed to ChatInput via the existing onTranscript callback.
 */

import { useEffect } from 'react';
import { observer } from 'mobx-react-lite';
import { Mic, MicOff, Square, Loader2, X } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { useStore } from '@/stores';
import { useSettingsModal } from '@/features/settings/settings-modal-context';
import { useVoiceRecording } from '../hooks/useVoiceRecording';

interface RecordButtonProps {
  /** Workspace ID for transcription API calls */
  workspaceId: string;
  /** Called with transcript text and audio URL when recording+transcription completes */
  onTranscript: (text: string, audioUrl: string | null) => void;
  /** Called with partial transcript text while user speaks (live mode only) */
  onPartialTranscript?: (text: string) => void;
  /** Whether the button is disabled (e.g. during AI streaming) */
  disabled?: boolean;
}

/** Format milliseconds as M:SS for elapsed recording display. */
function formatDuration(ms: number): string {
  const seconds = Math.floor(ms / 1000);
  const minutes = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${minutes}:${secs.toString().padStart(2, '0')}`;
}

/**
 * Audio waveform visualization — 7 bars with sine-wave phase offsets
 * that respond to real amplitude, creating an organic flowing wave.
 * Each bar has a base height (idle breathing) + amplitude-driven height.
 */
const WAVE_BARS = 7;
const WAVE_PHASE_OFFSETS = [0, 0.9, 1.8, 2.7, 1.8, 0.9, 0]; // symmetric wave shape

export const RecordButton = observer(function RecordButton({
  workspaceId,
  onTranscript,
  onPartialTranscript,
  disabled = false,
}: RecordButtonProps) {
  const { aiStore } = useStore();
  const { openSettings } = useSettingsModal();

  // Lazy-load AI settings if not yet loaded so sttConfigured reflects the real state.
  // Without this, sttConfigured defaults to false until the user visits Settings page.
  useEffect(() => {
    if (workspaceId && !aiStore.settings.settings && !aiStore.settings.isLoading) {
      aiStore.settings.loadSettings(workspaceId);
    }
  }, [workspaceId, aiStore.settings]);

  const isSttConfigured = aiStore.settings.sttConfigured;

  const {
    status,
    isSupported,
    isPermissionDenied,
    durationMs,
    amplitudeLevel,
    startRecording,
    stopRecording,
    cancelRecording,
  } = useVoiceRecording({
    workspaceId,
    mode: 'live',
    onTranscript: (text, audioUrl) => {
      onTranscript(text, audioUrl);
    },
    onPartialTranscript: (text) => {
      onPartialTranscript?.(text);
    },
  });

  const isRecording = status === 'recording';
  const isTranscribing = status === 'transcribing';
  const isUnavailable = !isSupported || isPermissionDenied;

  const handleClick = () => {
    if (disabled || isUnavailable) return;

    // Gate: require ElevenLabs API key before recording
    if (!isSttConfigured && !isRecording) {
      toast.error('ElevenLabs API key required', {
        description: 'Set up your voice provider in Settings → AI Providers.',
        action: {
          label: 'Open Settings',
          onClick: () => openSettings('ai-providers'),
        },
      });
      return;
    }

    if (isRecording) {
      stopRecording();
    } else if (status === 'idle') {
      void startRecording();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape' && isRecording) {
      e.preventDefault();
      cancelRecording();
    }
  };

  let tooltipLabel = 'Voice input';
  if (!isSupported) {
    tooltipLabel = 'Voice recording not supported in this browser';
  } else if (isPermissionDenied) {
    tooltipLabel = 'Microphone access denied — check browser settings';
  } else if (!isSttConfigured) {
    tooltipLabel = 'Voice input — set up ElevenLabs API key in Settings';
  } else if (isTranscribing) {
    tooltipLabel = 'Transcribing...';
  } else if (isRecording) {
    tooltipLabel = `Stop recording (${formatDuration(durationMs)})`;
  }

  // Screen reader announcement for status transitions
  let liveAnnouncement = '';
  if (isRecording) {
    liveAnnouncement = 'Recording started. Press Escape to cancel.';
  } else if (isTranscribing) {
    liveAnnouncement = 'Transcribing audio...';
  }

  // During recording: show an expanded pill with cancel + amplitude + timer + stop
  if (isRecording) {
    return (
      <TooltipProvider>
        <div
          className="flex items-center gap-1 bg-red-50 dark:bg-red-950/30 border border-red-200/60 dark:border-red-800/40 rounded-full px-1.5 py-0.5"
          onKeyDown={handleKeyDown}
          tabIndex={-1}
        >
          {/* Screen reader live announcements */}
          <span aria-live="assertive" className="sr-only">
            {liveAnnouncement}
          </span>

          {/* Cancel button */}
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="h-5 w-5 text-red-400 hover:text-red-600 hover:bg-red-100/60 dark:hover:bg-red-900/40 rounded-full flex-shrink-0"
                onClick={(e) => {
                  e.stopPropagation();
                  cancelRecording();
                }}
                aria-label="Cancel recording"
              >
                <X className="h-3 w-3" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="top" className="text-xs">
              Cancel recording
            </TooltipContent>
          </Tooltip>

          {/* Audio waveform — 7 bars with sine-wave phase offsets */}
          <div className="flex items-end gap-[2px] h-4" aria-hidden="true">
            {Array.from({ length: WAVE_BARS }, (_, i) => {
              // Base idle height (20-30%) + amplitude-driven height with wave phase
              const phase = WAVE_PHASE_OFFSETS[i] ?? 0;
              const wave = Math.sin(phase + Date.now() * 0.003) * 0.15 + 0.85;
              const amplitudeFactor = amplitudeLevel * wave;
              const height = Math.max(15, 15 + amplitudeFactor * 85);
              return (
                <div
                  key={i}
                  className="w-[2.5px] rounded-full"
                  style={{
                    height: `${Math.min(100, height)}%`,
                    backgroundColor: `color-mix(in oklch, oklch(0.637 0.177 25.331) ${50 + amplitudeFactor * 50}%, oklch(0.637 0.177 25.331 / 0.4))`,
                    transition: 'height 120ms cubic-bezier(0.22, 1, 0.36, 1)',
                  }}
                />
              );
            })}
          </div>

          {/* Elapsed time */}
          <span
            className="text-xs text-red-500 font-mono tabular-nums leading-none px-0.5"
            aria-label={`Recording time: ${formatDuration(durationMs)}`}
          >
            {formatDuration(durationMs)}
          </span>

          {/* Stop button */}
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                data-testid="record-button"
                className="h-6 w-6 text-red-500 hover:text-red-600 hover:bg-red-100/60 dark:hover:bg-red-900/40 rounded-full flex-shrink-0"
                onClick={handleClick}
                aria-label={tooltipLabel}
              >
                <Square className="h-3.5 w-3.5 fill-current" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="top" className="text-xs">
              Stop recording
            </TooltipContent>
          </Tooltip>
        </div>
      </TooltipProvider>
    );
  }

  // Default (idle / transcribing / unavailable) state
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div className="relative flex items-center justify-center">
            {/* Screen reader live announcements */}
            <span aria-live="assertive" className="sr-only">
              {liveAnnouncement}
            </span>

            <Button
              type="button"
              variant="ghost"
              size="icon"
              data-testid="record-button"
              className={[
                'h-6 w-6 relative',
                'text-muted-foreground/60 hover:text-foreground',
              ].join(' ')}
              onClick={handleClick}
              onKeyDown={handleKeyDown}
              disabled={disabled || isTranscribing || isUnavailable}
              aria-label={tooltipLabel}
            >
              {isTranscribing && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
              {!isTranscribing && isUnavailable && <MicOff className="h-3.5 w-3.5" />}
              {!isTranscribing && !isUnavailable && <Mic className="h-3.5 w-3.5" />}
            </Button>
          </div>
        </TooltipTrigger>
        <TooltipContent side="top" className="text-xs">
          {!isSttConfigured && isSupported && !isPermissionDenied ? (
            <button
              type="button"
              className="underline decoration-dotted cursor-pointer hover:text-foreground transition-colors"
              onClick={() => openSettings('ai-providers')}
            >
              Set up ElevenLabs API key
            </button>
          ) : (
            tooltipLabel
          )}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
});
