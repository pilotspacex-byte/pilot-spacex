/**
 * SkillAddModal - Dual-mode Add Skill modal with Manual + AI Generate tabs.
 *
 * Replaces SkillGeneratorModal. Manual tab for direct input, AI Generate tab
 * preserves existing flow. 896px wide, single-column, no guide panel.
 * Source: specs/023-skill-modal-redesign/ux-design-spec.md
 */

'use client';

import * as React from 'react';
import {
  ArrowLeft,
  Bold,
  Check,
  Code,
  Heading1,
  Heading2,
  Heading3,
  Italic,
  List,
  Pencil,
  RefreshCw,
  TriangleAlert,
  User,
  Users,
  Wand2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';
import { useGenerateSkill } from '@/features/onboarding/hooks';
import { useGenerateWorkspaceSkill } from '@/services/api/workspace-role-skills';
import { useCreateUserSkill } from '@/services/api/user-skills';
import { WordCountBar } from './word-count-bar';

type SkillMode = 'personal' | 'workspace';
type AiStep = 'form' | 'generating' | 'preview';

interface SkillPreview {
  content: string;
  suggestedName: string;
  wordCount: number;
}

export interface SkillAddModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  defaultTab?: 'manual' | 'ai-generate';
  defaultMode?: SkillMode;
  showModeToggle?: boolean;
  workspaceId: string;
  workspaceSlug?: string;
  template?: { id: string; name: string; description: string; skill_content: string } | null;
}

const AI_MIN_CHARS = 10;
const AI_MAX_CHARS = 5000;
const MAX_WORDS = 2000;

const AI_PLACEHOLDER = `e.g. Senior backend developer with 8 years of Python/FastAPI experience.
Focused on clean architecture, async patterns, and PostgreSQL optimization.
Prefer concise code reviews with security-first mindset.`;

interface ToolbarAction {
  icon: React.ElementType;
  label: string;
  prefix: string;
  suffix?: string;
}

const TOOLBAR_ACTIONS: ToolbarAction[] = [
  { icon: Bold, label: 'Bold', prefix: '**', suffix: '**' },
  { icon: Italic, label: 'Italic', prefix: '_', suffix: '_' },
  { icon: Heading1, label: 'Heading 1', prefix: '# ' },
  { icon: Heading2, label: 'Heading 2', prefix: '## ' },
  { icon: Heading3, label: 'Heading 3', prefix: '### ' },
  { icon: List, label: 'Bullet List', prefix: '- ' },
  { icon: Code, label: 'Code Block', prefix: '```\n', suffix: '\n```' },
];

function countWords(text: string): number {
  return text
    .replace(/[#*_`\->\[\]()]/g, '')
    .split(/\s+/)
    .filter((w) => w.length > 0).length;
}

export function SkillAddModal({
  open,
  onOpenChange,
  defaultTab = 'manual',
  defaultMode = 'personal',
  showModeToggle = false,
  workspaceId,
  workspaceSlug,
  template = null,
}: SkillAddModalProps) {
  const [activeTab, setActiveTab] = React.useState<'manual' | 'ai-generate'>(defaultTab);

  // Manual tab state
  const [manualName, setManualName] = React.useState('');
  const [manualDescription, setManualDescription] = React.useState('');
  const [manualContent, setManualContent] = React.useState('');
  const [manualNameError, setManualNameError] = React.useState(false);

  // AI Generate tab state
  const [aiStep, setAiStep] = React.useState<AiStep>('form');
  const [aiDescription, setAiDescription] = React.useState('');
  const [aiPreview, setAiPreview] = React.useState<SkillPreview | null>(null);
  const [aiEditableName, setAiEditableName] = React.useState('');
  const [aiEditableContent, setAiEditableContent] = React.useState('');
  const [aiShowError, setAiShowError] = React.useState(false);
  const [mode, setMode] = React.useState<SkillMode>(defaultMode);

  const manualTextareaRef = React.useRef<HTMLTextAreaElement>(null);
  const closeResetTimerRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  const createUserSkill = useCreateUserSkill(workspaceSlug ?? '');
  const generatePersonal = useGenerateSkill({ workspaceId });
  const generateWorkspace = useGenerateWorkspaceSkill({ workspaceId });

  const isPending =
    generatePersonal.isPending || generateWorkspace.isPending || createUserSkill.isPending;

  React.useEffect(() => {
    if (open) {
      if (closeResetTimerRef.current) {
        clearTimeout(closeResetTimerRef.current);
        closeResetTimerRef.current = null;
      }
      setMode(defaultMode);
      if (template) {
        setActiveTab('ai-generate');
        setAiDescription(template.description);
      } else {
        setActiveTab(defaultTab);
      }
    }
  }, [open, defaultMode, defaultTab, template]);

  const reset = React.useCallback(() => {
    setActiveTab(defaultTab);
    setManualName('');
    setManualDescription('');
    setManualContent('');
    setManualNameError(false);
    setAiStep('form');
    setAiDescription('');
    setAiPreview(null);
    setAiEditableName('');
    setAiEditableContent('');
    setAiShowError(false);
    setMode(defaultMode);
  }, [defaultTab, defaultMode]);

  const handleClose = React.useCallback(() => {
    onOpenChange(false);
    if (closeResetTimerRef.current) clearTimeout(closeResetTimerRef.current);
    closeResetTimerRef.current = setTimeout(reset, 200);
  }, [onOpenChange, reset]);

  // Manual tab
  const manualWordCount = countWords(manualContent);
  const isManualValid =
    manualName.trim().length > 0 && manualContent.trim().length > 0 && manualWordCount <= MAX_WORDS;

  const handleManualSave = React.useCallback(async () => {
    if (!isManualValid) return;
    try {
      await createUserSkill.mutateAsync({
        skill_name: manualName.trim(),
        skill_content: manualContent,
        experience_description: manualDescription.trim() || undefined,
      });
      handleClose();
    } catch {
      /* Error toast from mutation hook */
    }
  }, [isManualValid, manualName, manualDescription, manualContent, createUserSkill, handleClose]);

  const handleToolbarAction = React.useCallback(
    (action: ToolbarAction) => {
      const textarea = manualTextareaRef.current;
      if (!textarea) return;
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      const selected = manualContent.slice(start, end);
      const prefix = action.prefix;
      const suffix = action.suffix ?? '';
      setManualContent(
        manualContent.slice(0, start) + prefix + selected + suffix + manualContent.slice(end)
      );
      requestAnimationFrame(() => {
        textarea.focus();
        textarea.setSelectionRange(
          start + prefix.length + selected.length,
          start + prefix.length + selected.length
        );
      });
    },
    [manualContent]
  );

  // AI tab
  const canGenerate = aiDescription.trim().length >= AI_MIN_CHARS;

  const handleGenerate = React.useCallback(async () => {
    if (!canGenerate) return;
    setAiStep('generating');
    setAiShowError(false);
    try {
      if (mode === 'personal') {
        const r = await generatePersonal.mutateAsync({
          roleType: 'custom',
          experienceDescription: aiDescription.trim(),
        });
        setAiPreview({
          content: r.skillContent,
          suggestedName: r.suggestedRoleName,
          wordCount: r.wordCount,
        });
        setAiEditableName(r.suggestedRoleName);
        setAiEditableContent(r.skillContent);
      } else {
        const s = await generateWorkspace.mutateAsync({
          experience_description: aiDescription.trim(),
        });
        setAiPreview({
          content: s.skill_content,
          suggestedName: s.role_name,
          wordCount: s.skill_content.split(/\s+/).length,
        });
        setAiEditableName(s.role_name);
        setAiEditableContent(s.skill_content);
      }
      setAiStep('preview');
    } catch {
      setAiShowError(true);
      setAiStep('form');
    }
  }, [canGenerate, mode, aiDescription, generatePersonal, generateWorkspace]);

  const handleAiSave = React.useCallback(async () => {
    if (!aiPreview) return;
    const previewWords = countWords(aiEditableContent);
    if (previewWords === 0 || previewWords > MAX_WORDS) return;
    if (mode === 'personal') {
      try {
        await createUserSkill.mutateAsync({
          template_id: template?.id,
          skill_content: aiEditableContent,
          experience_description: aiDescription || undefined,
          skill_name: aiEditableName || undefined,
        });
        handleClose();
      } catch {
        /* Error toast from mutation hook */
      }
    } else {
      handleClose();
    }
  }, [
    aiPreview,
    mode,
    aiEditableName,
    aiEditableContent,
    aiDescription,
    createUserSkill,
    template,
    handleClose,
  ]);

  const handleRetry = React.useCallback(() => {
    setAiShowError(false);
    setAiPreview(null);
    setAiStep('form');
  }, []);

  const aiPreviewWordCount = countWords(aiEditableContent);
  const isReadOnly = mode === 'workspace';

  return (
    <Dialog open={open} onOpenChange={(v) => !v && handleClose()}>
      <DialogContent className="sm:max-w-4xl max-h-[85vh] flex flex-col p-0 gap-0 overflow-hidden">
        <DialogHeader className="px-6 pt-6 pb-4 border-b shrink-0">
          <div className="flex items-center justify-between gap-3">
            <DialogTitle className="flex items-center gap-2">Add Skill</DialogTitle>
            {showModeToggle && <ModeToggle mode={mode} onChange={setMode} />}
          </div>
        </DialogHeader>

        <Tabs
          value={activeTab}
          onValueChange={(v) => setActiveTab(v as 'manual' | 'ai-generate')}
          className="flex flex-col flex-1 min-h-0"
        >
          <div className="px-6 border-b shrink-0">
            <TabsList className="w-full justify-start">
              <TabsTrigger value="manual" disabled={aiStep === 'generating'}>
                Manual
              </TabsTrigger>
              <TabsTrigger value="ai-generate" disabled={aiStep === 'generating'}>
                AI Generate
              </TabsTrigger>
            </TabsList>
          </div>

          {/* Manual Tab */}
          <TabsContent value="manual" className="flex-1 overflow-y-auto px-6 py-5 mt-0">
            <div className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="manual-skill-name">
                  Skill Name <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="manual-skill-name"
                  value={manualName}
                  onChange={(e) => {
                    setManualName(e.target.value);
                    if (manualNameError && e.target.value.trim()) setManualNameError(false);
                  }}
                  onBlur={() => {
                    if (!manualName.trim()) setManualNameError(true);
                  }}
                  placeholder="e.g. Senior Backend Developer"
                  maxLength={200}
                  aria-invalid={manualNameError}
                  aria-describedby={manualNameError ? 'manual-name-error' : undefined}
                />
                {manualNameError && (
                  <p id="manual-name-error" className="text-xs text-destructive">
                    Skill name is required
                  </p>
                )}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="manual-skill-description">Description (optional)</Label>
                <Input
                  id="manual-skill-description"
                  value={manualDescription}
                  onChange={(e) => setManualDescription(e.target.value)}
                  placeholder="Brief description of what this skill covers"
                  maxLength={500}
                />
              </div>
              <div className="space-y-1.5">
                <Label>
                  Skill Content <span className="text-destructive">*</span>
                </Label>
                <div className="flex items-center gap-1 rounded-t-lg border border-b-0 bg-background p-1.5">
                  {TOOLBAR_ACTIONS.map((action) => {
                    const Icon = action.icon;
                    return (
                      <button
                        key={action.label}
                        type="button"
                        onClick={() => handleToolbarAction(action)}
                        className={cn(
                          'inline-flex h-8 w-8 items-center justify-center rounded border',
                          'bg-background text-muted-foreground hover:bg-muted hover:text-foreground',
                          'focus-visible:ring-[3px] focus-visible:ring-primary/30 focus-visible:outline-none'
                        )}
                        aria-label={action.label}
                        title={action.label}
                      >
                        <Icon className="h-4 w-4" />
                      </button>
                    );
                  })}
                </div>
                <textarea
                  ref={manualTextareaRef}
                  value={manualContent}
                  onChange={(e) => setManualContent(e.target.value)}
                  className={cn(
                    'w-full min-h-[320px] rounded-b-lg border bg-background p-4',
                    'font-mono text-sm leading-relaxed resize-y',
                    'focus-visible:ring-[3px] focus-visible:ring-primary/30 focus-visible:outline-none focus-visible:border-primary'
                  )}
                  aria-label="Skill content editor"
                  placeholder="Write your skill content in markdown..."
                />
                <WordCountBar wordCount={manualWordCount} maxWords={MAX_WORDS} />
              </div>
              <div className="rounded-md bg-primary/5 border border-primary/10 p-3 mt-4">
                <p className="text-xs text-muted-foreground leading-relaxed">
                  <span className="font-medium text-foreground">Tip:</span> Include your role, tech
                  stack, focus areas, and work style for best AI personalization.
                </p>
              </div>
            </div>
          </TabsContent>

          {/* AI Generate Tab */}
          <TabsContent value="ai-generate" className="flex-1 overflow-y-auto px-6 py-5 mt-0">
            {aiStep === 'form' && (
              <AiFormStep
                description={aiDescription}
                onDescriptionChange={setAiDescription}
                showError={aiShowError}
                templateName={template?.name}
              />
            )}
            {aiStep === 'generating' && <GeneratingStep />}
            {aiStep === 'preview' && aiPreview && (
              <AiPreviewStep
                editableName={aiEditableName}
                onNameChange={setAiEditableName}
                editableContent={aiEditableContent}
                onContentChange={setAiEditableContent}
                wordCount={aiPreviewWordCount}
                isReadOnly={isReadOnly}
                onBack={() => setAiStep('form')}
              />
            )}
          </TabsContent>
        </Tabs>

        {/* Footer */}
        {aiStep !== 'generating' && (
          <div className="px-6 py-4 border-t shrink-0 flex items-center justify-between gap-3 bg-background">
            {activeTab === 'manual' && (
              <>
                <Button variant="outline" onClick={handleClose}>
                  Cancel
                </Button>
                <Button
                  onClick={handleManualSave}
                  disabled={!isManualValid || createUserSkill.isPending}
                >
                  {createUserSkill.isPending ? 'Saving...' : 'Save Skill'}
                </Button>
              </>
            )}
            {activeTab === 'ai-generate' && aiStep === 'form' && (
              <>
                <Button variant="outline" onClick={handleClose}>
                  Cancel
                </Button>
                <Button onClick={handleGenerate} disabled={!canGenerate || isPending}>
                  {isPending ? (
                    <>
                      <span className="mr-1.5 h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent inline-block" />
                      Generating...
                    </>
                  ) : (
                    <>
                      <Wand2 className="mr-1.5 h-4 w-4" />
                      Generate
                    </>
                  )}
                </Button>
              </>
            )}
            {activeTab === 'ai-generate' && aiStep === 'preview' && (
              <>
                <Button variant="outline" onClick={handleRetry}>
                  <RefreshCw className="mr-1.5 h-4 w-4" />
                  Retry
                </Button>
                <Button onClick={handleAiSave} disabled={createUserSkill.isPending}>
                  {createUserSkill.isPending ? 'Saving...' : 'Save & Activate'}
                </Button>
              </>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

/* Mode Toggle */
function ModeToggle({ mode, onChange }: { mode: SkillMode; onChange: (mode: SkillMode) => void }) {
  const btn = (value: SkillMode, icon: React.ReactNode, label: string) => (
    <button
      role="radio"
      aria-checked={mode === value}
      onClick={() => onChange(value)}
      className={cn(
        'flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors',
        mode === value
          ? 'bg-background text-foreground shadow-sm'
          : 'text-muted-foreground hover:text-foreground'
      )}
    >
      {icon}
      {label}
    </button>
  );
  return (
    <div
      className="flex rounded-lg border bg-muted/50 p-0.5 gap-0.5"
      role="radiogroup"
      aria-label="Skill scope"
    >
      {btn('personal', <User className="h-3.5 w-3.5" />, 'For Me')}
      {btn('workspace', <Users className="h-3.5 w-3.5" />, 'For Workspace')}
    </div>
  );
}

/* AI Form Step */
function AiFormStep({
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

/* Generating Step */
function GeneratingStep() {
  const [progress, setProgress] = React.useState(0);
  React.useEffect(() => {
    const id = setInterval(() => setProgress((p) => (p >= 90 ? 90 : p + (90 - p) * 0.08)), 500);
    return () => clearInterval(id);
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

/* AI Preview Step */
function AiPreviewStep({
  editableName,
  onNameChange,
  editableContent,
  onContentChange,
  wordCount,
  isReadOnly,
  onBack,
}: {
  editableName: string;
  onNameChange: (n: string) => void;
  editableContent: string;
  onContentChange: (c: string) => void;
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
        <Label>Generated Content</Label>
        <Textarea
          value={editableContent}
          onChange={(e) => onContentChange(e.target.value)}
          readOnly={isReadOnly}
          className={cn(
            'min-h-[280px] max-h-[400px] font-mono text-xs leading-relaxed resize-y',
            isReadOnly && 'opacity-60 cursor-default'
          )}
          aria-label={
            isReadOnly ? 'Generated skill content (read-only)' : 'Edit generated skill content'
          }
        />
        <WordCountBar wordCount={wordCount} maxWords={MAX_WORDS} />
      </div>
    </div>
  );
}

export default SkillAddModal;
