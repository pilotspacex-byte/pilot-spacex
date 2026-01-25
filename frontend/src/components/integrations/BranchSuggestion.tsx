'use client';

/**
 * BranchSuggestion - Generate branch names from issues.
 *
 * T189: Shows suggested branch name with copy-to-clipboard functionality.
 *
 * @example
 * ```tsx
 * <BranchSuggestion
 *   workspaceId={workspace.id}
 *   issueId={issue.id}
 *   issueIdentifier={issue.identifier}
 * />
 * ```
 */

import * as React from 'react';
import { observer } from 'mobx-react-lite';
import { GitBranch, Copy, Check, Terminal, AlertCircle, RefreshCw } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { Skeleton } from '@/components/ui/skeleton';
import { useQuery } from '@tanstack/react-query';
import { integrationsApi, type BranchNameSuggestion } from '@/services/api';

// ============================================================================
// Types
// ============================================================================

export interface BranchSuggestionProps {
  /** Workspace ID */
  workspaceId: string;
  /** Issue ID */
  issueId: string;
  /** Issue identifier for display */
  issueIdentifier?: string;
  /** Compact mode for inline display */
  compact?: boolean;
  /** Additional class name */
  className?: string;
}

// ============================================================================
// Query Keys
// ============================================================================

const branchKeys = {
  all: ['branch-names'] as const,
  issue: (workspaceId: string, issueId: string) =>
    [...branchKeys.all, workspaceId, issueId] as const,
};

// ============================================================================
// Copy Button with Feedback
// ============================================================================

interface CopyButtonProps {
  text: string;
  label?: string;
  variant?: 'default' | 'outline' | 'ghost';
  size?: 'default' | 'sm' | 'icon';
  className?: string;
}

function CopyButton({ text, label, variant = 'outline', size = 'sm', className }: CopyButtonProps) {
  const [copied, setCopied] = React.useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant={variant}
            size={size}
            onClick={handleCopy}
            className={cn(
              'transition-all',
              copied && 'bg-green-50 text-green-600 border-green-200',
              className
            )}
          >
            {copied ? <Check className="size-4" /> : <Copy className="size-4" />}
            {label && <span className="ml-2">{label}</span>}
          </Button>
        </TooltipTrigger>
        <TooltipContent>{copied ? 'Copied!' : 'Copy to clipboard'}</TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

// ============================================================================
// Compact Mode
// ============================================================================

interface CompactBranchSuggestionProps {
  data: BranchNameSuggestion;
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
}

function CompactBranchSuggestion({
  data,
  isLoading,
  error,
  refetch,
}: CompactBranchSuggestionProps) {
  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-sm">
        <GitBranch className="size-4 text-muted-foreground" />
        <Skeleton className="h-4 w-48" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <AlertCircle className="size-4" />
        <span>Unable to generate branch name</span>
        <Button variant="ghost" size="icon" onClick={refetch}>
          <RefreshCw className="size-3" />
        </Button>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <code className="flex items-center gap-2 rounded bg-muted px-2 py-1 text-sm font-mono">
        <GitBranch className="size-3 text-muted-foreground" />
        {data.branchName}
      </code>
      <CopyButton text={data.branchName} size="icon" variant="ghost" />
    </div>
  );
}

// ============================================================================
// Full Card Mode
// ============================================================================

interface FullBranchSuggestionProps {
  data: BranchNameSuggestion;
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
  issueIdentifier?: string;
  className?: string;
}

function FullBranchSuggestion({
  data,
  isLoading,
  error,
  refetch,
  issueIdentifier,
  className,
}: FullBranchSuggestionProps) {
  if (isLoading) {
    return (
      <Card className={className}>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <GitBranch className="size-4" />
            Branch Name
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <Skeleton className="h-10" />
          <Skeleton className="h-10" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className={className}>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <GitBranch className="size-4" />
            Branch Name
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-4 text-center">
            <AlertCircle className="size-8 text-muted-foreground/50 mb-2" />
            <p className="text-sm text-muted-foreground">Unable to generate branch name</p>
            <Button variant="ghost" size="sm" onClick={refetch} className="mt-2">
              <RefreshCw className="size-4 mr-2" />
              Retry
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <GitBranch className="size-4" />
          Branch Name
        </CardTitle>
        {issueIdentifier && (
          <CardDescription>Suggested branch name for {issueIdentifier}</CardDescription>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Branch name */}
        <div className="space-y-2">
          <label className="text-xs font-medium text-muted-foreground">Branch</label>
          <div className="flex items-center gap-2">
            <code className="flex-1 flex items-center gap-2 rounded-md border bg-muted px-3 py-2 font-mono text-sm overflow-x-auto">
              <GitBranch className="size-4 text-muted-foreground shrink-0" />
              <span className="whitespace-nowrap">{data.branchName}</span>
            </code>
            <CopyButton text={data.branchName} label="Copy" />
          </div>
        </div>

        {/* Git command */}
        <div className="space-y-2">
          <label className="text-xs font-medium text-muted-foreground">Git Command</label>
          <div className="flex items-center gap-2">
            <code className="flex-1 flex items-center gap-2 rounded-md border bg-slate-900 text-slate-100 px-3 py-2 font-mono text-sm overflow-x-auto">
              <Terminal className="size-4 text-slate-400 shrink-0" />
              <span className="whitespace-nowrap">{data.gitCommand}</span>
            </code>
            <CopyButton text={data.gitCommand} label="Copy" className="border-slate-700" />
          </div>
        </div>

        {/* Format info */}
        <p className="text-xs text-muted-foreground">
          Format: <code className="text-xs bg-muted px-1 rounded">{data.format}</code>
        </p>
      </CardContent>
    </Card>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export const BranchSuggestion = observer(function BranchSuggestion({
  workspaceId,
  issueId,
  issueIdentifier,
  compact = false,
  className,
}: BranchSuggestionProps) {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: branchKeys.issue(workspaceId, issueId),
    queryFn: () => integrationsApi.getBranchName(workspaceId, issueId),
    enabled: !!workspaceId && !!issueId,
    staleTime: 1000 * 60 * 60, // 1 hour - branch names don't change often
    gcTime: 1000 * 60 * 60 * 24, // 24 hours
  });

  if (compact) {
    return (
      <CompactBranchSuggestion
        data={data!}
        isLoading={isLoading}
        error={error as Error | null}
        refetch={refetch}
      />
    );
  }

  return (
    <FullBranchSuggestion
      data={data!}
      isLoading={isLoading}
      error={error as Error | null}
      refetch={refetch}
      issueIdentifier={issueIdentifier}
      className={className}
    />
  );
});

// ============================================================================
// Hook for programmatic use
// ============================================================================

export function useBranchName(workspaceId: string, issueId: string) {
  return useQuery({
    queryKey: branchKeys.issue(workspaceId, issueId),
    queryFn: () => integrationsApi.getBranchName(workspaceId, issueId),
    enabled: !!workspaceId && !!issueId,
    staleTime: 1000 * 60 * 60,
    gcTime: 1000 * 60 * 60 * 24,
  });
}

export default BranchSuggestion;
