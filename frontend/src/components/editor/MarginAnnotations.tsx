'use client';

/**
 * MarginAnnotations - Unified right panel with AI suggestions and TOC
 * Groups annotations by block, sorted by position
 * TOC at bottom (collapsible, smart dynamic)
 */
import { useMemo, useState } from 'react';
import { observer } from 'mobx-react-lite';
import { motion, AnimatePresence } from 'motion/react';
import type { Editor } from '@tiptap/react';
import {
  AlertTriangle,
  TicketPlus,
  Check,
  X,
  Info,
  EyeOff,
  Sparkles,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  List,
  HelpCircle,
  Link2,
} from 'lucide-react';

import { AutoTOC } from './AutoTOC';

import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import type { NoteAnnotation } from '@/types';
import { AIConfidenceTag, getConfidenceLevel } from '@/components/ai/AIConfidenceTag';

export interface MarginAnnotationsProps {
  /** List of annotations */
  annotations: NoteAnnotation[];
  /** TipTap editor instance for TOC */
  editor?: Editor | null;
  /** Currently selected block ID */
  selectedBlockId?: string | null;
  /** Whether the panel is collapsed */
  isCollapsed?: boolean;
  /** Callback to toggle panel collapse */
  onToggleCollapse?: () => void;
  /** Callback when annotation is clicked */
  onAnnotationClick?: (annotation: NoteAnnotation) => void;
  /** Callback to accept suggestion */
  onAccept?: (annotation: NoteAnnotation) => void;
  /** Callback to reject suggestion */
  onReject?: (annotation: NoteAnnotation) => void;
  /** Callback to dismiss annotation */
  onDismiss?: (annotation: NoteAnnotation) => void;
}

/** Confidence category for grouping per DD-048 */
type ConfidenceCategory = 'recommend' | 'related' | 'default';

interface AnnotationsByCategory {
  category: ConfidenceCategory;
  label: string;
  annotations: NoteAnnotation[];
}

/**
 * Get category from confidence score per DD-048
 */
function getConfidenceCategory(confidence: number, type: string): ConfidenceCategory {
  if (type === 'info') return 'related';
  if (confidence >= 0.8) return 'recommend';
  if (confidence >= 0.5) return 'default';
  return 'default';
}

/**
 * Category header styling
 */
const CATEGORY_CONFIG: Record<
  ConfidenceCategory,
  { label: string; color: string; bgColor: string }
> = {
  recommend: { label: 'RECOMMEND', color: 'text-primary', bgColor: 'bg-primary/5' },
  related: { label: 'RELATED', color: 'text-ai', bgColor: 'bg-ai-muted/30' },
  default: { label: 'DEFAULT', color: 'text-muted-foreground', bgColor: 'bg-muted/30' },
};

const ANNOTATION_TYPE_CONFIG: Record<
  import('@/types').AnnotationType,
  {
    icon: typeof Sparkles;
    label: string;
    color: string;
    bgColor: string;
    borderColor: string;
  }
> = {
  suggestion: {
    icon: Sparkles,
    label: 'Suggestion',
    color: 'text-ai',
    bgColor: 'bg-ai-muted',
    borderColor: 'border-ai-border',
  },
  warning: {
    icon: AlertTriangle,
    label: 'Warning',
    color: 'text-destructive',
    bgColor: 'bg-destructive/10',
    borderColor: 'border-destructive/30',
  },
  issue_candidate: {
    icon: TicketPlus,
    label: 'Issue',
    color: 'text-primary',
    bgColor: 'bg-primary-muted',
    borderColor: 'border-primary/30',
  },
  info: {
    icon: Info,
    label: 'Related',
    color: 'text-ai',
    bgColor: 'bg-ai-muted',
    borderColor: 'border-ai-border',
  },
  question: {
    icon: HelpCircle,
    label: 'Question',
    color: 'text-purple-600',
    bgColor: 'bg-purple-50',
    borderColor: 'border-purple-200',
  },
  insight: {
    icon: Sparkles,
    label: 'Insight',
    color: 'text-green-600',
    bgColor: 'bg-green-50',
    borderColor: 'border-green-200',
  },
  reference: {
    icon: Link2,
    label: 'Reference',
    color: 'text-gray-600',
    bgColor: 'bg-gray-50',
    borderColor: 'border-gray-200',
  },
};

/**
 * Get confidence label based on annotation type and confidence score
 */
function getConfidenceLabel(type: string, confidence: number): string {
  const level = getConfidenceLevel(confidence);
  if (type === 'suggestion') {
    if (level === 'recommended') return 'Recommended';
    if (level === 'default') return 'Suggested';
    return 'Alternative';
  }
  if (type === 'info') return 'Related';
  if (type === 'issue_candidate') return 'Issue Found';
  return 'Note';
}

/**
 * Single annotation card with Pilot Suggestions styling
 */
function AnnotationCard({
  annotation,
  isSelected,
  onClick,
  onAccept,
  onReject,
  onDismiss,
}: {
  annotation: NoteAnnotation;
  isSelected: boolean;
  onClick: () => void;
  onAccept?: () => void;
  onReject?: () => void;
  onDismiss?: () => void;
}) {
  const config = ANNOTATION_TYPE_CONFIG[annotation.type];
  const Icon = config.icon;
  const isSuggestion = annotation.type === 'suggestion';
  const isPending = annotation.status === 'pending';

  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      data-testid="annotation-card"
      className={cn(
        'group relative rounded-lg border p-3 transition-all cursor-pointer',
        config.bgColor,
        config.borderColor,
        isSelected && 'ring-2 ring-ai ring-offset-2',
        'hover:shadow-warm-md'
      )}
      onClick={onClick}
    >
      {/* Header with confidence tag */}
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-1.5">
          <Icon className={cn('h-3.5 w-3.5', config.color)} />
          <AIConfidenceTag confidence={annotation.confidence} showIcon className="text-[10px]">
            {getConfidenceLabel(annotation.type, annotation.confidence)}
          </AIConfidenceTag>
        </div>
      </div>

      {/* Content */}
      <p className="text-sm text-foreground leading-relaxed">{annotation.content}</p>

      {/* Resolved badge */}
      {(annotation.status === 'accepted' || annotation.status === 'rejected') && (
        <Badge variant="secondary" className="mt-2 text-[10px]">
          <Check className="mr-1 h-3 w-3" />
          {annotation.status === 'accepted' ? 'Applied' : 'Dismissed'}
        </Badge>
      )}

      {/* Actions - Always visible for suggestions, hover for others */}
      {isPending && (
        <div
          className={cn(
            'mt-3 flex items-center gap-1.5 transition-opacity',
            isSuggestion ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'
          )}
        >
          {isSuggestion && onAccept && (
            <Button
              variant="default"
              size="sm"
              data-testid="accept-button"
              className="h-7 gap-1 bg-primary hover:bg-primary-hover text-primary-foreground"
              onClick={(e) => {
                e.stopPropagation();
                onAccept();
              }}
            >
              <Check className="h-3.5 w-3.5" />
              Apply
            </Button>
          )}
          {isSuggestion && onReject && (
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  data-testid="reject-button"
                  className="h-7 w-7 text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                  onClick={(e) => {
                    e.stopPropagation();
                    onReject();
                  }}
                >
                  <X className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Dismiss</TooltipContent>
            </Tooltip>
          )}
          {!isSuggestion && onDismiss && (
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  className="h-7 w-7 text-muted-foreground hover:text-foreground"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDismiss();
                  }}
                >
                  <EyeOff className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Dismiss</TooltipContent>
            </Tooltip>
          )}
        </div>
      )}
    </motion.div>
  );
}

/**
 * Empty state when no annotations
 */
function EmptyState({
  editor,
  isTocExpanded,
  onToggleToc,
}: {
  editor?: Editor | null;
  isTocExpanded: boolean;
  onToggleToc: () => void;
}) {
  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Branded header - same as populated state */}
      <div className="flex items-center gap-1.5 border-b border-border px-3 py-2.5 bg-ai-muted/30">
        <Sparkles className="h-4 w-4 text-ai flex-shrink-0" />
        <span className="text-sm font-medium text-foreground truncate">Pilot Suggestions</span>
      </div>

      {/* Empty content */}
      <div className="flex flex-1 flex-col items-center justify-center p-4 text-center">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-muted mb-3 flex-shrink-0">
          <Sparkles className="h-5 w-5 text-muted-foreground" />
        </div>
        <h3 className="font-medium text-foreground mb-1 text-sm whitespace-nowrap">
          No suggestions yet
        </h3>
        <p className="text-xs text-muted-foreground leading-relaxed">
          AI suggestions will appear here as you write.
        </p>
      </div>

      {/* TOC Section - Collapsible at bottom */}
      {editor && (
        <div className="border-t border-border flex-shrink-0">
          {/* TOC Header - Clickable to toggle */}
          <button
            type="button"
            onClick={onToggleToc}
            className="flex w-full items-center justify-between px-3 py-2 hover:bg-muted/50 transition-colors"
          >
            <div className="flex items-center gap-1.5">
              <List className="h-3.5 w-3.5 text-muted-foreground" />
              <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Contents
              </span>
            </div>
            {isTocExpanded ? (
              <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
            ) : (
              <ChevronUp className="h-3.5 w-3.5 text-muted-foreground" />
            )}
          </button>

          {/* TOC Content - Collapsible */}
          <AnimatePresence>
            {isTocExpanded && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2, ease: 'easeInOut' }}
                className="overflow-hidden"
              >
                <div className="max-h-[200px] overflow-auto scrollbar-thin px-1 pb-2">
                  <AutoTOC editor={editor} variant="tree" className="px-1" />
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}

/**
 * Edge toggle button component
 */
function EdgeToggle({ isCollapsed, onClick }: { isCollapsed: boolean; onClick: () => void }) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          onClick={onClick}
          className={cn(
            'absolute left-0 top-1/2 -translate-x-1/2 -translate-y-1/2',
            'w-6 h-12 bg-background border border-border rounded-md',
            'flex items-center justify-center cursor-pointer',
            'opacity-0 hover:opacity-100 transition-opacity duration-150',
            'group-hover/panel:opacity-100',
            'shadow-warm-sm hover:shadow-warm',
            'z-10'
          )}
          aria-label={isCollapsed ? 'Expand suggestions panel' : 'Collapse suggestions panel'}
        >
          {isCollapsed ? (
            <ChevronLeft className="h-3.5 w-3.5 text-muted-foreground" />
          ) : (
            <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
          )}
        </button>
      </TooltipTrigger>
      <TooltipContent side="left">
        {isCollapsed ? 'Show suggestions' : 'Hide suggestions'}
      </TooltipContent>
    </Tooltip>
  );
}

/**
 * MarginAnnotations panel component
 */
export const MarginAnnotations = observer(function MarginAnnotations({
  annotations,
  editor,
  selectedBlockId,
  isCollapsed = false,
  onToggleCollapse,
  onAnnotationClick,
  onAccept,
  onReject,
  onDismiss,
}: MarginAnnotationsProps) {
  const [isTocExpanded, setIsTocExpanded] = useState(true);
  // Group annotations by confidence category per DD-048
  const annotationsByCategory = useMemo((): AnnotationsByCategory[] => {
    const categoryMap = new Map<ConfidenceCategory, NoteAnnotation[]>();
    const categoryOrder: ConfidenceCategory[] = ['recommend', 'related', 'default'];

    // Only include pending annotations
    const pendingAnnotations = annotations.filter((a) => a.status === 'pending');

    pendingAnnotations.forEach((annotation) => {
      const category = getConfidenceCategory(annotation.confidence, annotation.type);
      const existing = categoryMap.get(category) ?? [];
      categoryMap.set(category, [...existing, annotation]);
    });

    // Return categories in order, only if they have annotations
    return categoryOrder
      .filter((category) => (categoryMap.get(category)?.length ?? 0) > 0)
      .map((category) => ({
        category,
        label: CATEGORY_CONFIG[category].label,
        annotations: (categoryMap.get(category) ?? []).sort(
          (a, b) => b.confidence - a.confidence // Higher confidence first within category
        ),
      }));
  }, [annotations]);

  // Count by type
  const counts = useMemo(() => {
    const isPending = (a: NoteAnnotation) => a.status === 'pending';
    return {
      suggestion: annotations.filter((a) => a.type === 'suggestion' && isPending(a)).length,
      warning: annotations.filter((a) => a.type === 'warning' && isPending(a)).length,
      issue_candidate: annotations.filter((a) => a.type === 'issue_candidate' && isPending(a))
        .length,
      info: annotations.filter((a) => a.type === 'info' && isPending(a)).length,
      total: annotations.filter(isPending).length,
    };
  }, [annotations]);

  if (annotations.length === 0) {
    return (
      <div
        className="group/panel relative flex h-full flex-col border-l border-border overflow-hidden"
        data-testid="margin-annotations"
      >
        {/* Edge toggle */}
        {onToggleCollapse && <EdgeToggle isCollapsed={isCollapsed} onClick={onToggleCollapse} />}
        <EmptyState
          editor={editor}
          isTocExpanded={isTocExpanded}
          onToggleToc={() => setIsTocExpanded(!isTocExpanded)}
        />
      </div>
    );
  }

  return (
    <div
      className="group/panel relative flex h-full flex-col border-l border-border bg-background-subtle/50 overflow-hidden"
      data-testid="margin-annotations"
    >
      {/* Edge toggle - visible on hover */}
      {onToggleCollapse && <EdgeToggle isCollapsed={isCollapsed} onClick={onToggleCollapse} />}
      {/* Header - "Pilot Suggestions" like prototype */}
      <div className="flex items-center justify-between border-b border-border px-3 py-2.5 bg-ai-muted/30 gap-2">
        <div className="flex items-center gap-1.5 min-w-0">
          <Sparkles className="h-4 w-4 text-ai flex-shrink-0" />
          <span className="text-sm font-medium text-foreground truncate">Pilot Suggestions</span>
        </div>
        <Badge
          variant="outline"
          className="text-[10px] bg-background border-ai-border text-ai flex-shrink-0 whitespace-nowrap"
        >
          {counts.total} new
        </Badge>
      </div>

      {/* Type filters/counts */}
      <div className="flex items-center gap-1.5 border-b border-border px-3 py-2 overflow-x-auto scrollbar-none">
        {counts.suggestion > 0 && (
          <Badge
            variant="outline"
            className="text-[10px] gap-1 bg-ai-muted/50 border-ai-border flex-shrink-0"
          >
            <Sparkles className="h-3 w-3 text-ai" />
            {counts.suggestion}
          </Badge>
        )}
        {counts.warning > 0 && (
          <Badge
            variant="outline"
            className="text-[10px] gap-1 bg-destructive/10 border-destructive/30 flex-shrink-0"
          >
            <AlertTriangle className="h-3 w-3 text-destructive" />
            {counts.warning}
          </Badge>
        )}
        {counts.issue_candidate > 0 && (
          <Badge
            variant="outline"
            className="text-[10px] gap-1 bg-primary-muted border-primary/30 flex-shrink-0"
          >
            <TicketPlus className="h-3 w-3 text-primary" />
            {counts.issue_candidate}
          </Badge>
        )}
        {counts.info > 0 && (
          <Badge
            variant="outline"
            className="text-[10px] gap-1 bg-ai-muted/50 border-ai-border flex-shrink-0"
          >
            <Info className="h-3 w-3 text-ai" />
            {counts.info}
          </Badge>
        )}
      </div>

      {/* Annotations list - grouped by confidence category per DD-048 */}
      <ScrollArea className="flex-1 min-h-0">
        <div className="p-3 space-y-4">
          <AnimatePresence mode="popLayout">
            {annotationsByCategory.map(({ category, label, annotations: categoryAnnotations }) => (
              <div key={category} className="space-y-2">
                {/* Category header per prototype v4 */}
                <div
                  className={cn(
                    'flex items-center gap-2 px-2 py-1.5 rounded-md',
                    CATEGORY_CONFIG[category].bgColor
                  )}
                >
                  <span
                    className={cn(
                      'text-[10px] font-semibold uppercase tracking-wider',
                      CATEGORY_CONFIG[category].color
                    )}
                  >
                    {label}
                  </span>
                </div>

                {/* Annotations in this category */}
                {categoryAnnotations.map((annotation) => (
                  <AnnotationCard
                    key={annotation.id}
                    annotation={annotation}
                    isSelected={selectedBlockId === annotation.blockId}
                    onClick={() => onAnnotationClick?.(annotation)}
                    onAccept={onAccept ? () => onAccept(annotation) : undefined}
                    onReject={onReject ? () => onReject(annotation) : undefined}
                    onDismiss={onDismiss ? () => onDismiss(annotation) : undefined}
                  />
                ))}
              </div>
            ))}
          </AnimatePresence>

          {/* Show resolved annotations separately if any exist */}
          {annotations.filter((a) => a.status !== 'pending').length > 0 && (
            <div className="space-y-2 pt-2 border-t border-border">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground px-2">
                Resolved
              </span>
              {annotations
                .filter((a) => a.status !== 'pending')
                .map((annotation) => (
                  <AnnotationCard
                    key={annotation.id}
                    annotation={annotation}
                    isSelected={selectedBlockId === annotation.blockId}
                    onClick={() => onAnnotationClick?.(annotation)}
                  />
                ))}
            </div>
          )}
        </div>
      </ScrollArea>

      {/* TOC Section - Collapsible at bottom */}
      {editor && (
        <div className="border-t border-border flex-shrink-0">
          {/* TOC Header - Clickable to toggle */}
          <button
            type="button"
            onClick={() => setIsTocExpanded(!isTocExpanded)}
            className="flex w-full items-center justify-between px-3 py-2 hover:bg-muted/50 transition-colors"
          >
            <div className="flex items-center gap-1.5">
              <List className="h-3.5 w-3.5 text-muted-foreground" />
              <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Contents
              </span>
            </div>
            {isTocExpanded ? (
              <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
            ) : (
              <ChevronUp className="h-3.5 w-3.5 text-muted-foreground" />
            )}
          </button>

          {/* TOC Content - Collapsible */}
          <AnimatePresence>
            {isTocExpanded && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2, ease: 'easeInOut' }}
                className="overflow-hidden"
              >
                <div className="max-h-[200px] overflow-auto scrollbar-thin px-1 pb-2">
                  <AutoTOC editor={editor} variant="tree" className="px-1" />
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
});

export default MarginAnnotations;
