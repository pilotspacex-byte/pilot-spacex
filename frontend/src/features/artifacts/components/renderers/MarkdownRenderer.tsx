'use client';

import { MarkdownContent } from '@/features/ai/ChatView/MessageList/MarkdownContent';

interface MarkdownRendererProps {
  content: string;
}

export function MarkdownRenderer({ content }: MarkdownRendererProps) {
  return (
    <div className="p-6">
      <MarkdownContent content={content} />
    </div>
  );
}
