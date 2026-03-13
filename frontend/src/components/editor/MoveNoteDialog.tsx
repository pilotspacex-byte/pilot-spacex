'use client';

/**
 * MoveNoteDialog - Project picker dialog for assigning a note to a project.
 *
 * Used by two flows:
 * 1. "New Note" project selection step (after TemplatePicker in sidebar.tsx)
 * 2. "Move..." option in the InlineNoteHeader options dropdown
 *
 * Accessibility contract
 * ─────────────────────
 * • role="dialog" + aria-modal="true" + aria-labelledby pointing to the heading
 * • Focus is trapped inside the dialog while open (Tab / Shift+Tab cycle)
 * • Escape closes and returns focus to the element that opened the dialog
 * • Project list uses role="listbox" / role="option" + aria-selected
 * • Arrow keys move the highlighted option; Enter / Space confirm selection
 * • Initial focus lands on the search input on mount
 *
 * @module components/editor/MoveNoteDialog
 */
import { useState, useMemo, useEffect, useRef, useCallback, useId } from 'react';
import { Folder, X, Check, Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';
import { useProjects, selectAllProjects } from '@/features/projects/hooks/useProjects';

export interface MoveNoteDialogProps {
  workspaceId: string;
  /** Pre-selects this project in the picker. null = "No project (root)". */
  currentProjectId?: string | null;
  /** Label for the confirm button. Defaults to "Confirm". */
  confirmLabel?: string;
  onSelect: (projectId: string | null) => void;
  onClose: () => void;
}

// All focusable element types that participate in the Tab cycle.
const FOCUSABLE =
  'a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])';

export function MoveNoteDialog({
  workspaceId,
  currentProjectId = null,
  confirmLabel = 'Confirm',
  onSelect,
  onClose,
}: MoveNoteDialogProps) {
  const [selected, setSelected] = useState<string | null>(currentProjectId ?? null);
  const [search, setSearch] = useState('');

  const { data: projectsData, isLoading } = useProjects({ workspaceId });
  const projects = useMemo(() => selectAllProjects(projectsData), [projectsData]);

  const filteredProjects = useMemo(() => {
    if (!search.trim()) return projects;
    const q = search.toLowerCase();
    return projects.filter((p) => p.name.toLowerCase().includes(q));
  }, [projects, search]);

  // Build the flat option list: [null, ...project ids] — mirrors the rendered order.
  const optionIds = useMemo(
    () => [null, ...filteredProjects.map((p) => p.id)] as (string | null)[],
    [filteredProjects]
  );

  // Keyboard-driven active index (separate from `selected` so arrow keys don't
  // change the committed selection until Enter/Space is pressed).
  const [activeIndex, setActiveIndex] = useState<number>(() => {
    const idx = optionIds.indexOf(currentProjectId ?? null);
    return idx >= 0 ? idx : 0;
  });

  // Keep activeIndex in bounds when the filtered list shrinks.
  useEffect(() => {
    setActiveIndex((prev) => Math.min(prev, Math.max(0, optionIds.length - 1)));
  }, [optionIds.length]);

  const dialogRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);
  // Unique IDs for ARIA wiring.
  const titleId = useId();
  const listboxId = useId();
  const activeOptionId = useId();

  // ── Focus return on unmount ────────────���─────────────────────────────────
  // Capture the element that had focus before the dialog opened so we can
  // restore it when the dialog closes.
  useEffect(() => {
    const previouslyFocused = document.activeElement as HTMLElement | null;
    // Move initial focus into the search input.
    searchRef.current?.focus();
    return () => {
      previouslyFocused?.focus();
    };
  }, []);

  // ── Focus trap (Tab / Shift+Tab) ─────────────────────────────────────────
  const handleDialogKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLDivElement>) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
        return;
      }

      if (e.key === 'Tab') {
        const container = dialogRef.current;
        if (!container) return;
        const focusable = Array.from(container.querySelectorAll<HTMLElement>(FOCUSABLE));
        if (focusable.length === 0) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (!first || !last) return;

        if (e.shiftKey) {
          if (document.activeElement === first) {
            e.preventDefault();
            last.focus();
          }
        } else {
          if (document.activeElement === last) {
            e.preventDefault();
            first.focus();
          }
        }
      }
    },
    [onClose]
  );

  // ── Listbox arrow-key navigation ─────────────────────────────────────────
  const handleListboxKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLDivElement>) => {
      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          setActiveIndex((prev) => Math.min(prev + 1, optionIds.length - 1));
          break;
        case 'ArrowUp':
          e.preventDefault();
          setActiveIndex((prev) => Math.max(prev - 1, 0));
          break;
        case 'Enter':
        case ' ':
          e.preventDefault();
          setSelected(optionIds[activeIndex] ?? null);
          break;
        default:
          break;
      }
    },
    [optionIds, activeIndex]
  );

  return (
    // Backdrop — click-outside closes; Escape is handled on the inner container.
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      {/* Dialog container */}
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="relative flex max-h-[70vh] w-full max-w-[400px] flex-col overflow-hidden rounded-xl bg-background shadow-xl mx-4"
        onKeyDown={handleDialogKeyDown}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-5 py-3.5">
          <h2 id={titleId} className="text-sm font-semibold text-foreground">
            Add to project
          </h2>
          <button
            type="button"
            className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
            aria-label="Close dialog"
            onClick={onClose}
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>

        {/* Search input */}
        <div className="flex items-center gap-2 border-b border-border px-3 py-2">
          <Search className="h-3.5 w-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
          <Input
            ref={searchRef}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search projects…"
            aria-label="Search projects"
            aria-controls={listboxId}
            className="h-6 border-none bg-transparent p-0 text-sm shadow-none focus-visible:ring-0"
          />
        </div>

        {/* Project listbox */}
        <div
          id={listboxId}
          role="listbox"
          aria-label="Projects"
          aria-activedescendant={`${activeOptionId}-${activeIndex}`}
          tabIndex={-1}
          className="overflow-y-auto px-3 py-2 outline-none"
          onKeyDown={handleListboxKeyDown}
        >
          {/* No project (root) option */}
          {(() => {
            const idx = 0;
            const isActive = activeIndex === idx;
            const isSelected = selected === null;
            return (
              <div
                key="no-project"
                id={`${activeOptionId}-${idx}`}
                role="option"
                aria-selected={isSelected}
                tabIndex={isActive ? 0 : -1}
                onClick={() => { setSelected(null); setActiveIndex(idx); }}
                onFocus={() => setActiveIndex(idx)}
                className={cn(
                  'flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition-colors cursor-pointer select-none',
                  isSelected
                    ? 'bg-primary/5 text-foreground'
                    : 'text-muted-foreground hover:bg-muted/50 hover:text-foreground',
                  isActive && !isSelected && 'bg-muted/50 text-foreground'
                )}
              >
                <Folder className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                <span className="flex-1 text-left">No project (root)</span>
                {isSelected && (
                  <Check className="h-3.5 w-3.5 shrink-0 text-primary" aria-hidden="true" />
                )}
              </div>
            );
          })()}

          {/* Loading state */}
          {isLoading && (
            <div className="mt-1 space-y-1 px-1" aria-busy="true" aria-label="Loading projects">
              <Skeleton className="h-8 w-full rounded-lg" />
              <Skeleton className="h-8 w-full rounded-lg" />
              <Skeleton className="h-8 w-3/4 rounded-lg" />
            </div>
          )}

          {/* Project rows */}
          {!isLoading &&
            filteredProjects.map((project, i) => {
              const idx = i + 1; // offset by 1 because "No project" is index 0
              const isActive = activeIndex === idx;
              const isSelected = selected === project.id;
              return (
                <div
                  key={project.id}
                  id={`${activeOptionId}-${idx}`}
                  role="option"
                  aria-selected={isSelected}
                  tabIndex={isActive ? 0 : -1}
                  onClick={() => { setSelected(project.id); setActiveIndex(idx); }}
                  onFocus={() => setActiveIndex(idx)}
                  className={cn(
                    'flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition-colors cursor-pointer select-none',
                    isSelected
                      ? 'bg-primary/5 text-foreground'
                      : 'text-muted-foreground hover:bg-muted/50 hover:text-foreground',
                    isActive && !isSelected && 'bg-muted/50 text-foreground'
                  )}
                >
                  {project.icon ? (
                    <span className="text-base leading-none shrink-0" aria-hidden="true">
                      {project.icon}
                    </span>
                  ) : (
                    <Folder className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                  )}
                  <span className="flex-1 truncate text-left">{project.name}</span>
                  {isSelected && (
                    <Check className="h-3.5 w-3.5 shrink-0 text-primary" aria-hidden="true" />
                  )}
                </div>
              );
            })}

          {!isLoading && filteredProjects.length === 0 && search && (
            <p role="status" className="px-3 py-2 text-xs text-muted-foreground">
              No projects found
            </p>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-border px-5 py-3">
          <Button variant="ghost" size="sm" onClick={onClose}>
            Cancel
          </Button>
          <Button size="sm" onClick={() => onSelect(selected)}>
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}
