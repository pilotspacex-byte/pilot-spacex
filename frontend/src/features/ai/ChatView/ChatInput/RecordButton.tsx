/**
 * RecordButton - Mic button with pulsing animation for voice-to-text input.
 *
 * Integrates with useVoiceRecording hook to manage recording lifecycle.
 * Shows mic icon (idle), red pulsing stop icon (recording), and spinner (transcribing).
 */

import { Mic, Square, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
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

export function RecordButton({ workspaceId, onTranscript, disabled = false }: RecordButtonProps) {
  const { status, durationMs, startRecording, stopRecording } = useVoiceRecording({
    workspaceId,
    onTranscript,
  });

  const isRecording = status === 'recording';
  const isTranscribing = status === 'transcribing';

  const handleClick = () => {
    if (disabled) return;
    if (isRecording) {
      stopRecording();
    } else if (status === 'idle') {
      void startRecording();
    }
  };

  const tooltipLabel = isTranscribing
    ? 'Transcribing...'
    : isRecording
      ? `Stop recording (${formatDuration(durationMs)})`
      : 'Voice input';

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

            <Button
              type="button"
              variant="ghost"
              size="icon"
              className={[
                'h-6 w-6 relative',
                isRecording
                  ? 'text-red-500 hover:text-red-600'
                  : 'text-muted-foreground/60 hover:text-foreground',
              ].join(' ')}
              onClick={handleClick}
              disabled={disabled || isTranscribing}
              aria-label={tooltipLabel}
            >
              {isTranscribing ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : isRecording ? (
                <Square className="h-3.5 w-3.5 fill-current" />
              ) : (
                <Mic className="h-3.5 w-3.5" />
              )}
            </Button>
          </div>
        </TooltipTrigger>
        <TooltipContent side="top" className="text-xs">
          {tooltipLabel}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
