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

export default observer(function ChatPage() {
  const aiStore = getAIStore();
  const store = aiStore.pilotSpace;
  const workspaceStore = useWorkspaceStore();

  // Get workspace ID from store (requires real auth)
  const workspaceId = workspaceStore.currentWorkspace?.id;

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
