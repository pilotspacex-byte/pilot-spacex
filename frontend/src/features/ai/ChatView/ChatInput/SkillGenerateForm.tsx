'use client';

/**
 * SkillGenerateForm — Inline form shown below ChatInput when \generate-skill is selected.
 * Collects experience description, calls generate API, transitions store state.
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { observer } from 'mobx-react-lite';
import { Loader2, Sparkles, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { useGenerateSkill } from '@/features/onboarding/hooks/useRoleSkillActions';
import type { PilotSpaceStore } from '@/stores/ai/PilotSpaceStore';

interface SkillGenerateFormProps {
  store: PilotSpaceStore;
  workspaceId: string;
}

const MIN_DESCRIPTION_LENGTH = 10;
const MAX_DESCRIPTION_LENGTH = 5000;

export const SkillGenerateForm = observer<SkillGenerateFormProps>(({ store, workspaceId }) => {
  const [description, setDescription] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const generateSkill = useGenerateSkill({ workspaceId });

  const isGenerating = store.skillGenerationState === 'generating';
  const isValid = description.trim().length >= MIN_DESCRIPTION_LENGTH;

  // Auto-focus on mount
  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  const handleGenerate = useCallback(async () => {
    if (!isValid || isGenerating) return;

    store.setSkillGenerationState('generating');

    try {
      const result = await generateSkill.mutateAsync({
        roleType: 'custom',
        experienceDescription: description.trim(),
      });

      // Add a synthetic assistant message with the skill preview
      store.addMessage({
        id: `skill-gen-${Date.now()}`,
        role: 'assistant',
        content: '',
        timestamp: new Date(),
        structuredResult: {
          schemaType: 'skill_generation_result',
          data: {
            ...result,
            experienceDescription: description.trim(),
          },
        },
      });

      store.setGeneratedSkill(result, description.trim());
    } catch {
      store.setSkillGenerationState('form');
    }
  }, [isValid, isGenerating, description, generateSkill, store]);

  const handleCancel = useCallback(() => {
    store.resetSkillGeneration();
  }, [store]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        handleCancel();
      }
    },
    [handleCancel]
  );

  const handleFormSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      void handleGenerate();
    },
    [handleGenerate]
  );

  return (
    <form
      onSubmit={handleFormSubmit}
      className={cn(
        'mx-3 mb-2 rounded-[12px] border border-border bg-background-subtle p-3',
        'shadow-warm-sm animate-in slide-in-from-bottom-2 duration-200'
      )}
      aria-label="Generate AI skill"
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Sparkles className="h-3.5 w-3.5 text-[var(--ai)]" />
          <span className="text-xs font-medium">Generate Skill</span>
        </div>
        <button
          type="button"
          onClick={handleCancel}
          className="p-1 -m-1 text-muted-foreground/60 hover:text-foreground transition-colors"
          aria-label="Cancel"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>

      <Textarea
        ref={textareaRef}
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Describe your experience and expertise... (e.g., 8 years Python/FastAPI, focus on clean architecture and testing)"
        disabled={isGenerating}
        maxLength={MAX_DESCRIPTION_LENGTH}
        className={cn(
          'min-h-[60px] max-h-[120px] resize-none text-xs',
          'rounded-lg border-border/60 bg-muted/20',
          'placeholder:text-muted-foreground/50'
        )}
        rows={2}
      />

      <div className="flex items-center justify-between mt-2">
        <span className="text-[10px] text-muted-foreground/60">
          {description.length}/{MAX_DESCRIPTION_LENGTH}
          {description.length > 0 && description.length < MIN_DESCRIPTION_LENGTH && (
            <span className="text-amber-500 ml-1">
              ({MIN_DESCRIPTION_LENGTH - description.length} more chars needed)
            </span>
          )}
        </span>

        <Button
          type="submit"
          size="sm"
          className="gap-1.5 text-xs h-7 bg-[var(--ai)] hover:bg-[var(--ai)]/90 text-white"
          disabled={!isValid || isGenerating}
        >
          {isGenerating ? (
            <>
              <Loader2 className="h-3 w-3 animate-spin" />
              Generating...
            </>
          ) : (
            <>
              <Sparkles className="h-3 w-3" />
              Generate
            </>
          )}
        </Button>
      </div>
    </form>
  );
});

SkillGenerateForm.displayName = 'SkillGenerateForm';
