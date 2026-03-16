/**
 * TemplateCard — Displays a skill template with prominent icon, source badge, and actions.
 *
 * Inspired by Anthropic Artifacts gallery cards: large icon hero, clean hierarchy.
 * Plain component (NOT observer) — receives all data via props.
 * Source: Phase 20, P20-09
 */

'use client';

import type { LucideIcon } from 'lucide-react';
import {
  Code,
  Container,
  FileSearch,
  GanttChart,
  GitBranch,
  Layers,
  Lock,
  MoreVertical,
  Pencil,
  Power,
  Target,
  TestTube,
  Trash2,
  Wand2,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import type { SkillTemplate } from '@/services/api/skill-templates';

interface TemplateCardProps {
  template: SkillTemplate;
  onUseThis: (template: SkillTemplate) => void;
  onEdit?: (template: SkillTemplate) => void;
  onToggleActive?: (template: SkillTemplate) => void;
  onDelete?: (template: SkillTemplate) => void;
  isAdmin: boolean;
}

/** Map of Lucide icon name strings to components for dynamic rendering. */
const ICON_MAP: Record<string, LucideIcon> = {
  Code,
  Container,
  FileSearch,
  GanttChart,
  GitBranch,
  Layers,
  Target,
  TestTube,
  Wand2,
};

const SOURCE_BADGE_STYLES: Record<string, string> = {
  built_in: 'border-blue-500/20 bg-blue-500/10 text-blue-600 dark:text-blue-400',
  workspace: 'border-emerald-500/20 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400',
  custom: 'border-purple-500/20 bg-purple-500/10 text-purple-600 dark:text-purple-400',
};

const SOURCE_LABELS: Record<string, string> = {
  built_in: 'Built-in',
  workspace: 'Workspace',
  custom: 'Custom',
};

export function TemplateCard({
  template,
  onUseThis,
  onEdit,
  onToggleActive,
  onDelete,
  isAdmin,
}: TemplateCardProps) {
  const isBuiltIn = template.source === 'built_in';
  const badgeStyle = SOURCE_BADGE_STYLES[template.source] ?? SOURCE_BADGE_STYLES.custom;
  const sourceLabel = SOURCE_LABELS[template.source] ?? template.source;

  return (
    <article
      className={`group relative flex flex-col rounded-xl border bg-card transition-all duration-200 hover:shadow-md hover:border-border/80 ${
        !template.is_active ? 'opacity-50' : ''
      }`}
      data-testid="template-card"
    >
      {/* Icon hero area */}
      <div className="flex items-center justify-center py-6 px-4 bg-muted/30 rounded-t-xl border-b border-border/40">
        {(() => {
          const IconComponent = template.icon ? ICON_MAP[template.icon] : undefined;
          if (IconComponent) {
            return (
              <IconComponent
                className="h-10 w-10 text-muted-foreground/60"
                aria-label={template.name}
              />
            );
          }
          // Fallback: render icon value as emoji, or default emoji
          return (
            <span className="text-4xl select-none" role="img" aria-label={template.name}>
              {template.icon || '\uD83C\uDFAF'}
            </span>
          );
        })()}
      </div>

      {/* Content */}
      <div className="flex flex-col flex-1 p-4">
        {/* Title row */}
        <div className="flex items-start justify-between gap-2 mb-1">
          <div className="min-w-0 flex-1">
            <h3 className="text-sm font-semibold leading-tight truncate" title={template.name}>
              {template.name}
            </h3>
          </div>

          <div className="flex items-center gap-1 shrink-0">
            {isBuiltIn && (
              <Lock
                className="h-3.5 w-3.5 text-muted-foreground/60"
                aria-label="Built-in (read-only)"
              />
            )}
            {/* Admin actions dropdown */}
            {isAdmin && (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <MoreVertical className="h-3.5 w-3.5" />
                    <span className="sr-only">Template actions</span>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  {!isBuiltIn && onEdit && (
                    <DropdownMenuItem onClick={() => onEdit(template)}>
                      <Pencil className="mr-2 h-3.5 w-3.5" />
                      Edit
                    </DropdownMenuItem>
                  )}
                  {onToggleActive && (
                    <DropdownMenuItem onClick={() => onToggleActive(template)}>
                      <Power className="mr-2 h-3.5 w-3.5" />
                      {template.is_active ? 'Deactivate' : 'Activate'}
                    </DropdownMenuItem>
                  )}
                  {!isBuiltIn && onDelete && (
                    <>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem
                        onClick={() => onDelete(template)}
                        className="text-destructive focus:text-destructive"
                      >
                        <Trash2 className="mr-2 h-3.5 w-3.5" />
                        Delete
                      </DropdownMenuItem>
                    </>
                  )}
                </DropdownMenuContent>
              </DropdownMenu>
            )}
          </div>
        </div>

        {/* Source badge */}
        <div className="mb-2">
          <Badge variant="outline" className={`text-[10px] px-1.5 py-0 h-4 ${badgeStyle}`}>
            {sourceLabel}
          </Badge>
        </div>

        {/* Description */}
        <p className="text-xs text-muted-foreground line-clamp-2 flex-1 mb-3">
          {template.description}
        </p>

        {/* Use This button */}
        {template.is_active && (
          <Button
            size="sm"
            variant="outline"
            className="w-full mt-auto hover:bg-primary hover:text-primary-foreground transition-colors"
            onClick={() => onUseThis(template)}
          >
            <Wand2 className="mr-1.5 h-3.5 w-3.5" />
            Use This
          </Button>
        )}
      </div>
    </article>
  );
}
