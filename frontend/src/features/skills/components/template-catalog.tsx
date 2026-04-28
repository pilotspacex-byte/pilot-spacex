/**
 * TemplateCatalog — Observer component displaying browsable skill templates.
 *
 * Features role-type filter chips (inspired by Anthropic Artifacts gallery).
 * Responsive grid: 1→2→3 columns. Loading skeletons match card shape.
 * Source: Phase 20, P20-09
 */

'use client';

import * as React from 'react';
import { Layers, AlertCircle } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useSkillTemplates } from '@/services/api/skill-templates';
import type { SkillTemplate } from '@/services/api/skill-templates';
import { TemplateCard } from './template-card';

interface TemplateCatalogProps {
  workspaceSlug: string;
  isAdmin: boolean;
  onUseThis?: (template: SkillTemplate) => void;
  onEditTemplate?: (template: SkillTemplate) => void;
  onToggleTemplateActive?: (template: SkillTemplate) => void;
  onDeleteTemplate?: (template: SkillTemplate) => void;
}

/** Extract unique role types from templates for filter chips. */
function getRoleTypes(templates: SkillTemplate[]): string[] {
  const roles = new Set<string>();
  for (const t of templates) {
    if (t.role_type) roles.add(t.role_type);
  }
  return Array.from(roles).sort();
}

function CardSkeleton() {
  return (
    <div className="rounded-xl border bg-card overflow-hidden">
      <Skeleton className="h-[72px] w-full rounded-none" />
      <div className="p-4 space-y-2">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-3 w-16" />
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-3/4" />
        <Skeleton className="h-8 w-full mt-2" />
      </div>
    </div>
  );
}

export function TemplateCatalog({
  workspaceSlug,
  isAdmin,
  onUseThis,
  onEditTemplate,
  onToggleTemplateActive,
  onDeleteTemplate,
}: TemplateCatalogProps) {
  const { data: templates, isLoading, isError, error } = useSkillTemplates(workspaceSlug);
  const [activeFilter, setActiveFilter] = React.useState<string | null>(null);

  if (isLoading) {
    return (
      <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <CardSkeleton key={i} />
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          Failed to load templates: {error?.message ?? 'Unknown error'}
        </AlertDescription>
      </Alert>
    );
  }

  if (!templates || templates.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 px-4">
        <div className="rounded-full border border-border/50 bg-muted/30 p-4 mb-4">
          <Layers className="h-8 w-8 text-muted-foreground/40" />
        </div>
        <h3 className="text-sm font-medium text-foreground">No skill templates available</h3>
        <p className="mt-1 text-xs text-muted-foreground text-center max-w-[300px]">
          {isAdmin
            ? 'Create a workspace template or wait for built-in templates to be seeded.'
            : 'No templates have been configured for this workspace yet.'}
        </p>
      </div>
    );
  }

  // Sort: active first, then by sort_order
  const sorted = [...templates].sort((a, b) => {
    if (a.is_active !== b.is_active) return a.is_active ? -1 : 1;
    return a.sort_order - b.sort_order;
  });

  // Filter by role type
  const filtered = activeFilter ? sorted.filter((t) => t.role_type === activeFilter) : sorted;

  const roleTypes = getRoleTypes(templates);

  return (
    <div className="space-y-4">
      {/* Filter chips */}
      {roleTypes.length > 1 && (
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => setActiveFilter(null)}
            className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              activeFilter === null
                ? 'bg-primary text-primary-foreground'
                : 'bg-muted text-muted-foreground hover:bg-muted/80'
            }`}
          >
            All
          </button>
          {roleTypes.map((role) => (
            <button
              key={role}
              type="button"
              onClick={() => setActiveFilter(activeFilter === role ? null : role)}
              className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-medium capitalize transition-colors ${
                activeFilter === role
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted text-muted-foreground hover:bg-muted/80'
              }`}
            >
              {role.replace(/_/g, ' ')}
            </button>
          ))}
        </div>
      )}

      {/* Template grid */}
      {filtered.length > 0 ? (
        <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((template, index) => (
            <div
              key={template.id}
              className="animate-fade-up h-full"
              style={{ animationDelay: `${index * 60}ms` }}
            >
              <TemplateCard
                template={template}
                onUseThis={onUseThis}
                onEdit={onEditTemplate}
                onToggleActive={onToggleTemplateActive}
                onDelete={onDeleteTemplate}
                isAdmin={isAdmin}
              />
            </div>
          ))}
        </div>
      ) : (
        <div className="py-8 text-center">
          <p className="text-sm text-muted-foreground">No templates match this filter.</p>
        </div>
      )}
    </div>
  );
}
