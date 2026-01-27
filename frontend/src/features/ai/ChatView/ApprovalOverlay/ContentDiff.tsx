/**
 * ContentDiff - Display content changes with before/after comparison
 */

import { memo } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';

interface ContentDiffProps {
  before: string;
  after: string;
  className?: string;
}

export const ContentDiff = memo<ContentDiffProps>(({ before, after, className }) => {
  return (
    <Tabs defaultValue="after" className={className}>
      <TabsList className="grid w-full grid-cols-2">
        <TabsTrigger value="before">Before</TabsTrigger>
        <TabsTrigger value="after">After</TabsTrigger>
      </TabsList>

      <TabsContent value="before" className="mt-2">
        <ScrollArea className="h-[300px] rounded border bg-muted/30">
          <pre className="p-4 text-xs font-mono whitespace-pre-wrap">{before}</pre>
        </ScrollArea>
      </TabsContent>

      <TabsContent value="after" className="mt-2">
        <ScrollArea className="h-[300px] rounded border bg-muted/30">
          <pre className="p-4 text-xs font-mono whitespace-pre-wrap">{after}</pre>
        </ScrollArea>
      </TabsContent>
    </Tabs>
  );
});

ContentDiff.displayName = 'ContentDiff';
