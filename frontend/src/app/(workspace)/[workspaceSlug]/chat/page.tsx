'use client';

/**
 * Chat Page - PilotSpace AI conversational interface
 * @route /[workspaceSlug]/chat
 */
import { observer } from 'mobx-react-lite';
import { ChatView } from '@/features/ai/ChatView';
import { getAIStore } from '@/stores/ai/AIStore';

export default observer(function ChatPage() {
  const aiStore = getAIStore();
  const store = aiStore.pilotSpace;

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
