'use client';

/**
 * SkillGenerationWizard - Three-path skill generation flow.
 *
 * Paths:
 * 1. Use Default — instant save with default template
 * 2. Describe Expertise — AI generates personalized skill
 * 3. Show Examples — educational, shows before/after comparisons
 *
 * T021: Create SkillGenerationWizard
 * Source: FR-001, FR-002, FR-003, FR-004, US1, US2
 */
import React, { useCallback, useRef, useEffect, useState } from 'react';
import { observer } from 'mobx-react-lite';
import {
  ArrowLeft,
  ArrowRight,
  FileText,
  Sparkles,
  Lightbulb,
  TriangleAlert,
  RefreshCw,
  Pencil,
  Check,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useRoleSkillStore } from '@/stores/RootStore';
import { useGenerateSkill, useCreateRoleSkill } from '../hooks/useRoleSkillActions';
import type { SDLCRoleType, RoleTemplate } from '@/services/api/role-skills';
import type { GenerationStep } from '@/stores/RoleSkillStore';

export interface SkillGenerationWizardProps {
  /** Role being configured. */
  roleType: SDLCRoleType;
  /** Template for this role (provides default_skill_content and display_name). */
  template: RoleTemplate | undefined;
  /** Workspace ID for API calls. */
  workspaceId: string;
  /** Called when Back is clicked (returns to role grid or previous role). */
  onBack: () => void;
  /** Called when skill is saved and wizard should advance (next role or finish). */
  onComplete: () => void;
  /** Current role index (1-based) if multi-role. */
  currentIndex?: number;
  /** Total roles being configured. */
  totalRoles?: number;
}

const MIN_DESCRIPTION_CHARS = 10;
const MAX_DESCRIPTION_CHARS = 5000;

export const SkillGenerationWizard = observer(function SkillGenerationWizard({
  roleType,
  template,
  workspaceId,
  onBack,
  onComplete,
  currentIndex = 1,
  totalRoles = 1,
}: SkillGenerationWizardProps) {
  const roleSkillStore = useRoleSkillStore();
  const generateSkillMutation = useGenerateSkill({ workspaceId });
  const createRoleSkillMutation = useCreateRoleSkill({ workspaceId });

  const step = roleSkillStore.generationStep ?? 'path';
  const roleName = template?.displayName ?? roleType.replace(/_/g, ' ');

  const [editableRoleName, setEditableRoleName] = useState(roleName);
  const [showError, setShowError] = useState(false);
  const descriptionRef = useRef<HTMLTextAreaElement>(null);

  // Focus management for step transitions
  useEffect(() => {
    if (step === 'describe' && descriptionRef.current) {
      descriptionRef.current.focus();
    }
  }, [step]);

  const handleSelectPath = useCallback(
    (path: GenerationStep) => {
      roleSkillStore.setGenerationStep(path);
    },
    [roleSkillStore]
  );

  const handleUseDefault = useCallback(() => {
    if (!template) return;
    setEditableRoleName(template.displayName);
    roleSkillStore.setSkillPreview({
      content: template.defaultSkillContent,
      suggestedName: template.displayName,
      wordCount: template.defaultSkillContent.split(/\s+/).length,
    });
    roleSkillStore.setGenerationStep('preview');
  }, [template, roleSkillStore]);

  const handleGenerate = useCallback(async () => {
    const description = roleSkillStore.experienceDescription;
    if (description.length < MIN_DESCRIPTION_CHARS) return;

    roleSkillStore.setGenerationStep('generating');
    roleSkillStore.setIsGenerating(true);
    setShowError(false);

    try {
      const result = await generateSkillMutation.mutateAsync({
        roleType: roleType,
        experienceDescription: description,
      });
      setEditableRoleName(result.suggestedRoleName);
      roleSkillStore.setSkillPreview({
        content: result.skillContent,
        suggestedName: result.suggestedRoleName,
        wordCount: result.wordCount,
      });
      roleSkillStore.setGenerationStep('preview');
    } catch {
      // Error fallback: show default template
      setShowError(true);
      if (template) {
        roleSkillStore.setSkillPreview({
          content: template.defaultSkillContent,
          suggestedName: template.displayName,
          wordCount: template.defaultSkillContent.split(/\s+/).length,
        });
        setEditableRoleName(template.displayName);
      }
      roleSkillStore.setGenerationStep('preview');
    } finally {
      roleSkillStore.setIsGenerating(false);
    }
  }, [roleSkillStore, roleType, template, generateSkillMutation]);

  const handleSave = useCallback(async () => {
    const preview = roleSkillStore.skillPreview;
    if (!preview) return;

    try {
      await createRoleSkillMutation.mutateAsync({
        roleType: roleType,
        roleName: editableRoleName || preview.suggestedName,
        skillContent: preview.content,
        experienceDescription: roleSkillStore.experienceDescription || undefined,
        isPrimary: roleSkillStore.selectedRoles[0] === roleType,
      });
      roleSkillStore.clearSkillPreview();
      roleSkillStore.setExperienceDescription('');
      roleSkillStore.setGenerationStep(null);
      onComplete();
    } catch {
      // Error toast handled by mutation hook
    }
  }, [roleSkillStore, roleType, editableRoleName, createRoleSkillMutation, onComplete]);

  const handleRetry = useCallback(() => {
    setShowError(false);
    roleSkillStore.clearSkillPreview();
    if (roleSkillStore.experienceDescription.length >= MIN_DESCRIPTION_CHARS) {
      handleGenerate();
    } else {
      roleSkillStore.setGenerationStep('describe');
    }
  }, [roleSkillStore, handleGenerate]);

  const headerText =
    totalRoles > 1
      ? `Skill Setup \u00b7 ${roleName} (${currentIndex} of ${totalRoles})`
      : `Skill Setup \u00b7 ${roleName}`;

  return (
    <div className="flex flex-col gap-4">
      {/* Header with back button */}
      {step !== 'generating' && (
        <div className="flex items-center justify-between">
          <button
            onClick={() => {
              if (step === 'describe' || step === 'examples') {
                handleSelectPath('path');
              } else if (step === 'preview') {
                handleSelectPath('path');
              } else {
                onBack();
              }
            }}
            className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
            aria-label="Back"
          >
            <ArrowLeft className="h-4 w-4" />
            Back
          </button>
          <span className="text-sm text-muted-foreground">{headerText}</span>
        </div>
      )}

      {/* Path Selection */}
      {step === 'path' && (
        <PathSelector
          roleName={roleName}
          onUseDefault={handleUseDefault}
          onDescribe={() => handleSelectPath('describe')}
          onExamples={() => handleSelectPath('examples')}
        />
      )}

      {/* Describe Expertise Input */}
      {step === 'describe' && (
        <DescribeExpertiseInput
          ref={descriptionRef}
          description={roleSkillStore.experienceDescription}
          onDescriptionChange={(text) => roleSkillStore.setExperienceDescription(text)}
          onGenerate={handleGenerate}
          isGenerating={false}
        />
      )}

      {/* Generating State */}
      {step === 'generating' && <GeneratingState roleName={roleName} />}

      {/* Preview */}
      {step === 'preview' && roleSkillStore.skillPreview && (
        <SkillPreviewView
          preview={roleSkillStore.skillPreview}
          editableRoleName={editableRoleName}
          onRoleNameChange={setEditableRoleName}
          showError={showError}
          roleName={roleName}
          onSave={handleSave}
          onRetry={handleRetry}
          isSaving={createRoleSkillMutation.isPending}
        />
      )}

      {/* Examples */}
      {step === 'examples' && (
        <ExamplesView roleName={roleName} onBack={() => handleSelectPath('path')} />
      )}
    </div>
  );
});

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

interface PathSelectorProps {
  roleName: string;
  onUseDefault: () => void;
  onDescribe: () => void;
  onExamples: () => void;
}

function PathSelector({ roleName, onUseDefault, onDescribe, onExamples }: PathSelectorProps) {
  return (
    <div className="flex flex-col gap-3">
      <div>
        <h3 className="text-lg font-semibold">Generate Your AI Skill</h3>
        <p className="mt-1 text-sm text-muted-foreground">
          How should we create your {roleName} skill? This shapes how the AI assistant helps you.
        </p>
      </div>

      {/* Path cards */}
      <div
        role="radiogroup"
        aria-label="Choose skill generation method"
        className="flex flex-col gap-3"
      >
        <PathCard
          icon={<FileText className="h-5 w-5 text-muted-foreground" />}
          title={`Use Default ${roleName} Skill`}
          description={`Start with the standard ${roleName} template. You can customize it later in Settings.`}
          actionLabel="Use"
          onClick={onUseDefault}
        />
        <PathCard
          icon={<Sparkles className="h-5 w-5 text-[#6B8FAD]" />}
          title="Describe Your Expertise"
          description="Tell us about your experience and the AI will generate a personalized skill tailored to you."
          actionLabel="Start"
          onClick={onDescribe}
          recommended
        />
        <PathCard
          icon={<Lightbulb className="h-5 w-5 text-muted-foreground" />}
          title="Show Me Examples"
          description={`See how the AI behaves with a ${roleName} skill before deciding.`}
          actionLabel="View"
          onClick={onExamples}
        />
      </div>
    </div>
  );
}

interface PathCardProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  actionLabel: string;
  onClick: () => void;
  recommended?: boolean;
}

function PathCard({ icon, title, description, actionLabel, onClick, recommended }: PathCardProps) {
  return (
    <button
      onClick={onClick}
      className="flex items-start gap-4 rounded-lg border border-border bg-background p-4 text-left transition-colors hover:border-primary hover:bg-primary/5 focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 outline-none"
      role="radio"
      aria-checked={false}
      aria-label={`${title}${recommended ? ', Recommended' : ''}`}
    >
      <div className="shrink-0 pt-0.5">{icon}</div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-medium text-sm">{title}</span>
          {recommended && (
            <span className="rounded-full bg-primary px-2 py-0.5 text-[10px] font-semibold text-white">
              REC
            </span>
          )}
        </div>
        <p className="mt-1 text-xs text-muted-foreground">{description}</p>
      </div>
      <div className="shrink-0">
        <span className="inline-flex items-center gap-1 text-sm font-medium text-primary">
          {actionLabel}
          <ArrowRight className="h-3.5 w-3.5" />
        </span>
      </div>
    </button>
  );
}

interface DescribeExpertiseInputProps {
  description: string;
  onDescriptionChange: (text: string) => void;
  onGenerate: () => void;
  isGenerating: boolean;
}

const DescribeExpertiseInput = React.forwardRef<HTMLTextAreaElement, DescribeExpertiseInputProps>(
  function DescribeExpertiseInput(
    { description, onDescriptionChange, onGenerate, isGenerating },
    ref
  ) {
    const charCount = description.length;
    const canGenerate = charCount >= MIN_DESCRIPTION_CHARS && !isGenerating;

    return (
      <div className="flex flex-col gap-4">
        <div>
          <h3 className="text-lg font-semibold">Describe Your Expertise</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            Tell us about your experience, specializations, and how you like to work. The more
            detail, the better the AI skill. We&apos;ll also generate a personalized role name from
            this.
          </p>
        </div>

        <div>
          <textarea
            ref={ref}
            value={description}
            onChange={(e) => onDescriptionChange(e.target.value.slice(0, MAX_DESCRIPTION_CHARS))}
            placeholder="Full-stack engineer with 5 years experience. TypeScript, React, Node.js, PostgreSQL. Strong focus on clean architecture and testing..."
            className="w-full rounded-[10px] border border-border bg-background p-3 text-sm placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/30 min-h-[180px] resize-y"
            maxLength={MAX_DESCRIPTION_CHARS}
            aria-label="Describe your expertise"
            aria-describedby="expertise-char-count expertise-min-hint"
            disabled={isGenerating}
          />
          <div className="mt-1 flex items-center justify-between">
            {charCount > 0 && charCount < MIN_DESCRIPTION_CHARS && (
              <p id="expertise-min-hint" className="text-xs text-muted-foreground">
                Min {MIN_DESCRIPTION_CHARS} characters required
              </p>
            )}
            <span className="flex-1" />
            <span
              id="expertise-char-count"
              className="text-xs text-muted-foreground"
              aria-live="polite"
            >
              {charCount} / {MAX_DESCRIPTION_CHARS} characters
            </span>
          </div>
        </div>

        <div className="flex justify-end">
          <Button
            onClick={onGenerate}
            disabled={!canGenerate}
            className="bg-[#6B8FAD] hover:bg-[#5A7D9A] text-white"
          >
            <Sparkles className="mr-1.5 h-4 w-4" />
            Generate Skill
          </Button>
        </div>
      </div>
    );
  }
);

interface GeneratingStateProps {
  roleName: string;
}

function GeneratingState({ roleName }: GeneratingStateProps) {
  const [progress, setProgress] = useState(0);

  // Simulate progress: 0% -> 90% over 25 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 90) return 90;
        return prev + (90 - prev) * 0.08;
      });
    }, 500);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex flex-col items-center justify-center py-12 gap-4">
      {/* Spinner */}
      <div className="flex gap-1.5" aria-hidden="true">
        <div className="h-2.5 w-2.5 animate-bounce rounded-full bg-[#6B8FAD] [animation-delay:0ms]" />
        <div className="h-2.5 w-2.5 animate-bounce rounded-full bg-[#6B8FAD] [animation-delay:150ms]" />
        <div className="h-2.5 w-2.5 animate-bounce rounded-full bg-[#6B8FAD] [animation-delay:300ms]" />
      </div>

      {/* Text */}
      <p className="text-base font-medium">Generating your {roleName} skill...</p>
      <p className="text-sm text-muted-foreground text-center max-w-sm">
        Our AI is crafting a personalized skill based on your expertise. This takes about 15-30
        seconds.
      </p>

      {/* Progress bar */}
      <div className="w-64">
        <div
          className="h-1 w-full rounded-full bg-border overflow-hidden"
          role="progressbar"
          aria-valuenow={Math.round(progress)}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="Skill generation progress"
        >
          <div
            className="h-full rounded-full bg-[#6B8FAD] transition-[width] duration-500 ease-out"
            style={{ width: `${progress}%` }}
          />
        </div>
        <p className="mt-1 text-center text-xs text-muted-foreground">{Math.round(progress)}%</p>
      </div>

      {/* Screen reader announcement */}
      <div className="sr-only" aria-live="assertive" role="status">
        Generating your {roleName} skill. Please wait.
      </div>
    </div>
  );
}

interface SkillPreviewViewProps {
  preview: { content: string; suggestedName: string; wordCount: number };
  editableRoleName: string;
  onRoleNameChange: (name: string) => void;
  showError: boolean;
  roleName: string;
  onSave: () => void;
  onRetry: () => void;
  isSaving: boolean;
}

function SkillPreviewView({
  preview,
  editableRoleName,
  onRoleNameChange,
  showError,
  roleName,
  onSave,
  onRetry,
  isSaving,
}: SkillPreviewViewProps) {
  return (
    <div className="flex flex-col gap-4">
      {/* Error banner */}
      {showError && (
        <div
          role="alert"
          className="flex items-start gap-3 rounded-lg border-l-4 border-l-[#D9853F] bg-[#FEF3CD] p-3"
        >
          <TriangleAlert className="h-5 w-5 shrink-0 text-[#D9853F]" />
          <div className="text-sm">
            <p className="font-medium">Skill generation unavailable</p>
            <p className="mt-1 text-muted-foreground">
              We couldn&apos;t reach the AI provider. We&apos;ve loaded the default {roleName}{' '}
              template instead. Your experience description has been saved &mdash; you can retry
              generation later from Settings.
            </p>
          </div>
        </div>
      )}

      {/* Header with AI badge */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Check className="h-5 w-5 text-primary" />
          <h3 className="text-lg font-semibold">Your Skill</h3>
        </div>
        {!showError && (
          <span className="rounded-full bg-[#6B8FAD]/10 px-2.5 py-0.5 text-xs font-medium text-[#6B8FAD]">
            Generated by AI
          </span>
        )}
      </div>

      {/* Editable role name */}
      <div>
        <label htmlFor="role-name-input" className="text-xs text-muted-foreground">
          Role Name (auto-generated &mdash; click to edit)
        </label>
        <div className="relative mt-1">
          <input
            id="role-name-input"
            type="text"
            value={editableRoleName}
            onChange={(e) => onRoleNameChange(e.target.value)}
            className="w-full rounded-[10px] border border-border bg-background px-3 py-2 pr-8 text-base font-semibold focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/30"
            aria-label="Role name. Auto-generated by AI. Click to edit."
          />
          <Pencil
            className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground pointer-events-none"
            aria-hidden="true"
          />
        </div>
      </div>

      {/* Skill content preview */}
      <div
        className="max-h-[400px] overflow-y-auto rounded-lg border bg-[#F7F5F2] p-4"
        aria-label="Generated skill preview"
      >
        <pre className="whitespace-pre-wrap font-mono text-sm leading-relaxed">
          {preview.content}
        </pre>
      </div>

      {/* Word count */}
      <div className="text-right" aria-live="polite">
        <span
          className={`text-xs ${preview.wordCount >= 1800 ? 'text-destructive' : 'text-muted-foreground'}`}
        >
          {preview.wordCount} / 2000 words
        </span>
      </div>

      {/* Action buttons */}
      <div className="flex items-center gap-2">
        <Button onClick={onSave} disabled={isSaving}>
          {isSaving ? 'Saving...' : 'Save & Activate'}
        </Button>
        <Button variant="outline" onClick={onRetry} disabled={isSaving}>
          <RefreshCw className="mr-1.5 h-4 w-4" />
          Retry
        </Button>
      </div>
    </div>
  );
}

interface ExamplesViewProps {
  roleName: string;
  onBack: () => void;
}

function ExamplesView({ roleName, onBack }: ExamplesViewProps) {
  return (
    <div className="flex flex-col gap-4">
      <div>
        <h3 className="text-lg font-semibold">How a {roleName} Skill Changes AI Behavior</h3>
      </div>

      {/* Example 1 */}
      <div className="rounded-lg border p-4 space-y-3">
        <p className="text-sm font-medium">Example 1: Reviewing an Issue</p>
        <p className="text-xs text-muted-foreground">
          You ask: &quot;Review this issue about adding caching&quot;
        </p>

        <div className="rounded-lg bg-[#F7F5F2] border p-3">
          <p className="text-xs font-medium text-muted-foreground mb-2">Without skill</p>
          <ul className="text-xs space-y-1 text-muted-foreground">
            <li>- Consider what data to cache</li>
            <li>- Think about cache invalidation</li>
            <li>- Review performance requirements</li>
          </ul>
        </div>

        <div className="rounded-lg bg-[#6B8FAD]/10 border border-[#6B8FAD]/30 p-3">
          <p className="text-xs font-medium text-[#6B8FAD] mb-2">
            <Sparkles className="inline h-3 w-3 mr-1" />
            With {roleName} skill
          </p>
          <ul className="text-xs space-y-1">
            <li>- Use Redis with read-through pattern</li>
            <li>- Set TTL based on data volatility (30m hot, 7d cold)</li>
            <li>- Add cache-aside for frequently queried endpoints</li>
            <li>- Watch for N+1 in the repository layer</li>
            <li>- Suggest: Add integration test for cache miss</li>
          </ul>
        </div>
      </div>

      {/* Example 2 */}
      <div className="rounded-lg border p-4 space-y-3">
        <p className="text-sm font-medium">Example 2: Writing a Note</p>
        <p className="text-xs text-muted-foreground">You write about a new feature design</p>

        <div className="rounded-lg bg-[#F7F5F2] border p-3">
          <p className="text-xs font-medium text-muted-foreground mb-2">Without skill</p>
          <p className="text-xs text-muted-foreground">
            Generic suggestions about feature requirements and user stories.
          </p>
        </div>

        <div className="rounded-lg bg-[#6B8FAD]/10 border border-[#6B8FAD]/30 p-3">
          <p className="text-xs font-medium text-[#6B8FAD] mb-2">
            <Sparkles className="inline h-3 w-3 mr-1" />
            With {roleName} skill
          </p>
          <p className="text-xs">
            Role-specific suggestions tailored to your expertise, tools, and workflow preferences.
          </p>
        </div>
      </div>

      <div className="flex justify-center">
        <Button variant="outline" onClick={onBack}>
          <ArrowLeft className="mr-1.5 h-4 w-4" />
          Back to Options
        </Button>
      </div>
    </div>
  );
}
