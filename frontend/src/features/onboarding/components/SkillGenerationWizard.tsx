'use client';

/**
 * SkillGenerationWizard - Single-form skill generation with two-panel layout.
 *
 * Left panel: "Describe Your Expertise" textarea (pre-filled per role).
 * Right panel: Role-specific before/after examples.
 * Bottom: Generate Skill + Use Default Template actions.
 *
 * T021: Create SkillGenerationWizard
 * Source: FR-001, FR-002, FR-003, FR-004, US1, US2
 */
import { useCallback, useEffect, useState } from 'react';
import { observer } from 'mobx-react-lite';
import {
  ArrowLeft,
  Sparkles,
  FileText,
  TriangleAlert,
  RefreshCw,
  Pencil,
  Check,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useRoleSkillStore } from '@/stores/RootStore';
import { useGenerateSkill, useCreateRoleSkill } from '../hooks/useRoleSkillActions';
import { ROLE_SAMPLE_DESCRIPTIONS, ROLE_EXAMPLES } from '../constants/skill-wizard-constants';
import type { SDLCRoleType, RoleTemplate } from '@/services/api/role-skills';
import type { SkillExample } from '../constants/skill-wizard-constants';

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

  const step = roleSkillStore.generationStep ?? 'form';
  const roleName = template?.displayName ?? roleType.replace(/_/g, ' ');

  const [editableRoleName, setEditableRoleName] = useState(roleName);
  const [showError, setShowError] = useState(false);

  // Pre-fill expertise description from role sample when entering form step
  useEffect(() => {
    if (step === 'form' && roleSkillStore.experienceDescription === '') {
      const sample = ROLE_SAMPLE_DESCRIPTIONS[roleType];
      if (sample) {
        roleSkillStore.setExperienceDescription(sample);
      }
    }
  }, [step, roleType, roleSkillStore]);

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
      roleSkillStore.setGenerationStep('form');
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
              if (step === 'preview') {
                roleSkillStore.setGenerationStep('form');
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

      {/* Skill Form — two-panel layout */}
      {step === 'form' && (
        <SkillFormView
          roleName={roleName}
          roleType={roleType}
          description={roleSkillStore.experienceDescription}
          onDescriptionChange={(text) => roleSkillStore.setExperienceDescription(text)}
          onGenerate={handleGenerate}
          onUseDefault={handleUseDefault}
          hasTemplate={!!template}
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
    </div>
  );
});

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

interface SkillFormViewProps {
  roleName: string;
  roleType: SDLCRoleType;
  description: string;
  onDescriptionChange: (text: string) => void;
  onGenerate: () => void;
  onUseDefault: () => void;
  hasTemplate: boolean;
}

function SkillFormView({
  roleName,
  roleType,
  description,
  onDescriptionChange,
  onGenerate,
  onUseDefault,
  hasTemplate,
}: SkillFormViewProps) {
  const charCount = description.length;
  const canGenerate = charCount >= MIN_DESCRIPTION_CHARS;
  const examples = ROLE_EXAMPLES[roleType] ?? [];

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h3 className="text-lg font-semibold">Generate Your AI Skill</h3>
        <p className="mt-1 text-sm text-muted-foreground">
          Describe your expertise to generate a personalized {roleName} skill.
        </p>
      </div>

      {/* Two-column layout */}
      <div className="flex flex-col md:flex-row gap-4">
        {/* Left panel — Describe Expertise */}
        <div className="flex-[3] flex flex-col gap-3">
          <label htmlFor="expertise-textarea" className="text-sm font-medium">
            Describe Your Expertise
          </label>
          <textarea
            id="expertise-textarea"
            value={description}
            onChange={(e) => onDescriptionChange(e.target.value.slice(0, MAX_DESCRIPTION_CHARS))}
            placeholder="Tell us about your experience, specializations, and how you work..."
            className="w-full rounded-[10px] border border-border bg-background p-3 text-sm placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/30 min-h-[200px] resize-y"
            maxLength={MAX_DESCRIPTION_CHARS}
            aria-label="Describe your expertise"
            aria-describedby="expertise-char-count"
          />
          <div className="flex items-center justify-between">
            {charCount > 0 && charCount < MIN_DESCRIPTION_CHARS && (
              <p className="text-xs text-muted-foreground">
                Min {MIN_DESCRIPTION_CHARS} characters required
              </p>
            )}
            <span className="flex-1" />
            <span id="expertise-char-count" className="text-xs text-muted-foreground" aria-live="polite">
              {charCount} / {MAX_DESCRIPTION_CHARS}
            </span>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-3">
            <Button
              onClick={onGenerate}
              disabled={!canGenerate}
              className="bg-[#6B8FAD] hover:bg-[#5A7D9A] text-white"
            >
              <Sparkles className="mr-1.5 h-4 w-4" />
              Generate Skill
            </Button>
            {hasTemplate && (
              <button
                onClick={onUseDefault}
                className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
              >
                <FileText className="h-4 w-4" />
                Use Default Template
              </button>
            )}
          </div>
        </div>

        {/* Right panel — Role Examples */}
        {examples.length > 0 && (
          <div className="flex-[2] flex flex-col gap-3">
            <p className="text-sm font-medium">
              How a {roleName} Skill Changes AI Behavior
            </p>
            {examples.map((ex) => (
              <ExampleCard key={ex.title} example={ex} roleName={roleName} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

interface ExampleCardProps {
  example: SkillExample;
  roleName: string;
}

function ExampleCard({ example, roleName }: ExampleCardProps) {
  return (
    <div className="rounded-lg border p-3 space-y-2">
      <p className="text-xs font-medium">{example.title}</p>
      <p className="text-xs text-muted-foreground">You ask: &quot;{example.prompt}&quot;</p>

      <div className="rounded-lg bg-[#F7F5F2] border p-2">
        <p className="text-[10px] font-medium text-muted-foreground mb-1">Without skill</p>
        <ul className="text-[10px] space-y-0.5 text-muted-foreground">
          {example.without.map((item) => (
            <li key={item}>- {item}</li>
          ))}
        </ul>
      </div>

      <div className="rounded-lg bg-[#6B8FAD]/10 border border-[#6B8FAD]/30 p-2">
        <p className="text-[10px] font-medium text-[#6B8FAD] mb-1">
          <Sparkles className="inline h-2.5 w-2.5 mr-0.5" />
          With {roleName} skill
        </p>
        <ul className="text-[10px] space-y-0.5">
          {example.with.map((item) => (
            <li key={item}>- {item}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}

interface GeneratingStateProps {
  roleName: string;
}

function GeneratingState({ roleName }: GeneratingStateProps) {
  const [progress, setProgress] = useState(0);

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
      <div className="flex gap-1.5" aria-hidden="true">
        <div className="h-2.5 w-2.5 animate-bounce rounded-full bg-[#6B8FAD] [animation-delay:0ms]" />
        <div className="h-2.5 w-2.5 animate-bounce rounded-full bg-[#6B8FAD] [animation-delay:150ms]" />
        <div className="h-2.5 w-2.5 animate-bounce rounded-full bg-[#6B8FAD] [animation-delay:300ms]" />
      </div>

      <p className="text-base font-medium">Generating your {roleName} skill...</p>
      <p className="text-sm text-muted-foreground text-center max-w-sm">
        Our AI is crafting a personalized skill based on your expertise. This takes about 15-30
        seconds.
      </p>

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

      <div
        className="max-h-[400px] overflow-y-auto rounded-lg border bg-[#F7F5F2] p-4"
        aria-label="Generated skill preview"
      >
        <pre className="whitespace-pre-wrap font-mono text-sm leading-relaxed">
          {preview.content}
        </pre>
      </div>

      <div className="text-right" aria-live="polite">
        <span
          className={`text-xs ${preview.wordCount >= 1800 ? 'text-destructive' : 'text-muted-foreground'}`}
        >
          {preview.wordCount} / 2000 words
        </span>
      </div>

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
