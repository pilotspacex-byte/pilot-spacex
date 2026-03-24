'use client';

import { useCallback } from 'react';
import { CircleX, TriangleAlert, Info, Lightbulb } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Diagnostic } from '../language/diagnostics';

const SEVERITY_ICON: Record<Diagnostic['severity'], { icon: typeof CircleX; className: string }> = {
  error: { icon: CircleX, className: 'text-red-500' },
  warning: { icon: TriangleAlert, className: 'text-amber-500' },
  info: { icon: Info, className: 'text-blue-500' },
  hint: { icon: Lightbulb, className: 'text-gray-500' },
};

interface DiagnosticRowProps {
  diagnostic: Diagnostic;
  onClick: (uri: string, line: number, column: number) => void;
}

export function DiagnosticRow({ diagnostic, onClick }: DiagnosticRowProps) {
  const { icon: Icon, className: iconClass } = SEVERITY_ICON[diagnostic.severity];

  const handleClick = useCallback(() => {
    onClick(diagnostic.modelUri, diagnostic.startLineNumber, diagnostic.startColumn);
  }, [onClick, diagnostic.modelUri, diagnostic.startLineNumber, diagnostic.startColumn]);

  return (
    <button
      type="button"
      onClick={handleClick}
      className={cn(
        'flex items-center gap-2 h-7 px-3 w-full text-left',
        'text-xs font-mono',
        'hover:bg-accent/50 rounded',
        'transition-colors cursor-pointer'
      )}
    >
      <Icon className={cn('size-3.5 shrink-0', iconClass)} />
      <span className="text-muted-foreground shrink-0">
        {diagnostic.fileName}:{diagnostic.startLineNumber}
      </span>
      <span className="truncate">{diagnostic.message}</span>
    </button>
  );
}
