/**
 * MemoryProducerToggles — 4 toggle switches for memory producer opt-out.
 *
 * Phase 70 Wave 4. Controls which memory producers are active for this workspace.
 * Reads toggle state from the telemetry endpoint and fires PUT mutations on change.
 *
 * Plain React component — NOT observer().
 */

'use client';

import { Cpu } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Skeleton } from '@/components/ui/skeleton';
import { Switch } from '@/components/ui/switch';
import { useAITelemetry, useSetProducerToggle } from '../hooks/use-ai-telemetry';

interface MemoryProducerTogglesProps {
  workspaceId: string | undefined;
}

interface ProducerToggleConfig {
  key: string;
  label: string;
  description: string;
  experimental?: boolean;
}

const PRODUCER_TOGGLES: ProducerToggleConfig[] = [
  {
    key: 'agent_turn',
    label: 'Record agent turns',
    description: 'Store AI conversation turns for long-term recall.',
  },
  {
    key: 'user_correction',
    label: 'Record user corrections',
    description: 'Learn from explicit user feedback and corrections.',
  },
  {
    key: 'pr_review_finding',
    label: 'Record PR review findings',
    description: 'Persist code review insights for future reference.',
  },
  {
    key: 'summarizer',
    label: 'Summarize memory (experimental)',
    description: 'Periodically condense memories into summaries. Opt-in only.',
    experimental: true,
  },
];

export function MemoryProducerToggles({ workspaceId }: MemoryProducerTogglesProps) {
  const { data, isLoading } = useAITelemetry(workspaceId);
  const toggleMutation = useSetProducerToggle(workspaceId);

  const toggles = data?.toggles;

  const handleToggle = (producer: string, enabled: boolean) => {
    toggleMutation.mutate({ producer, enabled });
  };

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <Cpu className="h-4 w-4 text-muted-foreground" />
          <CardTitle className="text-base">Memory Producers</CardTitle>
        </div>
        <CardDescription>
          Control which AI interactions are stored for long-term recall. Disabling a producer drops
          future events without deleting existing memories.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        ) : (
          PRODUCER_TOGGLES.map((toggle) => {
            const checked = toggles?.[toggle.key as keyof typeof toggles] ?? false;
            return (
              <div key={toggle.key} className="flex items-center justify-between gap-4">
                <div className="space-y-0.5">
                  <Label
                    htmlFor={`toggle-${toggle.key}`}
                    className="text-sm font-medium leading-none"
                  >
                    {toggle.label}
                    {toggle.experimental && (
                      <span className="ml-1.5 text-xs text-amber-600 dark:text-amber-400">
                        experimental
                      </span>
                    )}
                  </Label>
                  <p className="text-xs text-muted-foreground">{toggle.description}</p>
                </div>
                <Switch
                  id={`toggle-${toggle.key}`}
                  checked={checked}
                  onCheckedChange={(value) => handleToggle(toggle.key, value)}
                  aria-label={toggle.label}
                  disabled={toggleMutation.isPending}
                />
              </div>
            );
          })
        )}
      </CardContent>
    </Card>
  );
}
