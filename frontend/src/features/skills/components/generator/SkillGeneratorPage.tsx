/**
 * SkillGeneratorPage -- Unified 3-panel skill generator layout.
 *
 * Layout:
 *   +------------------------------------------+
 *   | Header: Back | title | [Save] [Publish]  |
 *   +------------------------------------------+
 *   |  Palette |  Graph Canvas  |  Chat Panel   |
 *   |  (w-56)  |  (flex-1)      |  (w-[380px])  |
 *   +----------+----------------+---------------+
 *   | SKILL.md Preview (collapsible, h-64)      |
 *   +------------------------------------------+
 *
 * CRITICAL: This component MUST NOT be wrapped in observer().
 * ReactFlow canvas inside MUST NOT be in an observer tree.
 * Context bridge pattern per TipTap/.claude rules.
 *
 * @module features/skills/components/generator/SkillGeneratorPage
 */

'use client';

import { Suspense, useCallback, useEffect, useMemo, useState } from 'react';
import dynamic from 'next/dynamic';
import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft, Loader2, Save, Upload } from 'lucide-react';
import { toast } from 'sonner';
import type { Node, Edge } from '@xyflow/react';

import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useStore } from '@/stores';
import {
  useSkillGraphByTemplate,
  useSkillGraphMutation,
} from '@/features/skills/hooks/use-skill-graph-queries';
import {
  useSkillTemplates,
  useCreateSkillTemplate,
  useUpdateSkillTemplate,
} from '@/services/api/skill-templates';
import { SkillGeneratorPageStore } from '@/features/skills/stores/SkillGeneratorPageStore';
import { GeneratorChatPanel } from './GeneratorChatPanel';
import { SkillPreviewPanel } from './SkillPreviewPanel';
import { PublishModal } from '@/features/skills/components/marketplace/PublishModal';
import type { WorkflowNodeData } from '@/features/skills/utils/graph-node-types';

// ---------------------------------------------------------------------------
// Dynamic imports (SSR disabled for ReactFlow)
// ---------------------------------------------------------------------------

const GraphWorkflowCanvas = dynamic(
  () =>
    import('@/features/skills/components/graph-workflow-canvas').then(
      (mod) => mod.GraphWorkflowCanvas,
    ),
  { ssr: false },
);

const GraphNodePalette = dynamic(
  () =>
    import('@/features/skills/components/graph-node-palette').then(
      (mod) => mod.GraphNodePalette,
    ),
  { ssr: false },
);

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const SKILL_CATEGORIES = [
  'code-review',
  'code-generation',
  'documentation',
  'testing',
  'debugging',
  'planning',
  'custom',
] as const;

// ---------------------------------------------------------------------------
// Component (NOT observer — context bridge pattern)
// ---------------------------------------------------------------------------

interface SkillGeneratorPageProps {
  skillId?: string;
}

export function SkillGeneratorPage({ skillId }: SkillGeneratorPageProps) {
  const params = useParams();
  const router = useRouter();
  const workspaceSlug = params?.workspaceSlug as string;
  const { workspaceStore } = useStore();
  const currentWorkspace = workspaceStore.getWorkspaceBySlug(workspaceSlug);
  const workspaceId = currentWorkspace?.id || workspaceSlug;

  // Dedicated store per page instance
  const store = useMemo(() => new SkillGeneratorPageStore(), []);

  // ── Edit mode: load template + graph ──────────────────────────────────

  const { data: templates } = useSkillTemplates(workspaceSlug);
  const editTemplate = useMemo(
    () => (skillId ? templates?.find((t) => t.id === skillId) : undefined),
    [skillId, templates],
  );

  const { data: existingGraph, isLoading: isGraphLoading } =
    useSkillGraphByTemplate(workspaceId, skillId);

  // Set edit mode when template loads
  useEffect(() => {
    if (editTemplate && !store.isEditMode) {
      store.setEditMode(editTemplate.id, editTemplate.name);
      store.setSkillContent(editTemplate.skill_content);
      store.setSkillDescription(editTemplate.description);
      store.setSkillCategory(editTemplate.role_type ?? 'custom');
      store.markClean();
    }
  }, [editTemplate, store]);

  // ── Mutations ─────────────────────────────────────────────────────────

  const graphMutation = useSkillGraphMutation(workspaceId);
  const createTemplate = useCreateSkillTemplate(workspaceSlug);
  const updateTemplate = useUpdateSkillTemplate(workspaceSlug);

  // ── Save dialog ───────────────────────────────────────────────────────

  const [saveDialogOpen, setSaveDialogOpen] = useState(false);
  const [pendingSaveData, setPendingSaveData] = useState<{
    nodes: Node<WorkflowNodeData>[];
    edges: Edge[];
  } | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  // ── Publish dialog ────────────────────────────────────────────────────

  const [publishOpen, setPublishOpen] = useState(false);

  // ── Handlers ──────────────────────────────────────────────────────────

  const handleSave = useCallback(
    (data: { nodes: Node<WorkflowNodeData>[]; edges: Edge[] }) => {
      setPendingSaveData(data);
      if (store.isEditMode && store.editingTemplateId) {
        // Direct save in edit mode (no dialog needed)
        void handleEditSave(data);
      } else {
        setSaveDialogOpen(true);
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [store.isEditMode, store.editingTemplateId],
  );

  const handleEditSave = useCallback(
    async (data: { nodes: Node<WorkflowNodeData>[]; edges: Edge[] }) => {
      if (!store.editingTemplateId) return;
      setIsSaving(true);
      try {
        // Update template
        await updateTemplate.mutateAsync({
          id: store.editingTemplateId,
          data: {
            name: store.skillName,
            description: store.skillDescription,
            skill_content: store.skillContent,
          },
        });

        // Save graph data
        await graphMutation.mutateAsync({
          templateId: store.editingTemplateId,
          data: {
            graph_json: { nodes: data.nodes, edges: data.edges },
            node_count: data.nodes.length,
            edge_count: data.edges.length,
          },
        });

        store.markClean();
        toast.success('Skill saved');
      } catch {
        toast.error('Failed to save skill');
      } finally {
        setIsSaving(false);
      }
    },
    [store, updateTemplate, graphMutation],
  );

  const handleNewSave = useCallback(async () => {
    if (!pendingSaveData || !store.skillName.trim()) return;
    setIsSaving(true);
    try {
      // Create template first
      const template = await createTemplate.mutateAsync({
        name: store.skillName.trim(),
        description:
          store.skillDescription ||
          `Graph workflow (${store.skillCategory}): ${store.skillName.trim()}`,
        skill_content:
          store.skillContent ||
          `# ${store.skillName.trim()}\n\nGraph-based skill workflow.`,
        role_type: store.skillCategory,
      });

      // Then save graph
      await graphMutation.mutateAsync({
        templateId: template.id,
        data: {
          graph_json: {
            nodes: pendingSaveData.nodes,
            edges: pendingSaveData.edges,
          },
          node_count: pendingSaveData.nodes.length,
          edge_count: pendingSaveData.edges.length,
        },
      });

      store.markClean();
      toast.success('Skill created');
      setSaveDialogOpen(false);
      router.push(`/${workspaceSlug}/skills`);
    } catch {
      toast.error('Failed to create skill');
    } finally {
      setIsSaving(false);
    }
  }, [
    pendingSaveData,
    store,
    createTemplate,
    graphMutation,
    router,
    workspaceSlug,
  ]);

  // ── Graph data for edit mode ──────────────────────────────────────────

  const graphJson = useMemo(() => {
    if (!existingGraph?.graph_json) return undefined;
    const json = existingGraph.graph_json as {
      nodes?: Node<WorkflowNodeData>[];
      edges?: Edge[];
    };
    return json;
  }, [existingGraph]);

  // ── Loading state for edit mode ───────────────────────────────────────

  if (skillId && isGraphLoading) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-3.5rem)]">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // ── Render ────────────────────────────────────────────────────────────

  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem)]">
      {/* Header */}
      <div className="shrink-0 flex items-center gap-3 px-4 py-3 border-b bg-background">
        <Button
          size="icon"
          variant="ghost"
          className="h-8 w-8"
          onClick={() => router.push(`/${workspaceSlug}/skills`)}
          aria-label="Back to skills"
        >
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <h1 className="text-sm font-semibold truncate">
          {store.isEditMode
            ? `Editing ${store.editingTemplateName}`
            : 'Skill Generator'}
        </h1>
        <div className="flex-1" />

        {/* Publish (only in edit mode with saved template) */}
        {store.isEditMode && store.editingTemplateId && (
          <Button
            size="sm"
            variant="outline"
            className="gap-1.5"
            onClick={() => setPublishOpen(true)}
          >
            <Upload className="h-3.5 w-3.5" />
            Publish
          </Button>
        )}

        {/* Save */}
        <Button
          size="sm"
          className="gap-1.5"
          disabled={isSaving}
          onClick={() =>
            handleSave({ nodes: [], edges: [] })
          }
        >
          {isSaving ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Save className="h-3.5 w-3.5" />
          )}
          Save
        </Button>
      </div>

      {/* Main 3-panel area */}
      <div className="flex flex-1 min-h-0">
        {/* Left: Node Palette */}
        <Suspense fallback={null}>
          <GraphNodePalette />
        </Suspense>

        {/* Center: Graph Canvas */}
        <div className="flex-1 min-h-0">
          <Suspense
            fallback={
              <div className="flex items-center justify-center h-full">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            }
          >
            <GraphWorkflowCanvas
              graphId={existingGraph?.id}
              initialNodes={graphJson?.nodes}
              initialEdges={graphJson?.edges}
              onSave={handleSave}
            />
          </Suspense>
        </div>

        {/* Right: Chat Panel */}
        <div className="w-[380px] shrink-0 border-l">
          <GeneratorChatPanel store={store} workspaceId={workspaceId} />
        </div>
      </div>

      {/* Bottom: Preview Panel */}
      <SkillPreviewPanel store={store} />

      {/* Save Dialog (new skill only) */}
      <Dialog open={saveDialogOpen} onOpenChange={setSaveDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Save Skill</DialogTitle>
            <DialogDescription>
              Create a new skill template for this graph workflow.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label htmlFor="gen-skill-name">Skill Name</Label>
              <Input
                id="gen-skill-name"
                value={store.skillName}
                onChange={(e) => store.setSkillName(e.target.value)}
                placeholder="e.g. Code Review Workflow"
                autoFocus
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="gen-skill-category">Category</Label>
              <Select
                value={store.skillCategory}
                onValueChange={(v) => store.setSkillCategory(v)}
              >
                <SelectTrigger id="gen-skill-category">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {SKILL_CATEGORIES.map((cat) => (
                    <SelectItem key={cat} value={cat}>
                      {cat
                        .split('-')
                        .map(
                          (w) => (w[0]?.toUpperCase() ?? '') + w.slice(1),
                        )
                        .join(' ')}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setSaveDialogOpen(false)}
              disabled={isSaving}
            >
              Cancel
            </Button>
            <Button
              onClick={handleNewSave}
              disabled={!store.skillName.trim() || isSaving}
            >
              {isSaving && (
                <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
              )}
              Create & Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Publish Modal */}
      {store.isEditMode && store.editingTemplateId && (
        <PublishModal
          open={publishOpen}
          onOpenChange={setPublishOpen}
          skillTemplateId={store.editingTemplateId}
          skillTemplateName={store.skillName}
          workspaceId={workspaceId}
        />
      )}
    </div>
  );
}
