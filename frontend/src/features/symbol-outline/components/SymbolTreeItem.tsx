'use client';

import { useState } from 'react';
import { ChevronRight, Hash, Blocks, FunctionSquare, Box, Variable, FileText } from 'lucide-react';
import type { DocumentSymbol, SymbolKind } from '../types';

const ICON_MAP: Record<SymbolKind, React.ComponentType<{ className?: string }>> = {
  heading: Hash,
  'pm-block': Blocks,
  function: FunctionSquare,
  class: Box,
  variable: Variable,
  interface: FileText,
  method: FunctionSquare,
  property: Variable,
};

interface SymbolTreeItemProps {
  symbol: DocumentSymbol;
  activeSymbolId: string | null;
  depth: number;
  onSelect: (symbol: DocumentSymbol) => void;
}

export function SymbolTreeItem({ symbol, activeSymbolId, depth, onSelect }: SymbolTreeItemProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const Icon = ICON_MAP[symbol.kind];
  const hasChildren = symbol.children.length > 0;
  const isActive = symbol.name === activeSymbolId;

  return (
    <div>
      <button
        type="button"
        className={`flex w-full items-center gap-1 rounded px-1 py-0.5 text-left text-xs hover:bg-accent ${
          isActive ? 'bg-accent' : ''
        }`}
        style={{ paddingLeft: `${depth * 12 + 4}px` }}
        onClick={() => onSelect(symbol)}
      >
        {hasChildren ? (
          <button
            type="button"
            className="shrink-0"
            onClick={(e) => {
              e.stopPropagation();
              setIsExpanded((prev) => !prev);
            }}
          >
            <ChevronRight
              className={`h-3 w-3 text-muted-foreground transition-transform ${
                isExpanded ? 'rotate-90' : ''
              }`}
            />
          </button>
        ) : (
          <span className="w-3 shrink-0" />
        )}
        <Icon className="h-4 w-4 shrink-0 text-muted-foreground" />
        <span className="truncate">{symbol.name}</span>
      </button>
      {hasChildren && isExpanded && (
        <div>
          {symbol.children.map((child) => (
            <SymbolTreeItem
              key={`${child.kind}-${child.line}-${child.name}`}
              symbol={child}
              activeSymbolId={activeSymbolId}
              depth={depth + 1}
              onSelect={onSelect}
            />
          ))}
        </div>
      )}
    </div>
  );
}
