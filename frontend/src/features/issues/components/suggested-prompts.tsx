/**
 * Suggested Prompts component.
 *
 * Displays clickable prompt chips for:
 * - Implementation guidance
 * - Testing advice
 * - Architecture questions
 * - Code review
 *
 * @see specs/004-mvp-agents-build/tasks/P22-P25-T178-T222.md#T214
 */
'use client';

import * as React from 'react';
import { Button } from '@/components/ui/button';
import { Lightbulb, TestTube, Layout, Code2 } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface SuggestedPromptsProps {
  onPromptClick: (prompt: string) => void;
  className?: string;
}

interface PromptOption {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  prompt: string;
}

const SUGGESTED_PROMPTS: PromptOption[] = [
  {
    icon: Lightbulb,
    label: 'How can I implement this?',
    prompt:
      'How can I implement this issue? Please provide a step-by-step implementation guide with code examples.',
  },
  {
    icon: TestTube,
    label: 'What tests should I write?',
    prompt:
      'What tests should I write for this issue? Please suggest test cases covering happy paths, edge cases, and error scenarios.',
  },
  {
    icon: Layout,
    label: 'What is the architecture?',
    prompt:
      'What is the recommended architecture for this feature? Please explain the design patterns and component structure.',
  },
  {
    icon: Code2,
    label: 'Review my approach',
    prompt:
      'Please review my implementation approach. Are there any potential issues, performance concerns, or better alternatives?',
  },
];

/**
 * Suggested prompts for starting conversation.
 *
 * @example
 * ```tsx
 * <SuggestedPrompts
 *   onPromptClick={(prompt) => sendMessage(prompt)}
 * />
 * ```
 */
export function SuggestedPrompts({ onPromptClick, className }: SuggestedPromptsProps) {
  return (
    <div className={cn('space-y-3', className)}>
      <p className="text-sm text-muted-foreground">Suggested prompts to get started:</p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {SUGGESTED_PROMPTS.map((option, index) => {
          const Icon = option.icon;
          return (
            <Button
              key={index}
              variant="outline"
              className="h-auto py-3 px-4 justify-start text-left hover:bg-ai/5 hover:border-ai/30 transition-colors"
              onClick={() => onPromptClick(option.prompt)}
            >
              <Icon className="h-4 w-4 mr-2 flex-shrink-0 text-ai" aria-hidden="true" />
              <span className="text-sm">{option.label}</span>
            </Button>
          );
        })}
      </div>
    </div>
  );
}
