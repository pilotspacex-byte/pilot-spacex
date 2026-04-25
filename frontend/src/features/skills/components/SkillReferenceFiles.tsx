/**
 * SkillReferenceFiles — collapsible list of a skill's reference files.
 *
 * Phase 91 Plan 04, Task 2. Default-open when there are 1–5 references
 * (UI-SPEC §Surface 2 — keeps small skills calm); collapsed by default
 * for >5 to avoid pushing the markdown body off-screen on smaller laptops.
 *
 * Each row dispatches an `onSelect(path)` callback to the parent (the
 * detail page), which is responsible for opening the peek drawer via
 * `useArtifactPeekState().openSkillFilePeek`.
 *
 * Empty state renders the UI-SPEC verbatim copy.
 */
'use client';

import * as React from 'react';
import {
  ChevronRight,
  Code2,
  File as FileIcon,
  FileText,
  Image as ImageIcon,
  Table as TableIcon,
} from 'lucide-react';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { cn } from '@/lib/utils';
import type { ReferenceFileMeta } from '@/types/skill';

export interface SkillReferenceFilesProps {
  /** File metadata; field shape mirrors backend `ReferenceFileMeta`. */
  references: ReferenceFileMeta[];
  /** Called with the relative file path (not slug-prefixed). */
  onSelect: (path: string) => void;
  className?: string;
}

type IconComponent = React.ComponentType<{
  className?: string;
  'aria-hidden'?: boolean;
}>;

/**
 * Map a (mime, filename) pair to a Lucide icon. The filename fallback covers
 * cases where the backend mime detection is generic (`text/plain` for `.py`
 * source files, etc.). Order matters — image / csv / pdf are decided first
 * because their mime types are unambiguous.
 */
function iconForMime(mime: string, name: string): IconComponent {
  if (mime.startsWith('image/')) return ImageIcon;
  if (mime === 'text/csv' || /\.csv$/i.test(name)) return TableIcon;
  if (mime === 'application/pdf' || /\.pdf$/i.test(name)) return FileText;
  if (mime.startsWith('text/markdown') || /\.(md|mdx)$/i.test(name)) return FileText;
  if (
    /\.(py|ts|tsx|js|jsx|sql|sh|rb|go|rs|css|scss|yaml|yml|toml|json)$/i.test(
      name,
    ) ||
    mime.startsWith('text/x-')
  ) {
    return Code2;
  }
  if (mime.startsWith('text/')) return FileText;
  return FileIcon;
}

/**
 * 1-decimal byte formatter. `1023 → "1023 B"`, `1024 → "1.0 KB"`,
 * `1024² → "1.0 MB"`. Larger files (>1 GB) are out-of-scope — reference
 * files in a skill template are bounded by the repo size budget.
 */
function formatBytes(n: number): string {
  if (!Number.isFinite(n) || n < 0) return '—';
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export function SkillReferenceFiles({
  references,
  onSelect,
  className,
}: SkillReferenceFilesProps) {
  // Default-open for [1..5]; closed for >5. The user's manual toggle wins
  // afterwards (state owned here, not derived from props after first render).
  const initialOpen = references.length > 0 && references.length <= 5;
  const [open, setOpen] = React.useState(initialOpen);

  if (references.length === 0) {
    return (
      <section
        aria-labelledby="skill-ref-files-heading"
        className={cn('mt-8', className)}
      >
        <h2
          id="skill-ref-files-heading"
          className="text-[15px] font-semibold text-foreground"
        >
          Reference Files
        </h2>
        <p className="mt-3 text-[13px] font-medium text-muted-foreground">
          This skill has no reference files.
        </p>
      </section>
    );
  }

  return (
    <Collapsible
      open={open}
      onOpenChange={setOpen}
      className={cn('mt-8', className)}
    >
      <CollapsibleTrigger
        className="flex items-center gap-2 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded"
        data-testid="skill-ref-files-trigger"
      >
        <ChevronRight
          className={cn(
            'h-4 w-4 transition-transform',
            open && 'rotate-90',
          )}
          aria-hidden
        />
        <h2 className="text-[15px] font-semibold text-foreground">
          Reference Files
        </h2>
        <span
          className="font-mono text-[10px] font-semibold text-muted-foreground"
          data-testid="skill-ref-files-count"
        >
          ({references.length})
        </span>
      </CollapsibleTrigger>
      <CollapsibleContent className="mt-3">
        <ul
          className="divide-y divide-border rounded-md border border-border"
          data-testid="skill-ref-files-list"
        >
          {references.map((ref) => {
            const Icon = iconForMime(ref.mime_type, ref.name);
            return (
              <li key={ref.path}>
                <button
                  type="button"
                  onClick={() => onSelect(ref.path)}
                  className="flex w-full items-center gap-3 px-4 py-2.5 text-left hover:bg-muted focus-visible:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  data-testid={`skill-ref-file-row-${ref.path}`}
                >
                  <Icon
                    className="h-4 w-4 shrink-0 text-muted-foreground"
                    aria-hidden
                  />
                  <span className="flex-1 truncate text-[13px] font-medium text-foreground">
                    {ref.name}
                  </span>
                  <span className="font-mono text-[10px] font-semibold text-muted-foreground">
                    {formatBytes(ref.size_bytes)}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      </CollapsibleContent>
    </Collapsible>
  );
}

// Exported for tests — pure helpers, no DOM dependency.
export const __test__ = { iconForMime, formatBytes };
