/**
 * SkillsSettingsPage - Workspace AI Skills configuration.
 *
 * Phase 20: Restructured with My Skills + Template Catalog sections.
 * Unified skill management: browse templates, create personal skills from templates.
 * Source: FR-009, FR-010, FR-015, FR-018, US6, P20-09, P20-10
 */

'use client';

import * as React from 'react';
import { observer } from 'mobx-react-lite';
import { useParams } from 'next/navigation';
import { AlertCircle, Layers, Lock, MousePointerClick, Package, Plus, Wand2 } from 'lucide-react';
import { toast } from 'sonner';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useStore } from '@/stores';
import { useUserSkills, useUpdateUserSkill, useDeleteUserSkill } from '@/services/api/user-skills';
import type { UserSkill } from '@/services/api/user-skills';
import { useUpdateSkillTemplate, useDeleteSkillTemplate } from '@/services/api/skill-templates';
import type { SkillTemplate } from '@/services/api/skill-templates';
import { MySkillCard } from '../components/my-skill-card';
import { TemplateCatalog } from '../components/template-catalog';
import { CreateTemplateModal } from '../components/create-template-modal';
import { EditTemplateModal } from '../components/edit-template-modal';
import { PluginsTabContent } from '../components/plugins-tab-content';
import { ActionButtonsTabContent } from '../components/action-buttons-tab-content';
import { SkillGeneratorModal } from '../components/skill-generator-modal';
import { ConfirmActionDialog } from '../components/confirm-action-dialog';

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

  // Skill generator modal state
  const [generatorOpen, setGeneratorOpen] = React.useState(false);
  const [selectedTemplate, setSelectedTemplate] = React.useState<SkillTemplate | null>(null);

  // Create/edit template modal state
  const [createTemplateOpen, setCreateTemplateOpen] = React.useState(false);
  const [templateToEdit, setTemplateToEdit] = React.useState<SkillTemplate | null>(null);

  // Confirm dialogs
  const [skillToDelete, setSkillToDelete] = React.useState<UserSkill | null>(null);
  const [templateToDelete, setTemplateToDelete] = React.useState<SkillTemplate | null>(null);

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
        <h1 className="text-2xl font-semibold tracking-tight mb-4">Skills</h1>
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

  return (
    <div className="px-4 py-4 sm:px-6 lg:px-8">
      <h1 className="text-2xl font-semibold tracking-tight mb-4">Skills</h1>

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
                  {userSkills?.map((skill) => (
                    <MySkillCard
                      key={skill.id}
                      skill={skill}
                      onToggleActive={handleToggleSkillActive}
                      onDelete={handleDeleteSkill}
                    />
                  ))}
                </div>
              ) : (
                <div className="rounded-xl border border-dashed border-border/50 bg-muted/20 p-8 text-center">
                  <p className="text-sm text-muted-foreground">
                    No skills yet. Browse templates below to get started.
                  </p>
                </div>
              )}
            </section>

            {/* Skill Templates Section */}
            <section>
              <h2 className="text-sm font-semibold text-foreground mb-4">Skill Templates</h2>
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

          {/* Skill Generator Modal */}
          <SkillGeneratorModal
            open={generatorOpen}
            onOpenChange={(v) => {
              setGeneratorOpen(v);
              if (!v) setTimeout(() => setSelectedTemplate(null), 200);
            }}
            defaultMode="personal"
            showModeToggle={isAdmin}
            workspaceId={workspaceId}
            workspaceSlug={workspaceSlug}
            template={selectedTemplate}
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
              title={`Remove ${skillToDelete.template_name ?? 'Custom'} Skill?`}
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
});
