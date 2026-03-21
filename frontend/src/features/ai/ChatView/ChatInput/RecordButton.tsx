/**
 * RecordButton — Compact mic button for live voice-to-text.
 *
 * Idle: mic icon. Recording: pulsing red ring + stop icon + timer.
 * Transcribing: spinner. All states stay in the same button footprint.
 */

import { useEffect } from 'react';
import { observer } from 'mobx-react-lite';
import { Mic, MicOff, Square, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { useStore } from '@/stores';
import { useSettingsModal } from '@/features/settings/settings-modal-context';
import { useVoiceRecording } from '../hooks/useVoiceRecording';

interface RecordButtonProps {
  workspaceId: string;
  onTranscript: (text: string, audioUrl: string | null) => void;
  onPartialTranscript?: (text: string) => void;
  disabled?: boolean;
}

function formatDuration(ms: number): string {
  const seconds = Math.floor(ms / 1000);
  const minutes = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${minutes}:${secs.toString().padStart(2, '0')}`;
}

export const RecordButton = observer(function RecordButton({
  workspaceId,
  onTranscript,
  onPartialTranscript,
  disabled = false,
}: RecordButtonProps) {
  const { aiStore } = useStore();
  const { openSettings } = useSettingsModal();

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
    startRecording,
    stopRecording,
    cancelRecording,
  } = useVoiceRecording({
    workspaceId,
    mode: 'live',
    onTranscript: (text, audioUrl) => onTranscript(text, audioUrl),
    onPartialTranscript: (text) => onPartialTranscript?.(text),
  });

  const isRecording = status === 'recording';
  const isTranscribing = status === 'transcribing';
  const isUnavailable = !isSupported || isPermissionDenied;

  const handleClick = () => {
    if (disabled || isUnavailable) return;

    if (!isSttConfigured && !isRecording) {
      toast.error('ElevenLabs API key required', {
        description: 'Set up your voice provider in Settings → AI Providers.',
        action: { label: 'Open Settings', onClick: () => openSettings('ai-providers') },
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
  if (!isSupported) tooltipLabel = 'Voice recording not supported in this browser';
  else if (isPermissionDenied) tooltipLabel = 'Microphone access denied';
  else if (!isSttConfigured) tooltipLabel = 'Set up ElevenLabs API key in Settings';
  else if (isTranscribing) tooltipLabel = 'Transcribing...';
  else if (isRecording) tooltipLabel = 'Click to stop · Esc to cancel';

  // Recording: show stop button with pulsing ring + timer
  if (isRecording) {
    return (
      <div className="flex items-center gap-1" onKeyDown={handleKeyDown} tabIndex={-1}>
        <span aria-live="assertive" className="sr-only">
          Recording. Press Escape to cancel.
        </span>

        {/* Timer */}
        <span className="text-[11px] text-destructive/70 font-mono tabular-nums leading-none select-none">
          {formatDuration(durationMs)}
        </span>

        {/* Stop button with pulsing ring */}
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                type="button"
                data-testid="record-button"
                className="relative h-7 w-7 flex items-center justify-center rounded-full text-destructive transition-colors hover:bg-destructive/10"
                onClick={handleClick}
                aria-label={tooltipLabel}
              >
                {/* Pulsing ring */}
                <span className="absolute inset-0 rounded-full border-2 border-destructive/60 animate-[record-pulse_1.5s_ease-in-out_infinite]" />
                <Square className="h-3 w-3 fill-current relative z-10" />
              </button>
            </TooltipTrigger>
            <TooltipContent side="top" className="text-xs">
              Click to stop · Esc to cancel
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>

        {/* Inline CSS for pulse animation */}
        <style>{`
          @keyframes record-pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.4; transform: scale(1.25); }
          }
        `}</style>
      </div>
    );
  }

  // Default: mic icon (idle / transcribing / unavailable)
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            data-testid="record-button"
            className="h-6 w-6 text-muted-foreground/60 hover:text-foreground"
            onClick={handleClick}
            onKeyDown={handleKeyDown}
            disabled={disabled || isTranscribing || isUnavailable}
            aria-label={tooltipLabel}
          >
            {isTranscribing && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
            {!isTranscribing && isUnavailable && <MicOff className="h-3.5 w-3.5" />}
            {!isTranscribing && !isUnavailable && <Mic className="h-3.5 w-3.5" />}
          </Button>
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
