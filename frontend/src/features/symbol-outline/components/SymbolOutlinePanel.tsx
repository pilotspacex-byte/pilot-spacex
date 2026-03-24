'use client';

import { X } from 'lucide-react';
import { ScrollArea } from '@/components/ui/scroll-area';
import type { DocumentSymbol } from '../types';
import { SymbolTreeItem } from './SymbolTreeItem';

interface SymbolOutlinePanelProps {
  isOpen: boolean;
  onToggle: () => void;
  symbols: DocumentSymbol[];
  activeSymbolId: string | null;
  onSelectSymbol: (symbol: DocumentSymbol) => void;
}

/**
 * Collapsible right sidebar panel showing the document symbol outline.
 * Renders a recursive tree of headings, PM blocks, and code symbols
 * with click-to-navigate and active symbol highlighting.
 */
export function SymbolOutlinePanel({
  isOpen,
  onToggle,
  symbols,
  activeSymbolId,
  onSelectSymbol,
}: SymbolOutlinePanelProps) {
  if (!isOpen) return null;

  return (
    <div className="flex h-full w-[240px] shrink-0 flex-col border-l border-border-subtle bg-background-subtle">
      <div className="flex h-8 items-center justify-between border-b border-border-subtle px-3">
        <span className="text-xs font-medium text-muted-foreground">Outline</span>
        <button
          type="button"
          className="rounded p-0.5 text-muted-foreground hover:bg-accent hover:text-foreground"
          onClick={onToggle}
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>
      <ScrollArea className="flex-1">
        {symbols.length === 0 ? (
          <div className="flex items-center justify-center py-8 text-xs text-muted-foreground">
            No symbols found
          </div>
        ) : (
          <div className="p-1">
            {symbols.map((symbol) => (
              <SymbolTreeItem
                key={`${symbol.kind}-${symbol.line}-${symbol.name}`}
                symbol={symbol}
                activeSymbolId={activeSymbolId}
                depth={0}
                onSelect={onSelectSymbol}
              />
            ))}
          </div>
        )}
      </ScrollArea>
    </div>
  );
}
