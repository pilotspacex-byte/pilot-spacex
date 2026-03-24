'use client';

import * as React from 'react';
import dynamic from 'next/dynamic';

const MarkdownContent = dynamic(
  () =>
    import('@/features/ai/ChatView/MessageList/MarkdownContent').then((m) => ({
      default: m.MarkdownContent,
    })),
  {
    loading: () => <CodeRendererSkeleton />,
  }
);

const SKELETON_WIDTHS = [72, 88, 55, 91, 63, 80, 48, 85, 70, 94];

function CodeRendererSkeleton() {
  return (
    <div className="p-6 space-y-2 animate-pulse">
      <div className="rounded-lg border border-border bg-muted/30 p-4 space-y-2">
        <div className="h-3 w-20 rounded bg-muted" />
        {SKELETON_WIDTHS.map((w, i) => (
          <div key={i} className="h-3 rounded bg-muted/70" style={{ width: `${w}%` }} />
        ))}
      </div>
    </div>
  );
}

interface CodeRendererProps {
  content: string;
  language: string;
}

export function CodeRenderer({ content, language }: CodeRendererProps) {
  const [copied, setCopied] = React.useState(false);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard API may be unavailable in insecure contexts
    }
  }

  const wrappedContent = '```' + language + '\n' + content + '\n```';

  return (
    <div className="relative flex flex-col h-full">
      <div className="absolute top-3 right-3 z-10">
        <button
          onClick={handleCopy}
          aria-label={copied ? 'Copied to clipboard' : 'Copy code'}
          className="text-xs px-2 py-1 rounded border border-border bg-background text-muted-foreground hover:text-foreground transition-colors"
        >
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>
      <div className="flex-1 overflow-auto p-6">
        <React.Suspense fallback={<CodeRendererSkeleton />}>
          <MarkdownContent content={wrappedContent} />
        </React.Suspense>
      </div>
    </div>
  );
}
