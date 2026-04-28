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
  Bold,
  Code,
  Heading1,
  Heading2,
  Heading3,
  Italic,
  List,
  RefreshCw,
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
import {
  AiFormStep,
  AiPreviewStep,
  GeneratingStep,
  TagChipInput,
  AI_MIN_CHARS,
} from './skill-add-modal-parts';

type SkillMode = 'personal' | 'workspace';
type AiStep = 'form' | 'generating' | 'preview';

interface AiSkillPreview {
  content: string;
  suggestedName: string;
  suggestedTags: string[];
  suggestedUsage: string | null;
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

const MAX_WORDS = 2000;

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
  const [manualTags, setManualTags] = React.useState<string[]>([]);
  const [manualUsage, setManualUsage] = React.useState('');
  const [manualNameError, setManualNameError] = React.useState(false);

  // AI Generate tab state
  const [aiStep, setAiStep] = React.useState<AiStep>('form');
  const [aiDescription, setAiDescription] = React.useState('');
  const [aiPreview, setAiPreview] = React.useState<AiSkillPreview | null>(null);
  const [aiEditableName, setAiEditableName] = React.useState('');
  const [aiEditableContent, setAiEditableContent] = React.useState('');
  const [aiEditableTags, setAiEditableTags] = React.useState<string[]>([]);
  const [aiEditableUsage, setAiEditableUsage] = React.useState('');
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
    setManualTags([]);
    setManualUsage('');
    setManualNameError(false);
    setAiStep('form');
    setAiDescription('');
    setAiPreview(null);
    setAiEditableName('');
    setAiEditableContent('');
    setAiEditableTags([]);
    setAiEditableUsage('');
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
        tags: manualTags.length > 0 ? manualTags : undefined,
        usage: manualUsage.trim() || undefined,
      });
      handleClose();
    } catch {
      /* Error toast from mutation hook */
    }
  }, [
    isManualValid,
    manualName,
    manualDescription,
    manualContent,
    manualTags,
    manualUsage,
    createUserSkill,
    handleClose,
  ]);

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
          suggestedTags: r.suggestedTags ?? [],
          suggestedUsage: r.suggestedUsage ?? null,
          wordCount: r.wordCount,
        });
        setAiEditableName(r.suggestedRoleName);
        setAiEditableContent(r.skillContent);
        setAiEditableTags(r.suggestedTags ?? []);
        setAiEditableUsage(r.suggestedUsage ?? '');
      } else {
        const s = await generateWorkspace.mutateAsync({
          experience_description: aiDescription.trim(),
        });
        setAiPreview({
          content: s.skill_content,
          suggestedName: s.role_name,
          suggestedTags: s.tags ?? [],
          suggestedUsage: s.usage ?? null,
          wordCount: s.skill_content.split(/\s+/).length,
        });
        setAiEditableName(s.role_name);
        setAiEditableContent(s.skill_content);
        setAiEditableTags(s.tags ?? []);
        setAiEditableUsage(s.usage ?? '');
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
          tags: aiEditableTags.length > 0 ? aiEditableTags : undefined,
          usage: aiEditableUsage.trim() || undefined,
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
    aiEditableTags,
    aiEditableUsage,
    aiDescription,
    createUserSkill,
    template,
    handleClose,
  ]);

  const handleRetry = React.useCallback(() => {
    setAiShowError(false);
    setAiPreview(null);
    setAiEditableTags([]);
    setAiEditableUsage('');
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
              <div className="space-y-1.5">
                <Label htmlFor="manual-skill-usage">Usage (optional)</Label>
                <Textarea
                  id="manual-skill-usage"
                  value={manualUsage}
                  onChange={(e) => setManualUsage(e.target.value.slice(0, 500))}
                  placeholder="When and how this skill is applied, e.g. Used during backend architecture reviews and API design sessions."
                  rows={2}
                  className="resize-none"
                />
                <p className="text-xs text-muted-foreground text-right">{manualUsage.length}/500</p>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="manual-skill-tags">Tags (optional)</Label>
                <TagChipInput id="manual-skill-tags" tags={manualTags} onChange={setManualTags} />
                <p className="text-xs text-muted-foreground">
                  Press Enter or comma to add a tag. Up to 20 tags.
                </p>
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
                editableTags={aiEditableTags}
                onTagsChange={setAiEditableTags}
                editableUsage={aiEditableUsage}
                onUsageChange={setAiEditableUsage}
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

export default SkillAddModal;
