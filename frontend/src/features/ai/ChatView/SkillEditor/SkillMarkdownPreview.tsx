/**
 * SkillMarkdownPreview — Renders SKILL.md content with monospace formatting.
 * Simple presentation component, no external syntax highlighter needed.
 *
 * @module features/ai/ChatView/SkillEditor/SkillMarkdownPreview
 */
'use client';

import { useMemo } from 'react';
import { cn } from '@/lib/utils';

interface SkillMarkdownPreviewProps {
  content: string;
  className?: string;
}

export function SkillMarkdownPreview({ content, className }: SkillMarkdownPreviewProps) {
  const lines = useMemo(() => content.split('\n'), [content]);

  return (
    <div className={cn('overflow-auto max-h-[calc(100vh-200px)]', className)}>
      <pre className="text-sm font-mono whitespace-pre-wrap bg-muted rounded-lg p-4">
        {lines.map((line, i) => (
          <div key={i} className="flex">
            <span className="inline-block w-8 shrink-0 text-right pr-3 text-muted-foreground/50 select-none text-xs leading-relaxed">
              {i + 1}
            </span>
            <span className="flex-1 leading-relaxed">{line || '\u00A0'}</span>
          </div>
        ))}
      </pre>
    </div>
  );
}
