/**
 * AudioPlaybackPill - Compact inline audio player for voice recording review.
 *
 * Rendered in two contexts:
 * 1. ChatInput: After transcription, before sending — shows play/pause, progress, duration + X dismiss.
 * 2. UserMessage: In chat history for voice-transcribed messages — no dismiss button.
 *
 * Design: rounded-full pill matching AttachmentChip style, warm neutral palette.
 * Audio URLs are signed with 1-hour expiry — expired links show a graceful fallback.
 */

import { useRef, useState, useEffect, useCallback } from 'react';
import { Play, Pause, X } from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';

interface AudioPlaybackPillProps {
  /** Signed URL for the recorded audio (1-hour TTL) */
  audioUrl: string;
  /** Known duration in seconds (from transcription API), used as fallback before metadata loads */
  durationSeconds?: number | null;
  className?: string;
  /** If provided, renders a dismiss X button at the end of the pill */
  onRemove?: () => void;
}

/** Format seconds as M:SS display string. */
function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

export function AudioPlaybackPill({
  audioUrl,
  durationSeconds,
  className,
  onRemove,
}: AudioPlaybackPillProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState<number>(durationSeconds ?? 0);
  const [hasError, setHasError] = useState(false);

  // Sync duration from metadata once audio element loads it
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const handleLoadedMetadata = () => {
      if (isFinite(audio.duration)) {
        setDuration(audio.duration);
      }
    };

    const handleTimeUpdate = () => {
      setCurrentTime(audio.currentTime);
    };

    const handleEnded = () => {
      setIsPlaying(false);
      setCurrentTime(0);
      audio.currentTime = 0;
    };

    const handleError = () => {
      setHasError(true);
      setIsPlaying(false);
    };

    audio.addEventListener('loadedmetadata', handleLoadedMetadata);
    audio.addEventListener('timeupdate', handleTimeUpdate);
    audio.addEventListener('ended', handleEnded);
    audio.addEventListener('error', handleError);

    return () => {
      audio.pause();
      audio.removeEventListener('loadedmetadata', handleLoadedMetadata);
      audio.removeEventListener('timeupdate', handleTimeUpdate);
      audio.removeEventListener('ended', handleEnded);
      audio.removeEventListener('error', handleError);
    };
  }, [audioUrl]);

  const handlePlayPause = useCallback(async () => {
    const audio = audioRef.current;
    if (!audio) return;

    if (isPlaying) {
      audio.pause();
      setIsPlaying(false);
    } else {
      try {
        await audio.play();
        setIsPlaying(true);
      } catch (err) {
        // Signed URL may have expired
        const isExpired =
          err instanceof DOMException &&
          (err.name === 'NotSupportedError' || err.name === 'NotAllowedError');
        if (isExpired || hasError) {
          toast.error('Audio link expired — re-record to play again', {
            duration: 4000,
          });
        } else {
          toast.error('Could not play audio', {
            description: err instanceof Error ? err.message : 'Unknown error',
          });
        }
        setHasError(true);
      }
    }
  }, [isPlaying, hasError]);

  const progressPercent = duration > 0 ? (currentTime / duration) * 100 : 0;

  if (hasError) {
    return (
      <span
        className={cn(
          'inline-flex items-center h-7 px-2.5 gap-1.5',
          'bg-muted/50 border border-border/40 rounded-full',
          'text-[10px] text-muted-foreground/60',
          className
        )}
      >
        Audio unavailable
        {onRemove && (
          <button
            type="button"
            onClick={onRemove}
            className="ml-0.5 text-muted-foreground/50 hover:text-muted-foreground transition-colors"
            aria-label="Dismiss audio"
          >
            <X className="h-3 w-3" />
          </button>
        )}
      </span>
    );
  }

  return (
    <span
      className={cn(
        'inline-flex items-center h-7 px-2.5 gap-1.5',
        'bg-muted/50 border border-border/40 rounded-full',
        'hover:bg-muted/80 transition-colors',
        className
      )}
    >
      {/* Hidden audio element */}
      <audio ref={audioRef} src={audioUrl} preload="metadata" />

      {/* Play/pause button */}
      <button
        type="button"
        onClick={() => void handlePlayPause()}
        className="flex items-center justify-center text-foreground/70 hover:text-foreground transition-colors flex-shrink-0"
        aria-label={isPlaying ? 'Pause recorded audio' : 'Play recorded audio'}
      >
        {isPlaying ? <Pause className="h-3 w-3" /> : <Play className="h-3 w-3" />}
      </button>

      {/* Progress bar */}
      <span
        className="h-0.5 w-16 bg-muted-foreground/20 rounded-full overflow-hidden flex-shrink-0"
        aria-hidden="true"
      >
        <span
          className="bg-primary h-full block transition-[width]"
          style={{ width: `${progressPercent}%` }}
        />
      </span>

      {/* Duration display */}
      <span className="text-[10px] font-mono tabular-nums text-muted-foreground leading-none flex-shrink-0">
        {duration > 0
          ? `${formatTime(currentTime)} / ${formatTime(duration)}`
          : formatTime(currentTime)}
      </span>

      {/* Dismiss button — only in pre-send context */}
      {onRemove && (
        <button
          type="button"
          onClick={onRemove}
          className="flex-shrink-0 text-muted-foreground/50 hover:text-muted-foreground transition-colors ml-0.5"
          aria-label="Remove audio"
        >
          <X className="h-3 w-3" />
        </button>
      )}
    </span>
  );
}
