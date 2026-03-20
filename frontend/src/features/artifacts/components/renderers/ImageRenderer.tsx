'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';
import { DownloadFallback } from './DownloadFallback';

interface ImageRendererProps {
  signedUrl: string;
  filename: string;
}

export function ImageRenderer({ signedUrl, filename }: ImageRendererProps) {
  const [isZoomed, setIsZoomed] = React.useState(false);
  const [imgError, setImgError] = React.useState(false);

  if (imgError) {
    return <DownloadFallback filename={filename} signedUrl={signedUrl} reason="expired" />;
  }

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label={isZoomed ? 'Zoom out' : 'Zoom in'}
      className={cn(
        'flex items-center justify-center cursor-zoom-in overflow-auto p-4',
        isZoomed && 'cursor-zoom-out'
      )}
      onClick={() => setIsZoomed((z) => !z)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          setIsZoomed((z) => !z);
        }
      }}
    >
      <img
        src={signedUrl}
        alt={filename}
        onError={() => setImgError(true)}
        className={cn(
          'rounded-md transition-all duration-200',
          isZoomed ? 'max-w-none w-auto' : 'max-w-full max-h-full object-contain'
        )}
      />
    </div>
  );
}
