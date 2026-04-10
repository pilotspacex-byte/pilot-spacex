/**
 * MemoryRecallPlayground — small admin tool to test semantic recall against
 * the long-term memory store. Each result has Pin / Forget actions.
 *
 * Phase 69 long-term memory.
 */

'use client';

import * as React from 'react';
import { Brain, Pin, Trash2 } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import {
  useForgetMemory,
  useMemoryRecall,
  usePinMemory,
  type MemoryItem,
} from '../hooks/use-ai-memory';

interface MemoryRecallPlaygroundProps {
  workspaceId: string | undefined;
}

export function MemoryRecallPlayground({ workspaceId }: MemoryRecallPlaygroundProps) {
  const [query, setQuery] = React.useState('');
  const recall = useMemoryRecall(workspaceId);
  const pin = usePinMemory(workspaceId);
  const forget = useForgetMemory(workspaceId);
  const [results, setResults] = React.useState<MemoryItem[]>([]);
  const [meta, setMeta] = React.useState<{ cacheHit: boolean; elapsedMs: number } | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    const data = await recall.mutateAsync({ query: query.trim(), k: 8 });
    setResults(data.items);
    setMeta({ cacheHit: data.cacheHit, elapsedMs: data.elapsedMs });
  };

  const handleForget = (id: string) => {
    forget.mutate(id, {
      onSuccess: () => setResults((prev) => prev.filter((r) => r.id !== id)),
    });
  };

  return (
    <Card>
      <CardHeader className="pb-4">
        <CardTitle className="text-base flex items-center gap-2">
          <Brain className="h-4 w-4 text-muted-foreground" />
          Memory Recall Playground
        </CardTitle>
        <CardDescription>
          Test what the AI will recall for a given query. Pin important results, forget noise.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <form onSubmit={handleSubmit} className="space-y-2">
          <label htmlFor="recall-query" className="text-sm font-medium text-foreground">
            Query
          </label>
          <Textarea
            id="recall-query"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g. authentication architecture decisions"
            rows={2}
          />
          <div className="flex items-center justify-between">
            {meta && (
              <span className="text-xs text-muted-foreground">
                {results.length} results · {meta.elapsedMs}ms{meta.cacheHit ? ' · cache' : ''}
              </span>
            )}
            <Button
              type="submit"
              size="sm"
              disabled={recall.isPending || !query.trim()}
              className="ml-auto"
            >
              {recall.isPending ? 'Recalling…' : 'Recall'}
            </Button>
          </div>
        </form>

        {results.length > 0 && (
          <ul className="space-y-2" aria-label="Recall results">
            {results.map((item) => (
              <li
                key={item.id}
                className="rounded-md border bg-card p-3 text-sm"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <Badge variant="secondary" className="text-[10px] uppercase">
                        {item.type}
                      </Badge>
                      <span className="text-[11px] text-muted-foreground">
                        score {item.score.toFixed(2)}
                      </span>
                      {item.sourceId && (
                        <code className="text-[10px] text-muted-foreground">
                          {item.sourceType}/{item.sourceId.slice(0, 8)}
                        </code>
                      )}
                    </div>
                    <p className="text-xs text-foreground/90 line-clamp-3">{item.content}</p>
                  </div>
                  <div className="flex shrink-0 gap-1">
                    <Button
                      type="button"
                      size="icon"
                      variant="ghost"
                      className="h-7 w-7"
                      onClick={() => pin.mutate(item.id)}
                      disabled={pin.isPending}
                      aria-label={`Pin memory ${item.id}`}
                    >
                      <Pin className="h-3.5 w-3.5" />
                    </Button>
                    <Button
                      type="button"
                      size="icon"
                      variant="ghost"
                      className="h-7 w-7 text-destructive hover:text-destructive"
                      onClick={() => handleForget(item.id)}
                      disabled={forget.isPending}
                      aria-label={`Forget memory ${item.id}`}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
