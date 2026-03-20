/**
 * SkillAddModal sub-components: TagChipInput, AiFormStep, GeneratingStep, AiPreviewStep.
 * Extracted to keep the parent modal file within the 700-line limit.
 */

'use client';

import * as React from 'react';
import { ArrowLeft, Check, Pencil, TriangleAlert, Wand2, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';
import { WordCountBar } from './word-count-bar';

// ---------------------------------------------------------------------------
// TagChipInput
// ---------------------------------------------------------------------------

const MAX_TAGS = 20;
const MAX_TAG_LENGTH = 30;

export { MAX_TAGS, MAX_TAG_LENGTH };

export function TagChipInput({
  tags,
  onChange,
  id,
}: {
  tags: string[];
  onChange: (tags: string[]) => void;
  id?: string;
}) {
  const [inputValue, setInputValue] = React.useState('');

  const addTag = React.useCallback(
    (raw: string) => {
      const normalized = raw.trim().toLowerCase().replace(/,+$/, '').slice(0, MAX_TAG_LENGTH);
      if (!normalized || tags.includes(normalized) || tags.length >= MAX_TAGS) return;
      onChange([...tags, normalized]);
    },
    [tags, onChange]
  );

  const removeTag = React.useCallback(
    (index: number) => {
      onChange(tags.filter((_, i) => i !== index));
    },
    [tags, onChange]
  );

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      addTag(inputValue);
      setInputValue('');
    } else if (e.key === 'Backspace' && inputValue === '' && tags.length > 0) {
      removeTag(tags.length - 1);
    }
  };

  return (
    <div
      className={cn(
        'flex flex-wrap gap-1.5 rounded-md border bg-background px-3 py-2 min-h-[40px]',
        'focus-within:ring-[3px] focus-within:ring-primary/30 focus-within:border-primary'
      )}
      aria-label="Tags input"
    >
      {tags.map((tag, i) => (
        <span
          key={tag}
          className="inline-flex items-center gap-1 rounded-full border bg-muted px-2.5 py-0.5 text-xs font-medium"
        >
          {tag}
          <button
            type="button"
            onClick={() => removeTag(i)}
            className="ml-0.5 rounded-full hover:bg-muted-foreground/20 focus-visible:outline-none focus-visible:ring-1"
            aria-label={`Remove tag ${tag}`}
          >
            <X className="h-3 w-3 text-muted-foreground" />
          </button>
        </span>
      ))}
      {tags.length < MAX_TAGS && (
        <input
          id={id}
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          onBlur={() => {
            if (inputValue.trim()) {
              addTag(inputValue);
              setInputValue('');
            }
          }}
          placeholder={tags.length === 0 ? 'python, backend, fastapi...' : ''}
          className="flex-1 min-w-[120px] bg-transparent text-xs outline-none placeholder:text-muted-foreground"
          aria-label="Add tag"
        />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// AiFormStep
// ---------------------------------------------------------------------------

const AI_MIN_CHARS = 10;
const AI_MAX_CHARS = 5000;

export { AI_MIN_CHARS, AI_MAX_CHARS };

const AI_PLACEHOLDER = `e.g. Senior backend developer with 8 years of Python/FastAPI experience.
Focused on clean architecture, async patterns, and PostgreSQL optimization.
Prefer concise code reviews with security-first mindset.`;

export function AiFormStep({
  description,
  onDescriptionChange,
  showError,
  templateName,
}: {
  description: string;
  onDescriptionChange: (text: string) => void;
  showError: boolean;
  templateName?: string;
}) {
  const wordCount = description.trim().split(/\s+/).filter(Boolean).length;
  return (
    <div className="space-y-4">
      {templateName && (
        <div className="flex items-center gap-2">
          <Wand2 className="h-4 w-4 text-primary" />
          <span className="text-sm font-medium">Generate from &quot;{templateName}&quot;</span>
        </div>
      )}
      <p className="text-sm text-muted-foreground">
        Describe your expertise. AI generates a personalized skill for you.
      </p>
      {showError && (
        <div
          role="alert"
          className="flex items-start gap-3 rounded-lg border-l-4 border-l-amber-500 bg-amber-50 dark:bg-amber-950/20 p-3"
        >
          <TriangleAlert className="h-4 w-4 shrink-0 text-amber-500 mt-0.5" />
          <p className="text-sm text-muted-foreground">
            Generation failed. Check your AI provider settings or try again.
          </p>
        </div>
      )}
      <div className="space-y-1.5">
        <Label htmlFor="ai-skill-description">Experience Description</Label>
        <Textarea
          id="ai-skill-description"
          value={description}
          onChange={(e) => onDescriptionChange(e.target.value.slice(0, AI_MAX_CHARS))}
          placeholder={AI_PLACEHOLDER}
          rows={10}
          className="resize-none min-h-[260px]"
        />
        <div className="flex items-center justify-between">
          {description.trim().length > 0 && description.trim().length < AI_MIN_CHARS ? (
            <p className="text-xs text-muted-foreground">Min {AI_MIN_CHARS} characters required</p>
          ) : (
            <span />
          )}
          <p className="text-xs text-muted-foreground">{wordCount} words</p>
        </div>
      </div>
      <div className="rounded-md bg-primary/5 border border-primary/10 p-3 mt-4">
        <p className="text-xs text-muted-foreground leading-relaxed">
          <span className="font-medium text-foreground">Tip:</span> The more specific your
          description, the better the AI personalizes the skill.
        </p>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// GeneratingStep
// ---------------------------------------------------------------------------

export function GeneratingStep() {
  const [progress, setProgress] = React.useState(0);
  React.useEffect(() => {
    if (progress >= 90) return;
    const id = setTimeout(() => {
      setProgress((p) => Math.min(90, p + Math.max(1, (90 - p) * 0.08)));
    }, 500);
    return () => clearTimeout(id);
  }, [progress]);
  return (
    <div className="flex flex-col items-center justify-center flex-1 gap-4 py-8">
      <div className="flex gap-1.5" aria-hidden="true">
        <div className="h-2.5 w-2.5 animate-bounce rounded-full bg-primary [animation-delay:0ms]" />
        <div className="h-2.5 w-2.5 animate-bounce rounded-full bg-primary [animation-delay:150ms]" />
        <div className="h-2.5 w-2.5 animate-bounce rounded-full bg-primary [animation-delay:300ms]" />
      </div>
      <p className="text-base font-medium">Generating your skill...</p>
      <p className="text-sm text-muted-foreground text-center max-w-sm">
        AI is crafting a personalized skill based on your description. This takes about 15-30
        seconds.
      </p>
      <div className="w-52">
        <div
          className="h-1 w-full rounded-full bg-border overflow-hidden"
          role="progressbar"
          aria-valuenow={Math.round(progress)}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="Skill generation progress"
        >
          <div
            className="h-full rounded-full bg-primary transition-[width] duration-500 ease-out"
            style={{ width: `${progress}%` }}
          />
        </div>
        <p className="mt-1 text-center text-xs text-muted-foreground">{Math.round(progress)}%</p>
      </div>
      <div className="sr-only" aria-live="assertive" role="status">
        Generating your skill. Please wait.
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// AiPreviewStep
// ---------------------------------------------------------------------------

const MAX_WORDS = 2000;

export function AiPreviewStep({
  editableName,
  onNameChange,
  editableContent,
  onContentChange,
  editableTags,
  onTagsChange,
  editableUsage,
  onUsageChange,
  wordCount,
  isReadOnly,
  onBack,
}: {
  editableName: string;
  onNameChange: (n: string) => void;
  editableContent: string;
  onContentChange: (c: string) => void;
  editableTags: string[];
  onTagsChange: (tags: string[]) => void;
  editableUsage: string;
  onUsageChange: (usage: string) => void;
  wordCount: number;
  isReadOnly: boolean;
  onBack: () => void;
}) {
  return (
    <div className="space-y-4">
      <Button
        variant="ghost"
        size="sm"
        onClick={onBack}
        className="text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="mr-1.5 h-4 w-4" />
        Back to description
      </Button>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Check className="h-5 w-5 text-primary" />
          <h3 className="text-base font-semibold">Skill Preview</h3>
        </div>
        <span className="rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-medium text-primary">
          Generated by AI
        </span>
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="ai-skill-name">
          {isReadOnly ? 'Skill Name' : 'Skill Name (auto-generated - click to edit)'}
        </Label>
        <div className="relative">
          <Input
            id="ai-skill-name"
            value={editableName}
            onChange={(e) => onNameChange(e.target.value)}
            readOnly={isReadOnly}
            className={cn('pr-8 font-semibold', isReadOnly && 'opacity-60 cursor-default')}
          />
          {!isReadOnly && (
            <Pencil
              className="absolute right-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground pointer-events-none"
              aria-hidden="true"
            />
          )}
        </div>
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="ai-skill-content">Generated Content</Label>
        <Textarea
          id="ai-skill-content"
          value={editableContent}
          onChange={(e) => onContentChange(e.target.value)}
          readOnly={isReadOnly}
          className={cn(
            'min-h-[280px] max-h-[400px] font-mono text-xs leading-relaxed resize-y',
            isReadOnly && 'opacity-60 cursor-default'
          )}
        />
        <WordCountBar wordCount={wordCount} maxWords={MAX_WORDS} />
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="ai-preview-usage">
          {isReadOnly ? 'Usage' : 'Usage (AI suggested - click to edit)'}
        </Label>
        <Textarea
          id="ai-preview-usage"
          value={editableUsage}
          onChange={(e) => onUsageChange(e.target.value.slice(0, 500))}
          readOnly={isReadOnly}
          placeholder="When and how this skill is applied..."
          rows={2}
          className={cn('resize-none', isReadOnly && 'opacity-60 cursor-default')}
        />
      </div>
      <div className="space-y-1.5">
        <Label>{isReadOnly ? 'Tags' : 'Tags (AI suggested - click chips to remove)'}</Label>
        {isReadOnly ? (
          editableTags.length > 0 ? (
            <div className="flex flex-wrap gap-1.5">
              {editableTags.map((tag) => (
                <span
                  key={tag}
                  className="inline-flex items-center rounded-full border bg-muted px-2.5 py-0.5 text-xs font-medium"
                >
                  {tag}
                </span>
              ))}
            </div>
          ) : (
            <p className="text-xs text-muted-foreground">No tags suggested</p>
          )
        ) : (
          <TagChipInput tags={editableTags} onChange={onTagsChange} />
        )}
      </div>
    </div>
  );
}
