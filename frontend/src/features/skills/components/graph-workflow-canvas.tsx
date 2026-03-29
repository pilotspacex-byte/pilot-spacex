'use client';

/**
 * GraphWorkflowCanvas — ReactFlow-based workflow graph editor.
 *
 * CRITICAL CONSTRAINT: GraphWorkflowInner MUST NOT be wrapped in observer().
 * MobX useSyncExternalStore + ReactFlow causes nested flushSync in React 19.
 * MobX state is accessed via GraphWorkflowContext (context bridge pattern).
 *
 * Structure:
 *   GraphWorkflowCanvas (outer) — provides ReactFlowProvider + context
 *   GraphWorkflowInner (inner) — plain React component, NOT observer
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  ReactFlow,
  ReactFlowProvider,
  MiniMap,
  Controls,
  Background,
  BackgroundVariant,
  Panel,
  addEdge,
  useReactFlow,
  type Node,
  type Edge,
  type Connection,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Eye, FileInput, LayoutGrid, Play, Square } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';

import {
  WorkflowNodeType,
  WORKFLOW_NODE_SPECS,
  createWorkflowNode,
  type WorkflowNodeData,
} from '@/features/skills/utils/graph-node-types';
import { validateGraph } from '@/features/skills/utils/graph-validation-engine';
import { GraphWorkflowStore } from '@/features/skills/stores/GraphWorkflowStore';
import { GraphWorkflowContext } from '@/features/skills/contexts/graph-workflow-context';
import { workflowNodeTypes } from '@/features/skills/components/graph-node-component';
import { workflowEdgeTypes } from '@/features/skills/components/graph-edge-component';
import { GraphConfigPanel } from '@/features/skills/components/graph-config-panel';
import { GraphValidationBadge } from '@/features/skills/components/graph-validation-badge';
import { useGraphWorkflow } from '@/features/skills/hooks/use-graph-workflow';
import { useDagreLayout } from '@/features/skills/hooks/use-dagre-layout';

// ── Inner Component (NOT observer) ──────────────────────────────────────────

interface GraphWorkflowInnerProps {
  store: GraphWorkflowStore;
  initialNodes?: Node<WorkflowNodeData>[];
  initialEdges?: Edge[];
  onSave?: (data: { nodes: Node<WorkflowNodeData>[]; edges: Edge[] }) => void;
  onPreview?: () => void;
  onCompile?: () => void;
  isCompiling?: boolean;
  onImport?: (skillContent: string) => void;
}

function GraphWorkflowInner({ store, initialNodes: initNodes, initialEdges: initEdges, onSave, onPreview, onCompile, isCompiling, onImport }: GraphWorkflowInnerProps) {
  const { screenToFlowPosition } = useReactFlow();
  const {
    nodes,
    edges,
    setNodes,
    setEdges,
    onNodesChange,
    onEdgesChange,
    onConnect: _hookOnConnect,
    undo,
    redo,
    pushHistory,
  } = useGraphWorkflow(initNodes, initEdges);

  const containerRef = useRef<HTMLDivElement>(null);
  const { applyLayout } = useDagreLayout();

  // ── Import dialog state ─────────────────────────────────────────────────
  const [showImportDialog, setShowImportDialog] = useState(false);
  const [importContent, setImportContent] = useState('');

  // ── Validation: run on node/edge changes with 500ms debounce ───────────

  const validationTimerRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  useEffect(() => {
    clearTimeout(validationTimerRef.current);
    validationTimerRef.current = setTimeout(() => {
      const errors = validateGraph(nodes, edges);
      store.setValidationErrors(errors);
    }, 500);
    return () => clearTimeout(validationTimerRef.current);
  }, [nodes, edges, store]);

  // ── Connect handler with conditional edge detection ─────────────────────

  const onConnect = useCallback(
    (connection: Connection) => {
      const sourceNode = nodes.find((n) => n.id === connection.source);
      const sourceHandle = connection.sourceHandle ?? '';

      // Detect conditional edges from Condition node boolean handles
      let edgeType = 'sequential';
      let edgeData: Record<string, unknown> = {};

      if (sourceNode?.data?.nodeType === WorkflowNodeType.Condition) {
        if (sourceHandle.startsWith('output:boolean:')) {
          edgeType = 'conditional';
          const branch = sourceHandle.split(':')[2] as 'true' | 'false';
          edgeData = { branch };
        }
      }

      setEdges((eds) =>
        addEdge(
          {
            ...connection,
            type: edgeType,
            data: edgeData,
          },
          eds
        )
      );
      requestAnimationFrame(() => pushHistory());
    },
    [nodes, setEdges, pushHistory]
  );

  // ── Drop handler ────────────────────────────────────────────────────────

  const onDrop = useCallback(
    (event: React.DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      const nodeType = event.dataTransfer.getData('application/workflowNodeType');
      if (!nodeType || !(nodeType in WORKFLOW_NODE_SPECS)) return;

      const position = screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });

      const newNode = createWorkflowNode(
        nodeType as WorkflowNodeType,
        position
      );

      setNodes((nds) => [...nds, newNode]);
      store.markDirty();
      requestAnimationFrame(() => pushHistory());
    },
    [screenToFlowPosition, setNodes, store, pushHistory]
  );

  const onDragOver = useCallback((event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  // ── Node click → select via store ───────────────────────────────────────

  const onNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node<WorkflowNodeData>) => {
      store.selectNode(node.id);
    },
    [store]
  );

  const onPaneClick = useCallback(() => {
    store.selectNode(null);
  }, [store]);

  // ── Node drag end → push history ────────────────────────────────────────

  const onNodeDragStop = useCallback(() => {
    store.markDirty();
    pushHistory();
  }, [store, pushHistory]);

  // ── Delete selected nodes/edges ─────────────────────────────────────────

  const deleteSelected = useCallback(() => {
    setNodes((nds) => nds.filter((n) => !n.selected));
    // Edges connected to deleted nodes are auto-removed by ReactFlow
    store.markDirty();
    requestAnimationFrame(() => pushHistory());
  }, [setNodes, store, pushHistory]);

  // ── Keyboard shortcuts ──────────────────────────────────────────────────

  const onKeyDown = useCallback(
    (event: React.KeyboardEvent<HTMLDivElement>) => {
      const isCtrlOrMeta = event.ctrlKey || event.metaKey;

      if (isCtrlOrMeta && event.shiftKey && event.key === 'z') {
        event.preventDefault();
        redo();
        return;
      }

      if (isCtrlOrMeta && event.key === 'z') {
        event.preventDefault();
        undo();
        return;
      }

      if (isCtrlOrMeta && event.key === 's') {
        event.preventDefault();
        onSave?.({ nodes, edges });
        return;
      }

      if (isCtrlOrMeta && event.key === 'a') {
        event.preventDefault();
        setNodes((nds) => nds.map((n) => ({ ...n, selected: true })));
        return;
      }

      if (event.key === 'Delete' || event.key === 'Backspace') {
        // Only delete if not typing in an input
        const target = event.target as HTMLElement;
        if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') return;
        event.preventDefault();
        deleteSelected();
      }
    },
    [undo, redo, deleteSelected, setNodes, onSave, nodes, edges]
  );

  // ── Update node data (for config panel) ──────────────────────────────────

  const updateNodeData = useCallback(
    (id: string, partialData: Partial<WorkflowNodeData>) => {
      setNodes((nds) =>
        nds.map((node) =>
          node.id === id
            ? { ...node, data: { ...node.data, ...partialData } }
            : node
        )
      );
      store.markDirty();
    },
    [setNodes, store]
  );

  // ── MiniMap node color ──────────────────────────────────────────────────

  const minimapNodeColor = useCallback((node: Node) => {
    const nodeType = node.type as WorkflowNodeType;
    return WORKFLOW_NODE_SPECS[nodeType]?.color ?? '#666';
  }, []);

  return (
    <div className="flex h-full">
      <div
        ref={containerRef}
        className="flex-1 h-full relative"
        onKeyDown={onKeyDown}
        tabIndex={0}
        style={{ outline: 'none' }}
      >
        <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={workflowNodeTypes}
        edgeTypes={workflowEdgeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onNodeClick={onNodeClick}
        onPaneClick={onPaneClick}
        onNodeDragStop={onNodeDragStop}
        fitView
        proOptions={{ hideAttribution: true }}
        minZoom={0.2}
        maxZoom={3}
        className="!bg-background dark:!bg-[#1a1a2e]"
        deleteKeyCode={null}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={24}
          size={0.6}
          className="opacity-[0.12]"
        />
        <MiniMap
          position="bottom-right"
          className="!bottom-4 !right-4"
          nodeColor={minimapNodeColor}
          maskColor="rgba(26, 26, 46, 0.7)"
        />
        <Controls position="bottom-left" className="!bottom-4 !left-4" />
        <Panel position="top-left">
          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={() => {
                applyLayout('TB');
                store.markDirty();
                requestAnimationFrame(() => pushHistory());
              }}
              className="flex items-center gap-1.5 rounded-md bg-muted/90 px-2.5 py-1.5 text-xs text-muted-foreground backdrop-blur-sm border border-border hover:bg-accent transition-colors"
              aria-label="Auto layout graph"
            >
              <LayoutGrid className="h-3.5 w-3.5" />
              Auto Layout
            </button>
            {store.isPreviewRunning ? (
              <button
                type="button"
                onClick={() => store.stopPreview()}
                aria-label="Stop preview"
                className="flex items-center gap-1.5 rounded-md bg-destructive/20 px-2.5 py-1.5 text-xs text-destructive backdrop-blur-sm border border-destructive/30 hover:bg-destructive/30 transition-colors"
              >
                <Square className="h-3.5 w-3.5" />
                Stop
              </button>
            ) : (
              <button
                type="button"
                onClick={onPreview}
                disabled={!store.graphId || store.hasErrors}
                aria-label="Preview execution"
                className="flex items-center gap-1.5 rounded-md bg-muted/90 px-2.5 py-1.5 text-xs text-muted-foreground backdrop-blur-sm border border-border hover:bg-accent transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <Eye className="h-3.5 w-3.5" />
                Preview
              </button>
            )}
            {onCompile && (
              <button
                type="button"
                onClick={onCompile}
                disabled={!store.graphId || store.hasErrors || isCompiling}
                aria-label="Compile graph to SKILL.md"
                className="flex items-center gap-1.5 rounded-md bg-primary/20 px-2.5 py-1.5 text-xs text-primary backdrop-blur-sm border border-primary/30 hover:bg-primary/30 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                data-testid="compile-btn"
              >
                {isCompiling ? (
                  <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-primary/30 border-t-primary" />
                ) : (
                  <Play className="h-3.5 w-3.5" />
                )}
                Compile
              </button>
            )}
            <button
              type="button"
              onClick={() => setShowImportDialog(true)}
              aria-label="Import from SKILL.md"
              className="flex items-center gap-1.5 rounded-md bg-muted/90 px-2.5 py-1.5 text-xs text-muted-foreground backdrop-blur-sm border border-border hover:bg-accent transition-colors"
            >
              <FileInput className="h-3.5 w-3.5" />
              Import
            </button>
          </div>
        </Panel>
        <Panel position="top-right">
          <GraphValidationBadge />
        </Panel>
      </ReactFlow>
      </div>
      <GraphConfigPanel nodes={nodes} onUpdateNode={updateNodeData} />

      {/* Import Dialog */}
      <Dialog open={showImportDialog} onOpenChange={(open) => {
        setShowImportDialog(open);
        if (!open) setImportContent('');
      }}>
        <DialogContent className="sm:max-w-[520px]">
          <DialogHeader>
            <DialogTitle>Import from SKILL.md</DialogTitle>
            <DialogDescription>
              Paste your SKILL.md content below to generate a graph representation.
            </DialogDescription>
          </DialogHeader>
          <Textarea
            value={importContent}
            onChange={(e) => setImportContent(e.target.value)}
            placeholder="Paste SKILL.md content here..."
            className="h-48 font-mono text-xs resize-none"
            aria-label="SKILL.md content to import"
          />
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setShowImportDialog(false);
                setImportContent('');
              }}
            >
              Cancel
            </Button>
            <Button
              disabled={!importContent.trim()}
              onClick={() => {
                onImport?.(importContent);
                setShowImportDialog(false);
                setImportContent('');
              }}
            >
              Import
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ── Outer Component (provides context) ──────────────────────────────────────

export interface GraphWorkflowCanvasProps {
  graphId?: string;
  initialNodes?: Node<WorkflowNodeData>[];
  initialEdges?: Edge[];
  onSave?: (data: { nodes: Node<WorkflowNodeData>[]; edges: Edge[] }) => void;
  onPreview?: () => void;
  onCompile?: () => void;
  isCompiling?: boolean;
  onImport?: (skillContent: string) => void;
}

export function GraphWorkflowCanvas({
  graphId,
  initialNodes,
  initialEdges,
  onSave,
  onPreview,
  onCompile,
  isCompiling,
  onImport,
}: GraphWorkflowCanvasProps) {
  const store = useMemo(() => {
    const s = new GraphWorkflowStore();
    if (graphId) s.setGraphId(graphId);
    return s;
  }, [graphId]);

  const onNodeSelect = useCallback(
    (id: string | null) => {
      store.selectNode(id);
    },
    [store]
  );

  const contextValue = useMemo(
    () => ({ store, onNodeSelect }),
    [store, onNodeSelect]
  );

  return (
    <ReactFlowProvider>
      <GraphWorkflowContext.Provider value={contextValue}>
        <GraphWorkflowInner
          store={store}
          initialNodes={initialNodes}
          initialEdges={initialEdges}
          onSave={onSave}
          onPreview={onPreview}
          onCompile={onCompile}
          isCompiling={isCompiling}
          onImport={onImport}
        />
      </GraphWorkflowContext.Provider>
    </ReactFlowProvider>
  );
}
