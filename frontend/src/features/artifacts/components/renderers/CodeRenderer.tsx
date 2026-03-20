'use client';

import * as React from 'react';
import { MarkdownContent } from '@/features/ai/ChatView/MessageList/MarkdownContent';

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
        <MarkdownContent content={wrappedContent} />
      </div>
    </div>
  );
}
