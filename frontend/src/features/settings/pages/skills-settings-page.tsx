/**
 * SkillsSettingsPage - Admin-only workspace skill configuration.
 *
 * Admin functions:
 * - Create/edit/delete workspace skill templates
 * - Manage plugins
 * - Configure action buttons
 *
 * Personal skill management has moved to /skills main view.
 * Source: FR-009, FR-010, FR-015, FR-018
 */

'use client';

import * as React from 'react';
import { observer } from 'mobx-react-lite';
import { useParams, useRouter } from 'next/navigation';
import {
  AlertCircle,
  ExternalLink,
  Layers,
  Lock,
  MousePointerClick,
  Package,
  Plus,
} from 'lucide-react';
import { toast } from 'sonner';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useStore } from '@/stores';
import { useSkillTemplates, useUpdateSkillTemplate, useDeleteSkillTemplate } from '@/services/api/skill-templates';
import type { SkillTemplate } from '@/services/api/skill-templates';
import { TemplateCatalog } from '../components/template-catalog';
import { CreateTemplateModal } from '../components/create-template-modal';
import { EditTemplateModal } from '../components/edit-template-modal';
import { PluginsTabContent } from '../components/plugins-tab-content';
import { ActionButtonsTabContent } from '../components/action-buttons-tab-content';
import { ConfirmActionDialog } from '../components/confirm-action-dialog';

function LoadingSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-8 w-40" />
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

function NonAdminView({ workspaceSlug }: { workspaceSlug: string }) {
  const router = useRouter();
  return (
    <div className="py-8">
      <Alert>
        <Lock className="h-4 w-4" />
        <AlertDescription className="flex items-center justify-between">
          <span>This page is for workspace admins. Manage your personal skills on the Skills page.</span>
          <Button
            variant="link"
            size="sm"
            className="gap-1"
            onClick={() => router.push(`/${workspaceSlug}/skills`)}
          >
            Go to Skills <ExternalLink className="h-3 w-3" />
          </Button>
        </AlertDescription>
      </Alert>
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

  // Templates query and mutations
  const { isLoading, isError, error } = useSkillTemplates(workspaceSlug);
  const updateTemplate = useUpdateSkillTemplate(workspaceSlug);
  const deleteTemplate = useDeleteSkillTemplate(workspaceSlug);

  // Tab state
  const [activeTab, setActiveTab] = React.useState('templates');
  const [addPluginDialogOpen, setAddPluginDialogOpen] = React.useState(false);

  // Template modal state
  const [createTemplateOpen, setCreateTemplateOpen] = React.useState(false);
  const [templateToEdit, setTemplateToEdit] = React.useState<SkillTemplate | null>(null);
  const [templateToDelete, setTemplateToDelete] = React.useState<SkillTemplate | null>(null);

  // Handlers
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

  // Guest cannot access settings at all
  if (isGuest) {
    return (
      <div className="px-4 py-4 sm:px-6 lg:px-8">
        <h1 className="text-2xl font-semibold tracking-tight mb-6 font-display">Skills Admin</h1>
        <Alert role="alert">
          <Lock className="h-4 w-4" />
          <AlertDescription>
            Skill configuration requires Member or higher access. Contact a workspace admin.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  // Non-admin members redirect to /skills
  if (!isAdmin) {
    return (
      <div className="px-4 py-4 sm:px-6 lg:px-8">
        <h1 className="text-2xl font-semibold tracking-tight mb-6 font-display">Skills Admin</h1>
        <NonAdminView workspaceSlug={workspaceSlug} />
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
            Failed to load templates: {error?.message ?? 'Unknown error'}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="px-4 py-4 sm:px-6 lg:px-8 h-full overflow-auto">
      <h1 className="text-2xl font-semibold tracking-tight mb-6 font-display">Skills Admin</h1>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <div className="flex items-center justify-between gap-3">
          <TabsList>
            <TabsTrigger value="templates">
              <Layers className="mr-1.5 h-4 w-4" />
              Templates
            </TabsTrigger>
            <TabsTrigger value="plugins">
              <Package className="mr-1.5 h-4 w-4" />
              Plugins
            </TabsTrigger>
            <TabsTrigger value="action-buttons">
              <MousePointerClick className="mr-1.5 h-4 w-4" />
              Action Buttons
            </TabsTrigger>
          </TabsList>
          {activeTab === 'templates' && (
            <Button size="sm" onClick={() => setCreateTemplateOpen(true)}>
              <Plus className="mr-1.5 h-4 w-4" />
              Create Template
            </Button>
          )}
          {activeTab === 'plugins' && (
            <Button size="sm" onClick={() => setAddPluginDialogOpen(true)}>
              <Plus className="mr-1.5 h-4 w-4" />
              Add Plugin
            </Button>
          )}
        </div>

        <TabsContent value="templates">
          <div className="pt-4">
            <div className="mb-4">
              <p className="text-sm text-muted-foreground">
                Manage workspace skill templates. Members can create personal skills from these templates.
              </p>
            </div>
            <TemplateCatalog
              workspaceSlug={workspaceSlug}
              isAdmin={true}
              onEditTemplate={handleEditTemplate}
              onToggleTemplateActive={handleToggleTemplateActive}
              onDeleteTemplate={handleDeleteTemplate}
            />
          </div>

          {/* Create Template Modal */}
          <CreateTemplateModal
            open={createTemplateOpen}
            onOpenChange={setCreateTemplateOpen}
            workspaceSlug={workspaceSlug}
          />

          {/* Edit Template Modal */}
          {templateToEdit && (
            <EditTemplateModal
              open={!!templateToEdit}
              onOpenChange={(v) => {
                if (!v) setTemplateToEdit(null);
              }}
              workspaceSlug={workspaceSlug}
              template={templateToEdit}
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

        <TabsContent value="plugins">
          <PluginsTabContent
            workspaceId={workspaceId}
            addDialogOpen={addPluginDialogOpen}
            onAddDialogOpenChange={setAddPluginDialogOpen}
          />
        </TabsContent>

        <TabsContent value="action-buttons">
          <ActionButtonsTabContent workspaceId={workspaceId} />
        </TabsContent>
      </Tabs>
    </div>
  );
});
