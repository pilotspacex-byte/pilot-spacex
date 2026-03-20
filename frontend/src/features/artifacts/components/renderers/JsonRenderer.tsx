'use client';

import { MarkdownContent } from '@/features/ai/ChatView/MessageList/MarkdownContent';

interface JsonRendererProps {
  content: string;
}

function formatJson(raw: string): string {
  try {
    return JSON.stringify(JSON.parse(raw), null, 2);
  } catch {
    return raw; // malformed JSON — render as-is
  }
}

export function JsonRenderer({ content }: JsonRendererProps) {
  const wrapped = '```json\n' + formatJson(content) + '\n```';

  return (
    <div className="p-6">
      <MarkdownContent content={wrapped} />
    </div>
  );
}
