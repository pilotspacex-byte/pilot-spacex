'use client';

/**
 * LinkBody — minimal external-URL preview inside the PeekDrawer.
 *
 * We intentionally do not attempt to iframe-embed arbitrary URLs — many sites
 * (Notion, Linear, Google, GitHub) set X-Frame-Options: DENY, and embedding
 * foreign origins inside the app shell is a phishing vector. Instead we show
 * the parsed hostname + full URL + a clear "open in new tab" affordance.
 */

import { ExternalLink, Link as LinkIcon } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface LinkBodyProps {
  url: string;
}

function safeHostname(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '');
  } catch {
    return url;
  }
}

function safeHref(url: string): string | null {
  try {
    const parsed = new URL(url);
    if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') return null;
    return parsed.toString();
  } catch {
    return null;
  }
}

export function LinkBody({ url }: LinkBodyProps) {
  const href = safeHref(url);
  const hostname = safeHostname(url);

  return (
    <div className="flex flex-col items-center justify-center h-full px-6 py-16 text-center gap-5">
      <div
        className="flex h-14 w-14 items-center justify-center rounded-2xl"
        style={{
          backgroundColor: `color-mix(in oklab, var(--color-artifact-link) 14%, transparent)`,
          color: 'var(--color-artifact-link)',
        }}
        aria-hidden="true"
      >
        <LinkIcon className="h-6 w-6" />
      </div>
      <div className="space-y-1 max-w-md">
        <p className="text-lg font-semibold text-foreground">{hostname}</p>
        <p className="text-xs text-muted-foreground break-all">{url}</p>
      </div>
      {href ? (
        <Button asChild>
          <a href={href} target="_blank" rel="noopener noreferrer">
            <ExternalLink className="h-4 w-4 mr-2" aria-hidden="true" />
            Open in new tab
          </a>
        </Button>
      ) : (
        <p className="text-xs text-destructive">
          This link uses an unsupported protocol and cannot be opened safely.
        </p>
      )}
    </div>
  );
}
