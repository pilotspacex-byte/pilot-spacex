'use client';

/**
 * TemplatePicker — Modal for selecting a note template when creating a new note.
 *
 * T-145: Template picker UI (FR-063, FR-064, FR-065)
 * - "Blank" option always first (pre-selected)
 * - 4 SDLC system templates (Sprint Planning, Design Review, Postmortem, Release Planning)
 * - Custom templates for admin/owner users (FR-065)
 * - Roving tabindex keyboard navigation
 * - Creates independent copy of template content on submit (FR-064)
 *
 * @module notes/components/TemplatePicker
 */
import React, { useState, useCallback, useMemo, useRef, useEffect, KeyboardEvent } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  LayoutDashboard,
  PenTool,
  AlertTriangle,
  Rocket,
  FileText,
  Plus,
  Check,
  X,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { templatesApi, type NoteTemplate } from '@/services/api/templates';

// ── Types ──────────────────────────────────────────────────────────────────

export type TemplateId = string | 'blank';

export interface TemplatePickerProps {
  workspaceId: string;
  /** Whether the current user has admin or owner role (FR-065). */
  isAdmin: boolean;
  onConfirm: (template: NoteTemplate | null) => void;
  onClose: () => void;
}

// ── System template icons ──────────────────────────────────────────────────

const SYSTEM_ICON_MAP: Record<string, React.ElementType> = {
  'Sprint Planning': LayoutDashboard,
  'Design Review': PenTool,
  Postmortem: AlertTriangle,
  'Release Planning': Rocket,
};

const SYSTEM_DESCRIPTIONS: Record<string, string> = {
  'Sprint Planning': 'Sprint goals, team assignments, and task breakdown',
  'Design Review': 'Design critique structure with feedback and decisions',
  Postmortem: 'Incident timeline, impact analysis, and action items',
  'Release Planning': 'Feature list, go/no-go criteria, and rollout plan',
};

function getTemplateIcon(template: NoteTemplate): React.ElementType {
  if (template.isSystem) {
    return SYSTEM_ICON_MAP[template.name] ?? FileText;
  }
  return FileText;
}

function getTemplateDescription(template: NoteTemplate): string {
  if (template.isSystem) {
    return SYSTEM_DESCRIPTIONS[template.name] ?? template.description ?? '';
  }
  return template.description ?? '';
}

// ── TemplateCard ───────────────────────────────────────────────────────────

interface TemplateCardProps {
  template: NoteTemplate;
  /** Icon component to render — resolved outside the component to satisfy React Compiler. */
  icon: React.ElementType;
  selected: boolean;
  isAdmin: boolean;
  tabIndex: number;
  onSelect: () => void;
  onEditClick?: (e: React.MouseEvent) => void;
  cardRef?: React.Ref<HTMLDivElement>;
}

function TemplateCard({
  template,
  icon: Icon,
  selected,
  isAdmin,
  tabIndex,
  onSelect,
  onEditClick,
  cardRef,
}: TemplateCardProps) {
  const description = getTemplateDescription(template);

  return (
    <div
      ref={cardRef}
      role="radio"
      aria-checked={selected}
      aria-label={`${template.name}${description ? ` — ${description}` : ''}`}
      tabIndex={tabIndex}
      title={description}
      className={cn(
        'group relative flex h-[140px] w-[120px] cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border p-3 transition-all duration-150',
        selected
          ? 'border-2 border-primary bg-primary/5 ring-2 ring-primary/20'
          : 'border-border bg-background hover:border-primary/40 hover:bg-primary/[0.03] hover:shadow-sm'
      )}
      onClick={onSelect}
      onKeyDown={(e) => {
        if (e.key === ' ' || e.key === 'Enter') {
          e.preventDefault();
          onSelect();
        }
      }}
    >
      <Icon
        className={cn('h-8 w-8 shrink-0', selected ? 'text-primary' : 'text-muted-foreground')}
        aria-hidden="true"
      />
      <span className="text-center text-xs font-medium text-foreground leading-snug">
        {template.name}
      </span>

      {/* Admin edit button for custom templates */}
      {!template.isSystem && isAdmin && onEditClick && (
        <button
          type="button"
          className="absolute right-1 top-1 hidden rounded p-0.5 text-muted-foreground hover:bg-muted hover:text-foreground group-hover:flex"
          aria-label={`Edit ${template.name} template`}
          onClick={onEditClick}
        >
          <PenTool className="h-3 w-3" aria-hidden="true" />
        </button>
      )}
    </div>
  );
}

// ── CreateTemplateCard ─────────────────────────────────────────────────────

function CreateTemplateCard({
  tabIndex,
  onClick,
  cardRef,
}: {
  tabIndex: number;
  onClick: () => void;
  cardRef?: React.Ref<HTMLDivElement>;
}) {
  return (
    <div
      ref={cardRef}
      role="button"
      aria-label="Create new template"
      tabIndex={tabIndex}
      className="flex h-[140px] w-[120px] cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed border-border bg-background transition-colors duration-150 hover:border-primary/50 hover:text-primary"
      onClick={onClick}
      onKeyDown={(e) => {
        if (e.key === ' ' || e.key === 'Enter') {
          e.preventDefault();
          onClick();
        }
      }}
    >
      <Plus className="h-8 w-8 text-muted-foreground" aria-hidden="true" />
      <span className="text-xs text-muted-foreground text-center">New Template</span>
    </div>
  );
}

// ── TemplatePicker ─────────────────────────────────────────────────────────

export function TemplatePicker({ workspaceId, isAdmin, onConfirm, onClose }: TemplatePickerProps) {
  const [selected, setSelected] = useState<TemplateId>('blank');
  const blankRef = useRef<HTMLDivElement>(null);
  const cardRefs = useRef<Map<string, HTMLDivElement>>(new Map());

  // Fetch workspace templates (system + custom)
  const { data, isLoading, isError } = useQuery({
    queryKey: ['templates', workspaceId],
    queryFn: () => templatesApi.list(workspaceId),
    staleTime: 5 * 60_000,
  });

  const systemTemplates = data?.templates.filter((t) => t.isSystem) ?? [];
  const customTemplates = data?.templates.filter((t) => !t.isSystem) ?? [];

  // Focus blank on mount
  useEffect(() => {
    blankRef.current?.focus();
  }, []);

  const selectedTemplate =
    selected === 'blank' ? null : (data?.templates.find((t) => t.id === selected) ?? null);

  const handleConfirm = useCallback(() => {
    // FR-064: creates an independent copy by passing template (caller does the deep clone)
    onConfirm(selectedTemplate);
  }, [selectedTemplate, onConfirm]);

  // Build flat list of all focusable items for roving tabindex
  const allIds = useMemo<TemplateId[]>(
    () => [
      'blank',
      ...systemTemplates.map((t) => t.id),
      ...customTemplates.map((t) => t.id),
      ...(isAdmin ? ['create-template' as TemplateId] : []),
    ],
    [systemTemplates, customTemplates, isAdmin]
  );

  const focusById = useCallback((id: TemplateId) => {
    if (id === 'blank') {
      blankRef.current?.focus();
    } else if (id === 'create-template') {
      cardRefs.current.get('create-template')?.focus();
    } else {
      cardRefs.current.get(id)?.focus();
    }
  }, []);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLDivElement>) => {
      const current = allIds.indexOf(selected !== 'create-template' ? selected : 'create-template');
      if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
        e.preventDefault();
        const next = allIds[(current + 1) % allIds.length] ?? 'blank';
        setSelected(next);
        focusById(next);
      } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
        e.preventDefault();
        const prev = allIds[(current - 1 + allIds.length) % allIds.length] ?? 'blank';
        setSelected(prev);
        focusById(prev);
      } else if (e.key === 'Escape') {
        onClose();
      } else if (e.key === 'Enter' && e.target === document.activeElement) {
        handleConfirm();
      }
    },
    [allIds, selected, focusById, onClose, handleConfirm]
  );

  const createLabel =
    selected === 'blank' ? 'Create Blank Note' : `Create ${selectedTemplate?.name ?? ''} Note`;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Create New Note — choose a template"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        className="relative flex max-h-[80vh] w-full max-w-[560px] flex-col overflow-hidden rounded-xl bg-background shadow-xl mx-4"
        onKeyDown={handleKeyDown}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-6 py-4">
          <h2 className="text-sm font-semibold text-foreground">Create New Note</h2>
          <button
            type="button"
            className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
            aria-label="Close"
            onClick={onClose}
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>

        {/* Body */}
        <div className="overflow-y-auto px-6 py-4 flex flex-col gap-4">
          {/* Blank Note row */}
          <div
            ref={blankRef}
            role="radio"
            aria-checked={selected === 'blank'}
            aria-label="Blank Note — start from scratch"
            tabIndex={0}
            className={cn(
              'flex cursor-pointer items-center gap-3 rounded-lg border p-3 transition-all duration-150',
              selected === 'blank'
                ? 'border-primary/30 bg-primary/5'
                : 'border-border hover:border-primary/30'
            )}
            onClick={() => setSelected('blank')}
            onKeyDown={(e) => {
              if (e.key === ' ' || e.key === 'Enter') {
                e.preventDefault();
                setSelected('blank');
              }
            }}
          >
            <FileText
              className={cn(
                'h-5 w-5 shrink-0',
                selected === 'blank' ? 'text-primary' : 'text-muted-foreground'
              )}
              aria-hidden="true"
            />
            <div className="flex-1">
              <p className="text-sm font-medium text-foreground">Blank Note</p>
              <p className="text-xs text-muted-foreground">Start from scratch</p>
            </div>
            {selected === 'blank' && (
              <Check className="h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
            )}
          </div>

          {/* Loading state */}
          {isLoading && (
            <p className="text-xs text-muted-foreground text-center py-2">Loading templates…</p>
          )}

          {/* Error state */}
          {isError && (
            <p className="text-xs text-destructive text-center py-2">Failed to load templates.</p>
          )}

          {/* SDLC Templates */}
          {systemTemplates.length > 0 && (
            <section>
              <p className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                SDLC Templates
              </p>
              <div
                role="radiogroup"
                aria-label="SDLC template selection"
                className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4"
              >
                {systemTemplates.map((template) => (
                  <TemplateCard
                    key={template.id}
                    template={template}
                    icon={getTemplateIcon(template)}
                    selected={selected === template.id}
                    isAdmin={isAdmin}
                    tabIndex={selected === template.id ? 0 : -1}
                    onSelect={() => setSelected(template.id)}
                    cardRef={(el) => {
                      if (el) cardRefs.current.set(template.id, el);
                    }}
                  />
                ))}
              </div>
            </section>
          )}

          {/* Custom Templates (admin) */}
          {isAdmin && (
            <section>
              <p className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                My Templates
              </p>
              <div
                role="radiogroup"
                aria-label="Custom template selection"
                className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4"
              >
                {customTemplates.map((template) => (
                  <TemplateCard
                    key={template.id}
                    template={template}
                    icon={getTemplateIcon(template)}
                    selected={selected === template.id}
                    isAdmin={isAdmin}
                    tabIndex={selected === template.id ? 0 : -1}
                    onSelect={() => setSelected(template.id)}
                    onEditClick={(e) => {
                      e.stopPropagation();
                      // Navigate to template editor — future feature
                    }}
                    cardRef={(el) => {
                      if (el) cardRefs.current.set(template.id, el);
                    }}
                  />
                ))}

                {customTemplates.length === 0 && (
                  <p className="col-span-full text-xs italic text-muted-foreground">
                    No custom templates yet. Create one for your team.
                  </p>
                )}

                {/* Create Template card */}
                <CreateTemplateCard
                  tabIndex={-1}
                  onClick={() => {
                    // Navigate to template creator — future feature
                    onClose();
                  }}
                  cardRef={(el) => {
                    if (el) cardRefs.current.set('create-template', el);
                  }}
                />
              </div>
            </section>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-border px-6 py-4">
          <Button variant="ghost" size="sm" onClick={onClose}>
            Cancel
          </Button>
          <Button size="sm" onClick={handleConfirm} disabled={!selected}>
            {createLabel} →
          </Button>
        </div>
      </div>
    </div>
  );
}
