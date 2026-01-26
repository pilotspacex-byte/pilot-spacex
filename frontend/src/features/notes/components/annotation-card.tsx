/**
 * Annotation Card - Individual annotation display in margin
 * T169: Shows annotation summary with type icon and confidence
 *
 * Features:
 * - Type-specific icons and colors
 * - Confidence indicator
 * - Selection state
 * - Click to expand
 */
'use client';

import type { ForwardRefExoticComponent, RefAttributes } from 'react';
import { cn } from '@/lib/utils';
import { Lightbulb, AlertTriangle, HelpCircle, Sparkles, Link2, Info } from 'lucide-react';
import type { LucideProps } from 'lucide-react';
import type { NoteAnnotation, AnnotationType } from '@/types';

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

export function AnnotationCard({ annotation, isSelected, onSelect }: AnnotationCardProps) {
  const Icon = typeIcons[annotation.type] || Lightbulb;

  return (
    <button
      onClick={onSelect}
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
    </button>
  );
}
