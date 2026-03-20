/**
 * NodeView Context Bridge Pattern
 *
 * CONSTRAINT: Never wrap a TipTap NodeView component in MobX observer().
 *
 * React 19's useSyncExternalStore (internal to MobX observer()) calls flushSync
 * when observables change. TipTap's ReactNodeViewRenderer also calls flushSync
 * during ProseMirror transaction processing. Nesting these produces:
 *   "flushSync was called from inside a lifecycle method" — a runtime crash.
 *
 * This is the same constraint as IssueEditorContent (feat/issue-note).
 * See: frontend/src/features/issues/components/issue-editor-content.tsx
 *
 * ## Pattern
 *
 * 1. **PlainNodeView** — passed to ReactNodeViewRenderer. Plain React function.
 *    NO observer(). Reads TipTap node attrs from NodeViewWrapper props.
 *    Wraps children in a bridge context provider.
 *
 * 2. **ReactiveChild** — rendered inside PlainNodeView. Wrapped in observer().
 *    Reads observable data from the bridge context (not from the NodeView wrapper).
 *
 * ## Usage
 *
 * ```typescript
 * // 1. Create a typed bridge context for your NodeView
 * const FileCardBridge = createNodeViewBridgeContext<FileCardBridgeData>();
 *
 * // 2. PlainNodeView (ReactNodeViewRenderer target) — NOT observer()
 * function FileCardNodeView({ node, ...tiptapProps }) {
 *   const bridgeData: FileCardBridgeData = { artifactId: node.attrs.artifactId, ... };
 *   return (
 *     <NodeViewWrapper>
 *       <FileCardBridge.Provider value={bridgeData}>
 *         <FileCardView />
 *       </FileCardBridge.Provider>
 *     </NodeViewWrapper>
 *   );
 * }
 *
 * // 3. ReactiveChild — observer() IS allowed here (not a NodeView root)
 * const FileCardView = observer(function FileCardView() {
 *   const { artifactId } = FileCardBridge.useBridgeContext();
 *   const artifactStore = useArtifactStore();
 *   // ... renders with full MobX reactivity
 * });
 * ```
 *
 * ## Phases using this pattern
 * - Phase 32: FileCardView (inline file card NodeView)
 * - Phase 33: VideoEmbedView (YouTube/Vimeo iframe NodeView)
 */
import { createContext, useContext } from 'react';

/**
 * Creates a typed React context bridge for a TipTap NodeView.
 *
 * Returns `{ Provider, useBridgeContext }`:
 * - `Provider`: wrap the NodeView's children in this to share data
 * - `useBridgeContext(): T`: call inside observer() child components to read data
 *
 * @throws {Error} if `useBridgeContext` is called outside a `Provider`
 *
 * @example
 * const FileCardBridge = createNodeViewBridgeContext<{ artifactId: string }>();
 */
export function createNodeViewBridgeContext<T>() {
  const Ctx = createContext<T | null>(null);

  function useBridgeContext(): T {
    const value = useContext(Ctx);
    if (value === null) {
      throw new Error('NodeView bridge context used outside provider');
    }
    return value;
  }

  return { Provider: Ctx.Provider, useBridgeContext };
}
