/**
 * SkillsSettingsPage - Workspace AI Skills configuration.
 *
 * Phase 20: Restructured with My Skills + Template Catalog sections.
 * Phase 64: Added inline ChatView panel for conversational skill creation.
 * Unified skill management: browse templates, create personal skills from templates.
 * Source: FR-009, FR-010, FR-015, FR-018, US6, P20-09, P20-10
 */

'use client';

import * as React from 'react';
import { lazy, Suspense } from 'react';
import { observer } from 'mobx-react-lite';
import { useParams } from 'next/navigation';
import {
  AlertCircle,
  Layers,
  Lock,
  MousePointerClick,
  Package,
  Plus,
  Sparkles,
  Wand2,
} from 'lucide-react';
import { motion } from 'motion/react';
import { toast } from 'sonner';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ResizablePanelGroup, ResizablePanel, ResizableHandle } from '@/components/ui/resizable';
import { CollapsedChatStrip } from '@/components/editor/CollapsedChatStrip';
import { useMediaQuery } from '@/hooks/useMediaQuery';
import { useStore } from '@/stores';
import { getAIStore } from '@/stores/ai/AIStore';
import { useUserSkills, useUpdateUserSkill, useDeleteUserSkill } from '@/services/api/user-skills';
import type { UserSkill } from '@/services/api/user-skills';
import { useUpdateSkillTemplate, useDeleteSkillTemplate } from '@/services/api/skill-templates';
import type { SkillTemplate } from '@/services/api/skill-templates';
import { MySkillCard } from '../components/my-skill-card';
import { SkillDetailModal } from '../components/skill-detail-modal';
import { TemplateCatalog } from '../components/template-catalog';
import { CreateTemplateModal } from '../components/create-template-modal';
import { EditTemplateModal } from '../components/edit-template-modal';
import { PluginsTabContent } from '../components/plugins-tab-content';
import { ActionButtonsTabContent } from '../components/action-buttons-tab-content';
import { SkillAddModal } from '../components/skill-add-modal';
import { ConfirmActionDialog } from '../components/confirm-action-dialog';

const ChatView = lazy(() =>
  import('@/features/ai/ChatView/ChatView').then((m) => ({ default: m.ChatView }))
);

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function LoadingSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-8 w-40" />
      <Skeleton className="h-9 w-56" />
      <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="rounded-xl border bg-card overflow-hidden">
            <Skeleton className="h-[72px] w-full rounded-none" />
            <div className="p-4 space-y-2">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-3 w-full" />
              <Skeleton className="h-8 w-full mt-2" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function GuestView() {
  return (
    <div className="py-8">
      <Alert role="alert">
        <Lock className="h-4 w-4" />
        <AlertDescription>
          Skill configuration requires Member or higher access. Contact a workspace admin for
          permission.
        </AlertDescription>
      </Alert>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Skill Creator Empty State — shown in ChatView when no conversation exists
// ---------------------------------------------------------------------------

function SkillCreatorEmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-full min-h-[400px] text-center px-6">
      <div className="w-16 h-16 rounded-full bg-gradient-to-br from-primary/80 to-ai/80 flex items-center justify-center mb-4">
        <Wand2 className="h-8 w-8 text-white" />
      </div>
      <h3 className="text-lg font-semibold mb-2">Skill Creator</h3>
      <p className="text-sm text-muted-foreground max-w-sm mb-5 leading-relaxed">
        Describe the skill you want to create in natural language. The AI will generate a SKILL.md
        file, let you preview and edit it, test it with a rubric, and refine until it&apos;s ready.
      </p>
      <div className="space-y-2 text-left w-full max-w-xs">
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">
          Try saying:
        </p>
        {[
          'Create a code review skill focused on security',
          'Build a skill for writing user stories',
          'Make a skill that helps with API design',
        ].map((prompt) => (
          <div
            key={prompt}
            className="flex items-start gap-2 text-xs text-muted-foreground"
          >
            <Sparkles className="h-3 w-3 mt-0.5 shrink-0 text-primary/60" />
            <span>{prompt}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export const SkillsSettingsPage = observer(function SkillsSettingsPage() {
  const { workspaceStore } = useStore();
  const params = useParams();
  const workspaceSlug = params?.workspaceSlug as string;
  const currentWorkspace = workspaceStore.getWorkspaceBySlug(workspaceSlug);
  const workspaceId = currentWorkspace?.id || workspaceSlug;

  const isAdmin = workspaceStore.isAdmin;
  const isGuest = workspaceStore.currentUserRole === 'guest';

  // User skills state
  const { data: userSkills, isLoading, isError, error } = useUserSkills(workspaceSlug);
  const updateUserSkill = useUpdateUserSkill(workspaceSlug);
  const deleteUserSkill = useDeleteUserSkill(workspaceSlug);

  // Template admin mutations
  const updateTemplate = useUpdateSkillTemplate(workspaceSlug);
  const deleteTemplate = useDeleteSkillTemplate(workspaceSlug);

  // Tab state
  const [activeTab, setActiveTab] = React.useState('skills');
  const [addPluginDialogOpen, setAddPluginDialogOpen] = React.useState(false);

  // ChatView panel state
  const [isChatOpen, setIsChatOpen] = React.useState(false);
  const [chatPrefill, setChatPrefill] = React.useState<string | undefined>(undefined);
  const isSmallScreen = useMediaQuery('(max-width: 1023px)');

  // AI store for ChatView
  const aiStore = getAIStore();
  const pilotSpaceStore = aiStore.pilotSpace;

  // Set workspace ID on AI store
  React.useEffect(() => {
    const resolvedId = currentWorkspace?.id ?? workspaceSlug;
    if (pilotSpaceStore && resolvedId && pilotSpaceStore.workspaceId !== resolvedId) {
      pilotSpaceStore.setWorkspaceId(resolvedId);
    }
  }, [currentWorkspace?.id, workspaceSlug, pilotSpaceStore]);

  // Skill generator modal state
  const [generatorOpen, setGeneratorOpen] = React.useState(false);
  const [selectedTemplate, setSelectedTemplate] = React.useState<SkillTemplate | null>(null);

  // Create/edit template modal state
  const [createTemplateOpen, setCreateTemplateOpen] = React.useState(false);
  const [templateToEdit, setTemplateToEdit] = React.useState<SkillTemplate | null>(null);

  // Skill detail modal state
  const [skillToView, setSkillToView] = React.useState<UserSkill | null>(null);

  // Confirm dialogs
  const [skillToDelete, setSkillToDelete] = React.useState<UserSkill | null>(null);
  const [templateToDelete, setTemplateToDelete] = React.useState<SkillTemplate | null>(null);

  // Reconcile skillToView with latest data after mutations
  React.useEffect(() => {
    if (skillToView && userSkills) {
      const updated = userSkills.find((s) => s.id === skillToView.id);
      if (!updated) {
        setSkillToView(null);
      } else if (updated !== skillToView) {
        setSkillToView(updated);
      }
    }
  }, [userSkills, skillToView]);

  // ---------------------------------------------------------------------------
  // Handlers: User Skills
  // ---------------------------------------------------------------------------

  const handleToggleSkillActive = (skill: UserSkill) => {
    updateUserSkill.mutate(
      { id: skill.id, data: { is_active: !skill.is_active } },
      {
        onSuccess: () => {
          toast.success(skill.is_active ? 'Skill deactivated' : 'Skill activated');
        },
        onError: () => {
          toast.error('Failed to toggle skill');
        },
      }
    );
  };

  const handleDeleteSkill = (skill: UserSkill) => {
    setSkillToDelete(skill);
  };

  const handleEditSkill = (
    skill: UserSkill,
    updates: { skill_content?: string; skill_name?: string }
  ) => {
    updateUserSkill.mutate(
      { id: skill.id, data: updates },
      {
        onSuccess: () => toast.success('Skill updated'),
        onError: () => toast.error('Failed to update skill'),
      }
    );
  };

  const handleDeleteSkillConfirm = () => {
    if (!skillToDelete) return;
    deleteUserSkill.mutate(skillToDelete.id, {
      onSuccess: () => {
        toast.success('Skill removed');
        setSkillToDelete(null);
      },
      onError: () => {
        toast.error('Failed to remove skill');
      },
    });
  };

  // ---------------------------------------------------------------------------
  // Handlers: Templates
  // ---------------------------------------------------------------------------

  const handleUseThis = (template: SkillTemplate) => {
    setSelectedTemplate(template);
    setGeneratorOpen(true);
  };

  const handleEditTemplate = (template: SkillTemplate) => {
    setTemplateToEdit(template);
  };

  const handleToggleTemplateActive = (template: SkillTemplate) => {
    updateTemplate.mutate(
      { id: template.id, data: { is_active: !template.is_active } },
      {
        onSuccess: () => {
          toast.success(template.is_active ? 'Template deactivated' : 'Template activated');
        },
        onError: () => {
          toast.error('Failed to toggle template');
        },
      }
    );
  };

  const handleDeleteTemplate = (template: SkillTemplate) => {
    setTemplateToDelete(template);
  };

  const handleDeleteTemplateConfirm = () => {
    if (!templateToDelete) return;
    deleteTemplate.mutate(templateToDelete.id, {
      onSuccess: () => {
        toast.success('Template deleted');
        setTemplateToDelete(null);
      },
      onError: () => {
        toast.error('Failed to delete template');
      },
    });
  };

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  if (isGuest) {
    return (
      <div className="px-4 py-4 sm:px-6 lg:px-8">
        <h1 className="text-2xl font-semibold tracking-tight mb-6 font-display">Skills</h1>
        <GuestView />
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="px-4 py-4 sm:px-6 lg:px-8">
        <LoadingSkeleton />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="px-4 py-4 sm:px-6 lg:px-8">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Failed to load skills: {error?.message ?? 'Unknown error'}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  const skillCount = userSkills?.length ?? 0;

  // ChatView content — lazy-loaded with empty state guideline
  const chatViewContent = (
    <Suspense
      fallback={
        <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
          Loading AI chat...
        </div>
      }
    >
      <ChatView
        store={pilotSpaceStore}
        approvalStore={aiStore.approval}
        autoFocus
        onClose={() => setIsChatOpen(false)}
        prefillValue={chatPrefill}
        emptyStateSlot={<SkillCreatorEmptyState />}
      />
    </Suspense>
  );

  // Skills content panel — all the existing skills UI
  const skillsContent = (
    <div className="px-4 py-4 sm:px-6 lg:px-8 h-full overflow-auto">
      <h1 className="text-2xl font-semibold tracking-tight mb-6 font-display">Skills</h1>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <div className="flex items-center justify-between gap-3">
          <TabsList>
            <TabsTrigger value="skills">
              <Wand2 className="mr-1.5 h-4 w-4" />
              Skills
            </TabsTrigger>
            {isAdmin && (
              <TabsTrigger value="plugins">
                <Package className="mr-1.5 h-4 w-4" />
                Plugins
              </TabsTrigger>
            )}
            {isAdmin && (
              <TabsTrigger value="action-buttons">
                <MousePointerClick className="mr-1.5 h-4 w-4" />
                Action Buttons
              </TabsTrigger>
            )}
          </TabsList>
          {activeTab === 'skills' && (
            <div className="flex gap-2">
              {isAdmin && (
                <Button size="sm" variant="outline" onClick={() => setCreateTemplateOpen(true)}>
                  <Layers className="mr-1.5 h-4 w-4" />
                  Create Template
                </Button>
              )}
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  setChatPrefill('/skill-creator');
                  setIsChatOpen(true);
                }}
              >
                <Wand2 className="mr-1.5 h-4 w-4" />
                Create Skill
              </Button>
              <Button size="sm" onClick={() => setGeneratorOpen(true)}>
                <Plus className="mr-1.5 h-4 w-4" />
                Add Skill
              </Button>
            </div>
          )}
          {activeTab === 'plugins' && isAdmin && (
            <Button size="sm" onClick={() => setAddPluginDialogOpen(true)}>
              <Plus className="mr-1.5 h-4 w-4" />
              Add Plugin
            </Button>
          )}
        </div>

        <TabsContent value="skills">
          <div className="space-y-8 pt-4">
            {/* My Skills Section */}
            <section>
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-sm font-semibold text-foreground">My Skills</h2>
                {skillCount > 0 && (
                  <span className="text-xs text-muted-foreground">
                    {skillCount} skill{skillCount !== 1 ? 's' : ''}
                  </span>
                )}
              </div>
              {skillCount > 0 ? (
                <div className="grid gap-3 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
                  {userSkills?.map((skill, index) => (
                    <div
                      key={skill.id}
                      className="animate-fade-up"
                      style={{ animationDelay: `${index * 60}ms` }}
                    >
                      <MySkillCard
                        skill={skill}
                        onToggleActive={handleToggleSkillActive}
                        onDelete={handleDeleteSkill}
                        onClick={setSkillToView}
                      />
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex flex-col items-center rounded-2xl bg-gradient-to-b from-primary/[0.04] to-ai/[0.04] border border-border/40 p-10 text-center">
                  <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 ring-1 ring-primary/20 shadow-sm">
                    <Wand2 className="h-6 w-6 text-primary" />
                  </div>
                  <h3 className="mt-4 text-base font-semibold text-foreground font-display">
                    Personalize your AI co-pilot
                  </h3>
                  <p className="mt-2 max-w-sm text-sm text-muted-foreground leading-relaxed">
                    Skills shape how AI assists you — from code reviews to writing style. Browse
                    templates below to add your first skill.
                  </p>
                </div>
              )}
            </section>

            {/* Skill Templates Section */}
            <section>
              <div className="mb-4">
                <h2 className="text-sm font-semibold text-foreground">Skill Templates</h2>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  Ready-made patterns to customize your AI assistant
                </p>
              </div>
              <TemplateCatalog
                workspaceSlug={workspaceSlug}
                isAdmin={isAdmin}
                onUseThis={handleUseThis}
                onEditTemplate={isAdmin ? handleEditTemplate : undefined}
                onToggleTemplateActive={isAdmin ? handleToggleTemplateActive : undefined}
                onDeleteTemplate={isAdmin ? handleDeleteTemplate : undefined}
              />
            </section>
          </div>

          {/* Add Skill Modal (dual-mode: Manual + AI Generate) */}
          <SkillAddModal
            open={generatorOpen}
            onOpenChange={(v) => {
              setGeneratorOpen(v);
              if (!v) setTimeout(() => setSelectedTemplate(null), 200);
            }}
            defaultTab={selectedTemplate ? 'ai-generate' : 'manual'}
            defaultMode="personal"
            showModeToggle={isAdmin}
            workspaceId={workspaceId}
            workspaceSlug={workspaceSlug}
            template={selectedTemplate}
          />

          {/* Skill Detail Modal */}
          <SkillDetailModal
            skill={skillToView}
            open={!!skillToView}
            onOpenChange={(v) => {
              if (!v) setSkillToView(null);
            }}
            onEdit={handleEditSkill}
            onToggleActive={handleToggleSkillActive}
            onDelete={handleDeleteSkill}
            isSaving={updateUserSkill.isPending}
          />

          {/* Create Template Modal (admin only) */}
          {isAdmin && (
            <CreateTemplateModal
              open={createTemplateOpen}
              onOpenChange={setCreateTemplateOpen}
              workspaceSlug={workspaceSlug}
            />
          )}

          {/* Edit Template Modal (admin only) */}
          {isAdmin && templateToEdit && (
            <EditTemplateModal
              open={!!templateToEdit}
              onOpenChange={(v) => {
                if (!v) setTemplateToEdit(null);
              }}
              workspaceSlug={workspaceSlug}
              template={templateToEdit}
            />
          )}

          {/* Delete skill confirmation */}
          {skillToDelete && (
            <ConfirmActionDialog
              open={!!skillToDelete}
              onCancel={() => setSkillToDelete(null)}
              onConfirm={handleDeleteSkillConfirm}
              title={`Remove ${skillToDelete.skill_name ?? skillToDelete.template_name ?? 'Custom'} Skill?`}
              description="This will permanently delete this skill. The AI assistant will no longer use this skill in your conversations."
              confirmLabel="Remove Skill"
              variant="destructive"
            />
          )}

          {/* Delete template confirmation */}
          {templateToDelete && (
            <ConfirmActionDialog
              open={!!templateToDelete}
              onCancel={() => setTemplateToDelete(null)}
              onConfirm={handleDeleteTemplateConfirm}
              title={`Delete "${templateToDelete.name}"?`}
              description="This will permanently delete this workspace template. Members who created skills from this template will keep their existing skills."
              confirmLabel="Delete Template"
              variant="destructive"
            />
          )}
        </TabsContent>

        {isAdmin && (
          <TabsContent value="plugins">
            <PluginsTabContent
              workspaceId={workspaceId}
              addDialogOpen={addPluginDialogOpen}
              onAddDialogOpenChange={setAddPluginDialogOpen}
            />
          </TabsContent>
        )}

        {isAdmin && (
          <TabsContent value="action-buttons">
            <ActionButtonsTabContent workspaceId={workspaceId} />
          </TabsContent>
        )}
      </Tabs>
    </div>
  );

  // Desktop: Resizable split layout with ChatView panel
  if (!isSmallScreen && isChatOpen) {
    return (
      <ResizablePanelGroup
        orientation="horizontal"
        className="h-full w-full"
        id="skills-page-layout"
      >
        <ResizablePanel id="skills-panel" defaultSize="62%" minSize="50%" className="min-w-0">
          {skillsContent}
        </ResizablePanel>

        <ResizableHandle withHandle />

        <ResizablePanel
          id="chat-panel"
          defaultSize="38%"
          minSize="30%"
          maxSize="50%"
          className="min-w-0"
        >
          <motion.aside
            aria-label="Skill Creator Chat"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2, ease: 'easeInOut' }}
            className="h-full w-full overflow-hidden border-l border-border"
          >
            {chatViewContent}
          </motion.aside>
        </ResizablePanel>
      </ResizablePanelGroup>
    );
  }

  // Desktop: Chat closed — skills full width + collapsed strip
  if (!isSmallScreen) {
    return (
      <div className="flex h-full w-full overflow-hidden">
        <div className="flex-1 min-w-0 overflow-hidden">{skillsContent}</div>
        <CollapsedChatStrip onClick={() => setIsChatOpen(true)} />
      </div>
    );
  }

  // Mobile/Tablet: Skills only (no split layout)
  return skillsContent;
});
