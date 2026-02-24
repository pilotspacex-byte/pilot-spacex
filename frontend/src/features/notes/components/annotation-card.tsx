/**
 * Annotation Card - Individual annotation display in margin
 * T169/T029: Shows annotation summary with type icon, confidence, and action buttons
 *
 * Features:
 * - Type-specific icons and colors
 * - Confidence indicator
 * - Selection state
 * - Click to expand
 * - Contextual action buttons based on annotation type (T029)
 */
'use client';

import { useState, useCallback, useRef } from 'react';
import type { ForwardRefExoticComponent, RefAttributes } from 'react';
import { observer } from 'mobx-react-lite';
import { cn } from '@/lib/utils';
import {
  Lightbulb,
  AlertTriangle,
  HelpCircle,
  Sparkles,
  Link2,
  Info,
  ArrowUpFromLine,
  MessageSquare,
  Plus,
  Loader2,
} from 'lucide-react';
import type { LucideProps } from 'lucide-react';
import type { NoteAnnotation, AnnotationType } from '@/types';
import { useStore } from '@/stores/RootStore';

interface AnnotationCardProps {
  annotation: NoteAnnotation;
  isSelected: boolean;
  onSelect: () => void;
}

type IconComponent = ForwardRefExoticComponent<
  Omit<LucideProps, 'ref'> & RefAttributes<SVGSVGElement>
>;

const typeIcons: Record<AnnotationType, IconComponent> = {
  suggestion: Lightbulb,
  warning: AlertTriangle,
  question: HelpCircle,
  insight: Sparkles,
  reference: Link2,
  issue_candidate: AlertTriangle,
  info: Info,
};

const typeColors: Record<AnnotationType, string> = {
  suggestion:
    'bg-blue-50 border-blue-200 text-blue-700 dark:bg-blue-950/30 dark:border-blue-800 dark:text-blue-300',
  warning:
    'bg-amber-50 border-amber-200 text-amber-700 dark:bg-amber-950/30 dark:border-amber-800 dark:text-amber-300',
  question:
    'bg-purple-50 border-purple-200 text-purple-700 dark:bg-purple-950/30 dark:border-purple-800 dark:text-purple-300',
  insight:
    'bg-green-50 border-green-200 text-green-700 dark:bg-green-950/30 dark:border-green-800 dark:text-green-300',
  reference:
    'bg-gray-50 border-gray-200 text-gray-700 dark:bg-gray-900/30 dark:border-gray-700 dark:text-gray-300',
  issue_candidate:
    'bg-purple-50 border-purple-200 text-purple-700 dark:bg-purple-950/30 dark:border-purple-800 dark:text-purple-300',
  info: 'bg-gray-50 border-gray-200 text-gray-700 dark:bg-gray-900/30 dark:border-gray-700 dark:text-gray-300',
};

/**
 * Action button configuration per annotation type.
 * Types without an entry are informational-only (no action button).
 */
interface ActionConfig {
  label: string;
  loadingLabel: string;
  icon: IconComponent;
  colorClass: string;
  buildMessage: (annotation: NoteAnnotation) => string;
}

const actionConfigs: Partial<Record<AnnotationType, ActionConfig>> = {
  issue_candidate: {
    label: 'Extract Issue',
    loadingLabel: 'Working...',
    icon: ArrowUpFromLine,
    colorClass:
      'bg-orange-100 text-orange-700 hover:bg-orange-200 dark:bg-orange-900/40 dark:text-orange-300 dark:hover:bg-orange-900/60',
    buildMessage: (a) => `/extract-issues from block: ${a.content}`,
  },
  question: {
    label: 'Ask AI',
    loadingLabel: 'Working...',
    icon: MessageSquare,
    colorClass:
      'bg-[#6B8FAD]/10 text-[#6B8FAD] hover:bg-[#6B8FAD]/20 dark:bg-[#6B8FAD]/20 dark:text-[#8BADC7] dark:hover:bg-[#6B8FAD]/30',
    buildMessage: (a) => `Clarify this section: ${a.aiMetadata?.summary ?? a.content}`,
  },
  suggestion: {
    label: 'Create Task',
    loadingLabel: 'Working...',
    icon: Plus,
    colorClass:
      'bg-[#29A386]/10 text-[#29A386] hover:bg-[#29A386]/20 dark:bg-[#29A386]/20 dark:text-[#3CC9A5] dark:hover:bg-[#29A386]/30',
    buildMessage: (a) => `/create-issue title: ${a.aiMetadata?.title ?? a.content}`,
  },
  warning: {
    label: 'Create Task',
    loadingLabel: 'Working...',
    icon: Plus,
    colorClass:
      'bg-[#29A386]/10 text-[#29A386] hover:bg-[#29A386]/20 dark:bg-[#29A386]/20 dark:text-[#3CC9A5] dark:hover:bg-[#29A386]/30',
    buildMessage: (a) => `/create-issue title: ${a.aiMetadata?.title ?? a.content}`,
  },
};

export const AnnotationCard = observer(function AnnotationCard({
  annotation,
  isSelected,
  onSelect,
}: AnnotationCardProps) {
  const { aiStore } = useStore();
  const [isActionLoading, setIsActionLoading] = useState(false);
  const actionLockRef = useRef(false);

  const Icon = typeIcons[annotation.type] || Lightbulb;
  const actionConfig = actionConfigs[annotation.type];

  const handleAction = useCallback(
    async (e: React.MouseEvent<HTMLButtonElement>) => {
      e.stopPropagation();
      if (!actionConfig || actionLockRef.current) return;

      actionLockRef.current = true;
      setIsActionLoading(true);
      try {
        const message = actionConfig.buildMessage(annotation);
        await aiStore.pilotSpace.sendMessage(message);
      } finally {
        actionLockRef.current = false;
        setIsActionLoading(false);
      }
    },
    [actionConfig, annotation, aiStore.pilotSpace]
  );

  const ActionIcon = actionConfig?.icon;

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onSelect}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onSelect();
        }
      }}
      className={cn(
        'w-full text-left p-3 rounded-lg border transition-all duration-200',
        'hover:shadow-md cursor-pointer mb-2',
        typeColors[annotation.type],
        isSelected && 'ring-2 ring-blue-500 ring-offset-2 shadow-lg scale-105'
      )}
      aria-label={`${annotation.type}: ${annotation.aiMetadata?.title ?? 'Annotation'}`}
      aria-pressed={isSelected}
    >
      <div className="flex items-start gap-2">
        <Icon className="w-4 h-4 mt-0.5 flex-shrink-0" aria-hidden="true" />
        <div className="flex-1 min-w-0">
          <p className="text-xs font-semibold truncate">
            {annotation.aiMetadata?.title ?? 'Annotation'}
          </p>
          <p className="text-xs opacity-80 line-clamp-2 mt-0.5">
            {annotation.aiMetadata?.summary ?? annotation.content}
          </p>
        </div>
      </div>
      <div className="flex items-center justify-between mt-2">
        <span className="text-xs opacity-60 capitalize font-medium">{annotation.type}</span>
        <span
          className="text-xs opacity-70 font-mono"
          title={`Confidence: ${Math.round(annotation.confidence * 100)}%`}
        >
          {Math.round(annotation.confidence * 100)}%
        </span>
      </div>

      {actionConfig && ActionIcon && (
        <div className="border-t border-current/10 mt-2 pt-2">
          <button
            type="button"
            onClick={handleAction}
            disabled={isActionLoading}
            className={cn(
              'inline-flex items-center gap-1 h-6 px-2 text-[11px] rounded-md',
              'font-medium transition-colors duration-150',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1',
              'disabled:pointer-events-none disabled:opacity-50',
              actionConfig.colorClass
            )}
            aria-label={`${actionConfig.label} for: ${annotation.aiMetadata?.title ?? annotation.type}`}
          >
            {isActionLoading ? (
              <Loader2 className="w-3 h-3 animate-spin" aria-hidden="true" />
            ) : (
              <ActionIcon className="w-3 h-3" aria-hidden="true" />
            )}
            {isActionLoading ? actionConfig.loadingLabel : actionConfig.label}
          </button>
        </div>
      )}
    </div>
  );
});
