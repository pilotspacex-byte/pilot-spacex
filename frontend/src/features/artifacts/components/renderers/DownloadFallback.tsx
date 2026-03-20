'use client';

import { Download, Link2Off, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface DownloadFallbackProps {
  filename: string;
  signedUrl: string;
  reason?: 'unsupported' | 'expired' | 'error';
}

const MESSAGES: Record<NonNullable<DownloadFallbackProps['reason']>, string> = {
  expired: 'This link has expired.',
  unsupported: 'Preview not available for this file type.',
  error: 'Failed to load file content.',
};

export function DownloadFallback({
  filename,
  signedUrl,
  reason = 'expired',
}: DownloadFallbackProps) {
  const message = MESSAGES[reason];

  return (
    <div className="flex flex-col items-center justify-center gap-4 p-8 text-center">
      <div className="rounded-full bg-muted p-4">
        {reason === 'expired' ? (
          <Link2Off className="size-8 text-muted-foreground" />
        ) : (
          <AlertCircle className="size-8 text-muted-foreground" />
        )}
      </div>
      <p className="text-sm text-muted-foreground">{message}</p>
      <Button asChild variant="outline">
        <a href={signedUrl} download={filename} target="_blank" rel="noopener noreferrer">
          <Download className="mr-2 size-4" />
          Download {filename}
        </a>
      </Button>
    </div>
  );
}
