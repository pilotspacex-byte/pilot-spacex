/**
 * SkillsGalleryPage — Unified Skills main view.
 *
 * Combines skill gallery discovery with full CRUD management.
 * Features:
 * - My Skills tab: personal skills with edit/toggle/delete
 * - Templates tab: browse and create skills from templates
 * - Grid/Graph view toggle for discovery
 * - Inline ChatView panel for AI skill creation via /skill-creator
 *
 * Source: Phase 91-92 (gallery), Phase 20 (CRUD), Phase 64 (ChatView)
 */
'use client';

import * as React from 'react';
import { lazy, Suspense, useCallback } from 'react';
import { observer } from 'mobx-react-lite';
import { useParams, useRouter } from 'next/navigation';
import { useQueryClient } from '@tanstack/react-query';
import {
  AlertCircle,
  Plus,
  Settings,
  Wand2,
  Sparkles,
} from 'lucide-react';
import { motion } from 'motion/react';
import { toast } from 'sonner';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  ResizablePanelGroup,
  ResizablePanel,
  ResizableHandle,
} from '@/components/ui/resizable';
import { CollapsedChatStrip } from '@/components/editor/CollapsedChatStrip';
import { ArtifactCardSkeleton } from '@/components/artifacts/ArtifactCardSkeleton';
import { useMediaQuery } from '@/hooks/useMediaQuery';
import { useArtifactPeekState } from '@/hooks/use-artifact-peek-state';
import { useStore } from '@/stores';
import { getAIStore } from '@/stores/ai/AIStore';
import { useSettingsModal } from '@/features/settings/settings-modal-context';
import {
  useUserSkills,
  useUpdateUserSkill,
  useDeleteUserSkill,
} from '@/services/api/user-skills';
import type { UserSkill } from '@/services/api/user-skills';
import { useSkillCatalog, SKILLS_CATALOG_QUERY_KEY } from '../hooks';
import { useSkillsViewQueryStringSync } from '../hooks/useSkillsViewQueryStringSync';
import { SkillCard } from './SkillCard';
import { SkillGraphView } from './SkillGraphView';
import { SkillsViewToggle } from './SkillsViewToggle';
import { MySkillCard } from './my-skill-card';
import { SkillDetailModal } from './skill-detail-modal';
import { TemplateCatalog } from './template-catalog';
import { SkillAddModal } from './skill-add-modal';
import { ConfirmActionDialog } from './confirm-action-dialog';
import type { SkillTemplate } from '@/services/api/skill-templates';

const ChatView = lazy(() =>
  import('@/features/ai/ChatView/ChatView').then((m) => ({ default: m.ChatView }))
);

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
          <div key={prompt} className="flex items-start gap-2 text-xs text-muted-foreground">
            <Sparkles className="h-3 w-3 mt-0.5 shrink-0 text-primary/60" />
            <span>{prompt}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-8 w-40" />
      <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <ArtifactCardSkeleton key={i} density="full" />
        ))}
      </div>
    </div>
  );
}

export const SkillsGalleryPage = observer(function SkillsGalleryPage() {
  const params = useParams<{ workspaceSlug: string }>();
  const workspaceSlug = params?.workspaceSlug ?? '';
  const router = useRouter();
  const queryClient = useQueryClient();
  const { openSettings } = useSettingsModal();
  const { workspaceStore } = useStore();
  const peekState = useArtifactPeekState();

  const currentWorkspace = workspaceStore.getWorkspaceBySlug(workspaceSlug);
  const isAdmin = workspaceStore.isAdmin;
  const isGuest = workspaceStore.currentUserRole === 'guest';

  // Gallery catalog (built-in skills)
  const { data: catalogSkills, isPending: catalogPending, isError: catalogError } = useSkillCatalog();
  const [viewMode, setViewMode] = useSkillsViewQueryStringSync();

  // User skills (personal skills)
  const { data: userSkills, isLoading: userSkillsLoading, isError: userSkillsError } = useUserSkills(workspaceSlug);
  const updateUserSkill = useUpdateUserSkill(workspaceSlug);
  const deleteUserSkill = useDeleteUserSkill(workspaceSlug);

  // Tab state
  const [activeTab, setActiveTab] = React.useState('my-skills');

  // ChatView panel state
  const [isChatOpen, setIsChatOpen] = React.useState(false);
  const [chatPrefill, setChatPrefill] = React.useState<string | undefined>(undefined);
  const isSmallScreen = useMediaQuery('(max-width: 1023px)');

  // AI store for ChatView
  const aiStore = getAIStore();
  const pilotSpaceStore = aiStore.pilotSpace;

  React.useEffect(() => {
    const resolvedId = currentWorkspace?.id ?? workspaceSlug;
    if (pilotSpaceStore && resolvedId && pilotSpaceStore.workspaceId !== resolvedId) {
      pilotSpaceStore.setWorkspaceId(resolvedId);
    }
  }, [currentWorkspace?.id, workspaceSlug, pilotSpaceStore]);

  // Modal state
  const [skillToView, setSkillToView] = React.useState<UserSkill | null>(null);
  const [skillToDelete, setSkillToDelete] = React.useState<UserSkill | null>(null);
  const [templateForAdd, setTemplateForAdd] = React.useState<SkillTemplate | null>(null);

  // Reconcile skillToView with latest data
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

  // Handlers
  const onSelectCatalogSkill = useCallback(
    (slug: string) => router.push(`/${workspaceSlug}/skills/${slug}`),
    [router, workspaceSlug]
  );

  const onReloadCatalog = useCallback(
    () => queryClient.invalidateQueries({ queryKey: SKILLS_CATALOG_QUERY_KEY }),
    [queryClient]
  );

  const onSwitchToCards = useCallback(() => setViewMode('cards'), [setViewMode]);

  const handleToggleSkillActive = (skill: UserSkill) => {
    updateUserSkill.mutate(
      { id: skill.id, data: { is_active: !skill.is_active } },
      {
        onSuccess: () => toast.success(skill.is_active ? 'Skill deactivated' : 'Skill activated'),
        onError: () => toast.error('Failed to toggle skill'),
      }
    );
  };

  const handleDeleteSkill = (skill: UserSkill) => setSkillToDelete(skill);

  const handleEditSkill = (skill: UserSkill, updates: { skill_content?: string; skill_name?: string }) => {
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
      onError: () => toast.error('Failed to remove skill'),
    });
  };

  const handleUseTemplate = (template: SkillTemplate) => {
    setTemplateForAdd(template);
  };

  const handleOpenAICreator = () => {
    setChatPrefill('/skill-creator');
    setIsChatOpen(true);
  };

  // Guest view
  if (isGuest) {
    return (
      <main className="mx-auto w-full max-w-screen-2xl px-4 py-6">
        <Alert role="alert">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Skill management requires Member or higher access. Contact a workspace admin for permission.
          </AlertDescription>
        </Alert>
      </main>
    );
  }

  const skillCount = userSkills?.length ?? 0;

  // ChatView content
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

  // Main content
  const mainContent = (
    <main className="mx-auto w-full max-w-screen-2xl px-4 py-6 h-full overflow-auto">
      {/* Header */}
      <header className="sticky top-0 z-10 -mx-4 mb-4 border-b border-border bg-background/95 px-4 py-3 backdrop-blur">
        <div className="flex items-center gap-2">
          <h1 className="text-[15px] font-semibold text-foreground">Skills</h1>
          {skillCount > 0 && (
            <span className="rounded-md bg-muted px-1.5 py-0.5 font-mono text-[10px] font-semibold text-muted-foreground">
              {skillCount}
            </span>
          )}
          <div className="ml-auto flex items-center gap-2">
            <Button
              size="sm"
              variant="default"
              onClick={handleOpenAICreator}
              className="text-[13px] font-medium gap-1.5"
            >
              <Wand2 className="h-3.5 w-3.5" /> Create with AI
            </Button>
            {isAdmin && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => openSettings('skills')}
                className="text-[13px] font-medium gap-1.5"
              >
                <Settings className="h-3.5 w-3.5" /> Admin
              </Button>
            )}
          </div>
        </div>
      </header>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <div className="flex items-center justify-between gap-3 mb-4">
          <TabsList>
            <TabsTrigger value="my-skills">My Skills</TabsTrigger>
            <TabsTrigger value="templates">Templates</TabsTrigger>
            <TabsTrigger value="discover">Discover</TabsTrigger>
          </TabsList>
          {activeTab === 'discover' && catalogSkills && catalogSkills.length > 0 && (
            <SkillsViewToggle value={viewMode} onValueChange={setViewMode} />
          )}
        </div>

        {/* My Skills Tab */}
        <TabsContent value="my-skills">
          {userSkillsLoading ? (
            <LoadingSkeleton />
          ) : userSkillsError ? (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>Failed to load your skills</AlertDescription>
            </Alert>
          ) : skillCount > 0 ? (
            <div className="grid gap-3 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
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
                Skills shape how AI assists you — from code reviews to writing style. Browse templates
                or create a custom skill with AI.
              </p>
              <div className="mt-6 flex gap-3">
                <Button variant="outline" size="sm" onClick={() => setActiveTab('templates')}>
                  <Plus className="h-3.5 w-3.5 mr-1.5" /> From Template
                </Button>
                <Button size="sm" onClick={handleOpenAICreator}>
                  <Wand2 className="h-3.5 w-3.5 mr-1.5" /> Create with AI
                </Button>
              </div>
            </div>
          )}
        </TabsContent>

        {/* Templates Tab */}
        <TabsContent value="templates">
          <div className="mb-4">
            <p className="text-sm text-muted-foreground">
              Ready-made patterns to customize your AI assistant
            </p>
          </div>
          <TemplateCatalog
            workspaceSlug={workspaceSlug}
            isAdmin={false}
            onUseThis={handleUseTemplate}
          />
        </TabsContent>

        {/* Discover Tab (Gallery) */}
        <TabsContent value="discover">
          {viewMode === 'graph' ? (
            <SkillGraphView
              workspaceSlug={workspaceSlug}
              onOpenFilePeek={peekState.openSkillFilePeek}
              onSwitchToCards={onSwitchToCards}
            />
          ) : catalogPending ? (
            <ul className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {Array.from({ length: 6 }).map((_, i) => (
                <li key={i}>
                  <ArtifactCardSkeleton density="full" />
                </li>
              ))}
            </ul>
          ) : catalogError ? (
            <div role="alert" className="flex flex-col items-start gap-3 py-12">
              <p className="text-[13px] font-semibold text-foreground">Couldn&apos;t load skills.</p>
              <Button variant="link" onClick={onReloadCatalog} className="px-0 text-[#29a386]">
                Reload
              </Button>
            </div>
          ) : !catalogSkills || catalogSkills.length === 0 ? (
            <div className="flex flex-col items-start gap-2 py-12">
              <p className="text-[13px] font-semibold text-foreground">No skills yet.</p>
              <p className="text-[13px] font-medium text-muted-foreground">
                Skills are defined in your backend templates.
              </p>
            </div>
          ) : (
            <ul className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {catalogSkills.map((skill) => (
                <li key={skill.slug}>
                  <SkillCard skill={skill} onClick={() => onSelectCatalogSkill(skill.slug)} />
                </li>
              ))}
            </ul>
          )}
        </TabsContent>
      </Tabs>

      {/* Modals */}
      <SkillDetailModal
        skill={skillToView}
        open={!!skillToView}
        onOpenChange={(v) => !v && setSkillToView(null)}
        onEdit={handleEditSkill}
        onToggleActive={handleToggleSkillActive}
        onDelete={handleDeleteSkill}
        isSaving={updateUserSkill.isPending}
      />

      {templateForAdd && (
        <SkillAddModal
          open={!!templateForAdd}
          onOpenChange={(v) => !v && setTemplateForAdd(null)}
          workspaceId={currentWorkspace?.id ?? workspaceSlug}
          workspaceSlug={workspaceSlug}
          template={templateForAdd}
        />
      )}

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
    </main>
  );

  // Desktop: Resizable split layout with ChatView panel
  if (!isSmallScreen && isChatOpen) {
    return (
      <div className="h-full w-full overflow-hidden">
        <ResizablePanelGroup
          orientation="horizontal"
          className="h-full w-full overflow-hidden"
          id="skills-page-layout-v2"
        >
          <ResizablePanel id="skills-panel" defaultSize={55} minSize={35} maxSize={65} className="min-w-0 overflow-hidden">
            {mainContent}
          </ResizablePanel>
          <ResizableHandle withHandle />
          <ResizablePanel id="chat-panel" defaultSize={45} minSize={35} maxSize={65} className="min-w-0 overflow-hidden">
            <motion.aside
              id="skills-chat-panel"
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
      </div>
    );
  }

  // Desktop: Chat closed — full width + collapsed strip
  if (!isSmallScreen) {
    return (
      <div className="flex h-full w-full overflow-hidden">
        <div className="flex-1 min-w-0 overflow-hidden">{mainContent}</div>
        <CollapsedChatStrip onClick={() => setIsChatOpen(true)} />
      </div>
    );
  }

  // Mobile: Main content only
  return mainContent;
});
