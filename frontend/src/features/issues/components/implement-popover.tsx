'use client';

/**
 * ImplementPopover - Popover UI for the "Implement with Claude" action.
 *
 * Fetches implementation context for the issue (suggested branch, CLI commands)
 * and presents copy-ready `pilot implement` commands for the user.
 *
 * NOT wrapped in observer() — this component is not in the TipTap editor tree
 * and has no MobX observable dependencies.
 */

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Bot, Copy, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Button } from '@/components/ui/button';
import { issuesApi } from '@/services/api/issues';
import { ApiError } from '@/services/api/client';

export interface ImplementPopoverProps {
  integrationId: string;
  workspaceId: string;
  issueId: string;
  issueIdentifier: string;
}

export function ImplementPopover({ workspaceId, issueId, issueIdentifier }: ImplementPopoverProps) {
  const [open, setOpen] = useState(false);

  const { data, isLoading, error } = useQuery({
    queryKey: ['implement-context', issueId],
    queryFn: () => issuesApi.getImplementContext(workspaceId, issueId),
    enabled: open,
    staleTime: 5 * 60_000,
    retry: false,
  });

  const handleCopy = (cmd: string) => {
    void navigator.clipboard.writeText(cmd);
    toast.success('Command copied', { description: cmd });
  };

  const interactiveCmd = `pilot implement ${issueIdentifier}`;
  const oneshotCmd = `pilot implement ${issueIdentifier} --oneshot`;

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="outline" size="sm" aria-label="Implement with Claude" aria-expanded={open}>
          <Bot className="size-3.5" />
          Implement with Claude
        </Button>
      </PopoverTrigger>

      <PopoverContent className="w-80 p-4" align="start">
        <h3 className="mb-3 text-sm font-semibold">Implement with Claude</h3>

        {isLoading && (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="size-4 animate-spin text-muted-foreground" />
          </div>
        )}

        {!isLoading && error && <ErrorMessage error={error} />}

        {!isLoading && !error && data && (
          <div className="space-y-3">
            <div>
              <p className="mb-1 text-xs font-medium text-muted-foreground">Branch</p>
              <code className="block rounded bg-muted px-2 py-1 font-mono text-xs">
                {data.suggestedBranch}
              </code>
            </div>

            <hr className="border-border" />

            <CommandRow label="Interactive" cmd={interactiveCmd} onCopy={handleCopy} />

            <CommandRow label="Oneshot (CI)" cmd={oneshotCmd} onCopy={handleCopy} />

            <p className="text-[11px] text-muted-foreground">
              Requires <code className="font-mono">pilot login</code> first.
            </p>
          </div>
        )}
      </PopoverContent>
    </Popover>
  );
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

interface CommandRowProps {
  label: string;
  cmd: string;
  onCopy: (cmd: string) => void;
}

function CommandRow({ label, cmd, onCopy }: CommandRowProps) {
  return (
    <div>
      <p className="mb-1 text-xs font-medium text-muted-foreground">{label}</p>
      <div className="flex items-center gap-2 rounded border bg-muted px-2 py-1">
        <code className="flex-1 overflow-x-auto whitespace-nowrap font-mono text-xs">{cmd}</code>
        <Button
          size="icon-sm"
          variant="ghost"
          aria-label={`Copy ${label} command`}
          className="h-5 w-5 shrink-0"
          onClick={() => onCopy(cmd)}
        >
          <Copy className="size-3" />
        </Button>
      </div>
    </div>
  );
}

interface ErrorMessageProps {
  error: unknown;
}

function ErrorMessage({ error }: ErrorMessageProps) {
  let message: string;

  if (error instanceof ApiError) {
    if (error.status === 403) {
      message = 'Only assignees and admins can implement this issue.';
    } else if (error.status === 422) {
      message = 'No GitHub integration configured. Go to Settings → Integrations.';
    } else {
      message = error.message;
    }
  } else {
    message = 'An unexpected error occurred.';
  }

  return <p className="text-sm text-destructive">{message}</p>;
}
