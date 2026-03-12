/**
 * SkillGeneratorModal — Unified two-panel modal for generating skills.
 *
 * Single modal with a personal/workspace toggle. Users describe their
 * expertise, AI generates skill name and content.
 *
 * Left panel: mode toggle + experience textarea + action buttons.
 * Right panel: writing guide with tips.
 *
 * Phase 20: Replaces separate role-selector + wizard and workspace-generate dialogs.
 */

'use client';

import * as React from 'react';
import {
  ArrowLeft,
  Check,
  Pencil,
  RefreshCw,
  TriangleAlert,
  User,
  Users,
  Wand2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';
import { useGenerateSkill, useCreateRoleSkill } from '@/features/onboarding/hooks';
import { useGenerateWorkspaceSkill } from '@/services/api/workspace-role-skills';
import { useCreateUserSkill } from '@/services/api/user-skills';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type SkillGeneratorMode = 'personal' | 'workspace';

type Step = 'form' | 'generating' | 'preview';

interface SkillPreview {
  content: string;
  suggestedName: string;
  wordCount: number;
}

export interface SkillGeneratorModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Initial mode — user can switch inside the modal. */
  defaultMode?: SkillGeneratorMode;
  /** Hide mode toggle (e.g. non-admin users can only create personal). */
  showModeToggle?: boolean;
  workspaceId: string;
  /** Workspace slug for API calls. Falls back to workspaceId if not provided. */
  workspaceSlug?: string;
  /** Pre-seed from a template — shows template name in header and pre-fills description. */
  template?: { id: string; name: string; description: string; skill_content: string } | null;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const MIN_CHARS = 10;
const MAX_CHARS = 5000;

const PLACEHOLDER = `e.g. Senior backend developer with 8 years of Python/FastAPI experience.
Focused on clean architecture, async patterns, and PostgreSQL optimization.
Prefer concise code reviews with security-first mindset.`;

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export function SkillGeneratorModal({
  open,
  onOpenChange,
  defaultMode = 'personal',
  showModeToggle = true,
  workspaceId,
  workspaceSlug,
  template = null,
}: SkillGeneratorModalProps) {
  const [mode, setMode] = React.useState<SkillGeneratorMode>(defaultMode);
  const [step, setStep] = React.useState<Step>('form');
  const [description, setDescription] = React.useState('');
  const [preview, setPreview] = React.useState<SkillPreview | null>(null);
  const [editableName, setEditableName] = React.useState('');
  const [showError, setShowError] = React.useState(false);

  // Reset mode when defaultMode changes (e.g. different button clicked)
  React.useEffect(() => {
    if (open) setMode(defaultMode);
  }, [open, defaultMode]);

  // Pre-fill description from template when opened with a template
  React.useEffect(() => {
    if (open && template) {
      setDescription(template.description);
    }
  }, [open, template]);

  // Personal skill mutations
  const generatePersonal = useGenerateSkill({ workspaceId });
  const createPersonal = useCreateRoleSkill({ workspaceId });

  // Workspace skill mutation
  const generateWorkspace = useGenerateWorkspaceSkill({ workspaceId });

  // New user_skills table mutation (Phase 20)
  const createUserSkill = useCreateUserSkill(workspaceSlug || workspaceId);

  const isPending =
    generatePersonal.isPending ||
    createPersonal.isPending ||
    generateWorkspace.isPending ||
    createUserSkill.isPending;

  const reset = React.useCallback(() => {
    setStep('form');
    setDescription('');
    setPreview(null);
    setEditableName('');
    setShowError(false);
  }, []);

  const handleClose = React.useCallback(() => {
    onOpenChange(false);
    setTimeout(reset, 200);
  }, [onOpenChange, reset]);

  const handleGenerate = React.useCallback(async () => {
    if (description.length < MIN_CHARS) return;
    setStep('generating');
    setShowError(false);

    try {
      if (mode === 'personal') {
        const result = await generatePersonal.mutateAsync({
          roleType: 'custom',
          experienceDescription: description,
        });
        setPreview({
          content: result.skillContent,
          suggestedName: result.suggestedRoleName,
          wordCount: result.wordCount,
        });
        setEditableName(result.suggestedRoleName);
      } else {
        const skill = await generateWorkspace.mutateAsync({
          experience_description: description,
        });
        setPreview({
          content: skill.skill_content,
          suggestedName: skill.role_name,
          wordCount: skill.skill_content.split(/\s+/).length,
        });
        setEditableName(skill.role_name);
      }
      setStep('preview');
    } catch {
      setShowError(true);
      setStep('form');
    }
  }, [description, mode, generatePersonal, generateWorkspace]);

  const handleSave = React.useCallback(async () => {
    if (!preview) return;

    if (mode === 'personal') {
      try {
        // If seeded from a template, save to user_skills table (Phase 20)
        if (template?.id) {
          await createUserSkill.mutateAsync({
            template_id: template.id,
            experience_description: description || undefined,
          });
        } else {
          // Legacy path for custom skills without a template
          await createPersonal.mutateAsync({
            roleType: 'custom',
            roleName: editableName || preview.suggestedName,
            skillContent: preview.content,
            experienceDescription: description || undefined,
            isPrimary: false,
          });
        }
        handleClose();
      } catch {
        // Error toast from mutation hook
      }
    } else {
      // Workspace skill already persisted during generate
      handleClose();
    }
  }, [
    preview,
    mode,
    editableName,
    description,
    createPersonal,
    createUserSkill,
    template,
    handleClose,
  ]);

  const handleRetry = React.useCallback(() => {
    setShowError(false);
    setPreview(null);
    setStep('form');
  }, []);

  return (
    <Dialog open={open} onOpenChange={(v) => !v && handleClose()}>
      <DialogContent className="sm:max-w-3xl p-0 gap-0 overflow-hidden">
        <div className="grid sm:grid-cols-[1fr_280px] min-h-[460px]">
          {/* Left: Main content area */}
          <div className="p-6 flex flex-col">
            {step === 'form' && (
              <FormStep
                mode={mode}
                onModeChange={setMode}
                showModeToggle={showModeToggle}
                description={description}
                onDescriptionChange={setDescription}
                onGenerate={handleGenerate}
                onCancel={handleClose}
                isPending={isPending}
                showError={showError}
                templateName={template?.name}
              />
            )}
            {step === 'generating' && <GeneratingStep />}
            {step === 'preview' && preview && (
              <PreviewStep
                preview={preview}
                editableName={editableName}
                onNameChange={setEditableName}
                onSave={handleSave}
                onRetry={handleRetry}
                onBack={() => setStep('form')}
                isSaving={createPersonal.isPending}
                mode={mode}
              />
            )}
          </div>

          {/* Right: Guide panel */}
          <div className="border-l bg-muted/30 p-5 space-y-4 hidden sm:flex sm:flex-col">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Writing Guide
            </h4>
            <div className="space-y-3">
              <GuideItem
                title="Role & Seniority"
                example="Senior backend developer, Lead QA engineer"
              />
              <GuideItem title="Tech Stack" example="Python, FastAPI, PostgreSQL, React" />
              <GuideItem title="Focus Areas" example="Clean architecture, security, performance" />
              <GuideItem title="Work Style" example="Concise reviews, TDD, pair programming" />
            </div>
            <div className="rounded-md bg-primary/5 border border-primary/10 p-3 mt-auto">
              <p className="text-xs text-muted-foreground leading-relaxed">
                <span className="font-medium text-foreground">Tip:</span> The more specific your
                description, the better the AI personalizes the skill.
              </p>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function GuideItem({ title, example }: { title: string; example: string }) {
  return (
    <div>
      <p className="text-xs font-medium text-foreground">{title}</p>
      <p className="text-xs text-muted-foreground italic">&quot;{example}&quot;</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Mode Toggle
// ---------------------------------------------------------------------------

function ModeToggle({
  mode,
  onChange,
}: {
  mode: SkillGeneratorMode;
  onChange: (mode: SkillGeneratorMode) => void;
}) {
  return (
    <div
      className="flex rounded-lg border bg-muted/50 p-0.5 gap-0.5"
      role="radiogroup"
      aria-label="Skill scope"
    >
      <button
        role="radio"
        aria-checked={mode === 'personal'}
        onClick={() => onChange('personal')}
        className={cn(
          'flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors',
          mode === 'personal'
            ? 'bg-background text-foreground shadow-sm'
            : 'text-muted-foreground hover:text-foreground'
        )}
      >
        <User className="h-3.5 w-3.5" />
        For Me
      </button>
      <button
        role="radio"
        aria-checked={mode === 'workspace'}
        onClick={() => onChange('workspace')}
        className={cn(
          'flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors',
          mode === 'workspace'
            ? 'bg-background text-foreground shadow-sm'
            : 'text-muted-foreground hover:text-foreground'
        )}
      >
        <Users className="h-3.5 w-3.5" />
        For Workspace
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Form Step
// ---------------------------------------------------------------------------

interface FormStepProps {
  mode: SkillGeneratorMode;
  onModeChange: (mode: SkillGeneratorMode) => void;
  showModeToggle: boolean;
  description: string;
  onDescriptionChange: (text: string) => void;
  onGenerate: () => void;
  onCancel: () => void;
  isPending: boolean;
  showError: boolean;
  templateName?: string;
}

function FormStep({
  mode,
  onModeChange,
  showModeToggle,
  description,
  onDescriptionChange,
  onGenerate,
  onCancel,
  isPending,
  showError,
  templateName,
}: FormStepProps) {
  const canGenerate = description.length >= MIN_CHARS;
  const wordCount = description.trim().split(/\s+/).filter(Boolean).length;

  const subtitle =
    mode === 'personal'
      ? 'Describe your expertise. AI generates a personalized skill for you.'
      : 'Describe this skill. AI generates content inherited by all workspace members.';

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onGenerate();
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col flex-1">
      <DialogHeader className="mb-3">
        <div className="flex items-center justify-between gap-3">
          <DialogTitle className="flex items-center gap-2">
            <Wand2 className="h-5 w-5 text-primary" />
            {templateName ? `Generate from "${templateName}"` : 'Generate Skill'}
          </DialogTitle>
          {showModeToggle && !templateName && <ModeToggle mode={mode} onChange={onModeChange} />}
        </div>
        <p className="text-sm text-muted-foreground mt-1.5">{subtitle}</p>
      </DialogHeader>

      {showError && (
        <div
          role="alert"
          className="flex items-start gap-3 rounded-lg border-l-4 border-l-amber-500 bg-amber-50 dark:bg-amber-950/20 p-3 mb-3"
        >
          <TriangleAlert className="h-4 w-4 shrink-0 text-amber-500 mt-0.5" />
          <p className="text-sm text-muted-foreground">
            Generation failed. Check your AI provider settings or try again.
          </p>
        </div>
      )}

      <div className="space-y-1.5 flex-1">
        <Label htmlFor="skill-description">Experience Description</Label>
        <Textarea
          id="skill-description"
          value={description}
          onChange={(e) => onDescriptionChange(e.target.value.slice(0, MAX_CHARS))}
          placeholder={PLACEHOLDER}
          rows={10}
          className="resize-none flex-1 min-h-[200px]"
          required
        />
        <div className="flex items-center justify-between">
          {description.length > 0 && description.length < MIN_CHARS ? (
            <p className="text-xs text-muted-foreground">Min {MIN_CHARS} characters required</p>
          ) : (
            <span />
          )}
          <p className="text-xs text-muted-foreground">{wordCount} words</p>
        </div>
      </div>

      <div className="flex justify-end gap-2 pt-3">
        <Button type="button" variant="outline" onClick={onCancel} disabled={isPending}>
          Cancel
        </Button>
        <Button type="submit" disabled={!canGenerate || isPending}>
          {isPending ? (
            <>
              <span className="mr-1.5 h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent inline-block" />
              Generating…
            </>
          ) : (
            <>
              <Wand2 className="mr-1.5 h-4 w-4" />
              Generate
            </>
          )}
        </Button>
      </div>
    </form>
  );
}

// ---------------------------------------------------------------------------
// Generating Step
// ---------------------------------------------------------------------------

function GeneratingStep() {
  const [progress, setProgress] = React.useState(0);

  React.useEffect(() => {
    const interval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 90) return 90;
        return prev + (90 - prev) * 0.08;
      });
    }, 500);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex flex-col items-center justify-center flex-1 gap-4 py-8">
      <div className="flex gap-1.5" aria-hidden="true">
        <div className="h-2.5 w-2.5 animate-bounce rounded-full bg-primary [animation-delay:0ms]" />
        <div className="h-2.5 w-2.5 animate-bounce rounded-full bg-primary [animation-delay:150ms]" />
        <div className="h-2.5 w-2.5 animate-bounce rounded-full bg-primary [animation-delay:300ms]" />
      </div>
      <p className="text-base font-medium">Generating your skill...</p>
      <p className="text-sm text-muted-foreground text-center max-w-sm">
        AI is crafting a personalized skill based on your description. This takes about 15–30
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
// Preview Step
// ---------------------------------------------------------------------------

interface PreviewStepProps {
  preview: SkillPreview;
  editableName: string;
  onNameChange: (name: string) => void;
  onSave: () => void;
  onRetry: () => void;
  onBack: () => void;
  isSaving: boolean;
  mode: SkillGeneratorMode;
}

function PreviewStep({
  preview,
  editableName,
  onNameChange,
  onSave,
  onRetry,
  onBack,
  isSaving,
  mode,
}: PreviewStepProps) {
  const saveLabel = mode === 'personal' ? 'Save & Activate' : 'Done';

  return (
    <div className="flex flex-col flex-1 gap-3">
      <button
        onClick={onBack}
        className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground self-start"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to edit
      </button>

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Check className="h-5 w-5 text-primary" />
          <h3 className="text-base font-semibold">Skill Preview</h3>
        </div>
        <span className="rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-medium text-primary">
          Generated by AI
        </span>
      </div>

      <div>
        <label htmlFor="skill-name" className="text-xs text-muted-foreground">
          Skill Name (auto-generated — click to edit)
        </label>
        <div className="relative mt-1">
          <input
            id="skill-name"
            type="text"
            value={editableName}
            onChange={(e) => onNameChange(e.target.value)}
            className="w-full rounded-md border border-border bg-background px-3 py-2 pr-8 text-sm font-semibold focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/30"
          />
          <Pencil
            className="absolute right-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground pointer-events-none"
            aria-hidden="true"
          />
        </div>
      </div>

      <div
        className="flex-1 max-h-[220px] overflow-y-auto rounded-md border bg-muted/30 p-3"
        aria-label="Generated skill preview"
      >
        <pre className="whitespace-pre-wrap font-mono text-xs leading-relaxed">
          {preview.content}
        </pre>
      </div>

      <div className="text-right">
        <span
          className={`text-xs ${preview.wordCount >= 1800 ? 'text-destructive' : 'text-muted-foreground'}`}
        >
          {preview.wordCount} / 2000 words
        </span>
      </div>

      <div className="flex items-center gap-2">
        <Button onClick={onSave} disabled={isSaving} size="sm">
          {isSaving ? 'Saving...' : saveLabel}
        </Button>
        <Button variant="outline" onClick={onRetry} disabled={isSaving} size="sm">
          <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
          Retry
        </Button>
      </div>
    </div>
  );
}

export default SkillGeneratorModal;
