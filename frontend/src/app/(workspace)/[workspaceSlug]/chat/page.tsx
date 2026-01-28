'use client';

/**
 * Chat Page - PilotSpace AI conversational interface
 * @route /[workspaceSlug]/chat
 */
import { useEffect } from 'react';
import { observer } from 'mobx-react-lite';
import { ChatView } from '@/features/ai/ChatView';
import { getAIStore } from '@/stores/ai/AIStore';
import { useWorkspaceStore } from '@/stores';

// Demo workspace UUID for development/testing
const DEMO_WORKSPACE_ID = '00000000-0000-0000-0000-000000000002';

export default observer(function ChatPage() {
  const aiStore = getAIStore();
  const store = aiStore.pilotSpace;
  const workspaceStore = useWorkspaceStore();

  // Get workspace ID, fallback to demo UUID
  const workspaceId = workspaceStore.currentWorkspace?.id || DEMO_WORKSPACE_ID;

  // Set workspace ID when component mounts or workspace changes
  useEffect(() => {
    if (workspaceId && store) {
      store.setWorkspaceId(workspaceId);
    }
  }, [workspaceId, store]);

  if (!store) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-muted-foreground">Loading AI Chat...</p>
      </div>
    );
  }

  return (
    <div className="h-full">
      <ChatView store={store} userName="User" className="h-full" />
    </div>
  );
});
