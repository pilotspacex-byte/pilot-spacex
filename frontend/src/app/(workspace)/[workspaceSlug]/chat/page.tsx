'use client';

/**
 * Chat Page - PilotSpace AI conversational interface
 * @route /[workspaceSlug]/chat
 */
import { useEffect } from 'react';
import { useParams, useSearchParams, useRouter } from 'next/navigation';
import { observer } from 'mobx-react-lite';
import { ChatView } from '@/features/ai/ChatView';
import { getAIStore } from '@/stores/ai/AIStore';
import { useWorkspaceStore } from '@/stores';

/** UUID v4 prefix pattern for distinguishing UUIDs from slugs */
const UUID_PREFIX_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-/i;

export default observer(function ChatPage() {
  const aiStore = getAIStore();
  const store = aiStore.pilotSpace;
  const workspaceStore = useWorkspaceStore();
  const params = useParams<{ workspaceSlug: string }>();
  const slug = params.workspaceSlug;
  const searchParams = useSearchParams();
  const prefill = searchParams.get('prefill') ?? undefined;
  const router = useRouter();

  // Redirect to workspace root when layout_v2 is active (chat IS the homepage)
  const useV2Layout = workspaceStore.isFeatureEnabled('layout_v2');
  useEffect(() => {
    if (useV2Layout && slug) {
      router.replace(`/${slug}`);
    }
  }, [useV2Layout, slug, router]);

  // Ensure workspaces are loaded so slug→UUID resolution works
  useEffect(() => {
    if (workspaceStore.workspaceList.length === 0 && !workspaceStore.isLoading) {
      workspaceStore.fetchWorkspaces({ ensureSelection: true });
    }
  }, [workspaceStore]);

  // Resolve workspace UUID with cascading fallback:
  // 1. currentWorkspace from store (populated after fetchWorkspaces)
  // 2. Slug lookup from workspace store
  // 3. currentWorkspaceId from localStorage (may be UUID from previous session)
  // 4. URL slug as last resort (backend accepts null context)
  const currentWs = workspaceStore.currentWorkspace;
  const storedId = workspaceStore.currentWorkspaceId;
  const resolvedWorkspaceId =
    currentWs?.id ??
    (slug && workspaceStore.getWorkspaceBySlug(slug)?.id) ??
    (storedId && UUID_PREFIX_RE.test(storedId) ? storedId : null) ??
    slug;

  // Select workspace in store if resolved from slug (so sidebar/header also update)
  useEffect(() => {
    if (slug && !currentWs) {
      const ws = workspaceStore.getWorkspaceBySlug(slug);
      if (ws) {
        workspaceStore.selectWorkspace(ws.id);
      }
    }
  }, [slug, currentWs, workspaceStore]);

  // Set workspace ID on AI store so conversation context includes it
  useEffect(() => {
    if (store && resolvedWorkspaceId && store.workspaceId !== resolvedWorkspaceId) {
      store.setWorkspaceId(resolvedWorkspaceId);
    }
  }, [store, resolvedWorkspaceId]);

  if (!store) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-muted-foreground">Loading AI Chat...</p>
      </div>
    );
  }

  return (
    <div className="h-full">
      <ChatView
        store={store}
        approvalStore={aiStore.approval}
        userName="User"
        className="h-full"
        prefillValue={prefill}
      />
    </div>
  );
});
