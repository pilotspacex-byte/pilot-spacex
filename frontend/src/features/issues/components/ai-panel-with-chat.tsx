/**
 * AI Panel with Chat Integration.
 *
 * Tabbed interface for:
 * - Context view (existing AIContextPanel)
 * - Chat view (new ConversationPanel)
 *
 * @see specs/004-mvp-agents-build/tasks/P22-P25-T178-T222.md#T219
 */
'use client';

import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Sparkles, MessageSquare } from 'lucide-react';
import { AIContextPanel } from './ai-context-panel';
import { ConversationPanel } from './conversation-panel';
import { cn } from '@/lib/utils';

export interface AIPanelWithChatProps {
  issueId: string;
  className?: string;
  defaultTab?: 'context' | 'chat';
}

/**
 * AI Panel with integrated Context and Chat tabs.
 *
 * Provides seamless navigation between AI context generation
 * and multi-turn conversation within issue context.
 *
 * @example
 * ```tsx
 * <AIPanelWithChat issueId="123" defaultTab="context" />
 * ```
 */
export function AIPanelWithChat({
  issueId,
  className,
  defaultTab = 'context',
}: AIPanelWithChatProps) {
  return (
    <Tabs defaultValue={defaultTab} className={cn('h-full flex flex-col', className)}>
      <TabsList variant="line" className="border-b px-4">
        <TabsTrigger value="context" className="gap-2">
          <Sparkles className="h-4 w-4" aria-hidden="true" />
          <span>Context</span>
        </TabsTrigger>
        <TabsTrigger value="chat" className="gap-2">
          <MessageSquare className="h-4 w-4" aria-hidden="true" />
          <span>Chat</span>
        </TabsTrigger>
      </TabsList>

      <TabsContent value="context" className="flex-1 m-0 focus-visible:ring-0">
        <AIContextPanel issueId={issueId} className="h-full" />
      </TabsContent>

      <TabsContent value="chat" className="flex-1 m-0 focus-visible:ring-0">
        <ConversationPanel issueId={issueId} className="h-full" />
      </TabsContent>
    </Tabs>
  );
}
