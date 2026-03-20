/**
 * RecordButton - Mic button with pulsing animation for voice-to-text input.
 *
 * Integrates with useVoiceRecording hook to manage recording lifecycle.
 * Shows mic icon (idle), red pulsing stop icon (recording), and spinner (transcribing).
 * Requires ElevenLabs API key to be configured — prompts user to open settings if missing.
 */

import { observer } from 'mobx-react-lite';
import { Mic, MicOff, Square, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { useStore } from '@/stores';
import { useSettingsModal } from '@/features/settings/settings-modal-context';
import { useVoiceRecording } from '../hooks/useVoiceRecording';

interface RecordButtonProps {
  /** Workspace ID for transcription API calls */
  workspaceId: string;
  /** Called with transcript text when recording+transcription completes */
  onTranscript: (text: string) => void;
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

export const RecordButton = observer(function RecordButton({
  workspaceId,
  onTranscript,
  disabled = false,
}: RecordButtonProps) {
  const { aiStore } = useStore();
  const { openSettings } = useSettingsModal();
  const isSttConfigured = aiStore.settings.sttConfigured;

  const {
    status,
    isSupported,
    isPermissionDenied,
    durationMs,
    startRecording,
    stopRecording,
    cancelRecording,
  } = useVoiceRecording({
    workspaceId,
    onTranscript,
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

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div className="relative flex items-center justify-center">
            {/* Pulsing ring shown during recording */}
            {isRecording && (
              <span
                className="absolute inset-0 rounded-full animate-ping bg-red-500/25"
                aria-hidden="true"
              />
            )}

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
                isRecording
                  ? 'text-red-500 hover:text-red-600'
                  : 'text-muted-foreground/60 hover:text-foreground',
              ].join(' ')}
              onClick={handleClick}
              onKeyDown={handleKeyDown}
              disabled={disabled || isTranscribing || isUnavailable}
              aria-label={tooltipLabel}
            >
              {isTranscribing && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
              {isRecording && <Square className="h-3.5 w-3.5 fill-current" />}
              {!isTranscribing && !isRecording && isUnavailable && (
                <MicOff className="h-3.5 w-3.5" />
              )}
              {!isTranscribing && !isRecording && !isUnavailable && <Mic className="h-3.5 w-3.5" />}
            </Button>
          </div>
        </TooltipTrigger>
        <TooltipContent side="top" className="text-xs">
          {tooltipLabel}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
});
